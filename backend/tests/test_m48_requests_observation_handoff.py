"""Synthetic first-party-only tests; no external Requests import or execution."""
import hashlib
import copy
import json

import pytest

from backend.evaluation import m47_requests_approved_reviewer_capture as m47
from backend.evaluation import m48_requests_observation_handoff as m48


def row(path, body):
    return {"path": path, "method": "POST", "length": len(body),
            "sha256": hashlib.sha256(body).hexdigest(), "body_utf8": body.decode(),
            "transfer_encoding": None, "content_length": str(len(body))}


def sample(revision="before", body=b"data", exception=False):
    wire = [row("/redirect", body)]
    if not exception:
        wire.append(row("/echo", body))
    url = "http://127.0.0.1:8765/redirect"
    obs = {"response_status": None if exception else 200,
           "redirect_history": [] if exception else [{"status": 307, "url": url}],
           "response_url": None if exception else url.replace("/redirect", "/echo"),
           "response_text": None if exception else json.dumps(wire[1]),
           "exception": {"type": "SyntheticError", "message": "mock"} if exception else None}
    client = {"schema": "m47-approved-reviewer-observation-v1",
              "reviewer_supplied": True, "independent_adjudication": False,
              "behavior_label": None, "revision": revision,
              "git_commit": m47.REVISIONS[revision],
              "verified_git_blobs": copy.deepcopy(m47.BLOBS[revision]), "fixture_url": url,
              "expected_payload_sha256": hashlib.sha256(m47.PAYLOAD).hexdigest(),
              "expected_payload_length": len(m47.PAYLOAD),
              "captured_at_utc": "2026-10-28T12:00:00Z", "python": "synthetic",
              "platform": "synthetic", "requests_module_path": "/synthetic/src/requests/__init__.py",
              "dependency_versions": {}, "observation": obs}
    return client, wire


def encode(client, wire):
    return json.dumps(client).encode(), ("\n".join(json.dumps(r) for r in wire) + "\n").encode()


def test_success_is_pending_not_gold(tmp_path):
    client, wire = sample()
    raw_client, raw_wire = encode(client, wire)
    (tmp_path / "client.json").write_bytes(raw_client)
    (tmp_path / "wire.jsonl").write_bytes(raw_wire)
    out = tmp_path / "handoff"
    result = m48.handoff(tmp_path / "client.json", tmp_path / "wire.jsonl", "A", out)
    assert result["wire_body_lengths"] == [4, 4]
    assert result["adjudicated_label"] is None
    assert result["independent_behavior_label"] is None
    assert result["human_approval_verified"] is False
    assert result["conformance_accuracy"] is None
    assert (out / "client_observation.json").read_bytes() == raw_client
    assert (out / "fixture_wire.jsonl").read_bytes() == raw_wire
    with pytest.raises(m48.HandoffError, match="overwrite"):
        m48.handoff(tmp_path / "client.json", tmp_path / "wire.jsonl", "A", out)


def test_exception_can_be_captured_without_fabricating_violation():
    client, wire = sample("after", exception=True)
    result = m48.inspect(*encode(client, wire), "B")
    assert result["wire_post_count"] == 1
    assert result["client_exception_type"] == "SyntheticError"
    assert result["independent_behavior_label"] is None


def test_body_loss_is_observation_not_verdict():
    client, wire = sample(body=b"")
    result = m48.inspect(*encode(client, wire), "A")
    assert result["wire_body_lengths"] == [0, 0]
    assert result["violation_recall"] is None


@pytest.mark.parametrize("change", ["revision", "blob", "label", "url", "echo", "hash", "extra"])
def test_mismatched_evidence_fails_closed(change):
    client, wire = sample()
    if change == "revision":
        client["git_commit"] = m47.REVISIONS["after"]
    elif change == "blob":
        client["verified_git_blobs"]["LICENSE"] = "0" * 40
    elif change == "label":
        client["behavior_label"] = "conforms"
    elif change == "url":
        client["fixture_url"] = "http://example.com/redirect"
    elif change == "echo":
        client["observation"]["response_text"] = "{}"
    elif change == "hash":
        wire[1]["sha256"] = "0" * 64
    else:
        wire.append(row("/echo", b"data"))
    with pytest.raises(m48.HandoffError):
        m48.inspect(*encode(client, wire), "A")


def test_invalid_reviewer_and_empty_wire_fail():
    client, wire = sample()
    with pytest.raises(m48.HandoffError):
        m48.inspect(*encode(client, wire), "C")
    with pytest.raises(m48.HandoffError):
        m48.inspect(json.dumps(client).encode(), b"", "A")
