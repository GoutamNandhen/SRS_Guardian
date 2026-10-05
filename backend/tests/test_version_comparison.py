import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.nlp.version_comparison import (
    compute_text_diff,
    compare_document_versions,
)
from backend.app.core.database import SessionLocal
from backend.app.models.document import Document, Requirement, Issue

client = TestClient(app)


def test_compute_text_diff():
    t1 = "The system should respond quickly."
    t2 = "The system shall respond within 500ms."
    diff = compute_text_diff(t1, t2)
    assert "[-should-]" in diff
    assert "[+shall+]" in diff
    assert "[-quickly.-]" in diff or "[-quickly-]" in diff


def test_compare_document_versions_lifecycle():
    db = SessionLocal()
    try:
        # Create Doc v1
        doc1 = Document(filename="srs_v1.txt", file_type="txt", file_size=100, page_count=1, raw_text="...", cleaned_text="...")
        db.add(doc1)
        db.commit()
        db.refresh(doc1)

        r1_v1 = Requirement(
            document_id=doc1.id,
            req_key="REQ-001",
            text="The system should respond quickly when the user checks account balance.",
            source_layer="layer1_id",
            confidence=0.95,
            char_start=0,
            char_end=70,
        )
        r2_v1 = Requirement(
            document_id=doc1.id,
            req_key="REQ-002",
            text="The system shall allow users to reset their password using registered email.",
            source_layer="layer1_id",
            confidence=0.95,
            char_start=75,
            char_end=150,
        )
        r3_v1 = Requirement(
            document_id=doc1.id,
            req_key="REQ-003",
            text="The legacy interface shall support obsolete protocol.",
            source_layer="layer1_id",
            confidence=0.95,
            char_start=155,
            char_end=210,
        )
        db.add_all([r1_v1, r2_v1, r3_v1])
        db.commit()
        db.refresh(r1_v1)

        # Add issue to r1_v1
        issue_v1 = Issue(
            requirement_id=r1_v1.id,
            module="ambiguity",
            type="AMB_WEAK_TERM",
            severity="warning",
            explanation_json='{"human_explanation": "Vague term quickly."}',
            status="ai_flagged",
        )
        db.add(issue_v1)
        db.commit()

        # Create Doc v2
        doc2 = Document(filename="srs_v2.txt", file_type="txt", file_size=100, page_count=1, raw_text="...", cleaned_text="...")
        db.add(doc2)
        db.commit()
        db.refresh(doc2)

        r1_v2 = Requirement(
            document_id=doc2.id,
            req_key="REQ-001",
            text="The system shall respond within 500ms when the user checks account balance.",
            source_layer="layer1_id",
            confidence=0.95,
            char_start=0,
            char_end=75,
        )
        r2_v2 = Requirement(
            document_id=doc2.id,
            req_key="REQ-002",
            text="The system shall allow users to reset their password using registered email.",
            source_layer="layer1_id",
            confidence=0.95,
            char_start=80,
            char_end=155,
        )
        r4_v2 = Requirement(
            document_id=doc2.id,
            req_key="REQ-004",
            text="The system shall encrypt all sensitive customer data at rest.",
            source_layer="layer1_id",
            confidence=0.95,
            char_start=160,
            char_end=220,
        )
        db.add_all([r1_v2, r2_v2, r4_v2])
        db.commit()

        res = compare_document_versions(doc1.id, doc2.id, db)
        assert res["total_v1"] == 3
        assert res["total_v2"] == 3
        assert res["modified_count"] == 1
        assert res["unchanged_count"] == 1
        assert res["removed_count"] == 1
        assert res["added_count"] == 1

        # Check modified REQ-001
        mod_item = next(i for i in res["items"] if i["req_key"] == "REQ-001")
        assert mod_item["status"] == "modified"
        assert mod_item["score_delta"] > 0
        assert len(mod_item["resolved_issues"]) >= 1

        # Check API endpoint
        api_res = client.get(f"/api/documents/{doc1.id}/compare/{doc2.id}")
        assert api_res.status_code == 200
        data = api_res.json()
        assert data["doc1_id"] == doc1.id
        assert data["doc2_id"] == doc2.id
        assert data["modified_count"] == 1
        assert data["added_count"] == 1
        assert data["removed_count"] == 1
        assert data["unchanged_count"] == 1
    finally:
        db.close()


def test_compare_not_found():
    res = client.get("/api/documents/99999/compare/88888")
    assert res.status_code == 404
