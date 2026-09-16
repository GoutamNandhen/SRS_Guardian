import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from backend.app.main import app
from backend.app.core.database import get_db, Base
from backend.app.models.document import Document, Requirement, Issue, Review
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

client = TestClient(app)


@pytest.fixture
def db_session():
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
    db = TestingSessionLocal()
    yield db
    db.close()
    app.dependency_overrides.clear()


def test_full_analyze_and_issues_workflow(db_session):
    # 1. Create document
    doc_text = (
        "ONLINE BANKING SYSTEM\n"
        "REQ-001: The system should respond quickly when the user checks the account balance.\n"
        "REQ-002: The system shall allow users to reset their password using their registered email.\n"
        "REQ-003: Users must recover forgotten passwords using their registered email address.\n"
        "REQ-006: The system shall allow users to download their transaction history.\n"
    )
    doc = Document(
        filename="banking.txt",
        file_type="txt",
        file_size=len(doc_text),
        page_count=1,
        status="uploaded",
        raw_text=doc_text,
        cleaned_text=doc_text,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    # 2. Trigger full analysis pipeline: POST /api/documents/{id}/analyze
    resp = client.post(f"/api/documents/{doc.id}/analyze")
    assert resp.status_code == 200
    data = resp.json()

    assert data["document_id"] == doc.id
    assert data["status"] == "analyzed"
    assert data["requirements_count"] == 4
    assert data["issues_count"] >= 3  # At least 2 ambiguity issues on REQ-001 + duplicate issues on REQ-002/003
    assert "quality_summary" in data

    # 3. Query all issues: GET /api/documents/{id}/issues
    issues_resp = client.get(f"/api/documents/{doc.id}/issues")
    assert issues_resp.status_code == 200
    all_issues = issues_resp.json()
    assert len(all_issues) == data["issues_count"]

    # Filter by module
    ambiguity_resp = client.get(f"/api/documents/{doc.id}/issues?module=ambiguity")
    assert ambiguity_resp.status_code == 200
    ambiguity_issues = ambiguity_resp.json()
    assert all(i["module"] == "ambiguity" for i in ambiguity_issues)

    # Filter by status
    flagged_resp = client.get(f"/api/documents/{doc.id}/issues?status_filter=ai_flagged")
    assert flagged_resp.status_code == 200
    assert len(flagged_resp.json()) == len(all_issues)

    # 4. Pick an issue to test human review: accept
    weak_term_issue = next(i for i in all_issues if i["type"] == "CHECK_A_WEAK_TERM")
    issue_id = weak_term_issue["id"]

    accept_resp = client.post(
        f"/api/issues/{issue_id}/review",
        json={"action": "accept", "note": "Confirmed: 'quickly' is non-verifiable."},
    )
    assert accept_resp.status_code == 200
    accepted_data = accept_resp.json()
    assert accepted_data["status"] == "accepted"
    assert accepted_data["is_human_reviewed"] is True
    assert len(accepted_data["reviews"]) == 1
    assert accepted_data["reviews"][0]["action"] == "accept"
    assert "Confirmed" in accepted_data["reviews"][0]["note"]

    # 5. Pick another issue to test edit action
    weak_modal_issue = next(i for i in all_issues if i["type"] == "CHECK_B_WEAK_MODAL")
    modal_issue_id = weak_modal_issue["id"]
    req_id = weak_modal_issue["requirement_id"]

    edit_resp = client.post(
        f"/api/issues/{modal_issue_id}/review",
        json={
            "action": "edit",
            "edited_text": "The system shall respond within 2.0 seconds when the user checks account balance.",
            "note": "Replaced 'should' with 'shall' and specified response time.",
        },
    )
    assert edit_resp.status_code == 200
    edited_data = edit_resp.json()
    assert edited_data["status"] == "edited"
    assert edited_data["is_human_reviewed"] is True

    # Verify requirement text was updated in DB
    updated_req = db_session.query(Requirement).filter(Requirement.id == req_id).first()
    assert "The system shall respond within 2.0 seconds" in updated_req.text

    # 6. Test reject action
    dup_issue = next((i for i in all_issues if i["type"] == "SEMANTIC_DUPLICATE"), None)
    if dup_issue:
        reject_resp = client.post(
            f"/api/issues/{dup_issue['id']}/review",
            json={"action": "reject", "note": "Not a duplicate in this operational context."},
        )
        assert reject_resp.status_code == 200
        assert reject_resp.json()["status"] == "rejected"

    # 7. Test requirement full detail endpoint: GET /api/requirements/{id}
    req_detail_resp = client.get(f"/api/requirements/{req_id}")
    assert req_detail_resp.status_code == 200
    req_detail = req_detail_resp.json()
    assert req_detail["id"] == req_id
    assert "quality_score" in req_detail
    assert "waterfall" in req_detail
    assert len(req_detail["issues"]) >= 1
    # Check that human reviewed status is reflected in issue
    assert any(i["is_human_reviewed"] for i in req_detail["issues"])
