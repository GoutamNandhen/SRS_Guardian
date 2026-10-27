"""M3 verifier regression suite: tests only fixed trusted synthetic ASGI apps."""
import asyncio
import hashlib
import json
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.services.conformance_verification import (
    UnsupportedRequirement, parse_transfer_rule, plan_cases, verify_trusted_demo,
    verify_approved_asgi_app, make_demo_app,
)
from backend.app.api.conformance_verification import router

BASE = "The banking system shall reject transfers exceeding ₹10,000."


def test_strict_parser():
    assert parse_transfer_rule("REQ-101", BASE).threshold == 10000
    assert parse_transfer_rule("REQ-101", "The system must reject transfers above 10000 rupees.").threshold == 10000
    assert parse_transfer_rule("REQ-101", "The banking system shall reject transfers exceeding a 10000 payment limit.").threshold == 10000


@pytest.mark.parametrize("text", [
    "The system should reject transfers exceeding 10000.",
    "The system shall allow transfers exceeding 10000.",
    "The system shall reject withdrawals exceeding 10000.",
    "The system shall reject transfers exceeding 10000 unless approved.",
    "The system shall reject transfers exceeding 10000 if the customer is unverified.",
    "The system shall reject transfers exceeding 10000 per day.",
    "The system shall reject transfers exceeding 10000 and 15000.",
    "The system shall reject transfers exceeding USD 10000.",
    "The system shall reject transfers exceeding 0.",
    "The system shall reject transfers exceeding 10,00.",
    "The system shall reject transfers exceeding -10000.",
    "The system shall reject transfers exceeding 10000.5.",
])
def test_unsupported_requirements_require_review(text):
    with pytest.raises(UnsupportedRequirement):
        parse_transfer_rule("REQ-1", text)


def test_no_unjustified_below_limit_acceptance_tests():
    cases = plan_cases(parse_transfer_rule("REQ-1", BASE))
    assert len(cases) == 3
    assert [c["request"]["amount"] for c in cases] == [10001, 10002, 11000]
    assert all(c["request"]["amount"] > 10000 for c in cases)
    assert all(c["expected"] == {"accepted": False} for c in cases)


def test_correct_target_passes_only_available_checks():
    report = asyncio.run(verify_trusted_demo(req_key="REQ-1", text=BASE,
                                              target_id="demo_correct", oracle_approved=True))
    assert report["decision"] == "passed_available_checks"
    assert all(x["test_status"] == "passed" for x in report["cases"])
    assert report["source_repository_verified"] is False
    assert report["demo_only"] is True


def test_buggy_target_produces_real_failure_evidence():
    report = asyncio.run(verify_trusted_demo(req_key="REQ-1", text=BASE,
                                              target_id="demo_buggy", oracle_approved=True))
    assert report["decision"] == "observed_violation"
    assert any(x["test_status"] == "failed" for x in report["cases"])
    assert any(x["actual"]["accepted"] is True for x in report["cases"])


def test_no_unapproved_or_nonregistered_test_targets():
    with pytest.raises(ValueError, match="approve"):
        asyncio.run(verify_trusted_demo(req_key="REQ-1", text=BASE,
                                        target_id="demo_correct", oracle_approved=False))
    with pytest.raises(ValueError, match="registered"):
        asyncio.run(verify_trusted_demo(req_key="REQ-1", text=BASE,
                                        target_id="http://127.0.0.1:8000", oracle_approved=True))



def test_fixed_demo_threshold_mismatch_abstains():
    with pytest.raises(UnsupportedRequirement, match="10,000"):
        asyncio.run(verify_trusted_demo(
            req_key="REQ-OTHER",
            text="The banking system shall reject transfers exceeding ₹20,000.",
            target_id="demo_correct",
            oracle_approved=True,
        ))


