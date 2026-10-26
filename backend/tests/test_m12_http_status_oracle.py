"""M12 regression: HTTP errors/redirects cannot masquerade as rule compliance.

Fixed, in-process trusted FastAPI fixtures only; no arbitrary code execution.
"""
import asyncio

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from backend.app.services.conformance_verification import (
    parse_transfer_rule, verify_approved_asgi_app,
)

RULE = "The system shall reject transfers exceeding 10000 rupees."


def verify(app):
    return asyncio.run(verify_approved_asgi_app(
        app=app,
        rule=parse_transfer_rule("REQ-M12", RULE),
        target_id="trusted-m12-regression",
        target_revision="m12-ci-fixture",
    ))


@pytest.mark.parametrize("http_status", [301, 302, 307, 400, 401, 403, 404, 422, 429, 500, 503])
def test_non_2xx_false_body_is_inconclusive(http_status):
    app = FastAPI()

    @app.post("/payments/transfer")
    async def transfer(payload: dict):
        return JSONResponse(status_code=http_status, content={"accepted": False})

    report = verify(app)
    assert report["decision"] == "insufficient_evidence"
    assert len(report["cases"]) == 3
    assert all(row["test_status"] == "inconclusive" for row in report["cases"])
    assert all(row["http_status"] == http_status for row in report["cases"])
    assert report["evidence_sha256"]


@pytest.mark.parametrize("http_status", [200, 201, 202])
def test_successful_2xx_false_body_still_passes_available_checks(http_status):
    app = FastAPI()

    @app.post("/payments/transfer")
    async def transfer(payload: dict):
        return JSONResponse(status_code=http_status, content={"accepted": False})

    report = verify(app)
    assert report["decision"] == "passed_available_checks"
    assert all(row["test_status"] == "passed" for row in report["cases"])


def test_missing_route_is_inconclusive():
    app = FastAPI()
    report = verify(app)
    assert report["decision"] == "insufficient_evidence"
    assert all(row["http_status"] == 404 for row in report["cases"])


def test_one_non_2xx_observation_prevents_passed_available_checks():
    app = FastAPI()

    @app.post("/payments/transfer")
    async def transfer(payload: dict):
        status = 404 if payload["amount"] == 10002 else 200
        return JSONResponse(status_code=status, content={"accepted": False})

    report = verify(app)
    assert report["decision"] == "insufficient_evidence"
    assert [r["test_status"] for r in report["cases"]] == ["passed", "inconclusive", "passed"]


def test_valid_2xx_accepted_true_still_detects_violation():
    app = FastAPI()

    @app.post("/payments/transfer")
    async def transfer(payload: dict):
        return JSONResponse(status_code=200, content={"accepted": True})

    report = verify(app)
    assert report["decision"] == "observed_violation"
    assert all(row["test_status"] == "failed" for row in report["cases"])
