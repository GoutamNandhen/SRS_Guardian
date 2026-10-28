"""First-party, offline M47/M45 observation handoff into M44/M20 human review.

Never imports or executes upstream Requests. An evidence bundle is NOT gold,
independent observation, a conformance decision, or a held-out score.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from backend.evaluation import m47_requests_approved_reviewer_capture as m47

MAX_BYTES = 1_000_000
CASE_ID = "REQUESTS_7432_REDIRECT"
PROJECT = "REQUESTS_STREAM_REDIRECT_7432"


class HandoffError(ValueError):
    """Invalid or inconsistent, self-reported reviewer capture."""


def _read(path: Path) -> bytes:
    if not path.is_file() or path.is_symlink() or not 0 < path.stat().st_size <= MAX_BYTES:
        raise HandoffError(f"Missing, symlinked, empty, or oversized evidence: {path}")
    return path.read_bytes()


def _object(raw: bytes, name: str) -> dict:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HandoffError(f"Invalid {name} JSON") from exc
    if not isinstance(value, dict):
        raise HandoffError(f"Expected {name} JSON object")
    return value


def inspect(client_raw: bytes, wire_raw: bytes, reviewer: str) -> dict:
    """Validate provenance and internal consistency, NOT observed correctness."""
    if reviewer not in ("A", "B"):
        raise HandoffError("Reviewer must be A or B")
    client = _object(client_raw, "client")
    revision = client.get("revision")
    if revision not in m47.REVISIONS:
        raise HandoffError("Unknown revision")
    if (client.get("schema") != "m47-approved-reviewer-observation-v1"
            or client.get("reviewer_supplied") is not True
            or client.get("independent_adjudication") is not False
            or client.get("behavior_label") is not None
            or client.get("git_commit") != m47.REVISIONS[revision]
            or client.get("verified_git_blobs") != m47.BLOBS[revision]
            or client.get("expected_payload_length") != len(m47.PAYLOAD)
            or client.get("expected_payload_sha256") != hashlib.sha256(m47.PAYLOAD).hexdigest()):
        raise HandoffError("Capture schema or pinned provenance mismatch")
    try:
        url = m47.validate_url(client.get("fixture_url", ""))
    except (TypeError, m47.CaptureError) as exc:
        raise HandoffError("Invalid fixture URL")
    for key in ("captured_at_utc", "python", "platform", "requests_module_path"):
        if not isinstance(client.get(key), str) or not client[key].strip():
            raise HandoffError(f"Missing client provenance: {key}")
    if not isinstance(client.get("dependency_versions"), dict):
        raise HandoffError("Missing dependency provenance")
    obs = client.get("observation")
    if not isinstance(obs, dict):
        raise HandoffError("Missing client observation")
    if obs.get("exception") is not None and obs.get("response_status") is not None:
        raise HandoffError("Exception and response status cannot coexist")
    if not isinstance(obs.get("redirect_history"), list):
        raise HandoffError("Missing redirect history")
    if not wire_raw or len(wire_raw) > MAX_BYTES:
        raise HandoffError("Empty or oversized wire log")
    try:
        wire = [json.loads(line) for line in wire_raw.splitlines() if line.strip()]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HandoffError("Invalid wire JSONL") from exc
    if not 1 <= len(wire) <= 2 or any(not isinstance(row, dict) for row in wire):
        raise HandoffError("Expected one isolated redirect attempt (one or two POST events)")
    if [row.get("path") for row in wire] not in (["/redirect"], ["/redirect", "/echo"]):
        raise HandoffError("Wire log is not one ordered redirect attempt")
    for row in wire:
        body = row.get("body_utf8")
        if (row.get("method") != "POST" or not isinstance(body, str)
                or not isinstance(row.get("length"), int)
                or row["length"] != len(body.encode("utf-8"))
                or row.get("sha256") != hashlib.sha256(body.encode("utf-8")).hexdigest()):
            raise HandoffError("Wire observation has inconsistent body hash/length")
    if obs.get("response_status") == 200:
        if (len(wire) != 2 or obs.get("exception") is not None
                or obs.get("response_url") != url.replace("/redirect", "/echo")
                or not any(isinstance(item, dict) and item.get("status") == 307
                           for item in obs["redirect_history"])):
            raise HandoffError("Successful redirect capture does not match wire sequence")
        response_text = obs.get("response_text")
        if not isinstance(response_text, str):
            raise HandoffError("Missing echo response")
        try:
            echoed = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise HandoffError("Invalid echo response") from exc
        if echoed != wire[1]:
            raise HandoffError("Client echo response disagrees with wire log")
    return {
        "schema": "m48-pending-reviewer-evidence-handoff-v1",
        "project_id": PROJECT, "case_id": CASE_ID,
        "reviewer": reviewer, "revision": revision,
        "source_commit": m47.REVISIONS[revision],
        "license": "Apache-2.0 (pinned source provenance from M44/M47)",
        "client_capture_sha256": hashlib.sha256(client_raw).hexdigest(),
        "wire_capture_sha256": hashlib.sha256(wire_raw).hexdigest(),
        "wire_post_count": len(wire),
        "wire_paths": [row["path"] for row in wire],
        "wire_body_lengths": [row["length"] for row in wire],
        "wire_body_sha256": [row["sha256"] for row in wire],
        "client_response_status": obs.get("response_status"),
        "client_exception_type": (obs["exception"].get("type")
                                  if isinstance(obs.get("exception"), dict) else None),
        "client_claims_independent_review": False,
        "human_approval_verified": False,
        "human_identity_verified": False,
        "independent_behavior_label": None,
        "adjudicated_label": None,
        "conformance_accuracy": None,
        "violation_precision": None,
        "violation_recall": None,
        "coverage": None,
        "held_out_scored": False,
        "review_required": [
            "Reviewer independently confirm environment, identity, execution approval, and capture authenticity.",
            "Reviewer assess both pinned revision observations and M20 source links; cite raw evidence in M44 behavior_seed.jsonl.",
            "Second independent reviewer submit separate evidence; third reviewer adjudicate without inferring labels from issue/fix.",
            "Freeze verifier and evaluate untouched external projects before computing conformance metrics.",
        ],
    }


def handoff(client_path: Path, wire_path: Path, reviewer: str, out_dir: Path) -> dict:
    if out_dir.exists():
        raise HandoffError("Refusing to overwrite existing handoff directory")
    client_raw, wire_raw = _read(client_path), _read(wire_path)
    result = inspect(client_raw, wire_raw, reviewer)
    out_dir.mkdir(parents=True)
    (out_dir / "client_observation.json").write_bytes(client_raw)
    (out_dir / "fixture_wire.jsonl").write_bytes(wire_raw)
    (out_dir / "pending_human_review.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", type=Path, required=True)
    parser.add_argument("--wire", type=Path, required=True)
    parser.add_argument("--reviewer", choices=("A", "B"), required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = handoff(args.client, args.wire, args.reviewer, args.out_dir)
    except (HandoffError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps({"case_id": result["case_id"], "revision": result["revision"],
                      "wire_post_count": result["wire_post_count"],
                      "status": "PENDING HUMAN REVIEW — NOT GOLD"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
