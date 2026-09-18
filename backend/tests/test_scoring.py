import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.app.core.database import get_db, Base
from backend.app.models.document import Document, Requirement
from backend.app.nlp.ambiguity import analyze_ambiguity
from backend.app.nlp.readability import analyze_readability
from backend.app.nlp.scoring import (
    score_requirement,
    score_document,
    load_score_weights,
)

client = TestClient(app)


def test_load_score_weights():
    weights = load_score_weights()
    assert "base_score" in weights
    assert "penalties" in weights
    assert weights["base_score"] == 100.0
    assert "CHECK_A_WEAK_TERM" in weights["penalties"]
    assert "CHECK_B_WEAK_MODAL" in weights["penalties"]


def test_clean_requirement_scoring():
    text = "The system shall allow users to download their transaction history."
    req_score = score_requirement(
        req_key="REQ-006",
        text=text,
        ambiguity_findings=[],
        readability_metrics=None,
        is_duplicate=False,
    )
    assert req_score.overall_score == 100.0
    assert len(req_score.waterfall) == 1
    assert req_score.waterfall[0].current_score == 100.0
    assert req_score.issues_count == 0
    for sub, val in req_score.sub_scores.items():
        assert val == 100.0


def test_ambiguous_requirement_waterfall():
    # REQ-001: "The system should respond quickly when the user checks the account balance."
    text = "The system should respond quickly when the user checks the account balance."
    findings = analyze_ambiguity(text)
    metrics = analyze_readability(text)

    # Should detect "quickly" (CHECK_A_WEAK_TERM, -20) and "should" (CHECK_B_WEAK_MODAL, -15)
    req_score = score_requirement(
        req_key="REQ-001",
        text=text,
        ambiguity_findings=findings,
        readability_metrics=metrics,
        is_duplicate=False,
    )

    # Expected deductions: 100 - 20 - 15 = 65.0
    assert req_score.overall_score == 65.0
    assert len(req_score.waterfall) == 3  # Base + 2 findings

    assert req_score.waterfall[0].step_name == "Base Score"
    assert req_score.waterfall[0].current_score == 100.0

    steps = [w.rule_id for w in req_score.waterfall[1:]]
    assert "CHECK_A_WEAK_TERM" in steps
    assert "CHECK_B_WEAK_MODAL" in steps

    # Final waterfall step current score matches overall score
    assert req_score.waterfall[-1].current_score == 65.0

    # Sub-scores impacted
    assert req_score.sub_scores["ambiguity"] < 100.0
    assert req_score.sub_scores["testability"] < 100.0


def test_duplicate_requirement_penalty():
    text = "Users must recover forgotten passwords using their registered email address."
    req_score = score_requirement(
        req_key="REQ-003",
        text=text,
        ambiguity_findings=[],
        readability_metrics=None,
        is_duplicate=True,
        duplicate_info={"target_req_key": "REQ-002", "similarity_score": 0.8218},
    )

    # 100 - 15 = 85.0
    assert req_score.overall_score == 85.0
    assert req_score.sub_scores["consistency"] == 50.0  # Penalized consistency
    assert any(w.rule_id == "SEMANTIC_DUPLICATE" for w in req_score.waterfall)


def test_score_clamping_floor_zero():
    # Artificially apply many findings
    text = "It should quickly and easily process this if necessary."
    findings = analyze_ambiguity(text)
    metrics = analyze_readability(text)

    req_score = score_requirement(
        req_key="REQ-BAD",
        text=text,
        ambiguity_findings=findings,
        readability_metrics=metrics,
        is_duplicate=True,
    )
    assert 0.0 <= req_score.overall_score <= 100.0
    for sub, val in req_score.sub_scores.items():
        assert 0.0 <= val <= 100.0


def test_document_quality_summary_aggregation():
    r1 = score_requirement("REQ-001", "text 1", ambiguity_findings=analyze_ambiguity("The system should respond quickly."))
    r2 = score_requirement("REQ-002", "text 2", ambiguity_findings=[])
    r3 = score_requirement("REQ-003", "text 3", ambiguity_findings=[], is_duplicate=True)

    summary = score_document([r1, r2, r3], document_id=1)
    assert summary.total_requirements == 3
    assert summary.min_score <= summary.median_score <= summary.max_score
    assert summary.distribution["90-100"] == 1  # r2 is 100.0
    assert summary.worst_requirements[0]["req_key"] == "REQ-001"  # Lowest score


def test_api_document_quality_endpoint():
    # Setup in-memory SQLite DB
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        db = TestingSessionLocal()
        doc = Document(
            filename="sample_scoring.txt",
            file_type="txt",
            file_size=300,
            page_count=1,
            status="extracted",
            raw_text="sample",
            cleaned_text="sample",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        req1 = Requirement(
            document_id=doc.id,
            req_key="REQ-001",
            text="The system should respond quickly when the user checks the account balance.",
            source_layer="explicit_id",
            confidence=1.0,
            char_start=0,
            char_end=80,
        )
        req2 = Requirement(
            document_id=doc.id,
            req_key="REQ-006",
            text="The system shall allow users to download their transaction history.",
            source_layer="explicit_id",
            confidence=1.0,
            char_start=81,
            char_end=150,
        )
        db.add_all([req1, req2])
        db.commit()

        # Call GET /api/documents/{id}/quality
        resp = client.get(f"/api/documents/{doc.id}/quality")
        assert resp.status_code == 200
        data = resp.json()

        assert data["document_id"] == doc.id
        assert data["total_requirements"] == 2
        assert "mean_score" in data
        assert "worst_requirements" in data
        assert len(data["requirements"]) == 2

        # Check REQ-001 waterfall in response (100 - 20 weak term - 15 weak modal - 5 ISO structure = 60.0)
        req1_data = next(r for r in data["requirements"] if r["req_key"] == "REQ-001")
        assert req1_data["overall_score"] == 60.0
        assert len(req1_data["waterfall"]) >= 3
        assert req1_data["waterfall"][0]["step_name"] == "Base Score"

    finally:
        app.dependency_overrides.clear()
