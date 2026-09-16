import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.ml.embeddings import (
    encode,
    compute_text_hash,
    get_cached_embedding,
)
from backend.app.ml.duplicates import (
    find_duplicates,
    attribute_similarity,
    extract_key_phrases,
)
from backend.app.models.document import Document, Requirement
from backend.app.core.database import get_db, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

client = TestClient(app)


def test_embedding_caching():
    text = "The system shall allow users to download transaction history in CSV format."
    text_hash = compute_text_hash(text)

    # First encode
    emb1 = encode([text])[0]
    assert emb1.shape == (384,)

    # Verify cached on disk / in memory
    cached = get_cached_embedding(text)
    assert cached is not None
    assert cached.shape == (384,)

    # Second encode should yield identical vector
    emb2 = encode([text])[0]
    assert (emb1 == emb2).all()


def test_key_phrase_extraction():
    text = "The system shall allow users to reset their password using their registered email."
    phrases = extract_key_phrases(text)
    phrase_texts = [p.text.lower() for p in phrases]

    assert any("password" in p for p in phrase_texts)
    assert any("email" in p for p in phrase_texts)


def test_find_duplicates_detected_and_explained():
    reqs = [
        {
            "id": 2,
            "req_key": "REQ-002",
            "text": "The system shall allow users to reset their password using their registered email.",
        },
        {
            "id": 3,
            "req_key": "REQ-003",
            "text": "Users must recover forgotten passwords using their registered email address.",
        },
    ]

    duplicates, total_checked = find_duplicates(reqs, threshold=0.80)
    assert total_checked == 1
    assert len(duplicates) == 1

    dup = duplicates[0]
    assert dup["requirement_id_1"] == 2
    assert dup["requirement_id_2"] == 3
    assert dup["similarity_score"] >= 0.80
    assert dup["is_potential_duplicate"] is True

    # Unified explanation schema contract checks
    explanation = dup["explanation"]
    assert explanation["module"] == "duplicates"
    assert explanation["method"] == "embedding_similarity"
    assert explanation["rule_id"] == "SEMANTIC_DUPLICATE"
    assert "POTENTIAL duplicate" in explanation["human_explanation"]
    assert "suggestion" in explanation
    assert len(explanation["factors"]) > 0
    assert len(explanation["spans"]) > 0

    # Aligned phrases checks
    aligned = dup["aligned_phrases"]
    assert len(aligned) > 0
    aligned_str = " ".join([f"{a['phrase_1']} {a['phrase_2']}" for a in aligned]).lower()
    assert "email" in aligned_str or "password" in aligned_str


def test_find_duplicates_no_false_positive():
    reqs = [
        {
            "id": 2,
            "req_key": "REQ-002",
            "text": "The system shall allow users to reset their password using their registered email.",
        },
        {
            "id": 4,
            "req_key": "REQ-004",
            "text": "The password must contain at least 8 characters.",
        },
        {
            "id": 6,
            "req_key": "REQ-006",
            "text": "The system shall allow users to download their transaction history.",
        },
    ]

    duplicates, total_checked = find_duplicates(reqs, threshold=0.80)
    assert total_checked == 3
    assert len(duplicates) == 0


def test_candidate_blocking_over_50_requirements():
    # 52 requirements with distinct vocabulary to test blocking without pairwise bottleneck
    topics = [
        "encryption", "billing", "shipping", "analytics", "compliance",
        "monitoring", "inventory", "checkout", "localization", "federation",
        "caching", "indexing", "compression", "throttling", "auditing",
        "serialization", "telemetry", "profiling", "clustering", "replication",
        "migration", "dispatching", "sanitization", "rendering", "pagination",
        "orchestration", "aggregation", "synchronization", "ingestion", "archival"
    ]
    reqs = []
    for i, topic in enumerate(topics):
        reqs.append(
            {
                "id": i + 100,
                "req_key": f"REQ-{topic.upper()}",
                "text": f"The system shall support {topic} configuration parameters.",
            }
        )
    # Add another 20 unique topics to reach > 50 requirements
    for i in range(22):
        reqs.append(
            {
                "id": i + 150,
                "req_key": f"REQ-SYS-{i}",
                "text": f"Subsystem component alpha-{i} operates independently.",
            }
        )

    # Add duplicate pair
    reqs.append(
        {
            "id": 201,
            "req_key": "REQ-201",
            "text": "The system shall allow users to reset their password using their registered email.",
        }
    )
    reqs.append(
        {
            "id": 202,
            "req_key": "REQ-202",
            "text": "Users must recover forgotten passwords using their registered email address.",
        }
    )

    duplicates, total_checked = find_duplicates(reqs, threshold=0.80)
    # Total requirements = 30 + 22 + 2 = 54 (>50)
    # Candidate blocking filters out pairs without shared content words
    assert total_checked < (54 * 53 // 2)
    dup_keys = [(d["req_key_1"], d["req_key_2"]) for d in duplicates]
    assert ("REQ-201", "REQ-202") in dup_keys



def test_api_duplicates_endpoint():
    # In-memory test database for isolated API endpoint testing
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
            filename="banking_test.txt",
            file_type="txt",
            file_size=500,
            page_count=1,
            status="extracted",
            raw_text="sample",
            cleaned_text="sample",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        r1 = Requirement(
            document_id=doc.id,
            req_key="REQ-002",
            text="The system shall allow users to reset their password using their registered email.",
            source_layer="explicit_id",
            confidence=1.0,
            char_start=0,
            char_end=80,
        )
        r2 = Requirement(
            document_id=doc.id,
            req_key="REQ-003",
            text="Users must recover forgotten passwords using their registered email address.",
            source_layer="explicit_id",
            confidence=1.0,
            char_start=81,
            char_end=160,
        )
        r3 = Requirement(
            document_id=doc.id,
            req_key="REQ-006",
            text="The system shall allow users to download their transaction history.",
            source_layer="explicit_id",
            confidence=1.0,
            char_start=161,
            char_end=230,
        )
        db.add_all([r1, r2, r3])
        db.commit()

        # Call GET /api/documents/{id}/duplicates
        response = client.get(f"/api/documents/{doc.id}/duplicates")
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == doc.id
        assert data["duplicate_pairs_count"] == 1
        assert len(data["duplicates"]) == 1

        dup_item = data["duplicates"][0]
        assert dup_item["req_key_1"] == "REQ-002"
        assert dup_item["req_key_2"] == "REQ-003"
        assert dup_item["similarity_score"] >= 0.80
        assert "POTENTIAL duplicate" in dup_item["explanation"]["human_explanation"]
    finally:
        app.dependency_overrides.clear()