def test_generic_trusted_asgi_adapter():
    rule = parse_transfer_rule("REQ-1", BASE)
    report = asyncio.run(verify_approved_asgi_app(
        app=make_demo_app(faulty=True), rule=rule,
        target_id="operator-authorized", target_revision="test-only-revision"))
    assert report["decision"] == "observed_violation"
    assert "demo_only" not in report
    assert report["source_repository_verified"] is False



def test_http_server_failure_is_inconclusive_not_a_pass():
    from fastapi.responses import JSONResponse

    app = FastAPI()

    @app.post("/payments/transfer")
    async def broken_service():
        return JSONResponse(status_code=503, content={"accepted": False})

    report = asyncio.run(verify_approved_asgi_app(
        app=app, rule=parse_transfer_rule("REQ-SERVER", BASE),
        target_id="trusted-service-error", target_revision="broken-fixture",
    ))
    assert report["decision"] == "insufficient_evidence"
    assert all(row["test_status"] == "inconclusive" for row in report["cases"])



def test_provenance_digest():
    report = asyncio.run(verify_trusted_demo(req_key="REQ-1", text=BASE,
                                              target_id="demo_correct", oracle_approved=True))
    digest = report.pop("evidence_sha256")
    canonical = json.dumps(report, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    assert hashlib.sha256(canonical.encode("utf-8")).hexdigest() == digest


def test_preview_support_and_abstention():
    app = FastAPI()
    app.include_router(router, prefix="/api")
    client = TestClient(app)
    good = client.post("/api/conformance/preview",
                       json={"req_key": "REQ-1", "requirement_text": BASE})
    assert good.status_code == 200
    assert good.json()["decision"] == "not_executed"
    unsupported = client.post("/api/conformance/preview",
                              json={"req_key": "REQ-2", "requirement_text": "The app shall be fast."})
    assert unsupported.status_code == 200
    assert unsupported.json()["decision"] == "needs_human_clarification"


def test_demo_endpoint_approval_and_target_allowlist():
    app = FastAPI()
    app.include_router(router, prefix="/api")
    client = TestClient(app)
    base = {"req_key": "REQ-1", "requirement_text": BASE, "oracle_approved": True}
    good = client.post("/api/conformance/demo/run", json={**base, "target_id": "demo_correct"})
    bad = client.post("/api/conformance/demo/run", json={**base, "target_id": "demo_buggy"})
    assert good.status_code == 200
    assert good.json()["decision"] == "passed_available_checks"
    assert bad.status_code == 200
    assert bad.json()["decision"] == "observed_violation"
    assert client.post("/api/conformance/demo/run", json={**base, "target_id": "http://localhost"}).status_code == 422
    assert client.post("/api/conformance/demo/run", json={**base, "oracle_approved": False, "target_id": "demo_correct"}).status_code == 422

def test_m11_probe_detects_known_isolated_plus_two_fault():
    """M5's controlled +2 fault was missed by the old two-probe M3 plan."""
    from backend.evaluation.m5_controlled_pilot import approved_fixture

    app = approved_fixture(10000, "accept_at_plus_2")
    report = asyncio.run(verify_approved_asgi_app(
        app=app, rule=parse_transfer_rule("REQ-M11", BASE),
        target_id="trusted-controlled-plus-two", target_revision="m11-fixture",
    ))
    assert report["decision"] == "observed_violation"
    assert len(report["cases"]) == 3
    failed = [row for row in report["cases"] if row["test_status"] == "failed"]
    assert len(failed) == 1
    assert failed[0]["request"] == {"amount": 10002}
    assert report["evidence_sha256"]


@pytest.mark.parametrize("limit", [1, 2, 10, 10000, 100000000])
def test_m11_three_distinct_above_limit_probes_for_all_supported_ranges(limit):
    rule = parse_transfer_rule("REQ-M11-LIMIT", f"The system shall reject transfers exceeding {limit} rupees.")
    cases = plan_cases(rule)
    values = [row["request"]["amount"] for row in cases]
    assert len(values) == len(set(values)) == 3
    assert values[0:2] == [limit + 1, limit + 2]
    assert all(v > limit for v in values)
