"""M3: conservative, execution-backed checks against *developer-trusted* FastAPI apps.

Never execute code from uploaded ZIP archives. The public API only uses built-in
synthetic targets; actual projects require a separately approved ASGI app supplied
directly by the developer, ideally inside an isolated test worker.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


class UnsupportedRequirement(ValueError):
    """Fail closed rather than inventing an expected outcome."""


@dataclass(frozen=True)
class TransferRule:
    threshold: int
    req_key: str
    statement: str


_AMOUNT = re.compile(r"(?:exceeding|above|greater\s+than|over)\b[^.\n;]{0,48}?\b(\d[\d,]*)\b", re.I)


def parse_transfer_rule(req_key: str, text: str) -> TransferRule:
    if not 1 <= len(text) <= 1200 or not 1 <= len(req_key) <= 100:
        raise UnsupportedRequirement("Requirement key/text is missing or too long")
    sentence = " ".join(text.strip().split())
    lowered = sentence.lower()
    if not re.search(r"\b(?:shall|must)\s+reject\b", lowered):
        raise UnsupportedRequirement("Only mandatory 'shall/must reject' transfer rules are supported")
    if not re.search(r"\btransfers?\b", lowered):
        raise UnsupportedRequirement("Only transfer-amount requirements are supported")
    if re.search(r"\b(?:unless|except|if|when|provided\s+that|only\s+if|at\s+least|up\s+to|per\s+day|daily|each\s+day)\b", lowered):
        raise UnsupportedRequirement("Conditional, aggregated, or ambiguous transfer rules need review")
    if re.search(r"\b(?:USD|EUR|dollars?|euros?|million|crore|lakhs?)\b|[$€£]", sentence, re.I):
        raise UnsupportedRequirement("Currency or unit is not supported for this INR demo oracle")
    if re.search(r"(?<!\w)-\d|\d\.\d", sentence):
        raise UnsupportedRequirement("Negative or fractional amounts need review")
    numbers = re.findall(r"(?<!\w)\d[\d,]*(?!\w)", sentence)
    candidate = _AMOUNT.findall(sentence)
    if len(numbers) != 1 or len(candidate) != 1 or candidate[0] != numbers[0]:
        raise UnsupportedRequirement("Require exactly one explicit, unambiguous numeric threshold")
    value = int(candidate[0].replace(",", ""))
    if value < 1 or value > 100_000_000:
        raise UnsupportedRequirement("Threshold is outside the supported positive-integer range")
    if "," in numbers[0] and not re.fullmatch(r"\d{1,3}(?:,\d{3})+", numbers[0]):
        raise UnsupportedRequirement("Invalid thousands-grouping format")
    return TransferRule(threshold=value, req_key=req_key, statement=sentence)


def plan_cases(rule: TransferRule) -> list[dict[str, Any]]:
    """Only above-limit rejection follows from this requirement; not below-limit success."""
    # M11: the original two probes missed a narrow faulty implementation
    # accepting *only* threshold+2 (observed in M5's controlled pilot).
    # Keep the distant probe while adding the adjacent +2 boundary. Ensure
    # exactly three distinct above-limit amounts, even for small thresholds.
    wide = rule.threshold + max(2, (rule.threshold + 9) // 10)
    amounts = list(dict.fromkeys([rule.threshold + 1, rule.threshold + 2, wide]))
    if len(amounts) < 3:
        amounts.append(rule.threshold + 3)
    return [{"case_id": f"{rule.req_key}-ABOVE-{i+1}",
             "request": {"amount": amount},
             "expected": {"accepted": False},
             "reason": "amount strictly exceeds limit"}
            for i, amount in enumerate(dict.fromkeys(amounts))]


def make_demo_app(*, faulty: bool) -> FastAPI:
    """Synthetic approved target. It does not import user-uploaded source code."""
    app = FastAPI(title="SRS Guardian synthetic transfer target")

    @app.post("/payments/transfer")
    async def submit_transfer(payload: dict[str, Any]):
        amount = payload.get("amount")
        if type(amount) is not int or amount < 0:
            return {"accepted": False, "reason": "invalid amount"}
        if faulty:
            return {"accepted": amount <= 20_000}
        return {"accepted": amount <= 10_000}

    return app


TARGETS: dict[str, dict[str, Any]] = {
    "demo_correct": {"description": "Trusted fixed synthetic app; rejects amounts > 10000", "faulty": False},
    "demo_buggy": {"description": "Trusted fixed synthetic app; erroneously allows amounts <= 20000", "faulty": True},
}


def _evidence_digest(report: dict[str, Any]) -> str:
    canonical = json.dumps(report, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def verify_approved_asgi_app(*, app: FastAPI, rule: TransferRule,
                                   target_id: str, target_revision: str,
                                   route: str = "/payments/transfer") -> dict:
    """Check an explicitly trusted ASGI instance, never a URL or import path.

    In-process ASGI execution is NOT a sandbox; only use on trusted operator-provisioned
    application instances. Untrusted projects need an isolated worker.
    """
    if not re.fullmatch(r"/[A-Za-z0-9_/{}/-]{1,150}", route):
        raise ValueError("Test route must be a simple relative ASGI path")
    observations = []
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://trusted-target.invalid", timeout=5.0) as client:
        for case in plan_cases(rule):
            try:
                response = await client.post(route, json=case["request"])
                body = response.json()
                actual = body.get("accepted") if isinstance(body, dict) else None
                # An HTTP error or redirect is not a successful business-rule
                # rejection, even if its JSON happens to say accepted=false.
                # Require a 2xx application response before judging the oracle.
                # M4 already enforced this in its worker; keep the M3 verifier
                # consistent so demos and approved execution cannot disagree.
                status = ("inconclusive" if not 200 <= response.status_code < 300
                          else "passed" if actual is False
                          else "failed" if actual is True else "inconclusive")
                observation = {
                    "case_id": case["case_id"], "request": case["request"],
                    "expected": case["expected"], "actual": {"accepted": actual},
                    "http_status": response.status_code, "test_status": status,
                    "response_excerpt": json.dumps(body, ensure_ascii=False)[:500],
                }
            except Exception as exc:
                observation = {
                    "case_id": case["case_id"], "request": case["request"],
                    "expected": case["expected"], "test_status": "inconclusive",
                    "execution_error_type": type(exc).__name__,
                }
            observations.append(observation)
    outcomes = {row["test_status"] for row in observations}
    decision = ("observed_violation" if "failed" in outcomes
                else "insufficient_evidence" if "inconclusive" in outcomes
                else "passed_available_checks")
    report = {
        "schema_version": "m3-asgi-1",
        "verification_scope": "strict transfer amount rejection; reviewer-approved boolean response contract",
        "target_id": target_id, "target_revision": target_revision,
        "endpoint": {"method": "POST", "route": route},
        "source_repository_verified": False,
        "requirement_key": rule.req_key, "requirement_text": rule.statement,
        "threshold": rule.threshold,
        "oracle": {"rejection_state": {"accepted": False}, "reviewer_approved": True},
        "cases": observations, "decision": decision,
        "evidence_disclaimer": (
            "Observed responses from a developer-approved ASGI test target, for specified cases only. "
            "The provided target revision is a caller label, not cryptographically attested. "
            "No proof of complete requirement satisfaction or source-index identity is implied."),
    }
    report["evidence_sha256"] = _evidence_digest(report)
    return report


async def verify_trusted_demo(*, req_key: str, text: str,
                              target_id: str, oracle_approved: bool) -> dict:
    if not oracle_approved:
        raise ValueError("A reviewer must explicitly approve the transfer rejection oracle")
    if target_id not in TARGETS:
        raise ValueError("Only registered trusted demo targets are allowed")
    rule = parse_transfer_rule(req_key, text)
    if rule.threshold != 10_000:
        raise UnsupportedRequirement(
            "Built-in demo applications implement the ₹10,000 limit only. "
            "Use the approved development adapter for other thresholds."
        )
    demo = TARGETS[target_id]
    report = await verify_approved_asgi_app(
        app=make_demo_app(faulty=demo["faulty"]), rule=rule,
        target_id=target_id, target_revision="synthetic-fixture-v1",
        route="/payments/transfer",
    )
    report["demo_only"] = True
    report["target_description"] = demo["description"]
    report["evidence_disclaimer"] += " This demonstration is not testing uploaded source code."
    del report["evidence_sha256"]
    report["evidence_sha256"] = _evidence_digest(report)
    return report
