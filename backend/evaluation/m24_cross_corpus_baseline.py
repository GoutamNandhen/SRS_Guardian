"""M24: fixed, honest external observed-link retrieval baseline across two projects.

Dronology observed trace graph and TeaStore paper-declared SAD→Java file links
are *not* independently adjudicated conformance labels. No missing link is a
negative. This evaluates M7 path-only retrieval, NOT M2 Python AST matching,
code execution, or ≥95% conformance. Third-party Java source is never executed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from backend.evaluation.m6_external_trace import load_dataset
from backend.evaluation.m7_hybrid_retrieval import rank
from backend.evaluation.m20_annotation_queue import _validate
from backend.evaluation.m23_teastore_external import CODE_COMMIT, PROJECT_ID

METHODS = ("path_bm25", "hybrid_rrf")
K_VALUES = (1, 3, 5)
NO_CONFORMANCE = {
    "conformance_accuracy": None,
    "violation_precision": None,
    "violation_recall": None,
    "conformance_coverage": None,
}


class BaselineError(ValueError):
    """Reject mismatched, incomplete or mislabeled external evidence."""


def _sha(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def _cohort(project: str, version: str, reqs: list[dict], paths: list[str],
            method: str) -> dict:
    """Rank without access to links; score only observed positives afterward."""
    if not reqs or not paths or len(set(paths)) != len(paths):
        raise BaselineError("Empty or duplicate candidate paths/requirements")
    path_set = set(paths)
    ids = [r["id"] for r in reqs]
    if len(ids) != len(set(ids)):
        raise BaselineError("Duplicate requirement identifiers")
    cases = []
    for req in sorted(reqs, key=lambda r: r["id"]):
        known = set(req["observed_paths"])
        if not known.issubset(path_set):
            raise BaselineError("Observed link points outside candidate universe")
        ranked = rank(req["text"], paths, method)
        if len(ranked) != len(set(ranked)) or not set(ranked).issubset(path_set):
            raise BaselineError("Ranking returned invalid paths")
        case = {
            "requirement_id": req["id"],
            "observed_positive_count": len(known),
            "returned_candidate_count": len(ranked),
            "first_observed_positive_rank": next(
                (i for i, path in enumerate(ranked, 1) if path in known), None),
            "observed_positive_hits_at_k": {
                str(k): len(set(ranked[:k]) & known) for k in K_VALUES},
            "retrieval_has_candidates": bool(ranked),
        }
        cases.append(case)
    linked = [c for c in cases if c["observed_positive_count"]]
    observed = sum(c["observed_positive_count"] for c in linked)
    result = {
        "project": project, "version": version, "method": method,
        "total_statements": len(reqs),
        "statements_with_observed_positive": len(linked),
        "statements_without_observed_positive_unknown": len(reqs) - len(linked),
        "candidate_source_files": len(paths),
        "observed_positive_links_unverified": observed,
        "ranking_nonempty_statement_count": sum(c["retrieval_has_candidates"] for c in cases),
        "ranking_nonempty_statement_fraction": round(
            sum(c["retrieval_has_candidates"] for c in cases) / len(cases), 6),
        "hit_at_k_among_observed_linked_statements": {
            str(k): round(sum(c["observed_positive_hits_at_k"][str(k)] > 0 for c in linked)
                          / len(linked), 6) if linked else None
            for k in K_VALUES},
        "observed_positive_link_recall_at_k": {
            str(k): round(sum(c["observed_positive_hits_at_k"][str(k)] for c in linked)
                          / observed, 6) if observed else None
            for k in K_VALUES},
        "cases": cases,
        "has_independently_adjudicated_labels": False,
        "has_true_negative_labels": False,
        "has_behavioral_conformance_labels": False,
        **NO_CONFORMANCE,
    }
    return result


def _dronology_cohorts(data: dict) -> list[tuple[str, str, list[dict], list[str]]]:
    if data.get("schema_version") != "m6-external-trace-v1" or data.get("no_negative_labels") is not True:
        raise BaselineError("Expected verified M6 observed-positive fixture")
    versions = data["versions"]
    if {v["version"] for v in versions} != {"V0", "V1"}:
        raise BaselineError("Expected Dronology V0 and V1")
    return [("Dronology", v["version"], [
        {"id": r["requirement_id"], "text": r["text"],
         "observed_paths": r["observed_link_paths"]}
        for r in v["requirements"]], v["candidate_code_paths"])
        for v in sorted(versions, key=lambda x: x["version"])]


def _teastore_cohort(universe: dict, evidence: dict) -> tuple:
    if universe.get("project_id") != PROJECT_ID or universe.get("source_commit") != CODE_COMMIT:
        raise BaselineError("TeaStore provenance does not match pinned M23 source")
    if evidence.get("schema_version") != "m23-teastore-external-evidence-1":
        raise BaselineError("Missing M23 external source manifest")
    if (evidence.get("code_commit") != CODE_COMMIT
            or evidence.get("source_subset_sha256") != universe.get("code_snapshot_sha256")
            or evidence.get("licenses_verified_by_pinned_git_blob") is not True):
        raise BaselineError("TeaStore evidence/source/license mismatch")
    if evidence.get("independently_reviewed_link_pairs") != 0 or evidence.get("research_95_eligible") is not False:
        raise BaselineError("TeaStore labels cannot be promoted to independent gold")
    reqs, symbols, observed = _validate(universe)
    if len(reqs) != 3 or len(symbols) != 5 or len(observed) != 6:
        raise BaselineError("Unexpected M23 purposive subset size")
    by_id = {s["symbol_id"]: s["source_path"] for s in symbols}
    paths = [s["source_path"] for s in symbols]
    if len(set(paths)) != len(paths):
        raise BaselineError("Duplicate TeaStore source paths")
    return ("TeaStore", "M23-five-file-subset", [
        {"id": r["requirement_id"], "text": r["requirement_text"],
         "observed_paths": [by_id[sid] for rid, sid in sorted(observed)
                            if rid == r["requirement_id"]]}
        for r in reqs], paths)


def evaluate(dronology: dict, universe: dict, evidence: dict) -> dict:
    cohorts = _dronology_cohorts(dronology) + [_teastore_cohort(universe, evidence)]
    runs = [_cohort(*cohort, method) for cohort in cohorts for method in METHODS]
    return {
        "schema_version": "m24-two-external-project-observed-link-baseline-1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_task": "retrieval_of_externally_observed_links_using_source_paths_only",
        "projects": ["Dronology", "TeaStore"],
        "independent_project_count": 2,
        "evaluation_cohorts": 3,
        "methods_frozen_before_teastore_scoring": list(METHODS),
        "dronology_fixture_sha256": dronology["_fixture_sha256"],
        "teastore_source_subset_sha256": universe["code_snapshot_sha256"],
        "teastore_universe_sha256": _sha(universe),
        "teastore_m23_evidence_sha256": _sha(evidence),
        "published_links_are_independent_gold": False,
        "independently_adjudicated_link_pairs": 0,
        "independently_adjudicated_conformance_cases": 0,
        "has_true_negative_labels": False,
        "has_executable_conformance_labels": False,
        "held_out_real_project_conformance_evaluation": False,
        "research_95_eligible": False,
        **NO_CONFORMANCE,
        "runs": runs,
        "limitations": [
            "Dronology V0 and V1 are two versions of one project, not independent projects.",
            "Dronology graph paths are indirect observed links; code snapshot is not fully pinned here.",
            "TeaStore comprises three architecture statements and five selected Java files, not a complete application.",
            "TeaStore links are paper-declared observations, not independently adjudicated gold.",
            "Top-5 TeaStore retrieval is saturated by a five-file candidate universe; top-1/top-3 are more informative.",
            "Unknown or absent links are never counted as negatives. No link precision, classification accuracy or behavioral conformance can be computed.",
            "M7 methods were developed on Dronology; these cohorts are exploratory, not an independently held-out test set.",
            "Two reviewers must independently inspect all 15 M20 TeaStore pairs with source-line evidence; a third must adjudicate disagreements.",
            "Separate, real behavioral requirements and independently confirmed conforming/violating code versions are necessary for conformance accuracy and violation precision/recall.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dronology", required=True, type=Path)
    parser.add_argument("--teastore-universe", required=True, type=Path)
    parser.add_argument("--teastore-evidence", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    data = load_dataset(args.dronology)
    universe = json.loads(args.teastore_universe.read_text(encoding="utf-8"))
    evidence = json.loads(args.teastore_evidence.read_text(encoding="utf-8"))
    result = evaluate(data, universe, evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "independent_project_count": result["independent_project_count"],
        "independently_adjudicated_conformance_cases": 0,
        "research_95_eligible": False,
        "observed_link_baselines": [
            {"project": r["project"], "version": r["version"], "method": r["method"],
             "linked_statements": r["statements_with_observed_positive"],
             "hit_at_1": r["hit_at_k_among_observed_linked_statements"]["1"],
             "observed_link_recall_at_3": r["observed_positive_link_recall_at_k"]["3"]}
            for r in result["runs"]]}, indent=2))


if __name__ == "__main__":
    main()
