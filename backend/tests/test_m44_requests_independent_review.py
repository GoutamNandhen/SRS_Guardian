"""First-party checks for M44 external evidence; never execute Requests code."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.evaluation import m44_requests_independent_review as m44


@pytest.fixture(scope="module")
def pinned():
    return m44.fetch_pinned()


@pytest.fixture(scope="module")
def evidence(pinned):
    return m44.build_evidence(pinned)


def test_pinned_source_and_license_are_verified(pinned, evidence):
    assert set(pinned) == {"before", "after"}
    assert all(set(paths) == {m44.LICENSE, m44.SOURCE, m44.TEST}
               for paths in pinned.values())
    assert evidence["manifest"]["file_revision_objects_hash_verified"] == 6
    assert evidence["manifest"]["license"].startswith("Apache-2.0")
    assert evidence["manifest"]["source_anchors"]["before_source"].endswith("#L599")
    assert evidence["manifest"]["source_anchors"]["after_source"].endswith("#L600")
    assert evidence["manifest"]["source_anchors"]["after_test"].endswith("#L2076")


def test_hash_tampering_fails_closed(pinned):
    changed = {revision: dict(paths) for revision, paths in pinned.items()}
    changed["after"][m44.SOURCE] += b"\n# modified"
    with pytest.raises(m44.EvidenceError, match="Git blob mismatch"):
        m44.build_evidence(changed)


def test_missing_revision_fails_closed(pinned):
    with pytest.raises(m44.EvidenceError, match="revision"):
        m44.build_evidence({"after": pinned["after"]})


def test_m20_is_blinded_and_no_behavioral_labels(evidence):
    assert len(evidence["queue"]["queue"]) == 2
    assert evidence["queue"]["manifest"]["independent_labels_collected"] is False
    for row in evidence["queue"]["queue"]:
        assert "gold_link" not in row
        assert "sampling_provenance" not in row
    manifest = evidence["manifest"]
    assert manifest["independent_adjudications"] == 0
    assert manifest["approved_runtime_observations"] == 0
    assert manifest["held_out_scored"] is False
    assert all(value is None for value in manifest["metrics"].values())


def test_offline_review_handoff_is_pending(tmp_path: Path, pinned, evidence):
    root = tmp_path / "m44"
    m44.write_evidence(evidence, pinned, root)
    for reviewer in ("A", "B"):
        path = root / f"reviewer_{reviewer}"
        assert (path / "workspace.html").exists()
        assert (path / "source" / "before" / (m44.SOURCE + ".txt")).read_bytes() == pinned["before"][m44.SOURCE]
        links = [json.loads(x) for x in (path / "link_seed.jsonl").read_text().splitlines()]
        behaviors = [json.loads(x) for x in (path / "behavior_seed.jsonl").read_text().splitlines()]
        assert len(links) == 2 and len(behaviors) == 2
        assert all(row["link_label"] is None and row["annotation_status"] == "pending" for row in links)
        assert all(row["conformance_label"] is None and row["violation_label"] is None
                   and row["status"] == "pending" for row in behaviors)
        assert "Independent annotation workspace" in (path / "workspace.html").read_text()
    assert (root / "internal" / "evidence_manifest.json").exists()
    with pytest.raises(m44.EvidenceError, match="empty"):
        m44.write_evidence(evidence, pinned, root)


def test_unpinned_source_url_rejected():
    with pytest.raises(m44.EvidenceError, match="Unpinned"):
        m44.url("main", m44.SOURCE)
