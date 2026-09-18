import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.nlp.ears import analyze_ears, EarsResult
from backend.app.nlp.iso_checks import (
    analyze_iso_checks,
    check_singular,
    check_unambiguous,
    check_verifiable,
    check_complete,
    check_consistent,
    check_traceable,
    check_structure,
)
from backend.app.nlp.scoring import score_requirement

client = TestClient(app)


def test_ears_patterns_recognition():
    # 1. Ubiquitous
    u = analyze_ears("The system shall store transaction records.")
    assert u.pattern == "ubiquitous"
    assert u.is_valid_ears is True
    assert u.system == "The system"
    assert u.modal == "shall"

    # 2. Event-driven
    e = analyze_ears("When the user clicks submit, the system shall process the request.")
    assert e.pattern == "event_driven"
    assert e.is_valid_ears is True
    assert e.trigger is not None
    assert "user clicks submit" in e.trigger.lower()

    # 3. State-driven
    s = analyze_ears("While offline, the system shall queue outgoing messages.")
    assert s.pattern == "state_driven"
    assert s.is_valid_ears is True
    assert s.state is not None

    # 4. Unwanted behavior
    un = analyze_ears("If invalid credentials are entered, then the system shall lock the account.")
    assert un.pattern == "unwanted_behavior"
    assert un.is_valid_ears is True
    assert un.condition is not None

    # 5. Optional feature
    opt = analyze_ears("Where GPS is enabled, the system shall attach coordinates to photos.")
    assert opt.pattern == "optional_feature"
    assert opt.is_valid_ears is True
    assert opt.feature is not None

    # 6. Complex
    cx = analyze_ears("While in battery saver mode, when a heavy download starts, the system shall throttle CPU.")
    assert cx.pattern == "complex"
    assert cx.is_valid_ears is True

    # 7. Non-conforming
    nc = analyze_ears("Fast response times are desirable.")
    assert nc.pattern == "non_conforming"
    assert nc.is_valid_ears is False
    assert "modal" in nc.missing_elements


def test_iso_singular():
    # Clean single obligation
    c1 = check_singular("The system shall allow users to reset their password.")
    assert c1.status == "passed"
    assert c1.score_deduction == 0.0

    # Multiple modals
    c2 = check_singular("The system shall validate the email and shall send a confirmation code.")
    assert c2.status == "failed"
    assert c2.score_deduction == 10.0
    assert "Multiple modal verbs" in c2.explanation

    # Conjoined action verbs
    c3 = check_singular("The system shall validate and encrypt user records.")
    assert c3.status == "failed"
    assert c3.score_deduction == 10.0


def test_iso_unambiguous():
    # Clean
    u1 = check_unambiguous("The system shall allow users to download their transaction history.")
    assert u1.status == "passed"

    # Ambiguous term
    u2 = check_unambiguous("The system should respond quickly when the user checks balance.")
    assert u2.status == "failed"
    assert u2.score_deduction > 0.0


def test_iso_verifiable():
    # Subjective speed modifier without quantity
    v1 = check_verifiable("The system shall respond quickly to user queries.")
    assert v1.status == "failed"
    assert v1.score_deduction == 15.0

    # Quantitative threshold
    v2 = check_verifiable("The system shall respond within 2.0 seconds.")
    assert v2.status == "passed"
    assert v2.score_deduction == 0.0

    # Numeric constraint
    v3 = check_verifiable("The password must contain at least 8 characters.")
    assert v3.status == "passed"
    assert v3.score_deduction == 0.0

    # Qualitative boolean capability
    v4 = check_verifiable("The system shall allow users to download statements.")
    assert v4.status == "passed"
    assert v4.score_deduction == 0.0


def test_iso_complete():
    # Complete
    c1 = check_complete("The system shall display the user profile.")
    assert c1.status == "passed"

    # Missing actor / subject
    c2 = check_complete("Shall display the user profile.")
    assert c2.status == "failed"
    assert "Subject/Actor" in c2.explanation

    # Missing modal
    c3 = check_complete("The application processes the payment.")
    assert c3.status == "failed"
    assert "Modal Verb" in c3.explanation


def test_iso_consistent():
    all_reqs = [
        {"id": 1, "req_key": "REQ-002", "text": "The system shall allow users to reset their password."},
        {"id": 2, "req_key": "REQ-003", "text": "Users must recover forgotten passwords."},
    ]

    r1 = check_consistent(all_reqs[0], all_reqs)
    assert r1.status == "warning"
    assert "reset" in r1.explanation and "recover" in r1.explanation

    r2 = check_consistent(all_reqs[1], all_reqs)
    assert r2.status == "warning"


def test_iso_traceable():
    t1 = check_traceable({"id": 1, "req_key": "REQ-001", "source_layer": "layer1_explicit_id"})
    assert t1.status == "passed"

    t2 = check_traceable({"id": 2, "req_key": "", "source_layer": "layer4_fallback"})
    assert t2.status == "failed"
    assert t2.score_deduction == 5.0


