"""M4 CLI-only Docker execution of operator-approved FastAPI image builds.

NO API endpoint. No user-uploaded code is executed. Operator supplies an
allowlisted, immutable Docker image ID and reviews the linked route/symbol.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Callable

from backend.app.services.code_traceability import load_index
from backend.app.services.conformance_verification import parse_transfer_rule, plan_cases, UnsupportedRequirement

SHA = re.compile(r"^[a-f0-9]{64}$")
IMAGE = re.compile(r"^sha256:[a-f0-9]{64}$")
SYMBOL = re.compile(r"^[a-f0-9]{20}$")
MODULE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")
ROUTE = re.compile(r"^/[A-Za-z0-9_/{}/-]{1,150}$")
SENTINEL = "SRS_M4_EVIDENCE:"


class ApprovalError(ValueError):
    """Fail closed if target, symbol, revision or oracle is unapproved."""


def _canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def read_manifest(path: Path) -> dict[str, Any]:
    """Operator-local manifest; cannot be set via public API."""
    if not path.is_file() or path.stat().st_size > 64_000:
        raise ApprovalError("Missing or oversized operator manifest")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != "m4-approvals-1":
        raise ApprovalError("Unsupported approval manifest version")
    targets = payload.get("targets")
    if not isinstance(targets, list) or not targets:
        raise ApprovalError("No operator-approved targets")
    names = [t.get("id") for t in targets if isinstance(t, dict)]
    if len(names) != len(targets) or len(names) != len(set(names)):
        raise ApprovalError("Malformed or duplicate target identifiers")
    return payload


def resolve_binding(*, manifest: dict, target_id: str, index_id: str,
                    symbol_id: str, index_directory: Path) -> dict[str, Any]:
    """Require an explicit reviewed index/symbol/endpoint binding; no fuzzy autolinking."""
    if not SHA.fullmatch(index_id) or not SYMBOL.fullmatch(symbol_id):
        raise ApprovalError("Malformed index or symbol identifier")
    matches = [t for t in manifest["targets"] if t.get("id") == target_id]
    if len(matches) != 1:
        raise ApprovalError("Target is not registered")
    target = matches[0]
    if target.get("approved") is not True or target.get("source_index_id") != index_id:
        raise ApprovalError("Source archive not approved for this target")
    if not IMAGE.fullmatch(target.get("image_id", "")):
        raise ApprovalError("Image must be an immutable local sha256 image ID")
    if not MODULE.fullmatch(target.get("app_module", "")) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", target.get("app_attribute", "")):
        raise ApprovalError("Invalid operator-pinned app module or symbol")
    if target.get("method") != "POST" or not ROUTE.fullmatch(target.get("route", "")):
        raise ApprovalError("Unsupported or unsafe approved route")
    if target.get("symbol_id") != symbol_id or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", target.get("revision", "")):
        raise ApprovalError("Symbol or revision was not explicitly approved")
    # M2's SHA-256 index ID is the raw source archive SHA-256, not an image digest.
    try:
        index = load_index(index_id, index_directory)
    except (FileNotFoundError, ValueError, OSError) as exc:
        raise ApprovalError("Indexed source archive not found or invalid") from exc
    symbols = [s for s in index["symbols"] if s["symbol_id"] == symbol_id]
    if len(symbols) != 1 or not any(p.get("method") == "POST" and p.get("route") == target["route"] for p in symbols[0]["http"]):
        raise ApprovalError("Approved symbol is not the declared POST endpoint in the indexed source")
    return dict(target, path=symbols[0]["path"], qualified_name=symbols[0]["qualified_name"])


def _docker(args: list[str], *, input_json: str | None = None, timeout: int = 30,
            executor: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> subprocess.CompletedProcess:
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.environ.get("HOME", "/tmp")}
    # An operator should use a local Docker daemon; refuse network-configured daemons.
    docker_host = os.environ.get("DOCKER_HOST", "")
    if docker_host and not (docker_host.startswith("unix://") or docker_host.startswith("npipe://")):
        raise ApprovalError("Remote Docker daemons are not allowed")
    socket = docker_host or ("npipe:////./pipe/docker_engine" if os.name == "nt" else "unix:///var/run/docker.sock")
    try:
        return executor(["docker", "--host", socket, *args], input=input_json, text=True, capture_output=True,
                        check=False, timeout=timeout, env=env)
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        raise ApprovalError("Local Docker unavailable or timed out") from exc


def execute_approved(*, manifest_path: Path, index_directory: Path,
                     target_id: str, index_id: str, symbol_id: str,
                     req_key: str, requirement: str, reviewer_approved: bool,
                     executor: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> dict[str, Any]:
    if reviewer_approved is not True:
        raise ApprovalError("Human approval of requirement oracle is mandatory")
    rule = parse_transfer_rule(req_key, requirement)
    target = resolve_binding(manifest=read_manifest(manifest_path), target_id=target_id,
                             index_id=index_id, symbol_id=symbol_id, index_directory=index_directory)
    inspect = _docker(["image", "inspect", "--format", "{{.Id}}", target["image_id"]],
                      timeout=12, executor=executor)
    if inspect.returncode != 0 or inspect.stdout.strip() != target["image_id"]:
        raise ApprovalError("Docker image identity mismatch or unavailable locally")
    req = {"req_key": rule.req_key, "requirement": rule.statement,
           "app_module": target["app_module"], "app_attribute": target["app_attribute"],
           "route": target["route"], "target_id": target_id, "revision": target["revision"]}
    # --pull never avoids implicit network pulls. The container cannot read host
    # source, local Git, user secrets, or the Docker socket; no mounts are supplied.
    cmd = ["run", "--rm", "--interactive", "--pull", "never", "--network", "none",
           "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
           "--pids-limit", "64", "--memory", "512m", "--cpus", "1",
           "--user", "65534:65534", "--tmpfs", "/tmp:rw,nosuid,noexec,size=16m",
           "--env", "PYTHONDONTWRITEBYTECODE=1", "--entrypoint", "python",
           target["image_id"], "-m", "backend.app.research.m4_worker"]
    result = _docker(cmd, input_json=json.dumps(req), timeout=35, executor=executor)
    if result.returncode != 0 or len(result.stdout) > 65_536:
        raise ApprovalError("Isolated worker failed or returned excessive output")
    lines = [line[len(SENTINEL):] for line in result.stdout.splitlines() if line.startswith(SENTINEL)]
    if len(lines) != 1:
        raise ApprovalError("Missing or ambiguous evidence from isolated worker")
    try:
        observed = json.loads(lines[0])
    except json.JSONDecodeError as exc:
        raise ApprovalError("Malformed worker evidence") from exc
    if not isinstance(observed, dict):
        raise ApprovalError("Worker evidence must be an object")
    if observed.get("target_id") != target_id or observed.get("target_revision") != target["revision"]:
        raise ApprovalError("Worker reported unexpected target identity")
    if observed.get("requirement_key") != rule.req_key or observed.get("requirement_text") != rule.statement:
        raise ApprovalError("Worker evidence requirement mismatch")
    if observed.get("endpoint") != {"method":"POST", "route":target["route"]}:
        raise ApprovalError("Worker route differed from reviewed route")
    if observed.get("decision") not in {"observed_violation", "passed_available_checks", "insufficient_evidence"}:
        raise ApprovalError("Worker returned unsupported decision")
    cases = observed.get("cases")
    expected_cases = plan_cases(rule)
    if not isinstance(cases, list) or len(cases) != len(expected_cases):
        raise ApprovalError("Missing or extra execution observations")
    for row, planned in zip(cases, expected_cases):
        if not isinstance(row, dict) or any(row.get(k) != planned[k] for k in ("case_id", "request", "expected")):
            raise ApprovalError("Worker evidence deviates from approved test plan")
        if row.get("test_status") not in ("passed", "failed", "inconclusive"):
            raise ApprovalError("Invalid test outcome")
        actual = (row.get("actual") or {}).get("accepted")
        status = row["test_status"]
        if status == "passed" and (actual is not False or row.get("http_status", 500) >= 500):
            raise ApprovalError("Invalid reported passing observation")
        if status == "failed" and (actual is not True or row.get("http_status", 500) >= 500):
            raise ApprovalError("Invalid reported failing observation")
    decisions = {row["test_status"] for row in cases}
    derived = ("observed_violation" if "failed" in decisions else
               "insufficient_evidence" if "inconclusive" in decisions else
               "passed_available_checks")
    if observed["decision"] != derived:
        raise ApprovalError("Aggregate decision contradicts observations")
    # Validate the worker-provided evidence checksum; integrity *not* attestation.
    digest = observed.pop("evidence_sha256", None)
    if digest != _hash(observed):
        raise ApprovalError("Evidence checksum invalid")
    observed["evidence_sha256"] = digest
    return {
        "schema_version": "m4-bound-evidence-1", "requirement_key": rule.req_key,
        "requirement_sha256": hashlib.sha256(rule.statement.encode("utf-8")).hexdigest(),
        "source_index_id": index_id, "approved_symbol_id": symbol_id,
        "approved_source_path": target["path"], "approved_symbol": target["qualified_name"],
        "approved_route": target["route"], "image_id": target["image_id"],
        "target_revision_label": target["revision"],
        "source_image_binding": "operator_attested_not_cryptographically_verified",
        "isolation": "docker_local_network_none_readonly_unprivileged_no_mounts",
        "oracle_reviewed": True, "worker_evidence": observed,
        "research_warning": "Trusted operator-approved Docker image only. This does not prove arbitrary source correctness or 95% accuracy.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline, operator-only M4 approved target verifier")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--index-dir", type=Path, default=Path("data/code_indexes"))
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--index-id", required=True)
    parser.add_argument("--symbol-id", required=True)
    parser.add_argument("--req-key", required=True)
    parser.add_argument("--requirement", required=True)
    parser.add_argument("--approve-oracle", action="store_true")
    args = parser.parse_args()
    try:
        report = execute_approved(manifest_path=args.manifest, index_directory=args.index_dir,
            target_id=args.target_id, index_id=args.index_id, symbol_id=args.symbol_id,
            req_key=args.req_key, requirement=args.requirement,
            reviewer_approved=args.approve_oracle)
    except (ApprovalError, UnsupportedRequirement, ValueError) as exc:
        parser.exit(status=2, message=f"M4 declined: {exc}\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
