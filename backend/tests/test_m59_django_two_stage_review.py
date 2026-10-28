"""Offline first-party tests for M59; all source bytes are synthetic, NOT GOLD."""
import json

import pytest

from backend.evaluation import m29_pip_historical_regression as m29
from backend.evaluation import m58_django_frozen_file_transfer as m58
from backend.evaluation import m59_django_two_stage_review as m59


def fixture():
    files = {
        f"django/core/module_{i}.py":
        (f"def process_{i}(request):\n    return 'alpha beta gamma {i}'\n").encode()
        for i in range(6)
    }
    snapshot = {
        "commit": "a" * 40,
        "tree_sha": "b" * 40,
        "license_git_blob": "c" * 40,
        "license_sha256": "d" * 64,
        "files": files,
        "expected": {p: m29.blob_sha(raw) for p, raw in files.items()},
    }
    row = {
        "repo": "django/django",
        "instance_id": "django__django-1",
        "base_commit": snapshot["commit"],
        "problem_statement": "alpha beta gamma process_3",
        "patch": "diff --git a/django/core/module_3.py b/django/core/module_3.py\n",
        "test_patch": "diff --git a/tests/test_feature.py b/tests/test_feature.py\n"
                      "@@ -1 +1 @@\n+assert feature()\n",
        "FAIL_TO_PASS": json.dumps(["tests.test_feature.FeatureTests.test_case"]),
    }
    internal, reviewers = m58.evaluate(row, snapshot)
    return row, snapshot, internal, reviewers


def test_stage1_source_is_pinned_and_stage2_keeps_test_patch_separate(tmp_path):
    row, snapshot, internal, reviewers = fixture()
    result = m59.build(row, snapshot, internal, reviewers)
    assert result["internal"]["source_candidates_per_reviewer"] == 5
    assert result["internal"]["candidate_regression_tests"] == 1
    assert result["internal"]["conformance_accuracy"] is None
    assert result["internal"]["violation_precision"] is None
    assert result["internal"]["violation_recall"] is None
    assert result["internal"]["coverage"] is None
    assert result["internal"]["external_project_code_executed"] is False
    assert {x["case_id"] for x in result["stage1"]["A"]} == {
        x["case_id"] for x in result["stage1"]["B"]}
    for reviewer in ("A", "B"):
        for candidate in result["stage1"][reviewer]:
            raw = snapshot["files"][candidate["source_path"]]
            assert candidate["source_git_blob"] == m29.blob_sha(raw)
            assert candidate["source_file_sha256"] == m59.sha(raw)
            assert candidate["independent_link_decision"] is None
            assert candidate["source_excerpt"]["source_lines"]
            assert "candidate_test_patch" not in candidate
            assert row["test_patch"] not in json.dumps(candidate)
        test = result["stage2"][reviewer]
        assert test["candidate_test_patch_UNTRUSTED_TEXT"] == row["test_patch"]
        assert test["independent_behavioral_label"] is None
        assert test["before_revision_observation"] is None
        assert test["after_revision_observation"] is None
    out = tmp_path / "m59"
    m59.write(result, out)
    assert len((out / "reviewer_A_stage1.jsonl").read_text().splitlines()) == 5
    assert json.loads((out / "reviewer_B_stage2.json").read_text())[
        "test_relevance_decision"] is None
    with pytest.raises(ValueError, match="overwrite"):
        m59.write(result, out)


def test_rejects_tampered_source_and_pinned_metadata():
    row, snapshot, internal, reviewers = fixture()
    path = reviewers["A"][0]["source_path"]
    snapshot["files"][path] = b"tampered"
    with pytest.raises(ValueError, match="Git blob mismatch"):
        m59.build(row, snapshot, internal, reviewers)
    row, snapshot, internal, reviewers = fixture()
    internal["historical_test_patch_sha256_INTERNAL"] = "0" * 64
    with pytest.raises(ValueError, match="mismatch"):
        m59.build(row, snapshot, internal, reviewers)


def test_rejects_prelabelled_or_mismatched_reviewers():
    row, snapshot, internal, reviewers = fixture()
    reviewers["A"][0]["link_label"] = "linked"
    with pytest.raises(ValueError, match="unlabeled"):
        m59.build(row, snapshot, internal, reviewers)
    row, snapshot, internal, reviewers = fixture()
    reviewers["B"][0]["case_id"] = "different"
    with pytest.raises(ValueError, match="differ"):
        m59.build(row, snapshot, internal, reviewers)


def test_test_patch_is_inert_and_fail_to_pass_is_only_expectation():
    row, snapshot, internal, reviewers = fixture()
    row["FAIL_TO_PASS"] = "not-json"
    with pytest.raises(ValueError, match="FAIL_TO_PASS"):
        m59.build(row, snapshot, internal, reviewers)
    assert m59.test_patch_paths("diff --git a/tests/a.py b/tests/a.py\n") == [
        "tests/a.py"]
    with pytest.raises(ValueError, match="Unsafe"):
        m59.test_patch_paths("diff --git a/../evil.py b/../evil.py\n")


def test_excerpt_has_correct_line_numbers_and_does_not_execute():
    raw = b"def a():\n    return 'ordinary'\ndef b():\n    return 'special_token'\n"
    result = m59.excerpt(raw, "special_token")
    assert result["start_line"] == 1
    assert result["end_line"] == 4
    assert result["source_lines"][3] == {
        "line": 4, "text": "    return 'special_token'"}


def test_upstream_empty_and_repeated_test_metadata_is_preserved():
    assert m59.expected_tests("[]") == []
    assert m59.expected_tests('["x", "x"]') == ["x", "x"]