def test_iso_structure():
    s1 = check_structure("The system shall export logs.")
    assert s1.status == "passed"

    s2 = check_structure("Fast logs are required.")
    assert s2.status in ("warning", "failed")


def test_analyze_iso_checks_sample():
    sample_reqs = [
        {"id": 1, "req_key": "REQ-001", "text": "The system should respond quickly when the user checks the account balance.", "source_layer": "layer1_explicit_id"},
        {"id": 2, "req_key": "REQ-002", "text": "The system shall allow users to reset their password using their registered email.", "source_layer": "layer1_explicit_id"},
        {"id": 3, "req_key": "REQ-003", "text": "Users must recover forgotten passwords using their registered email address.", "source_layer": "layer1_explicit_id"},
        {"id": 4, "req_key": "REQ-004", "text": "The password must contain at least 8 characters.", "source_layer": "layer1_explicit_id"},
        {"id": 5, "req_key": "REQ-005", "text": "The password must contain exactly 6 characters.", "source_layer": "layer1_explicit_id"},
        {"id": 6, "req_key": "REQ-006", "text": "The system shall allow users to download their transaction history.", "source_layer": "layer1_explicit_id"},
    ]

    r1_rep = analyze_iso_checks(sample_reqs[0], all_reqs=sample_reqs)
    assert r1_rep.ears_result.pattern == "event_driven"
    assert r1_rep.ears_result.is_valid_ears is False  # 'should' is not normative
    assert any(c.check_id == "ISO_VERIFIABLE" and c.status == "failed" for c in r1_rep.checks)

    r2_rep = analyze_iso_checks(sample_reqs[1], all_reqs=sample_reqs)
    assert r2_rep.ears_result.is_valid_ears is True
    assert any(c.check_id == "ISO_CONSISTENT" and c.status == "warning" for c in r2_rep.checks)

    r6_rep = analyze_iso_checks(sample_reqs[5], all_reqs=sample_reqs)
    assert r6_rep.ears_result.is_valid_ears is True
    assert all(c.status == "passed" for c in r6_rep.checks)
    assert r6_rep.total_iso_deductions == 0.0


def test_scoring_integration_with_iso():
    sample_reqs = [
        {"id": 1, "req_key": "REQ-002", "text": "The system shall allow users to reset their password using their registered email.", "source_layer": "layer1_explicit_id"},
        {"id": 2, "req_key": "REQ-003", "text": "Users must recover forgotten passwords using their registered email address.", "source_layer": "layer1_explicit_id"},
    ]

    iso_report = analyze_iso_checks(sample_reqs[0], all_reqs=sample_reqs)
    score_res = score_requirement(
        req_key=sample_reqs[0]["req_key"],
        text=sample_reqs[0]["text"],
        iso_checks=iso_report.checks,
    )

    # REQ-002 should have a terminology inconsistency penalty from ISO_CONSISTENT (-10.0)
    assert any(w.rule_id == "ISO_CONSISTENT" for w in score_res.waterfall)
    assert score_res.overall_score == 90.0
    assert score_res.sub_scores["consistency"] < 100.0


def test_api_standards_endpoint():
    # 1. Upload sample document
    sample_text = """ONLINE BANKING SYSTEM
REQ-001: The system should respond quickly when the user checks the account balance.
REQ-002: The system shall allow users to reset their password using their registered email.
REQ-003: Users must recover forgotten passwords using their registered email address.
REQ-004: The password must contain at least 8 characters.
REQ-005: The password must contain exactly 6 characters.
REQ-006: The system shall allow users to download their transaction history.
"""
    files = {"file": ("test_iso_srs.txt", sample_text.encode("utf-8"), "text/plain")}
    res = client.post("/api/documents/upload", files=files)
    assert res.status_code == 201
    doc_id = res.json()["id"]

    # 2. Extract requirements
    res_ext = client.post(f"/api/documents/{doc_id}/extract")
    assert res_ext.status_code == 200

    # 3. Query standards endpoint
    res_std = client.get(f"/api/documents/{doc_id}/standards")
    assert res_std.status_code == 200
    data = res_std.json()
    assert data["document_id"] == doc_id
    assert data["total_requirements"] == 6
    assert "ISO/IEC/IEEE 29148" in data["standards_name"]
    assert len(data["requirements"]) == 6

    # REQ-001 should show event-driven and failed verifiability
    r1 = data["requirements"][0]
    assert r1["req_key"] == "REQ-001"
    assert r1["ears_result"]["pattern"] == "event_driven"
    v_chk = next(c for c in r1["checks"] if c["check_id"] == "ISO_VERIFIABLE")
    assert v_chk["status"] == "failed"

    # REQ-006 should be fully conforming
    r6 = data["requirements"][5]
    assert r6["req_key"] == "REQ-006"
    assert r6["ears_result"]["is_valid_ears"] is True
    assert all(c["status"] == "passed" for c in r6["checks"])
