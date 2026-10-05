from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.services.llm import (
    suggest_rewrite,
    generate_gherkin,
    _compute_cache_key,
    _CACHE,
)
from backend.app.core.database import SessionLocal
from backend.app.models.document import Document, Requirement

client = TestClient(app)


def test_suggest_rewrite_disabled():
    original_setting = settings.LLM_ENABLED
    try:
        settings.LLM_ENABLED = False
        res = suggest_rewrite("The system should respond quickly when checking balance.")
        assert res["enabled"] is False
        assert res["cached"] is False
        assert res["suggested_text"] is None
        assert "disabled" in res["rationale"].lower()
    finally:
        settings.LLM_ENABLED = original_setting


def test_generate_gherkin_disabled():
    original_setting = settings.LLM_ENABLED
    try:
        settings.LLM_ENABLED = False
        res = generate_gherkin("The system shall allow users to download transaction history.")
        assert res["enabled"] is False
        assert res["cached"] is False
        assert res["gherkin_scenarios"] is None
        assert "disabled" in res["error"].lower()
    finally:
        settings.LLM_ENABLED = original_setting


def test_suggest_rewrite_cached():
    original_setting = settings.LLM_ENABLED
    try:
        settings.LLM_ENABLED = True
        req_text = "Test requirement for caching."
        cache_key = _compute_cache_key("rewrite", req_text, "None:0")

        # Inject mock into cache
        from backend.app.services import llm
        llm._CACHE = {
            cache_key: {
                "suggested_text": "The system shall process requests within 1 second.",
                "rationale": "Made measurable.",
                "changes_made": ["Added 1s threshold"],
                "conforms_to_ears": True,
            }
        }

        # Should retrieve from cache without calling client
        res = suggest_rewrite(req_text, issues=[], ears_pattern=None)
        assert res["enabled"] is True
        assert res["cached"] is True
        assert res["suggested_text"] == "The system shall process requests within 1 second."
        assert res["rationale"] == "Made measurable."
    finally:
        settings.LLM_ENABLED = original_setting


def test_generate_gherkin_cached():
    original_setting = settings.LLM_ENABLED
    try:
        settings.LLM_ENABLED = True
        req_text = "Test requirement for gherkin caching."
        cache_key = _compute_cache_key("gherkin", req_text, "Functional")

        from backend.app.services import llm
        llm._CACHE = {
            cache_key: {
                "gherkin_scenarios": "Feature: Caching\n  Scenario: Test\n    Given X\n    When Y\n    Then Z"
            }
        }

        res = generate_gherkin(req_text, classification_label="Functional")
        assert res["enabled"] is True
        assert res["cached"] is True
        assert "Feature: Caching" in res["gherkin_scenarios"]
    finally:
        settings.LLM_ENABLED = original_setting


def test_adhoc_endpoints():
    original_setting = settings.LLM_ENABLED
    try:
        settings.LLM_ENABLED = False
        # Ad-hoc rewrite endpoint
        res = client.post(
            "/api/requirements/suggest-rewrite",
            json={
                "requirement_text": "The system should respond quickly.",
                "issues": [{"rule_id": "AMB_WEAK_TERM", "human_explanation": "Vague term"}],
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["enabled"] is False

        # Ad-hoc Gherkin endpoint
        res_gh = client.post(
            "/api/requirements/generate-gherkin",
            json={
                "requirement_text": "The system shall authenticate users with password.",
                "classification_label": "Functional",
            },
        )
        assert res_gh.status_code == 200
        data_gh = res_gh.json()
        assert data_gh["enabled"] is False
    finally:
        settings.LLM_ENABLED = original_setting


def test_requirement_endpoints():
    db = SessionLocal()
    try:
        doc = Document(filename="test_llm.txt", file_type="txt", file_size=100, raw_text="Sample text", cleaned_text="Sample text")
        db.add(doc)
        db.commit()
        db.refresh(doc)

        req = Requirement(
            document_id=doc.id,
            req_key="REQ-LLM-001",
            text="The system should respond quickly when checking balance.",
            source_layer="layer1",
            confidence=1.0,
            char_start=0,
            char_end=56,
            classification_label="Functional",
        )
        db.add(req)
        db.commit()
        db.refresh(req)

        original_setting = settings.LLM_ENABLED
        try:
            settings.LLM_ENABLED = False
            # 1. Suggest rewrite
            res = client.post(f"/api/requirements/{req.id}/suggest-rewrite")
            assert res.status_code == 200
            assert res.json()["enabled"] is False

            # 2. Generate Gherkin
            res_gh = client.post(f"/api/requirements/{req.id}/generate-gherkin")
            assert res_gh.status_code == 200
            assert res_gh.json()["enabled"] is False

            # 3. Not found test
            res_nf = client.post("/api/requirements/999999/suggest-rewrite")
            assert res_nf.status_code == 404
        finally:
            settings.LLM_ENABLED = original_setting

    finally:
        db.close()
