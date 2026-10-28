"""Offline synthetic unit fixtures only; never conformance evaluation data."""
import json
import pytest
from backend.evaluation import m56_sympy_regression_review_handoff as m56


def fixtures():
    selected, rows, provenance = [], [], []
    reviewer_rows = {"A": [], "B": []}
    for i in range(1, 4):
        cid = f"CASE-{i:03d}"
        instance = f"sympy__sympy-{1000+i}"
        req = f"The function should preserve property {i}."
        patch = (f"diff --git a/sympy/core/logic.py b/sympy/core/logic.py\n"
                 "--- a/sympy/core/logic.py\n+++ b/sympy/core/logic.py\n"
                 "@@ -1 +1 @@\n-x\n+y\n")
        test_patch = ("diff --git a/sympy/core/tests/test_logic.py "
                      "b/sympy/core/tests/test_logic.py\n"
                      "--- a/sympy/core/tests/test_logic.py\n"
                      "+++ b/sympy/core/tests/test_logic.py\n"
                      f"@@ -1 +1 @@\n-x\n+assert {i}\n")
        tests = json.dumps([f"sympy/core/tests/test_logic.py::test_case_{i}"])
        source_commit = str(i)*40
        rows.append({"instance_id": instance, "repo": "sympy/sympy", "base_commit": source_commit,
                     "problem_statement": req, "patch": patch, "test_patch": test_patch,
                     "FAIL_TO_PASS": tests})
        selected.append({"review_case_id": cid, "instance_id": instance,
                         "source_commit": source_commit, "requirement_sha256": m56.digest(req),
                         "patch_sha256": m56.digest(patch), "test_patch_sha256": m56.digest(test_patch),
                         "fail_to_pass_metadata_sha256": m56.digest(tests)})
        provenance.append({"review_case_id": cid, "instance_id_INTERNAL": instance,
                           "source_commit": source_commit, "requirement_sha256": m56.digest(req),
                           "historical_patch_sha256": m56.digest(patch),
                           "source_snapshot_sha256": "a"*64, "license": "BSD-3-Clause",
                           "license_git_blob": "b"*40})
        for reviewer in ("A", "B"):
            for j in range(5):
                reviewer_rows[reviewer].append({"review_case_id": cid, "case_id": f"PAIR-{i}-{j}",
                                               "source_commit": source_commit, "link_label": None,
                                               "behavioral_label": None})
    m55 = {"project": "sympy/sympy", "candidate_cases": 3, "cases": provenance,
           "external_code_executed": False, "independent_behavioral_labels": 0,
           "independent_adjudications": 0}
    return m55, selected, rows, reviewer_rows


def test_real_test_handoff_shape_with_synthetic_fixtures(tmp_path):
    result = m56.build(*fixtures())
    assert result["case_count"] == 3
    assert result["independent_behavioral_observations"] == 0
    assert result["conformance_accuracy"] is None
    out = tmp_path / "review"
    m56.write(result, out)
    assert len((out / "behavior_reviewer_A.jsonl").read_text().splitlines()) == 3
    packet = json.loads((out / "behavior_reviewer_A.jsonl").read_text().splitlines()[0])
    assert len(packet["m20_candidate_pair_ids"]) == 5
    assert packet["independent_behavioral_label"] is None
    assert "historical_patch" not in packet
    assert "instance_id" not in packet
    assert packet["candidate_fail_to_pass_test_ids"]
    with pytest.raises(ValueError, match="overwrite"):
        m56.write(result, out)


def test_tampered_test_patch_and_requirement_rejected():
    args = list(fixtures())
    args[2][0]["test_patch"] += "tampered"
    with pytest.raises(ValueError, match="provenance mismatch"):
        m56.build(*args)
    args = list(fixtures())
    args[2][0]["problem_statement"] = "different requirement"
    with pytest.raises(ValueError, match="provenance mismatch"):
        m56.build(*args)


def test_m20_unlabeled_and_revision_alignment_required():
    args = list(fixtures())
    args[3]["A"][0]["link_label"] = "linked"
    with pytest.raises(ValueError, match="already contains labels"):
        m56.build(*args)
    args = list(fixtures())
    args[3]["B"][0]["source_commit"] = "f"*40
    with pytest.raises(ValueError, match="revision mismatch"):
        m56.build(*args)


def test_test_ids_and_paths_are_inert_and_checked():
    assert m56.parse_test_ids('["a::test_one"]') == ["a::test_one"]
    with pytest.raises(ValueError, match="duplicate"):
        m56.parse_test_ids('["same", "same"]')
    with pytest.raises(ValueError, match="Invalid"):
        m56.parse_test_ids("not json")
    with pytest.raises(ValueError, match="path"):
        m56.test_paths("diff --git a/../bad.py b/../bad.py\n")
