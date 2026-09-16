import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from backend.app.main import app

client = TestClient(app)


def test_document_lifecycle():
    sample_path = Path("data/test/sample_srs.txt")
    assert sample_path.exists()

    # 1. Upload document
    with open(sample_path, "rb") as f:
        upload_resp = client.post(
            "/api/documents/upload",
            files={"file": ("sample_srs.txt", f, "text/plain")},
        )
    assert upload_resp.status_code == 201
    doc_data = upload_resp.json()
    doc_id = doc_data["id"]
    assert doc_data["filename"] == "sample_srs.txt"
    assert doc_data["file_type"] == "txt"
    assert doc_data["status"] == "uploaded"
    assert doc_data["version"] == "v1.0"
    assert "ONLINE BANKING SYSTEM" in doc_data["cleaned_text"]

    # 2. List documents
    list_resp = client.get("/api/documents")
    assert list_resp.status_code == 200
    docs_list = list_resp.json()
    assert any(d["id"] == doc_id for d in docs_list)

    # 3. Get document detail
    detail_resp = client.get(f"/api/documents/{doc_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == doc_id

    # 4. Extract requirements
    extract_resp = client.post(f"/api/documents/{doc_id}/extract")
    assert extract_resp.status_code == 200
    extract_data = extract_resp.json()
    assert extract_data["document_id"] == doc_id
    assert extract_data["status"] == "extracted"
    assert extract_data["extracted_count"] == 6
    assert len(extract_data["requirements"]) == 6
    assert extract_data["requirements"][0]["req_key"] == "REQ-001"

    # 5. Get document requirements
    reqs_resp = client.get(f"/api/documents/{doc_id}/requirements")
    assert reqs_resp.status_code == 200
    reqs = reqs_resp.json()
    assert len(reqs) == 6
    assert reqs[0]["req_key"] == "REQ-001"
    assert reqs[5]["req_key"] == "REQ-006"

    # 6. Delete document
    delete_resp = client.delete(f"/api/documents/{doc_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["status"] == "deleted"

    # 7. Verify 404 after deletion
    get_again = client.get(f"/api/documents/{doc_id}")
    assert get_again.status_code == 404


def test_upload_invalid_file(tmp_path):
    invalid_file = tmp_path / "bad.xyz"
    invalid_file.write_text("random content")

    with open(invalid_file, "rb") as f:
        resp = client.post(
            "/api/documents/upload",
            files={"file": ("bad.xyz", f, "application/octet-stream")},
        )
    assert resp.status_code == 400
    assert "Unsupported file format" in resp.json()["detail"]


def test_nonexistent_document_404():
    resp = client.get("/api/documents/999999")
    assert resp.status_code == 404

    extract_resp = client.post("/api/documents/999999/extract")
    assert extract_resp.status_code == 404

    req_resp = client.get("/api/documents/999999/requirements")
    assert req_resp.status_code == 404
