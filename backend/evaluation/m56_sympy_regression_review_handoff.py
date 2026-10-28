"""M56: connect real pinned SWE-bench regression tests to M55/M20 review.

Upstream test patches are inert candidate evidence, not independent behavioral
labels. Never import, apply, or execute external project code in this tool.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath

SCHEMA = "m56-sympy-regression-review-handoff-1"
DIFF = re.compile(r"^diff --git a/(\S+) b/(\S+)$", re.MULTILINE)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_paths(patch: str) -> list[str]:
    if not isinstance(patch, str) or not patch.strip() or len(patch) > 500_000:
        raise ValueError("Missing or oversized upstream test patch")
    matches = DIFF.findall(patch)
    if not matches:
        raise ValueError("Upstream test patch has no file paths")
    paths = set()
    for before, after in matches:
        for path in (before, after):
            parts = PurePosixPath(path).parts
            if (path.startswith("/") or "\\" in path or ".." in parts
                    or not path.startswith("sympy/") or not path.endswith(".py")):
                raise ValueError("Unexpected upstream test patch path")
        paths.add(after)
    return sorted(paths)


def parse_test_ids(raw: str) -> list[str]:
    try:
        tests = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise ValueError("Invalid FAIL_TO_PASS JSON") from exc
    if (not isinstance(tests, list) or not 1 <= len(tests) <= 100
            or any(not isinstance(t, str) or not t.strip() or len(t) > 500 for t in tests)
            or len(tests) != len(set(tests))):
        raise ValueError("Missing, duplicate or invalid FAIL_TO_PASS test IDs")
    return tests


def build(m55: dict, selected: list[dict], dataset: list[dict],
          reviewer_rows: dict[str, list[dict]]) -> dict:
    """Bind independently reviewable tests to the already verified M55 cases."""
    if (m55.get("project") != "sympy/sympy" or m55.get("candidate_cases") != 3
            or len(m55.get("cases", [])) != 3 or len(selected) != 3):
        raise ValueError("Expected the three M55 SymPy cases")
    if (m55.get("external_code_executed") is not False
            or m55.get("independent_behavioral_labels") != 0
            or m55.get("independent_adjudications") != 0):
        raise ValueError("M55 provenance cannot support behavioral claims")
    cases = {c["review_case_id"]: c for c in m55["cases"]}
    rows = {r["instance_id"]: r for r in dataset}
    if len(cases) != 3 or len(rows) != len(dataset):
        raise ValueError("Duplicate case or dataset identifiers")
    if set(reviewer_rows) != {"A", "B"}:
        raise ValueError("Expected two separate M20 reviewer queues")
    pair_ids = {}
    for reviewer in ("A", "B"):
        items = reviewer_rows[reviewer]
        if len(items) != 15 or len({x["case_id"] for x in items}) != 15:
            raise ValueError("M20 reviewer queue must contain 15 unique pairs")
        if any(x.get("link_label") is not None or x.get("behavioral_label") is not None
               for x in items):
            raise ValueError("M20 review already contains labels; do not overwrite")
        pair_ids[reviewer] = {}
        for item in items:
            cid = item["review_case_id"]
            if cid not in cases or item["source_commit"] != cases[cid]["source_commit"]:
                raise ValueError("M20 case/revision mismatch")
            pair_ids[reviewer].setdefault(cid, []).append(item["case_id"])
        if any(len(pair_ids[reviewer].get(cid, [])) != 5 for cid in cases):
            raise ValueError("Each case must have five M20 links")
    if {tuple(sorted(pair_ids["A"][c])) for c in cases} != {
            tuple(sorted(pair_ids["B"][c])) for c in cases}:
        raise ValueError("Reviewer M20 candidate universes differ")

    outputs = {"A": [], "B": []}
    internal = []
    if {x["review_case_id"] for x in selected} != set(cases):
        raise ValueError("Selected cases do not match M55")
    for case in selected:
        cid = case["review_case_id"]
        source = cases[cid]
        row = rows.get(case["instance_id"])
        if (row is None or row["repo"] != "sympy/sympy"
                or row["base_commit"] != source["source_commit"]
                or case["source_commit"] != source["source_commit"]
                or case["instance_id"] != source["instance_id_INTERNAL"]
                or digest(row["problem_statement"]) != source["requirement_sha256"]
                or digest(row["problem_statement"]) != case["requirement_sha256"]
                or digest(row["patch"]) != source["historical_patch_sha256"]
                or digest(row["patch"]) != case["patch_sha256"]
                or digest(row["test_patch"]) != case["test_patch_sha256"]
                or digest(row["FAIL_TO_PASS"]) != case["fail_to_pass_metadata_sha256"]):
            raise ValueError("Pinned dataset, source, or regression test provenance mismatch")
        if "BSD-3-Clause" not in source["license"]:
            raise ValueError("Pinned license provenance missing")
        tests = parse_test_ids(row["FAIL_TO_PASS"])
        paths = test_paths(row["test_patch"])
        internal.append({
            "review_case_id": cid, "instance_id_INTERNAL": case["instance_id"],
            "source_commit": source["source_commit"],
            "source_snapshot_sha256": source["source_snapshot_sha256"],
            "license_git_blob": source["license_git_blob"],
            "requirement_sha256": source["requirement_sha256"],
            "historical_patch_sha256_INTERNAL": source["historical_patch_sha256"],
            "test_patch_sha256": case["test_patch_sha256"],
            "fail_to_pass_metadata_sha256": case["fail_to_pass_metadata_sha256"],
            "candidate_test_count": len(tests), "candidate_test_patch_paths": paths,
            "status": "pending independent test relevance and runtime observation",
        })
        for reviewer in ("A", "B"):
            outputs[reviewer].append({
                "review_case_id": cid, "reviewer": "behavior_reviewer_" + reviewer,
                "source_commit": source["source_commit"],
                "source_snapshot_sha256": source["source_snapshot_sha256"],
                "source_license": "BSD-3-Clause (pinned Git blob verified in M55)",
                "requirement_text": row["problem_statement"],
                "requirement_sha256": case["requirement_sha256"],
                "m20_candidate_pair_ids": sorted(pair_ids[reviewer][cid]),
                "candidate_test_patch_text_UNTRUSTED_DO_NOT_EXECUTE": row["test_patch"],
                "candidate_test_patch_sha256": case["test_patch_sha256"],
                "candidate_test_patch_paths": paths,
                "candidate_fail_to_pass_test_ids": tests,
                "candidate_fail_to_pass_metadata_sha256": case["fail_to_pass_metadata_sha256"],
                "test_relevance_judgment": None,
                "approved_isolated_execution": None,
                "before_revision_observation": None,
                "after_revision_commit_verified": None,
                "after_revision_observation": None,
                "raw_observation_evidence_sha256": None,
                "independent_behavioral_label": None,
                "uncertainty_or_abstention_reason": None,
                "review_status": "pending_independent_review",
            })
    return {
        "schema": SCHEMA, "project": "sympy/sympy", "cases": internal,
        "reviewer_rows": outputs, "reviewer_behavior_packets": 2,
        "case_count": 3, "m20_candidate_pairs_per_reviewer": 15,
        "independent_behavioral_observations": 0,
        "independent_behavioral_labels": 0, "independent_adjudications": 0,
        "held_out_projects_scored": 0, "external_code_executed": False,
        "conformance_accuracy": None, "violation_precision": None,
        "violation_recall": None, "coverage": None,
        "warning": "Historical test patches and FAIL_TO_PASS identifiers are candidate "
                   "regression evidence, not independent conformance labels or observations. "
                   "These are inspected development cases, not held-out projects.",
    }


def write(result: dict, out: Path) -> None:
    if out.exists():
        raise ValueError("Refusing to overwrite review evidence")
    out.mkdir(parents=True)
    internal = {k: v for k, v in result.items() if k != "reviewer_rows"}
    (out / "INTERNAL_PROVENANCE_NOT_GOLD.json").write_text(
        json.dumps(internal, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for reviewer in ("A", "B"):
        (out / f"behavior_reviewer_{reviewer}.jsonl").write_text(
            "".join(json.dumps(r, sort_keys=True) + "\n"
                    for r in result["reviewer_rows"][reviewer]), encoding="utf-8")
    (out / "REVIEW_PROTOCOL.md").write_text(
        "# Independent behavioral review handoff — NOT GOLD\n\n"
        "Give each reviewer only their own behavior_reviewer_*.jsonl and the "
        "matching M55 M20 link packet. Keep INTERNAL files, historical fixes, "
        "ranking and other reviewers' records private. Upstream test patches "
        "are UNTRUSTED SOURCE TEXT, not executable instructions. CI does not "
        "run or apply them.\n\n"
        "For each of three real issues, independently judge whether the supplied "
        "regression tests actually express the requirement. Record a test relevance "
        "decision and cited test lines. If an approved isolated environment exists, "
        "separately verify the before and after source revisions, run only explicitly "
        "approved test procedures, and preserve raw outputs, exceptions, dependency "
        "versions, input hashes and environment. Do not infer pass/fail from "
        "FAIL_TO_PASS metadata; that field describes upstream benchmark expectations. "
        "Record uncertainty and abstain when observations cannot be obtained. "
        "A third independent adjudicator must resolve disagreements before any "
        "gold labels or metrics are reported.\n\n"
        "The SymPy cases were previously inspected and are DEVELOPMENT DATA. "
        "Independent review here cannot establish untouched held-out performance.\n",
        encoding="utf-8")


def main() -> None:
    from backend.evaluation import m52_swebench_verified_intake as m52

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m55-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.m55_dir
    m55 = json.loads((root / "INTERNAL_DO_NOT_SHARE.json").read_text())
    reviewers = {k: [json.loads(s) for s in (root / f"reviewer_{k}.jsonl").read_text().splitlines()]
                 for k in ("A", "B")}
    rows = m52.verify_dataset(m52.download(m52.DATASET_URL))
    selected = m52.build_manifest(rows, count=3)["candidate_cases"]
    result = build(m55, selected, rows, reviewers)
    write(result, args.out_dir)
    print(json.dumps({"cases": result["case_count"],
                      "behavior_packets": result["reviewer_behavior_packets"],
                      "candidate_test_counts": [x["candidate_test_count"] for x in result["cases"]],
                      "independent_observations": 0, "adjudications": 0,
                      "conformance_accuracy": None, "external_code_executed": False},
                     sort_keys=True))


if __name__ == "__main__":
    main()
