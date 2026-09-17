import json
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.nlp.numeric_constraints import (
    extract_constraints,
    detect_numeric_conflicts,
    intervals_conflict,
)
from backend.app.ml.contradictions import (
    select_candidate_pairs,
    detect_semantic_contradictions,
    explain_semantic_contradiction,
)


@pytest.fixture
def client():
    return TestClient(app)


def test_numeric_constraint_extraction_sample():
    """Verify extraction of REQ-004 and REQ-005 from sample specification."""
    req4_text = "The password must contain at least 8 characters."
    req5_text = "The password must contain exactly 6 characters."

    c4 = extract_constraints(req4_text, req_key="REQ-004", requirement_id=4)
    c5 = extract_constraints(req5_text, req_key="REQ-005", requirement_id=5)

    assert len(c4) == 1
    assert c4[0].entity == "password"
    assert c4[0].attribute == "length"
    assert c4[0].comparator == ">="
    assert c4[0].value == 8.0
    assert c4[0].normalized_unit == "characters"

    assert len(c5) == 1
    assert c5[0].entity == "password"
    assert c5[0].attribute == "length"
    assert c5[0].comparator == "=="
    assert c5[0].value == 6.0
    assert c5[0].normalized_unit == "characters"


def test_numeric_constraint_comparators():
    """Verify extraction across various comparative constructs and units."""
    cases = [
        ("The response time must be under 500 ms.", "<", 500.0, "latency", "seconds", 0.5),
        ("Files up to 10 MB may be uploaded.", "<=", 10.0, "size", "mb", 10.0),
        ("The system must support between 100 and 500 users.", "between", 100.0, "capacity", "users", 100.0),
        ("The timeout shall be greater than 30 seconds.", ">", 30.0, "latency", "seconds", 30.0),
    ]

    for text, comp, val, attr, norm_unit, norm_val in cases:
        c_list = extract_constraints(text)
        assert len(c_list) >= 1, f"Failed to extract constraint from: {text}"
        c = c_list[0]
        assert c.comparator == comp
        assert c.value == val
        assert c.normalized_unit == norm_unit
        assert abs(c.normalized_value - norm_val) < 1e-4


def test_interval_conflict_logic():
    """Verify mathematical range intersection checking."""
    # Conflict: [8, inf) vs == 6
    c1 = extract_constraints("The password must contain at least 8 characters.")[0]
    c2 = extract_constraints("The password must contain exactly 6 characters.")[0]
    conflict, reason = intervals_conflict(c1, c2)
    assert conflict is True
    assert "Upper bound" in reason or "strictly below" in reason

    # Compatible: [8, inf) vs [6, inf)
    c3 = extract_constraints("The password must contain at least 6 characters.")[0]
    conflict, _ = intervals_conflict(c1, c3)
    assert conflict is False

    # Conflict: <= 5 vs >= 10
    c4 = extract_constraints("The timeout must be at most 5 seconds.")[0]
    c5 = extract_constraints("The timeout must be at least 10 seconds.")[0]
    conflict, _ = intervals_conflict(c4, c5)
    assert conflict is True

    # Compatible: <= 10 vs <= 20
    c6 = extract_constraints("The timeout must be at most 20 seconds.")[0]
    conflict, _ = intervals_conflict(c4, c6)
    assert conflict is False


def test_detect_numeric_conflicts_sample():
    """Verify detect_numeric_conflicts catches REQ-004 vs REQ-005."""
    reqs = [
        {"id": 4, "req_key": "REQ-004", "text": "The password must contain at least 8 characters."},
        {"id": 5, "req_key": "REQ-005", "text": "The password must contain exactly 6 characters."},
        {"id": 6, "req_key": "REQ-006", "text": "The system shall allow users to download their transaction history."},
    ]

    findings = detect_numeric_conflicts(reqs)
    assert len(findings) == 1
    f = findings[0]
    assert f.req_key_1 == "REQ-004"
    assert f.req_key_2 == "REQ-005"
    assert "POTENTIAL contradiction" in f.human_explanation
    assert f.rule_id == "NUMERIC_CONSTRAINT_CONFLICT"
    assert f.severity == "critical"


