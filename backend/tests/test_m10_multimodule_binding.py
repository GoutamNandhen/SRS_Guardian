"""M10 tests: binding actual included-router handler, not the ASGI entrypoint."""
from __future__ import annotations

import hashlib
from io import BytesIO
import json
from pathlib import Path
from subprocess import CompletedProcess
from zipfile import ZipFile

import pytest

from backend.app.research.approved_runner import (
    ApprovalError, SENTINEL, _hash, execute_approved,
)
from backend.app.research.m4_worker import execute_request
from backend.app.services.code_traceability import index_archive, save_index

ROOT = Path(__file__).resolve().parents[2]
IMAGE = "sha256:" + "b" * 64
RULE = "The system shall reject transfers exceeding 10000 rupees."
SAMPLES = [
    ("router_correct.py", "examples.m10.app_correct", "passed_available_checks"),
    ("router_buggy.py", "examples.m10.app_buggy", "observed_violation"),
]


def _request(module):
    return {
        "req_key": "REQ-M10", "requirement": RULE,
        "app_module": module, "app_attribute": "app",
        "route": "/payments/transfer", "target_id": "m10-reviewed",
        "revision": "m10-trusted",
    }


@pytest.mark.parametrize("source_name,module,expected", SAMPLES)
def test_worker_identifies_actual_included_router_source(source_name, module, expected):
    report = execute_request(_request(module))
    source = (ROOT / "examples/m10" / source_name).read_bytes()
    assert report["decision"] == expected
    assert report["executed_endpoint_sha256"] == hashlib.sha256(source).hexdigest()
    assert report["executed_endpoint_qualname"] == "transfer_money"
    assert report["executed_endpoint_module"] == module.replace("app_", "router_")
    assert report["executed_module_sha256"] != report["executed_endpoint_sha256"]
    assert report["evidence_sha256"] == _hash({
        k: v for k, v in report.items() if k != "evidence_sha256"
    })


def _setup(tmp_path, *, source_name="router_correct.py", extra_source=b""):
    source = (ROOT / "examples/m10" / source_name).read_bytes() + extra_source
    buf = BytesIO()
    with ZipFile(buf, "w") as z:
        z.writestr(source_name, source)
    index = index_archive(buf.getvalue(), "M10 trusted router")
    indexes = tmp_path / "indexes"
    save_index(index, indexes)
    matches = [
        s for s in index["symbols"]
        if s["qualified_name"] == "transfer_money"
        and {"method": "POST", "route": "/payments/transfer"} in s["http"]
    ]
    assert len(matches) == 1
    module = "examples.m10.app_" + ("buggy" if "buggy" in source_name else "correct")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "schema_version": "m4-approvals-1",
        "targets": [{
            "id": "m10-reviewed", "approved": True,
            "source_index_id": index["index_id"],
            "symbol_id": matches[0]["symbol_id"], "image_id": IMAGE,
            "app_module": module, "app_attribute": "app",
            "method": "POST", "route": "/payments/transfer",
            "revision": "m10-trusted",
        }],
    }), encoding="utf-8")
    return {
        "manifest_path": manifest, "index_directory": indexes,
        "target_id": "m10-reviewed", "index_id": index["index_id"],
        "symbol_id": matches[0]["symbol_id"], "req_key": "REQ-M10",
        "requirement": RULE, "reviewer_approved": True,
    }, module


def _fake_docker(*, tamper=None):
    def executor(argv, **kwargs):
        if argv[3:5] == ["image", "inspect"]:
            return CompletedProcess(argv, 0, IMAGE + "\n", "")
        assert argv[3] == "run"
        observed = execute_request(json.loads(kwargs["input"]))
        if tamper:
            tamper(observed)
            observed.pop("evidence_sha256")
            observed["evidence_sha256"] = _hash(observed)
        return CompletedProcess(argv, 0, SENTINEL + json.dumps(observed) + "\n", "")
    return executor


@pytest.mark.parametrize("source_name,module,expected", SAMPLES)
def test_runner_accepts_matching_separate_router(tmp_path, source_name, module, expected):
    kwargs, actual_module = _setup(tmp_path, source_name=source_name)
    assert module == actual_module
    report = execute_approved(**kwargs, executor=_fake_docker())
    assert report["worker_evidence"]["decision"] == expected
    assert report["source_content_binding"] == "worker_reported_endpoint_digest_matches_index"
    assert report["executed_endpoint_sha256"] == report["indexed_source_sha256"]
    assert report["executed_endpoint_sha256"] != report["executed_module_sha256"]


def test_rejects_modified_router_with_same_endpoint_name(tmp_path):
    kwargs, _ = _setup(tmp_path, extra_source=b"\n# M10 deliberate router source drift\n")
    with pytest.raises(ApprovalError, match="Executed endpoint source differs"):
        execute_approved(**kwargs, executor=_fake_docker())


def test_rejects_forged_handler_qualname_even_with_matching_digest(tmp_path):
    kwargs, _ = _setup(tmp_path)
    def tamper(observed):
        observed["executed_endpoint_qualname"] = "different_handler"
    with pytest.raises(ApprovalError, match="Executed endpoint symbol differs"):
        execute_approved(**kwargs, executor=_fake_docker(tamper=tamper))


def test_no_silent_entrypoint_fallback_when_endpoint_digest_missing(tmp_path):
    kwargs, _ = _setup(tmp_path)
    def tamper(observed):
        observed["executed_endpoint_sha256"] = None
    with pytest.raises(ApprovalError, match="Executed module source differs"):
        execute_approved(**kwargs, executor=_fake_docker(tamper=tamper))
