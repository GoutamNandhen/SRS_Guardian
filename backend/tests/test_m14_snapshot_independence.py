"""M14: source snapshot independence checks (no claims of model accuracy)."""
from __future__ import annotations

from backend.evaluation.m5_research_benchmark import audit_benchmark, canonical_digest


def real_case(case_id: str, project: str, split: str, digest: str) -> dict:
    return {
        "case_id": case_id,
        "project_id": project,
        "split": split,
        "requirement_id": "REQ-" + case_id,
        "requirement_text": "The " + case_id + " service shall reject requests above a limit.",
        "candidate_code_ref": "src/" + project + "/rules.py::check_" + case_id,
        "source_commit": (case_id.lower() + "0" * 40)[:40],
        "annotation_source": "independently adjudicated external source (test stub)",
        "adjudication_status": "adjudicated",
        "dataset_status": "real_adjudicated",
        "gold_link": True,
        "gold_conformance": "violates",
        "public_source_url": "https://example.org/" + project,
        "source_license": "MIT",
        "code_snapshot_sha256": digest,
        "annotator_1": "reviewer-a",
        "annotator_2": "reviewer-b",
        "adjudication_record": "review record (test stub)",
        "oracle_provenance": "test-only oracle",
        "reproduction_instructions": "not executable (test stub)",
    }


def test_reused_snapshot_across_project_ids_and_splits_blocks_research():
    rows = [real_case("A", "upstream", "train", "a" * 64),
            real_case("B", "fork", "test", "a" * 64)]
    report = audit_benchmark(rows, expected_sha256=canonical_digest(rows))
    assert report["projects"] == 2
    assert report["real_distinct_source_snapshots"] == 1
    assert any("identical source snapshot" in issue for issue in report["critical_issues"])
    assert report["research_eligible_by_provenance"] is False


def test_reused_snapshot_within_same_split_does_not_count_as_two_projects():
    rows = [real_case("A", "upstream", "test", "a" * 64),
            real_case("B", "fork", "test", "a" * 64)]
    report = audit_benchmark(rows)
    assert report["real_distinct_source_snapshots"] == 1
    assert any("cannot count as independent projects" in issue for issue in report["critical_issues"])
    assert report["research_eligible_by_provenance"] is False


def test_repeated_snapshot_within_one_project_is_permitted():
    rows = [real_case("A", "same", "test", "a" * 64),
            real_case("B", "same", "test", "a" * 64)]
    report = audit_benchmark(rows)
    assert report["real_distinct_source_snapshots"] == 1
    assert report["critical_issues"] == []
    assert report["research_eligible_by_provenance"] is True


def test_independent_digests_can_pass_structural_screen_but_not_human_review():
    rows = [real_case("A", "one", "train", "a" * 64),
            real_case("B", "two", "test", "b" * 64)]
    report = audit_benchmark(rows)
    assert report["real_distinct_source_snapshots"] == 2
    assert report["critical_issues"] == []
    assert report["research_eligible_by_provenance"] is True
    assert "independent human" in report["note"]


def test_invalid_or_uppercase_or_missing_snapshot_digest_is_blocked():
    for digest in ("not-a-digest", "A" * 64, "", None):
        row = real_case("A", "one", "test", digest)
        report = audit_benchmark([row])
        assert any("code_snapshot_sha256 must be" in issue for issue in report["critical_issues"])
        assert report["research_eligible_by_provenance"] is False


def test_synthetic_rows_never_become_real_evidence():
    row = real_case("A", "one", "test", "a" * 64)
    row["dataset_status"] = "synthetic_fixture"
    report = audit_benchmark([row])
    assert report["research_eligible_by_provenance"] is False
    assert report["real_distinct_source_snapshots"] == 0
