import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.ml.clustering import (
    determine_optimal_clusters,
    extract_cluster_keywords,
    cluster_requirements,
)
from backend.app.core.database import SessionLocal
from backend.app.models.document import Document, Requirement

client = TestClient(app)


def test_determine_optimal_clusters():
    assert determine_optimal_clusters(0) == 1
    assert determine_optimal_clusters(1) == 1
    assert determine_optimal_clusters(2) == 2
    assert determine_optimal_clusters(3) == 2
    assert determine_optimal_clusters(5) == 3
    assert determine_optimal_clusters(8) == 4
    assert determine_optimal_clusters(50) <= 10


def test_cluster_empty():
    res = cluster_requirements([])
    assert res["total_requirements"] == 0
    assert res["num_clusters"] == 0
    assert res["clusters"] == []


def test_cluster_single_requirement():
    reqs = [{"id": 1, "req_key": "REQ-001", "text": "The system shall display balance."}]
    res = cluster_requirements(reqs)
    assert res["total_requirements"] == 1
    assert res["num_clusters"] == 1
    assert len(res["clusters"]) == 1
    assert res["clusters"][0]["size"] == 1


def test_cluster_sample_requirements():
    reqs = [
        {"id": 1, "req_key": "REQ-001", "text": "The system should respond quickly when the user checks the account balance."},
        {"id": 2, "req_key": "REQ-002", "text": "The system shall allow users to reset their password using their registered email."},
        {"id": 3, "req_key": "REQ-003", "text": "Users must recover forgotten passwords using their registered email address."},
        {"id": 4, "req_key": "REQ-004", "text": "The password must contain at least 8 characters."},
        {"id": 5, "req_key": "REQ-005", "text": "The password must contain exactly 6 characters."},
        {"id": 6, "req_key": "REQ-006", "text": "The system shall allow users to download their transaction history."},
    ]
    res = cluster_requirements(reqs, n_clusters=3)
    assert res["total_requirements"] == 6
    assert res["num_clusters"] == 3
    assert len(res["clusters"]) == 3

    # All 6 requirements must be partitioned exactly
    clustered_keys = set()
    for c in res["clusters"]:
        assert c["size"] > 0
        assert len(c["keywords"]) > 0
        assert len(c["label"]) > 0
        for r in c["requirements"]:
            clustered_keys.add(r["req_key"])

    assert clustered_keys == {"REQ-001", "REQ-002", "REQ-003", "REQ-004", "REQ-005", "REQ-006"}


def test_api_document_clusters():
    db = SessionLocal()
    try:
        doc = Document(
            filename="test_clustering.txt",
            file_type="txt",
            file_size=200,
            page_count=1,
            raw_text="...",
            cleaned_text="...",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        r1 = Requirement(
            document_id=doc.id,
            req_key="REQ-001",
            text="The system shall allow users to reset their password.",
            source_layer="layer1_id",
            confidence=0.95,
            char_start=0,
            char_end=50,
        )
        r2 = Requirement(
            document_id=doc.id,
            req_key="REQ-002",
            text="Users must recover forgotten passwords using registered email.",
            source_layer="layer1_id",
            confidence=0.95,
            char_start=55,
            char_end=110,
        )
        r3 = Requirement(
            document_id=doc.id,
            req_key="REQ-003",
            text="The system shall download transaction statement as PDF.",
            source_layer="layer1_id",
            confidence=0.95,
            char_start=115,
            char_end=170,
        )
        db.add_all([r1, r2, r3])
        db.commit()

        res = client.get(f"/api/documents/{doc.id}/clusters")
        assert res.status_code == 200
        data = res.json()
        assert data["document_id"] == doc.id
        assert data["total_requirements"] == 3
        assert data["num_clusters"] >= 1
        assert len(data["clusters"]) >= 1
    finally:
        db.close()
