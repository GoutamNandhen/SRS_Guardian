"""M55: three real SymPy issues, frozen M42 retrieval, M20 review and patch-file proxy.

Historical patch overlap is a *development diagnostic*, NOT independently reviewed
traceability, behavioral conformance, or untouched held-out evaluation.
No upstream source is imported or executed.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from backend.evaluation import m52_swebench_verified_intake as m52
from backend.evaluation import m54_sympy_frozen_retrieval_review as m54

SCHEMA = "m55-three-sympy-issue-retrieval-proxy-1"
DIFF_PATH = re.compile(r"^diff --git a/(.+) b/(.+)$", re.MULTILINE)


def patch_paths(patch: str) -> set[str]:
    """Only explicit unified-diff Git paths; never infer labels from prose."""
    if not isinstance(patch, str) or not patch.strip():
        raise ValueError("Missing historical patch")
    matches = DIFF_PATH.findall(patch)
    if not matches:
        raise ValueError("Historical patch has no diff --git paths")
    return {b for a, b in matches if a == b and m54.production_source(b)}


def fix_file_proxy(report: dict, patch: str, base_paths: set[str]) -> dict:
    """Path overlap with historical patch, not requirement correctness."""
    changed = patch_paths(patch)
    indexable = changed & base_paths
    top_five = {s["path"] for s in report["internal_top_five_NOT_GOLD"]}
    return {
        "historical_patch_production_files": sorted(changed),
        "historical_patch_base_indexable_files": sorted(indexable),
        "historical_patch_added_or_unindexed_files": sorted(changed - base_paths),
        "top_five_retrieved_files": sorted(top_five),
        "historical_fix_file_hit_at_5_PROXY_NOT_GOLD":
            bool(top_five & indexable) if indexable else None,
        "proxy_eligible": bool(indexable),
        "warning": "Historical patch-file overlap is a biased development proxy; "
                   "not independent trace ground truth, recall, or conformance.",
    }


def assemble(cases: list[tuple[dict, dict, dict]]) -> dict:
    """Consume externally verified M54 reports and pinned historical patch rows."""
    if len(cases) != 3:
        raise ValueError("Expected exactly three independently sourced issue records")
    seen, combined = set(), []
    reviewer_rows = {"A": [], "B": []}
    for case, report, row in cases:
        cid = case["review_case_id"]
        if cid in seen or report["review_case_id"] != cid:
            raise ValueError("Duplicate or mismatched case")
        seen.add(cid)
        if row["instance_id"] != case["instance_id"]:
            raise ValueError("Historical dataset case mismatch")
        if m52.digest(row["patch"].encode("utf-8")) != case["patch_sha256"]:
            raise ValueError("Historical patch digest mismatch")
        if report["source_commit"] != case["source_commit"]:
            raise ValueError("Pinned revision mismatch")
        if report["external_code_executed"] is not False:
            raise ValueError("Untrusted code execution disallowed")
        for name in ("conformance_accuracy", "violation_precision", "violation_recall", "coverage"):
            if report[name] is not None:
                raise ValueError("Unverified behavioral scores present")
        base_paths = set(report["source_paths_verified"])
        proxy = fix_file_proxy(report, row["patch"], base_paths)
        for reviewer in ("A", "B"):
            rows = report["reviewer_rows"][reviewer]
            if len(rows) != 5:
                raise ValueError("Expected five M20 candidates per reviewer")
            reviewer_rows[reviewer].extend(
                [{**item, "review_case_id": cid} for item in rows])
        combined.append({
            "review_case_id": cid,
            "instance_id_INTERNAL": case["instance_id"],
            "source_commit": report["source_commit"],
            "git_tree_sha": report["git_tree_sha"],
            "license": report["license"],
            "license_git_blob": report["license_git_blob"],
            "source_snapshot_sha256": report["source_snapshot_sha256"],
            "verified_production_python_files": report["verified_production_python_files"],
            "indexed_production_symbols": report["indexed_production_symbols"],
            "requirement_sha256": case["requirement_sha256"],
            "historical_patch_sha256": case["patch_sha256"],
            "m20_queue_sha256": report["m20_queue_sha256"],
            "retrieval_method": report["retrieval_method"],
            "proxy": proxy,
        })
    all_ids = [r["case_id"] for r in reviewer_rows["A"]]
    if len(set(all_ids)) != 15:
        raise ValueError("M20 pair IDs collided across distinct cases")
    if {r["case_id"] for r in reviewer_rows["B"]} != set(all_ids):
        raise ValueError("Reviewer candidate universes differ")
    eligible = [x["proxy"]["historical_fix_file_hit_at_5_PROXY_NOT_GOLD"]
                for x in combined if x["proxy"]["proxy_eligible"]]
    return {
        "schema": SCHEMA, "project": "sympy/sympy",
        "source": "pinned SWE-bench Verified 500-case dataset, three M52-selected SymPy cases",
        "retrieval": "unchanged M42 normalized BM25, whole non-test production Python tree",
        "cases": combined,
        "candidate_cases": len(combined),
        "m20_unlabeled_candidates_per_reviewer": len(all_ids),
        "historical_patch_file_proxy_eligible_cases": len(eligible),
        "historical_patch_file_proxy_hits_at_5": sum(eligible),
        "proxy_is_independent_gold": False,
        "independent_link_labels": 0,
        "independent_behavioral_labels": 0,
        "independent_adjudications": 0,
        "approved_behavioral_observations": 0,
        "held_out_projects_scored": 0,
        "conformance_accuracy": None, "violation_precision": None,
        "violation_recall": None, "coverage": None,
        "external_code_executed": False,
        "reviewer_rows": reviewer_rows,
        "limitations": [
            "All three cases are from one previously inspected development project.",
            "Patch-file overlap is not independent ground truth or behavioral evidence.",
            "Fix files absent at the base commit cannot be retrieved by the base index.",
            "Five candidates per case do not establish whole-repository recall.",
            "Two independent M20 link reviewers, approved behavioral observations, "
            "third-party adjudication and untouched project evaluation remain missing.",
            "Issue-text contamination and public source-history unblinding remain possible.",
        ],
    }


def write(report: dict, out: Path) -> None:
    if out.exists():
        raise ValueError("Refusing to overwrite existing evidence")
    out.mkdir(parents=True)
    internal = {k: v for k, v in report.items() if k != "reviewer_rows"}
    (out / "INTERNAL_DO_NOT_SHARE.json").write_text(
        json.dumps(internal, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for reviewer, rows in report["reviewer_rows"].items():
        (out / f"reviewer_{reviewer}.jsonl").write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8")
    (out / "REVIEW_PROTOCOL.md").write_text(
        "# M55 independent-review handoff (NOT GOLD)\n\n"
        "Give each reviewer only their own JSONL. Do not give either reviewer "
        "INTERNAL_DO_NOT_SHARE.json or historical patches. Each reviewer must "
        "independently inspect all 15 pinned source candidates, record a link "
        "judgment, source-line evidence and rationale, and flag unresolved cases. "
        "These are top-five retrieval predictions, not the complete link universe.\n\n"
        "For each issue, independently collect approved, revision-matched behavioral "
        "observations (inputs, environment, outputs/exceptions, hashes) before any "
        "conformance judgment. A separate adjudicator resolves disagreement. "
        "Preserve abstentions and non-observable cases. No reviewer labels or "
        "runtime observations have been collected by this script.\n\n"
        "All three SymPy cases are development data, not untouched held-out "
        "projects. Historical patch-file hits are INTERNAL retrieval diagnostics "
        "and must never be reported as conformance precision/recall.\n",
        encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    rows = m52.verify_dataset(m52.download(m52.DATASET_URL))
    manifest = m52.build_manifest(rows, count=3)
    by_id = {row["instance_id"]: row for row in rows}
    prepared = []
    for case in manifest["candidate_cases"]:
        snapshot = m54.fetch_snapshot(case)
        report = m54.build(case, snapshot, unique_case_ids=True)
        report["source_paths_verified"] = sorted(snapshot["expected"])
        prepared.append((case, report, by_id[case["instance_id"]]))
    result = assemble(prepared)
    write(result, args.out_dir)
    print(json.dumps({
        "candidate_cases": result["candidate_cases"],
        "m20_candidates_per_reviewer": result["m20_unlabeled_candidates_per_reviewer"],
        "historical_patch_file_proxy_eligible_cases":
            result["historical_patch_file_proxy_eligible_cases"],
        "historical_patch_file_proxy_hits_at_5_NOT_GOLD":
            result["historical_patch_file_proxy_hits_at_5"],
        "independent_behavioral_labels": 0, "held_out_projects_scored": 0,
        "conformance_accuracy": None, "external_code_executed": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
