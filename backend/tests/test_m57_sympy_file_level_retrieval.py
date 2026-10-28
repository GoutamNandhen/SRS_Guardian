"""M57 unit tests use synthetic first-party fixtures, NEVER evaluation gold."""
import copy
import hashlib
import json

import pytest

from backend.evaluation import m29_pip_historical_regression as m29
from backend.evaluation import m52_swebench_verified_intake as m52
from backend.evaluation import m57_sympy_file_level_retrieval as m57


def sample(i=1):
    commit = str(i) * 40
    paths = [f"sympy/core/{name}.py" for name in
             ("widgets", "parsing", "matrix", "algebra", "logic", "other")]
    files = {
        path: ("def sample():\n    # " +
               ("widgets rendering canvas graphics" if "widgets" in path
                else "matrix numeric algorithm arrays") +
               "\n    return 1\n").encode()
        for path in paths
    }
    snapshot = {
        "commit": commit, "tree_sha": "a" * 40, "license_git_blob": "b" * 40,
        "files": files,
        "expected": {path: m29.blob_sha(raw) for path, raw in files.items()},
    }
    requirement = "The widgets rendering canvas graphics must work."
    patch = ("diff --git a/sympy/core/widgets.py b/sympy/core/widgets.py\n"
             "--- a/sympy/core/widgets.py\n+++ b/sympy/core/widgets.py\n"
             "@@ -1 +1 @@\n-old\n+new\n")
    case = {
        "review_case_id": f"CASE-{i:03d}", "instance_id": f"sympy__sympy-{1000+i}",
        "source_commit": commit,
        "requirement_sha256": m52.digest(requirement.encode()),
        "patch_sha256": m52.digest(patch.encode()),
    }
    row = {
        "instance_id": case["instance_id"], "base_commit": commit,
        "problem_statement": requirement, "patch": patch,
    }
    return case, row, snapshot


def test_file_retrieval_returns_actual_file_and_deterministic_order():
    _, row, snapshot = sample()
    first, truncated = m57.file_rank(snapshot, row["problem_statement"])
    second, _ = m57.file_rank(snapshot, row["problem_statement"])
    assert first == second
    assert len(first) == 5
    assert first[0]["path"] == "sympy/core/widgets.py"
    assert truncated == 0


def test_m20_file_level_reviewer_packets_are_unlabeled(tmp_path):
    cases = [m57.evaluate(*sample(i)) for i in (1, 2, 3)]
    report = m57.build(cases)
    assert report["development_cases"] == 3
    assert report["proxy_eligible"] == 3
    assert report["patch_file_hit_at_5_DEVELOPMENT_PROXY_NOT_GOLD"] == 3
    assert report["conformance_accuracy"] is None
    assert report["held_out_projects_scored"] == 0
    out = tmp_path / "review"
    m57.write(report, out)
    assert len((out / "reviewer_A.jsonl").read_text().splitlines()) == 15
    assert len((out / "reviewer_B.jsonl").read_text().splitlines()) == 15
    record = json.loads((out / "reviewer_A.jsonl").read_text().splitlines()[0])
    assert record["link_label"] is None
    assert record["behavioral_label"] is None
    assert "historical_patch" not in json.dumps(record)
    assert "instance_id" not in json.dumps(record)
    assert "score" not in json.dumps(record)
    assert record["symbol_id"].startswith("FILE-")
    with pytest.raises(ValueError, match="overwrite"):
        m57.write(report, out)


def test_rejects_tampered_source_and_mismatched_case():
    case, row, snapshot = sample()
    snapshot["files"]["sympy/core/widgets.py"] += b"\n# tampered"
    with pytest.raises(ValueError, match="Unverified"):
        m57.evaluate(case, row, snapshot)
    case, row, snapshot = sample()
    row["base_commit"] = "f" * 40
    with pytest.raises(ValueError, match="provenance"):
        m57.evaluate(case, row, snapshot)
    case, row, snapshot = sample()
    row["problem_statement"] += " tampered"
    with pytest.raises(ValueError, match="provenance"):
        m57.evaluate(case, row, snapshot)


def test_abstain_when_no_usable_terms_or_missing_source():
    _, _, snapshot = sample()
    with pytest.raises(ValueError, match="usable lexical"):
        m57.file_rank(snapshot, "the and but")
    del snapshot["files"]["sympy/core/widgets.py"]
    with pytest.raises(ValueError, match="Incomplete"):
        m57.file_rank(snapshot, "widgets")


def test_reviewer_labels_are_not_accepted_as_evidence():
    cases = [m57.evaluate(*sample(i)) for i in (1, 2, 3)]
    cases[0]["reviewer_rows"]["A"][0]["link_label"] = "linked"
    with pytest.raises(ValueError, match="unlabeled"):
        m57.build(cases)
