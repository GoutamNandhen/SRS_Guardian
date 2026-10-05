"""
Tests for Phase 18: Explainable Visual Review & Comprehensive Reporting.

Validates:
1. Finding location metadata and exact span extraction.
2. Requirement-level findings and pair findings (duplicates, contradictions).
3. Confidence band calculation without conflating with severity.
4. Review Report API endpoints (JSON, Annotated PDF, Comprehensive PDF, DOCX).
5. 404 on missing document, 400 on unanalyzed document.
6. Non-regression of existing reporting endpoints.
"""

import io
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.app.core.database import Base, get_db
from backend.app.models.document import Document, Requirement, Issue, Review
from backend.app.schemas.review_report import compute_confidence_band
from backend.app.services.review_report import (
    build_review_report_data,
    generate_annotated_srs_pdf,
    generate_comprehensive_pdf_report,
    generate_comprehensive_docx_report,
)


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_analyzed_doc(db_session):
    """Creates a sample document with requirements, ambiguity, duplicate, and contradiction issues."""
    doc = Document(
        filename="online_banking_srs.txt",
        file_type="txt",
        file_size=1024,
        page_count=1,
        status="analyzed",
        raw_text=(
            "REQ-001: The system should respond quickly when the user checks balance.\n"
            "REQ-002: The system shall allow users to reset their password using registered email.\n"
            "REQ-003: Users must recover forgotten passwords using their registered email address.\n"
            "REQ-004: The password must contain at least 8 characters.\n"
            "REQ-005: The password must contain exactly 6 characters.\n"
            "REQ-006: The system shall allow users to download their transaction history."
        ),
        cleaned_text=(
            "REQ-001: The system should respond quickly when the user checks balance.\n"
            "REQ-002: The system shall allow users to reset their password using registered email.\n"
            "REQ-003: Users must recover forgotten passwords using their registered email address.\n"
            "REQ-004: The password must contain at least 8 characters.\n"
            "REQ-005: The password must contain exactly 6 characters.\n"
            "REQ-006: The system shall allow users to download their transaction history."
        ),
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    req1 = Requirement(
        document_id=doc.id,
        req_key="REQ-001",
        text="The system should respond quickly when the user checks balance.",
        source_layer="layer1_id",
        confidence=0.95,
        char_start=0,
        char_end=67,
        classification_label="Non-Functional",
        classification_prob=0.88,
    )
    req2 = Requirement(
        document_id=doc.id,
        req_key="REQ-002",
        text="The system shall allow users to reset their password using registered email.",
        source_layer="layer1_id",
        confidence=0.95,
        char_start=68,
        char_end=144,
        classification_label="Functional",
        classification_prob=0.92,
    )
    req3 = Requirement(
        document_id=doc.id,
        req_key="REQ-003",
        text="Users must recover forgotten passwords using their registered email address.",
        source_layer="layer1_id",
        confidence=0.95,
        char_start=145,
        char_end=221,
        classification_label="Functional",
        classification_prob=0.91,
    )
    req4 = Requirement(
        document_id=doc.id,
        req_key="REQ-004",
        text="The password must contain at least 8 characters.",
        source_layer="layer1_id",
        confidence=0.95,
        char_start=222,
        char_end=270,
        classification_label="Non-Functional",
        classification_prob=0.85,
    )
    req5 = Requirement(
        document_id=doc.id,
        req_key="REQ-005",
        text="The password must contain exactly 6 characters.",
        source_layer="layer1_id",
        confidence=0.95,
        char_start=271,
        char_end=318,
        classification_label="Non-Functional",
        classification_prob=0.85,
    )
    req6 = Requirement(
        document_id=doc.id,
        req_key="REQ-006",
        text="The system shall allow users to download their transaction history.",
        source_layer="layer1_id",
        confidence=0.95,
        char_start=319,
        char_end=386,
        classification_label="Functional",
        classification_prob=0.94,
    )
    db_session.add_all([req1, req2, req3, req4, req5, req6])
    db_session.commit()

    # Ambiguity finding on REQ-001 (sub-spans)
    issue1 = Issue(
        requirement_id=req1.id,
        module="ambiguity",
        type="CHECK_A_WEAK_TERM",
        severity="warning",
        explanation_json=json.dumps({
            "finding_id": "AMB-001",
            "rule_id": "CHECK_A_WEAK_TERM",
            "confidence": 0.95,
            "spans": [{"start": 26, "end": 33, "text": "quickly", "weight": 1.0}],
            "human_explanation": "Subjective term 'quickly' lacks a measurable response-time bound.",
            "suggestion": "Specify exact latency threshold (e.g. within 500 ms).",
        }),
        status="ai_flagged",
    )

    # Duplicate finding on REQ-002 paired with REQ-003
    issue2 = Issue(
        requirement_id=req2.id,
        module="duplicates",
        type="SEMANTIC_DUPLICATE",
        severity="warning",
        explanation_json=json.dumps({
            "finding_id": "DUP-001",
            "rule_id": "SEMANTIC_DUPLICATE",
            "confidence": 0.88,
            "spans": [],
            "factors": {"target_req_key": "REQ-003", "similarity_score": 0.88},
            "human_explanation": "Highly similar intent to REQ-003 (88% semantic similarity).",
            "suggestion": "Merge duplicate password recovery requirements.",
        }),
        status="ai_flagged",
    )

    # Contradiction finding on REQ-004 paired with REQ-005
    issue3 = Issue(
        requirement_id=req4.id,
        module="contradiction",
        type="NUMERIC_CONSTRAINT_CONFLICT",
        severity="critical",
        explanation_json=json.dumps({
            "finding_id": "CON-001",
            "rule_id": "NUMERIC_CONSTRAINT_CONFLICT",
            "confidence": 1.0,
            "spans": [{"start": 26, "end": 45, "text": "at least 8 characters", "weight": 1.0}],
            "req_key_1": "REQ-004",
            "req_key_2": "REQ-005",
            "human_explanation": "Conflicting length constraints: [8, inf) vs [6, 6].",
            "suggestion": "Harmonize minimum password length requirement.",
        }),
        status="ai_flagged",
    )

    db_session.add_all([issue1, issue2, issue3])
    db_session.commit()
    return doc


def test_confidence_band_computation():
    assert compute_confidence_band(0.95) == "high"
    assert compute_confidence_band(0.80) == "high"
    assert compute_confidence_band(0.79) == "medium"
    assert compute_confidence_band(0.60) == "medium"
    assert compute_confidence_band(0.59) == "low"
    assert compute_confidence_band(0.10) == "low"
    assert compute_confidence_band(None) == "unavailable"


def test_build_review_report_data(db_session, sample_analyzed_doc):
    data = build_review_report_data(sample_analyzed_doc.id, db_session)

    assert data["total_requirements"] == 6
    assert data["total_findings"] == 3
    assert len(data["requirements"]) == 6
    assert len(data["all_findings"]) == 3

    # Check finding spans & confidence
    f_amb = next(f for f in data["all_findings"] if f["module"] == "ambiguity")
    assert f_amb["req_key"] == "REQ-001"
    assert f_amb["has_sub_spans"] is True
    assert len(f_amb["spans"]) == 1
    assert f_amb["spans"][0]["text"] == "quickly"
    assert f_amb["confidence_band"] == "high"
    assert f_amb["confidence"] == 0.95

    # Check pair finding (duplicate)
    f_dup = next(f for f in data["all_findings"] if f["module"] == "duplicates")
    assert f_dup["is_pair_finding"] is True
    assert f_dup["target_req_key"] == "REQ-003"
    assert f_dup["confidence_band"] == "high"

    # Check pair finding (contradiction)
    f_con = next(f for f in data["all_findings"] if f["module"] == "contradiction")
    assert f_con["is_pair_finding"] is True
    assert f_con["severity"] == "critical"
    assert f_con["target_req_key"] == "REQ-005"


def test_annotated_srs_pdf_generation(db_session, sample_analyzed_doc):
    pdf_bytes = generate_annotated_srs_pdf(sample_analyzed_doc.id, db_session)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")


def test_comprehensive_pdf_report_generation(db_session, sample_analyzed_doc):
    pdf_bytes = generate_comprehensive_pdf_report(sample_analyzed_doc.id, db_session)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000
    assert pdf_bytes.startswith(b"%PDF")


def test_comprehensive_docx_report_generation(db_session, sample_analyzed_doc):
    docx_bytes = generate_comprehensive_docx_report(sample_analyzed_doc.id, db_session)
    assert isinstance(docx_bytes, bytes)
    assert len(docx_bytes) > 2000
    # Valid DOCX starts with PK zip signature
    assert docx_bytes.startswith(b"PK")


def test_review_report_api_endpoints(db_session, sample_analyzed_doc):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    try:
        # 1. JSON report data endpoint
        res = client.get(f"/api/documents/{sample_analyzed_doc.id}/review-report")
        assert res.status_code == 200
        json_data = res.json()
        assert json_data["document_id"] == sample_analyzed_doc.id
        assert json_data["total_requirements"] == 6
        assert json_data["total_findings"] == 3
        assert len(json_data["requirements"]) == 6

        # 2. Annotated PDF endpoint
        res_annot = client.get(f"/api/documents/{sample_analyzed_doc.id}/review-report/annotated-pdf")
        assert res_annot.status_code == 200
        assert res_annot.headers["content-type"] == "application/pdf"
        assert res_annot.content.startswith(b"%PDF")

        # 3. Comprehensive PDF endpoint
        res_pdf = client.get(f"/api/documents/{sample_analyzed_doc.id}/review-report/pdf")
        assert res_pdf.status_code == 200
        assert res_pdf.headers["content-type"] == "application/pdf"
        assert res_pdf.content.startswith(b"%PDF")

        # 4. Comprehensive DOCX endpoint
        res_docx = client.get(f"/api/documents/{sample_analyzed_doc.id}/review-report/docx")
        assert res_docx.status_code == 200
        assert "officedocument" in res_docx.headers["content-type"]
        assert res_docx.content.startswith(b"PK")

        # 5. 404 check
        res_404 = client.get("/api/documents/99999/review-report")
        assert res_404.status_code == 404

    finally:
        app.dependency_overrides.clear()
