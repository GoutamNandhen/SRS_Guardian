"""M15 regression: gold-lock fingerprint and unfinished annotation fail-closed checks.

Fixtures are fabricated, never independent research evidence.
"""
from __future__ import annotations

import pytest

from backend.evaluation.evaluate_conformance import EvaluationError
from backend.evaluation.m5_research_benchmark import (
    audit_benchmark, canonical_digest, compare_systems,
)
from backend.tests.test_m14_snapshot_independence import real_case


def test_gold_fingerprint_not_overwritten_by_last_source_snapshot():
    rows = [
        real_case("A", "one", "train", "a" * 64),
        real_case("B", "two", "test", "b" * 64),
    ]
    locked = canonical_digest(rows)
    report = audit_benchmark(rows, expected_sha256=locked)
    assert report["fingerprint_sha256"] == locked
    assert report["fingerprint_sha256"] != rows[-1]["code_snapshot_sha256"]
    assert report["real_distinct_source_snapshots"] == 2


def test_gold_lock_remains_bound_to_all_rows_when_source_digest_unchanged():
    rows = [real_case("A", "one", "test", "a" * 64)]
    original_lock = canonical_digest(rows)
    assert audit_benchmark(rows, expected_sha256=original_lock)["fingerprint_sha256"] == original_lock
    changed = [dict(rows[0], requirement_text="A changed requirement label")]
    assert canonical_digest(changed) != original_lock
    with pytest.raises(EvaluationError, match="fingerprint"):
        audit_benchmark(changed, expected_sha256=original_lock)


def test_real_claim_with_draft_annotation_cannot_pass_provenance():
    row = real_case("A", "one", "test", "a" * 64)
    row["adjudication_status"] = "draft"
    report = audit_benchmark([row], expected_sha256=canonical_digest([row]))
    assert report["fingerprint_sha256"] == canonical_digest([row])
    assert any("draft labels are not accepted" in x for x in report["critical_issues"])
    assert report["research_eligible_by_provenance"] is False


def test_draft_in_train_split_blocks_test_claim_even_with_valid_lock(tmp_path):
    train = real_case("A", "one", "train", "a" * 64)
    train["adjudication_status"] = "draft"
    test = real_case("B", "two", "test", "b" * 64)
    rows = [train, test]
    report = compare_systems(
        rows, {"baseline": [], "proposed": []},
        evidence_roots={"baseline": tmp_path, "proposed": tmp_path},
        benchmark_lock=canonical_digest(rows),
    )
    assert report["audit"]["research_eligible_by_provenance"] is False
    assert report["status"] == "COMPARISON_ONLY_NOT_PUBLICATION_READY"
    assert all(
        value["acceptance"]["status"] == "BLOCKED_BY_M5_PROVENANCE_OR_LOCK"
        for value in report["systems"].values()
    )


def test_adjudicated_real_claim_still_only_passes_structural_screen():
    rows = [real_case("A", "one", "test", "a" * 64)]
    report = audit_benchmark(rows, expected_sha256=canonical_digest(rows))
    assert report["critical_issues"] == []
    assert report["research_eligible_by_provenance"] is True
    assert "independent human" in report["note"]


def test_synthetic_draft_does_not_masquerade_as_real():
    row = real_case("A", "one", "test", "a" * 64)
    row["dataset_status"] = "synthetic_fixture"
    row["adjudication_status"] = "draft"
    report = audit_benchmark([row])
    assert report["research_eligible_by_provenance"] is False
    assert report["real_distinct_source_snapshots"] == 0
