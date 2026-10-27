"""M9 source-byte binding tests. Uses trusted repository fixtures only.

Fake Docker transport tests host validation; separate GitHub Actions Docker job
runs the actual restricted container and validates both fixture source digests.
"""
from __future__ import annotations

import hashlib
from io import BytesIO
import json
from pathlib import Path
from subprocess import CompletedProcess
from zipfile import ZipFile

import pytest

from backend.app.research.approved_runner import (
    ApprovalError, SENTINEL, _hash, execute_approved, resolve_binding, read_manifest,
)
from backend.app.research.m4_worker import execute_request
from backend.app.services.code_traceability import index_archive, save_index

ROOT = Path(__file__).resolve().parents[2]
IMAGE_ID = "sha256:" + "b" * 64
RULE = "The system shall reject transfers exceeding 10000 rupees."


def _index(source: bytes):
    buf = BytesIO()
    with ZipFile(buf, "w") as archive:
        archive.writestr("banking_api.py", source)
    return index_archive(buf.getvalue(), "M9 trusted source")


def _fixture(tmp_path, *, source: bytes | None = None):
    original = (ROOT / "examples/m4/banking_api.py").read_bytes()
    data = original if source is None else source
    index = _index(data)
    indexes = tmp_path / "indexes"
    save_index(index, indexes)
    matches = [s for s in index["symbols"] if s["qualified_name"] == "transfer_money"
               and {"method": "POST", "route": "/payments/transfer"} in s["http"]]
    assert len(matches) == 1
    symbol = matches[0]
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "schema_version": "m4-approvals-1",
        "targets": [{
            "id": "trusted-bank", "approved": True,
            "source_index_id": index["index_id"], "symbol_id": symbol["symbol_id"],
            "image_id": IMAGE_ID, "app_module": "examples.m4.banking_api",
            "app_attribute": "app", "method": "POST",
            "route": "/payments/transfer", "revision": "trusted-m9",
        }],
    }), encoding="utf-8")
    kwargs = {
        "manifest_path": manifest, "index_directory": indexes,
        "target_id": "trusted-bank", "index_id": index["index_id"],
        "symbol_id": symbol["symbol_id"], "req_key": "REQ-M9",
        "requirement": RULE, "reviewer_approved": True,
    }
    return kwargs, symbol, data


def _fake_docker(*, source_digest: str | None = "original"):
    """Transport-only stub. Worker itself executes the actual trusted FastAPI app."""
    def executor(argv, **kwargs):
        if argv[3:5] == ["image", "inspect"]:
            return CompletedProcess(argv, 0, IMAGE_ID + "\n", "")
        assert argv[3] == "run"
        request = json.loads(kwargs["input"])
        observed = execute_request(request)
        if source_digest != "original":
            observed["executed_module_sha256"] = source_digest
            observed.pop("evidence_sha256")
            observed["evidence_sha256"] = _hash(observed)
        return CompletedProcess(argv, 0, SENTINEL + json.dumps(observed) + "\n", "")
    return executor


@pytest.mark.parametrize("name", ["banking_api.py", "banking_api_buggy.py"])
def test_m2_index_stores_exact_member_bytes(name):
    data = (ROOT / "examples/m4" / name).read_bytes()
    index = _index(data)
    assert index["symbols"]
    assert all(s["source_sha256"] == hashlib.sha256(data).hexdigest()
               for s in index["symbols"])


@pytest.mark.parametrize("name", ["banking_api", "banking_api_buggy"])
def test_worker_reports_imported_module_exact_digest(name):
    source = (ROOT / "examples/m4" / (name + ".py")).read_bytes()
    report = execute_request({
        "req_key": "REQ-M9", "requirement": RULE,
        "app_module": "examples.m4." + name, "app_attribute": "app",
        "route": "/payments/transfer", "target_id": "trusted-bank",
        "revision": "trusted-m9",
    })
    assert report["executed_module_sha256"] == hashlib.sha256(source).hexdigest()
    assert report["evidence_sha256"] == _hash({
        k: v for k, v in report.items() if k != "evidence_sha256"
    })


def test_runner_accepts_only_matching_source_bytes(tmp_path):
    kwargs, symbol, source = _fixture(tmp_path)
    bound = resolve_binding(
        manifest=read_manifest(kwargs["manifest_path"]), target_id=kwargs["target_id"],
        index_id=kwargs["index_id"], symbol_id=kwargs["symbol_id"],
        index_directory=kwargs["index_directory"],
    )
    assert bound["indexed_source_sha256"] == hashlib.sha256(source).hexdigest()
    report = execute_approved(**kwargs, executor=_fake_docker())
    assert report["source_content_binding"] == "worker_reported_module_digest_matches_index"
    assert report["indexed_source_sha256"] == hashlib.sha256(source).hexdigest()
    assert report["executed_module_sha256"] == hashlib.sha256(source).hexdigest()
    assert report["source_image_binding"] == "operator_attested_not_cryptographically_verified"


@pytest.mark.parametrize("digest", ["f" * 64, None, "not-a-sha"])
def test_runner_rejects_mismatched_or_missing_worker_digest(tmp_path, digest):
    kwargs, _, _ = _fixture(tmp_path)
    with pytest.raises(ApprovalError, match="Executed module source differs"):
        execute_approved(**kwargs, executor=_fake_docker(source_digest=digest))


def test_runner_rejects_source_drift_even_if_route_and_symbol_match(tmp_path):
    source = (ROOT / "examples/m4/banking_api.py").read_bytes() + b"\n# M9 source drift\n"
    kwargs, symbol, data = _fixture(tmp_path, source=source)
    assert symbol["source_sha256"] == hashlib.sha256(source).hexdigest()
    with pytest.raises(ApprovalError, match="Executed module source differs"):
        execute_approved(**kwargs, executor=_fake_docker())


def test_runner_rejects_malformed_index_digest(tmp_path):
    kwargs, symbol, _ = _fixture(tmp_path)
    index_file = kwargs["index_directory"] / (kwargs["index_id"] + ".json")
    index = json.loads(index_file.read_text())
    index["symbols"][0]["source_sha256"] = "malformed"
    index_file.write_text(json.dumps(index))
    with pytest.raises(ApprovalError, match="Invalid indexed source"):
        execute_approved(**kwargs, executor=_fake_docker())


def test_legacy_index_reports_missing_content_binding(tmp_path):
    kwargs, symbol, _ = _fixture(tmp_path)
    index_file = kwargs["index_directory"] / (kwargs["index_id"] + ".json")
    index = json.loads(index_file.read_text())
    for s in index["symbols"]:
        s.pop("source_sha256", None)
    index_file.write_text(json.dumps(index))
    report = execute_approved(**kwargs, executor=_fake_docker())
    assert report["source_content_binding"] == "unverified_legacy_index_missing_file_digest"
    assert report["indexed_source_sha256"] is None
