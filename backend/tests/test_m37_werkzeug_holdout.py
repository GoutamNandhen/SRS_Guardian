"""M37 first-party engineering tests; never score external behavior as gold."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.evaluation import m37_werkzeug_holdout as m37


@pytest.fixture(scope="module")
def pinned():
    # Download only pinned text files; do not import or execute Werkzeug.
    files = m37.fetch_pinned()
    return files, m37.build_evidence(files)


def test_verified_real_upstream_snapshots_and_license(pinned):
    files, evidence = pinned
    assert sum(len(paths) for paths in files.values()) == 8
    assert files["before"][m37.LICENSE] == files["after"][m37.LICENSE]
    assert files["before"][m37.CALLER] == files["after"][m37.CALLER]
    assert files["before"][m37.PARSER] != files["after"][m37.PARSER]
    assert files["before"][m37.TEST] != files["after"][m37.TEST]
    manifest = evidence["manifest"]
    assert manifest["license"].startswith("BSD-3-Clause")
    assert manifest["file_revision_objects_verified"] == 8
    assert manifest["independent_adjudications"] == 0
    assert manifest["external_project_code_executed"] is False
    assert all(value is None for value in manifest["metrics"].values())
    assert manifest["held_out_candidate_only"] is True


def test_m20_reviewers_are_blinded_and_unlabeled(pinned):
    _, evidence = pinned
    queue = evidence["queue"]
    assert queue["manifest"]["possible_pairs"] == 6
    assert queue["manifest"]["sampled_pairs"] == 6
    assert len(queue["queue"]) == 6
    assert len({x["case_id"] for x in queue["queue"]}) == 6
    assert all("origin" not in row and "gold" not in row
               for row in queue["queue"])
    assert queue["manifest"]["independent_labels_collected"] is False


def test_reviewer_packet_requires_humans_and_independent_runtime_evidence(pinned, tmp_path):
    _, evidence = pinned
    m37.write_evidence(evidence, tmp_path)
    reviewers = tmp_path / "reviewers"
    for reviewer in ("A", "B"):
        links = [json.loads(x) for x in (reviewers / f"reviewer_{reviewer}.jsonl").read_text().splitlines()]
        behaviors = [json.loads(x) for x in (reviewers / f"behavior_reviewer_{reviewer}.jsonl").read_text().splitlines()]
        assert len(links) == 6
        assert len(behaviors) == 4
        assert all(row["link_label"] is None and row["annotation_status"] == "pending" for row in links)
        assert all(row["conformance_label"] is None and row["violation_label"] is None
                   and row["approved_runtime_evidence"] is None and row["status"] == "pending"
                   for row in behaviors)
        assert {row["revision"] for row in behaviors} == {"before", "after"}
    assert "sampling_provenance" not in (reviewers / "blind_queue.jsonl").read_text()
    assert not (reviewers / "manifest.json").exists()
    assert (tmp_path / "internal" / "m20" / "manifest.json").exists()
    assert (tmp_path / "internal" / "evidence_manifest.json").exists()


def test_tampered_pinned_bytes_fail_closed(pinned):
    files, _ = pinned
    mutated = {revision: dict(paths) for revision, paths in files.items()}
    mutated["after"][m37.PARSER] += b"#tampered\n"
    with pytest.raises(m37.EvidenceError, match="Git blob mismatch"):
        m37.build_evidence(mutated)


def test_snapshot_and_blind_queue_deterministic(pinned):
    files, evidence = pinned
    again = m37.build_evidence(files)
    assert evidence["queue"]["manifest"]["blind_queue_sha256"] == again["queue"]["manifest"]["blind_queue_sha256"]
    assert evidence["manifest"]["source_provenance"] == again["manifest"]["source_provenance"]
