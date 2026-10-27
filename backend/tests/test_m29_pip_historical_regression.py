"""Offline tests for M29. These fixtures are NOT external evidence or gold."""
from __future__ import annotations

import json

import pytest

from backend.evaluation import m29_pip_historical_regression as m29


def _fixtures(monkeypatch):
    license_text = b"Copyright (c) pip developers\nPermission is hereby granted, free of charge\n"
    before_source = b"def _make_candidate_from_link(\n    pass\n"
    after_source = (
        b"def _make_candidate_from_link(\n    pass\n"
        b"def _make_base_candidate_from_link(\n    install_req_drop_extras\n"
    )
    before_test = b"def unrelated_test():\n    pass\n"
    after_test = (
        b"def test_new_resolver_constraint_on_link_with_extra(\n    pass\n"
        b"def test_new_resolver_constraint_on_link_with_extra_indirect(\n    pass\n"
    )
    files = {
        "before": {m29.LICENSE: license_text, m29.SOURCE: before_source, m29.TEST: before_test},
        "after": {m29.LICENSE: license_text, m29.SOURCE: after_source, m29.TEST: after_test},
    }
    monkeypatch.setattr(
        m29, "FILES",
        {rev: {path: m29.blob_sha(raw) for path, raw in paths.items()} for rev, paths in files.items()},
    )
    return files


def test_build_and_write_unadjudicated_review_packet(monkeypatch, tmp_path):
    result = m29.build_evidence(_fixtures(monkeypatch))
    assert result["internal"]["static_file_revision_objects_verified"] == 6
    assert result["internal"]["distinct_git_blobs_verified"] == 5
    assert result["internal"]["upstream_behavior_scenarios"] == 3
    assert result["internal"]["m20_link_pairs_pending"] == 6
    assert result["internal"]["behavior_revision_cases_pending_per_reviewer"] == 6
    assert len(result["queue"]["queue"]) == 6
    assert result["internal"]["external_code_executed"] is False
    assert result["internal"]["representative_held_out"] is False
    for metric in ("conformance_accuracy", "violation_precision", "violation_recall", "conformance_coverage"):
        assert result["internal"][metric] is None
    m29.write_evidence(result, tmp_path)
    reviewer = tmp_path / "reviewers"
    assert not (reviewer / "manifest.json").exists()
    for name in ("reviewer_A.jsonl", "reviewer_B.jsonl"):
        rows = [json.loads(line) for line in (reviewer / name).read_text().splitlines()]
        assert len(rows) == 6
        assert all(row["link_label"] is None and row["annotation_status"] == "pending" for row in rows)
    for name in ("behavior_reviewer_A.jsonl", "behavior_reviewer_B.jsonl"):
        rows = [json.loads(line) for line in (reviewer / name).read_text().splitlines()]
        assert len(rows) == 6
        assert all(row["observed_behavior"] is None and row["conformance_label"] is None
                   and row["violation_label"] is None for row in rows)
        assert "23.3.1" not in (reviewer / name).read_text()
    assert "23.3.1" not in (reviewer / "source_index.json").read_text()
    internal = json.loads((tmp_path / "internal" / "internal.json").read_text())
    assert internal["reporter_allegations_not_gold"][0]["case_id"] == "PIP_ISSUE_12372"
    assert (tmp_path / "internal" / "m20_sampling_manifest.json").exists()


def test_modified_pinned_source_fails_closed(monkeypatch):
    files = _fixtures(monkeypatch)
    files["before"][m29.SOURCE] += b"tampered"
    with pytest.raises(m29.EvidenceError, match="Git blob mismatch"):
        m29.build_evidence(files)


def test_missing_post_fix_test_fails_closed(monkeypatch):
    files = _fixtures(monkeypatch)
    files["after"][m29.TEST] = b"def unrelated_test():\n    pass\n"
    monkeypatch.setattr(
        m29, "FILES",
        {rev: {path: m29.blob_sha(raw) for path, raw in paths.items()} for rev, paths in files.items()},
    )
    with pytest.raises(m29.EvidenceError, match="regression tests"):
        m29.build_evidence(files)


def test_license_missing_fails_closed(monkeypatch):
    files = _fixtures(monkeypatch)
    files["after"][m29.LICENSE] = b"unknown rights"
    monkeypatch.setattr(
        m29, "FILES",
        {rev: {path: m29.blob_sha(raw) for path, raw in paths.items()} for rev, paths in files.items()},
    )
    with pytest.raises(m29.EvidenceError, match="MIT license"):
        m29.build_evidence(files)


def test_real_pins_and_revision_separation():
    assert len(m29.BEFORE) == len(m29.AFTER) == 40
    assert m29.BEFORE != m29.AFTER
    assert set(m29.FILES) == {"before", "after"}
    assert all(len(sha) == 40 for paths in m29.FILES.values() for sha in paths.values())
    assert m29.FILES["before"][m29.SOURCE] != m29.FILES["after"][m29.SOURCE]
    assert m29.FILES["before"][m29.TEST] != m29.FILES["after"][m29.TEST]
    assert m29.FILES["before"][m29.LICENSE] == m29.FILES["after"][m29.LICENSE]
