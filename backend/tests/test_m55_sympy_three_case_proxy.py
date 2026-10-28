"""Offline first-party M55 unit tests; fixtures are synthetic, never evaluation gold."""
import json
import pytest

from backend.evaluation import m52_swebench_verified_intake as m52
from backend.evaluation import m55_sympy_three_case_proxy as m55


def make_case(i, hit=True):
    cid = f"CASE-{i:03d}"
    instance = f"sympy__sympy-{1000+i}"
    patch = f"diff --git a/sympy/core/fix_{i}.py b/sympy/core/fix_{i}.py\n--- a/sympy/core/fix_{i}.py\n+++ b/sympy/core/fix_{i}.py\n@@ -1 +1 @@\n-old\n+new\n"
    case = {"review_case_id": cid, "instance_id": instance,
            "source_commit": str(i)*40, "requirement_sha256": "a"*64,
            "patch_sha256": m52.digest(patch.encode())}
    rows = {}
    for reviewer in ("A", "B"):
        rows[reviewer] = [{"case_id": f"PAIR-{i}-{j}", "project_id": "SYMPY",
                           "requirement_id": cid.replace("-", ""),
                           "source_path": f"sympy/core/other_{j}.py",
                           "link_label": None, "behavioral_label": None}
                          for j in range(5)]
    ranked = [{"path": f"sympy/core/other_{j}.py"} for j in range(5)]
    if hit:
        ranked[0]["path"] = f"sympy/core/fix_{i}.py"
    report = {"review_case_id": cid, "source_commit": str(i)*40,
              "git_tree_sha": "b"*40, "license": "BSD-3-Clause",
              "license_git_blob": "c"*40, "source_snapshot_sha256": "d"*64,
              "verified_production_python_files": 50,
              "indexed_production_symbols": 100,
              "m20_queue_sha256": "e"*64,
              "retrieval_method": "unchanged M42 normalized BM25",
              "internal_top_five_NOT_GOLD": ranked,
              "source_paths_verified": [f"sympy/core/fix_{i}.py"],
              "reviewer_rows": rows,
              "external_code_executed": False,
              "conformance_accuracy": None, "violation_precision": None,
              "violation_recall": None, "coverage": None}
    return case, report, {"instance_id": instance, "patch": patch}


def test_three_real_case_shape_but_synthetic_unit_data(tmp_path):
    cases = [make_case(1, True), make_case(2, False), make_case(3, True)]
    result = m55.assemble(cases)
    assert result["candidate_cases"] == 3
    assert result["historical_patch_file_proxy_eligible_cases"] == 3
    assert result["historical_patch_file_proxy_hits_at_5"] == 2
    assert result["m20_unlabeled_candidates_per_reviewer"] == 15
    assert result["conformance_accuracy"] is None
    assert result["independent_adjudications"] == 0
    out = tmp_path / "review"
    m55.write(result, out)
    internal = json.loads((out / "INTERNAL_DO_NOT_SHARE.json").read_text())
    assert len(internal["cases"]) == 3
    assert len((out / "reviewer_A.jsonl").read_text().splitlines()) == 15
    assert len((out / "reviewer_B.jsonl").read_text().splitlines()) == 15
    reviewer = (out / "reviewer_A.jsonl").read_text()
    assert "historical_patch" not in reviewer
    assert "proxy_eligible" not in reviewer
    assert "instance_id" not in reviewer
    with pytest.raises(ValueError, match="overwrite"):
        m55.write(result, out)


def test_patch_file_proxy_unindexable_and_nonproduction():
    report = {"internal_top_five_NOT_GOLD": [{"path": "sympy/core/other.py"}]}
    patch = ("diff --git a/sympy/core/new.py b/sympy/core/new.py\n"
             "diff --git a/sympy/core/tests/test_new.py b/sympy/core/tests/test_new.py\n")
    proxy = m55.fix_file_proxy(report, patch, {"sympy/core/other.py"})
    assert proxy["proxy_eligible"] is False
    assert proxy["historical_fix_file_hit_at_5_PROXY_NOT_GOLD"] is None
    assert proxy["historical_patch_production_files"] == ["sympy/core/new.py"]


def test_rejects_unverified_patch_or_mismatched_revision():
    cases = [make_case(1), make_case(2), make_case(3)]
    cases[0][2]["patch"] += "tamper"
    with pytest.raises(ValueError, match="digest mismatch"):
        m55.assemble(cases)
    cases = [make_case(1), make_case(2), make_case(3)]
    cases[0][1]["source_commit"] = "f"*40
    with pytest.raises(ValueError, match="revision mismatch"):
        m55.assemble(cases)


def test_rejects_colliding_review_ids_and_fake_conformance():
    cases = [make_case(1), make_case(2), make_case(3)]
    cases[1][1]["reviewer_rows"]["A"][0]["case_id"] = "PAIR-1-0"
    with pytest.raises(ValueError, match="collided"):
        m55.assemble(cases)
    cases = [make_case(1), make_case(2), make_case(3)]
    cases[0][1]["conformance_accuracy"] = 0.95
    with pytest.raises(ValueError, match="Unverified"):
        m55.assemble(cases)
