import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.app.core.database import get_db, Base
from backend.app.models.document import Document, Requirement, Issue, Review


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


def _setup_analyzed_doc(db_session) -> int:
    doc_text = (
        "ONLINE BANKING SYSTEM\n"
        "REQ-001: The system should respond quickly when the user checks the account balance.\n"
        "REQ-002: The system shall allow users to reset their password using their registered email.\n"
        "REQ-003: Users must recover forgotten passwords using their registered email address.\n"
        "REQ-006: The system shall allow users to download their transaction history.\n"
    )
    doc = Document(
        filename="banking_report_test.txt",
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

    # Analyze
    resp = client.post(f"/api/documents/{doc.id}/analyze")
    assert resp.status_code == 200

    # Perform a human review action on one issue
    issues_resp = client.get(f"/api/documents/{doc.id}/issues")
    issues = issues_resp.json()
    if issues:
        first_issue = issues[0]
        client.post(
            f"/api/issues/{first_issue['id']}/review",
            json={"action": "accept", "note": "Verified by human engineer."},
        )

    return doc.id


def test_html_report_generation(db_session):
    doc_id = _setup_analyzed_doc(db_session)

    resp = client.get(f"/api/documents/{doc_id}/report?format=html")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    html = resp.text

    assert "<!DOCTYPE html>" in html
    assert "banking_report_test.txt" in html
    assert "SRS Guardian" in html
    assert "REQ-001" in html
    assert "REQ-002" in html
    assert "Quality Score" in html
    assert "Executive Quality Summary" in html
    assert "Verified by human engineer" in html


def test_csv_report_requirements(db_session):
    doc_id = _setup_analyzed_doc(db_session)

    resp = client.get(f"/api/documents/{doc_id}/report?format=csv&type=requirements")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "attachment" in resp.headers["content-disposition"]
    csv_text = resp.text

    lines = csv_text.strip().split("\r\n") if "\r\n" in csv_text else csv_text.strip().split("\n")
    header = lines[0]
    assert "req_id,req_key,classification,confidence,quality_score" in header
    # 1 header line + 4 requirement lines = 5 lines
    assert len(lines) == 5
    assert "REQ-001" in csv_text
    assert "REQ-006" in csv_text


def test_csv_report_issues(db_session):
    doc_id = _setup_analyzed_doc(db_session)

    resp = client.get(f"/api/documents/{doc_id}/report?format=csv&type=issues")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    csv_text = resp.text

    lines = csv_text.strip().split("\r\n") if "\r\n" in csv_text else csv_text.strip().split("\n")
    header = lines[0]
    assert "issue_id,req_key,module,rule_type,severity,status" in header
    assert len(lines) >= 3  # At least 2 ambiguity + duplicate issues
    assert "CHECK_A_WEAK_TERM" in csv_text or "CHECK_B_WEAK_MODAL" in csv_text
    assert "Verified by human engineer" in csv_text


def test_pdf_report_generation(db_session):
    doc_id = _setup_analyzed_doc(db_session)

    resp = client.get(f"/api/documents/{doc_id}/report?format=pdf")
    assert resp.status_code == 200
    assert "application/pdf" in resp.headers["content-type"]
    assert "attachment" in resp.headers["content-disposition"]
    pdf_bytes = resp.content

    # Validate PDF signature
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 1000


def test_report_nonexistent_document_404(db_session):
    resp = client.get("/api/documents/9999/report?format=html")
    assert resp.status_code == 404


def test_report_invalid_format_400(db_session):
    doc_id = _setup_analyzed_doc(db_session)
    resp = client.get(f"/api/documents/{doc_id}/report?format=docx")
    assert resp.status_code == 400
