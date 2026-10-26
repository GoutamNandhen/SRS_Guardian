"""M4 container-only worker. Bundled into an operator-built image with trusted app.

Do not expose as a network service and never import host-uploaded source code.
"""
from __future__ import annotations

import asyncio
import importlib
import json
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
    app = getattr(importlib.import_module(module), attr)
    if not isinstance(app, FastAPI):
        raise ValueError("Approved target is not a FastAPI instance")
    rule = parse_transfer_rule(payload["req_key"], payload["requirement"])
    return asyncio.run(verify_approved_asgi_app(
        app=app, rule=rule, target_id=payload["target_id"],
        target_revision=payload["revision"], route=route))


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
