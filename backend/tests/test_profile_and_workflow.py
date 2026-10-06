"""
SRS Guardian — Phase 18.2 Integration Tests
Tests:
1. User Profile API CRUD & persistence (GET/PUT /api/profile)
2. Document analysis compact breakdown counts (needs_attention, critical, warning, no_issues)
3. Reviewer profile integration in Review Report API, DOCX, and PDF reports
4. Verification that empty profile details default cleanly without placeholder data
"""

import io
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.user_profile import UserProfile
from backend.app.models.document import Document

client = TestClient(app)


def test_user_profile_crud():
    # 1. Reset / Fetch initial profile
    res = client.get("/api/profile")
    assert res.status_code == 200
    data = res.json()
    assert "id" in data
    assert "full_name" in data

    # 2. Update profile with real details
    update_payload = {
        "full_name": "Sarah Connor",
        "email": "sarah.connor@cyberdyne.org",
        "organization": "Systems Verification Laboratory",
        "role": "Chief Verification Officer",
        "phone": "+1 555-0144",
    }
    put_res = client.put("/api/profile", json=update_payload)
    assert put_res.status_code == 200
    put_data = put_res.json()
    assert put_data["full_name"] == "Sarah Connor"
    assert put_data["email"] == "sarah.connor@cyberdyne.org"
    assert put_data["organization"] == "Systems Verification Laboratory"
    assert put_data["role"] == "Chief Verification Officer"
    assert put_data["phone"] == "+1 555-0144"

    # 3. Verify persistence with a new GET request
    get_res = client.get("/api/profile")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["full_name"] == "Sarah Connor"
    assert get_data["organization"] == "Systems Verification Laboratory"

    # 4. Clean up / reset to empty values
    reset_res = client.put(
        "/api/profile",
        json={"full_name": "", "email": "", "organization": "", "role": "", "phone": ""},
    )
    assert reset_res.status_code == 200
    reset_data = reset_res.json()
    assert reset_data["full_name"] is None
    assert reset_data["email"] is None


def test_document_analysis_compact_counts():
    # Ingest a small test document to verify breakdown counts
    test_content = (
        "REQ-001: The system shall respond quickly.\n"
        "REQ-002: The system shall allow users to reset password.\n"
        "REQ-003: The system shall allow users to download transaction history.\n"
    )
    upload_res = client.post(
        "/api/documents/upload",
        files={"file": ("test_compact_srs.txt", io.BytesIO(test_content.encode("utf-8")), "text/plain")},
    )
    assert upload_res.status_code in (200, 201)
    doc_id = upload_res.json()["id"]

    try:
        # Run analyze
        analyze_res = client.post(f"/api/documents/{doc_id}/analyze")
        assert analyze_res.status_code == 200
        data = analyze_res.json()

        assert data["document_id"] == doc_id
        assert data["requirements_count"] == 3
        assert data["filename"] == "test_compact_srs.txt"
        assert "needs_attention_count" in data
        assert "critical_count" in data
        assert "warning_count" in data
        assert "no_issues_count" in data

        # Check arithmetic invariants
        assert data["needs_attention_count"] + data["no_issues_count"] == data["requirements_count"]
        assert data["needs_attention_count"] >= 1  # REQ-001 has ambiguity 'quickly'
    finally:
        client.delete(f"/api/documents/{doc_id}")


def test_reviewer_profile_in_review_reports():
    # 1. Set specific profile
    client.put(
        "/api/profile",
        json={
            "full_name": "Marcus Aurelius",
            "email": "marcus@rome.org",
            "organization": "Imperial Systems Audit",
            "role": "Principal Quality Inspector",
            "phone": "+1 555-0100",
        },
    )

    # 2. Ingest & analyze document
    test_content = (
        "REQ-001: The system shall authenticate users securely.\n"
    )
    upload_res = client.post(
        "/api/documents/upload",
        files={"file": ("test_reviewer_doc.txt", io.BytesIO(test_content.encode("utf-8")), "text/plain")},
    )
    assert upload_res.status_code in (200, 201)
    doc_id = upload_res.json()["id"]

    try:
        client.post(f"/api/documents/{doc_id}/analyze")

        # 3. Test review report JSON
        report_res = client.get(f"/api/documents/{doc_id}/review-report")
        assert report_res.status_code == 200
        report_data = report_res.json()
        assert report_data["reviewer_profile"] is not None
        assert report_data["reviewer_profile"]["full_name"] == "Marcus Aurelius"
        assert report_data["reviewer_profile"]["role"] == "Principal Quality Inspector"
        assert report_data["reviewer_profile"]["organization"] == "Imperial Systems Audit"

        # 4. Test DOCX generation
        docx_res = client.get(f"/api/documents/{doc_id}/review-report/docx")
        assert docx_res.status_code == 200
        assert len(docx_res.content) > 1000

        # 5. Test PDF generation
        pdf_res = client.get(f"/api/documents/{doc_id}/review-report/pdf")
        assert pdf_res.status_code == 200
        assert pdf_res.content.startswith(b"%PDF")
    finally:
        client.delete(f"/api/documents/{doc_id}")
        # Reset profile
        client.put(
            "/api/profile",
            json={"full_name": "", "email": "", "organization": "", "role": "", "phone": ""},
        )
