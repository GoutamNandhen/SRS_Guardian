"""M4 container-only worker. Bundled into an operator-built image with trusted app.

Do not expose as a network service and never import host-uploaded source code.
"""
from __future__ import annotations

import asyncio
import hashlib
import importlib
import json
from pathlib import Path
import re
import sys
from fastapi import FastAPI
from backend.app.services.conformance_verification import (
    parse_transfer_rule, verify_approved_asgi_app,
)

SENTINEL = "SRS_M4_EVIDENCE:"
MODULE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")
ROUTE = re.compile(r"^/[A-Za-z0-9_/{}/-]{1,150}$")


def execute_request(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Worker request must be JSON object")
    module, attr = payload["app_module"], payload["app_attribute"]
    route = payload["route"]
    if not MODULE.fullmatch(module) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", attr) or not ROUTE.fullmatch(route):
        raise ValueError("Invalid operator-pinned application location")
    # Image is prebuilt and approved, and container is already restricted by host.
    module_obj = importlib.import_module(module)
    app = getattr(module_obj, attr)
    if not isinstance(app, FastAPI):
        raise ValueError("Approved target is not a FastAPI instance")
    rule = parse_transfer_rule(payload["req_key"], payload["requirement"])
    report = asyncio.run(verify_approved_asgi_app(
        app=app, rule=rule, target_id=payload["target_id"],
        target_revision=payload["revision"], route=route))
    # M9: report the exact bytes of the imported app module in this image.
    # The host compares this with the indexed ZIP member. This detects accidental
    # source/image drift, but a malicious image could forge its own report.
    source_path = getattr(module_obj, "__file__", None)
    source_sha256 = None
    if isinstance(source_path, str) and source_path.endswith(".py"):
        file = Path(source_path)
        if file.is_file() and file.stat().st_size <= 1_048_576:
            source_sha256 = hashlib.sha256(file.read_bytes()).hexdigest()
    report["executed_module_sha256"] = source_sha256
    # This *specific* oracle assumes a 2xx JSON response carrying accepted=false.
    # 4xx/5xx, including nonexistent endpoints, cannot be treated as successful tests.
    for case in report["cases"]:
        http_status = case.get("http_status")
        if not isinstance(http_status, int) or not 200 <= http_status < 300:
            case["test_status"] = "inconclusive"
    statuses = {case["test_status"] for case in report["cases"]}
    report["decision"] = (
        "observed_violation" if "failed" in statuses
        else "insufficient_evidence" if "inconclusive" in statuses
        else "passed_available_checks")
    report.pop("evidence_sha256", None)
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    report["evidence_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return report


def main() -> int:
    line = sys.stdin.buffer.readline(8193)
    if len(line) > 8192 or not line:
        raise ValueError("Invalid worker request size")
    request = json.loads(line)
    result = execute_request(request)
    print(SENTINEL + json.dumps(result, separators=(",", ":"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
