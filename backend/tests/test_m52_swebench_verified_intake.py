"""First-party-only M52 intake checks; no external downloads or source execution."""
import hashlib
import json
import pytest

from backend.evaluation import m52_swebench_verified_intake as m52


def fake_rows():
    return [
        {
            "repo": "sympy/sympy",
            "instance_id": f"sympy__sympy-{number}",
            "base_commit": f"{number:040x}",
            "problem_statement": f"Real issue text {number}",
            "patch": f"diff --git a/x b/x {number}",
            "test_patch": f"diff --git a/tests b/tests {number}",
            "FAIL_TO_PASS": '["test_case"]',
        }
        for number in (3, 2, 1)
    ]


LICENSE = b"""Redistribution and use in source and binary forms
Neither the name of SymPy
THIS SOFTWARE IS PROVIDED"""


def test_bounded_verified_license_intake():
    urls = []
    def get_license(url):
        urls.append(url)
        return LICENSE
    manifest = m52.build_manifest(fake_rows(), license_fetch=get_license, count=2)
    assert [x["instance_id"] for x in manifest["candidate_cases"]] == [
        "sympy__sympy-1", "sympy__sympy-2"]
    assert len(urls) == 2
    assert all(x["source_tree_blobs_verified"] is False for x in manifest["candidate_cases"])
    assert manifest["conformance_accuracy"] is None
    assert manifest["independent_behavioral_labels"] == 0
    assert manifest["held_out_projects_scored"] == 0


def test_invalid_license_rejected():
    with pytest.raises(ValueError, match="license"):
        m52.build_manifest(fake_rows(), license_fetch=lambda _: b"MIT", count=1)


def test_missing_test_patch_rejected():
    rows = fake_rows()
    rows[-1]["test_patch"] = ""
    with pytest.raises(ValueError, match="test_patch"):
        m52.build_manifest(rows, license_fetch=lambda _: LICENSE, count=1)


def test_no_patch_leak_in_reviewer_intake(tmp_path):
    manifest = m52.build_manifest(fake_rows(), license_fetch=lambda _: LICENSE, count=1)
    m52.write_manifest(manifest, tmp_path)
    reviewer = (tmp_path / "reviewer_A_intake_NOT_M20_GOLD.jsonl").read_text()
    assert "diff --git" not in reviewer
    assert "sympy__sympy-" not in reviewer
    assert "historical_pr_url" not in reviewer
    assert "/pull/" not in reviewer
    assert "Real issue text 1" in reviewer
    assert '"review_case_id": "CASE-001"' in reviewer
    internal = json.loads((tmp_path / "INTERNAL_PROVENANCE_NOT_GOLD.json").read_text())
    assert internal["candidate_cases"][0]["historical_pr_url"].endswith("/pull/1")
    assert internal["candidate_cases"][0]["instance_id"] == "sympy__sympy-1"
    assert '"link_label": null' in reviewer
    assert '"behavioral_label": null' in reviewer
    assert "pending_source_tree_and_m20_queue" in reviewer


def test_dataset_hash_rejected_without_parsing():
    with pytest.raises(ValueError, match="SHA-256"):
        m52.verify_dataset(b"not pinned parquet")


def test_duplicate_candidates_rejected():
    with pytest.raises(ValueError, match="Duplicate"):
        m52.build_manifest(fake_rows() + fake_rows()[:1],
                           license_fetch=lambda _: LICENSE, count=2)