def test_semantic_candidate_blocking():
    """Verify unrelated pairs are blocked before reaching NLI."""
    reqs = [
        {"id": 1, "req_key": "REQ-001", "text": "The system shall allow users to reset their password using registered email."},
        {"id": 2, "req_key": "REQ-002", "text": "The system shall allow users to download their transaction history."},
    ]

    candidates = select_candidate_pairs(reqs, min_similarity=0.55)
    # Password reset and transaction download should not pass candidate blocking
    assert len(candidates) == 0


def test_semantic_contradiction_detection():
    """Verify NLI detects direct semantic opposition."""
    reqs = [
        {"id": 1, "req_key": "REQ-A", "text": "The system shall allow users to delete their accounts."},
        {"id": 2, "req_key": "REQ-B", "text": "The system must prohibit users from deleting accounts."},
    ]

    findings = detect_semantic_contradictions(reqs, confidence_threshold=0.70)
    assert len(findings) == 1
    f = findings[0]
    assert f.req_key_1 == "REQ-A"
    assert f.req_key_2 == "REQ-B"
    assert f.confidence >= 0.70
    assert "POTENTIAL contradiction" in f.human_explanation


def test_on_demand_captum_attribution():
    """Verify on-demand Captum LayerIntegratedGradients returns token attributions."""
    premise = "The system shall allow users to delete their accounts."
    hypothesis = "The system must prohibit users from deleting accounts."

    tokens = explain_semantic_contradiction(premise, hypothesis, n_steps=2)
    assert len(tokens) > 0
    token_words = [t["token"] for t in tokens]
    # 'prohibit' or 'delete' should be among the top tokens
    assert any("prohibit" in w.lower() or "delete" in w.lower() for w in token_words)


def test_end_to_end_analyze_contradictions(client):
    """End-to-end test uploading sample SRS, analyzing, and verifying contradictions endpoint."""
    sample_content = (
        "REQ-001: The system should respond quickly when the user checks the account balance.\n"
        "REQ-002: The system shall allow users to reset their password using their registered email.\n"
        "REQ-003: Users must recover forgotten passwords using their registered email address.\n"
        "REQ-004: The password must contain at least 8 characters.\n"
        "REQ-005: The password must contain exactly 6 characters.\n"
        "REQ-006: The system shall allow users to download their transaction history.\n"
    )

    # 1. Upload document
    upload_res = client.post(
        "/api/documents/upload",
        files={"file": ("sample_contra_test.txt", sample_content.encode("utf-8"), "text/plain")},
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # 2. Analyze document
    analyze_res = client.post(f"/api/documents/{doc_id}/analyze")
    assert analyze_res.status_code == 200
    summary = analyze_res.json()

    # 3. Check contradiction endpoint
    contra_res = client.get(f"/api/documents/{doc_id}/contradictions")
    assert contra_res.status_code == 200
    data = contra_res.json()

    assert data["total_contradictions_count"] >= 1
    assert data["numeric_conflicts_count"] >= 1

    # Verify REQ-004 vs REQ-005 is caught
    pairs = [(c["req_key_1"], c["req_key_2"]) for c in data["contradictions"]]
    assert ("REQ-004", "REQ-005") in pairs or ("REQ-005", "REQ-004") in pairs

    # 4. Check that waterfall score reflects the contradiction penalty
    reqs_res = client.get(f"/api/documents/{doc_id}/requirements")
    assert reqs_res.status_code == 200
    req_items = reqs_res.json()

    req4_id = next(r["id"] for r in req_items if r["req_key"] == "REQ-004")
    req4_detail = client.get(f"/api/requirements/{req4_id}").json()

    waterfall = req4_detail["waterfall"]
    step_names = [s["step_name"] for s in waterfall]
    assert any("Potential Contradiction" in name for name in step_names)
