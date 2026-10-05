import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.config import settings
from backend.app.nlp.gherkin import generate_gherkin_skeleton
from backend.app.core.database import SessionLocal
from backend.app.models.document import Document, Requirement

client = TestClient(app)


def test_gherkin_event_driven():
    text = "When the user clicks submit, the system shall validate the email address."
    result = generate_gherkin_skeleton(text)
    assert result["enabled"] is True
    assert result["source"] == "ears_rule"
    assert result["ears_pattern"] == "event_driven"
    gherkin = result["gherkin_scenarios"]
    assert "When The user clicks submit" in gherkin or "When the user clicks submit" in gherkin.lower()
    assert "Then the system shall validate the email address" in gherkin


def test_gherkin_ubiquitous():
    text = "The system shall allow users to download their transaction history."
    result = generate_gherkin_skeleton(text)
    assert result["enabled"] is True
    assert result["source"] == "ears_rule"
    assert result["ears_pattern"] == "ubiquitous"
    gherkin = result["gherkin_scenarios"]
    assert "Feature: The System Verification" in gherkin
    assert "Given the system is initialized and ready" in gherkin
    assert "Then the system shall allow users to download their transaction history" in gherkin


def test_gherkin_state_driven():
    text = "While in maintenance mode, the system shall reject all incoming transaction requests."
    result = generate_gherkin_skeleton(text)
    assert result["enabled"] is True
    assert result["source"] == "ears_rule"
    assert result["ears_pattern"] == "state_driven"
    gherkin = result["gherkin_scenarios"]
    assert "in maintenance mode" in gherkin
    assert "reject all incoming transaction requests" in gherkin


def test_gherkin_unwanted_behavior():
    text = "If an invalid PIN is entered three times, then the system shall lock the account."
    result = generate_gherkin_skeleton(text)
    assert result["enabled"] is True
    assert result["source"] == "ears_rule"
    assert result["ears_pattern"] == "unwanted_behavior"
    gherkin = result["gherkin_scenarios"]
    assert "invalid PIN is entered three times" in gherkin
    assert "lock the account" in gherkin


def test_gherkin_optional_feature():
    text = "Where camera hardware is available, the system shall capture the user photo."
    result = generate_gherkin_skeleton(text)
    assert result["enabled"] is True
    assert result["source"] == "ears_rule"
    assert result["ears_pattern"] == "optional_feature"
    gherkin = result["gherkin_scenarios"]
    assert "camera hardware is available" in gherkin
    assert "capture the user photo" in gherkin


def test_gherkin_fallback_when_disabled():
    original_setting = settings.LLM_ENABLED
    try:
        settings.LLM_ENABLED = False
        text = "Quick response time."  # Non-conforming, lacks modal/system
        result = generate_gherkin_skeleton(text)
        assert result["enabled"] is True
        assert result["source"] == "fallback_rule"
        assert result["ears_pattern"] == "non_conforming"
        assert "Scenario: Satisfy requirement statement" in result["gherkin_scenarios"]
    finally:
        settings.LLM_ENABLED = original_setting


def test_adhoc_gherkin_api_endpoint():
    res = client.post(
        "/api/requirements/generate-gherkin",
        json={"requirement_text": "The system shall allow users to reset their password using their registered email."},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["enabled"] is True
    assert data["source"] == "ears_rule"
    assert data["ears_pattern"] == "ubiquitous"
    assert "Feature: The System Verification" in data["gherkin_scenarios"]


def test_requirement_gherkin_api_endpoint():
    db = SessionLocal()
    try:
        doc = Document(filename="test_gherkin.txt", file_type="txt", file_size=100, page_count=1, raw_text="...", cleaned_text="...")
        db.add(doc)
        db.commit()
        db.refresh(doc)

        req = Requirement(
            document_id=doc.id,
            req_key="REQ-002",
            text="The system shall allow users to reset their password using their registered email.",
            source_layer="layer1_id",
            confidence=0.95,
            char_start=0,
            char_end=80,
            classification_label="Functional",
        )
        db.add(req)
        db.commit()
        db.refresh(req)

        res = client.post(f"/api/requirements/{req.id}/generate-gherkin")
        assert res.status_code == 200
        data = res.json()
        assert data["requirement_id"] == req.id
        assert data["source"] == "ears_rule"
        assert "reset their password" in data["gherkin_scenarios"]
    finally:
        db.close()
