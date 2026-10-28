"""M57: file-level retrieval ablation on three pinned SymPy DEVELOPMENT issues.

Tests whether the function-only M42 baseline's 0/3 historical patch-file
proxy improves when module/class-level code is represented at file scope.
This is NOT independent traceability ground truth or behavioral conformance.
External code is read as Git-verified inert text, never imported/executed.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re

from backend.evaluation import m20_annotation_queue as m20
from backend.evaluation import m52_swebench_verified_intake as m52
from backend.evaluation import m54_sympy_frozen_retrieval_review as m54
from backend.evaluation import m55_sympy_three_case_proxy as m55
from backend.evaluation import m29_pip_historical_regression as m29

SCHEMA = "m57-file-bm25-sympy-development-ablation-1"
MAX_INDEX_CHARS_PER_FILE = 120_000
STOP = frozenset("""the and for from with that this should would could into when then
are was were not but can have has had its use using user issue error test tests
file code python sympy import def class self return true false none what which
each all any one two three also more than only such same does did do how
expected actual following example reproduce problem expected behavior""".split())


def tokens(value: str) -> list[str]:
    """Predeclared identifier-aware lexical tokenization; no case-specific tuning."""
    split_camel = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return [w for w in re.findall(r"[A-Za-z][A-Za-z0-9]*", split_camel.lower())
            if len(w) >= 3 and w not in STOP]


def file_rank(snapshot: dict, requirement: str) -> tuple[list[dict], int]:
    """BM25 over complete verified file set, with explicit per-file text cap."""
    if (not snapshot.get("files") or
            set(snapshot["files"]) != set(snapshot["expected"])):
        raise ValueError("Incomplete source tree")
    q = set(tokens(requirement))
    if not q:
        raise ValueError("Requirement has no usable lexical terms")
    docs = []
    df = Counter()
    truncated = 0
    for path in sorted(snapshot["files"]):
        raw = snapshot["files"][path]
        if not m54.production_source(path) or m29.blob_sha(raw) != snapshot["expected"][path]:
            raise ValueError("Unverified source blob")
        source = raw.decode("utf-8-sig")
        truncated += len(source) > MAX_INDEX_CHARS_PER_FILE
        # Path weighting is fixed before seeing any historical patch labels.
        terms = tokens((" ".join(path.replace(".py", "").split("/")) + " ") * 4
                       + source[:MAX_INDEX_CHARS_PER_FILE])
        counts = Counter(terms)
        docs.append((path, counts, len(terms)))
        df.update(counts.keys())
    avgdl = sum(length for _, _, length in docs) / len(docs)
    n = len(docs)
    ranked = []
    for path, counts, length in docs:
        score = 0.0
        for term in q:
            tf = counts[term]
            if not tf:
                continue
            idf = math.log(1.0 + (n - df[term] + 0.5) / (df[term] + 0.5))
            score += idf * (tf * 2.2) / (tf + 1.2 * (0.25 + 0.75 * length / avgdl))
        ranked.append({"path": path, "score": score})
    ranked.sort(key=lambda item: (-item["score"], item["path"]))
    return ranked[:5], truncated


def evaluate(case: dict, row: dict, snapshot: dict) -> dict:
    """Compute development patch-file proxy AFTER retrieval, never as input."""
    if (case["source_commit"] != snapshot["commit"] or
            row["base_commit"] != snapshot["commit"] or
            row["instance_id"] != case["instance_id"] or
            m52.digest(row["problem_statement"].encode("utf-8")) != case["requirement_sha256"] or
            m52.digest(row["patch"].encode("utf-8")) != case["patch_sha256"]):
        raise ValueError("Case, revision or requirement provenance mismatch")
    ranked, truncated = file_rank(snapshot, row["problem_statement"])
    if len(ranked) != 5:
        raise ValueError("Insufficient file-level retrieval candidates")
    # M20 treats each file as a candidate review unit, not a function symbol.
    symbols = []
    for item in ranked:
        path = item["path"]
        symbols.append({
            "symbol_id": "FILE-" + hashlib.sha256(path.encode()).hexdigest()[:24],
            "source_path": path,
            "qualified_name": path,
            "description": "File-level candidate (not function): "
                           + "https://github.com/sympy/sympy/blob/"
                           + snapshot["commit"] + "/" + path,
        })
    universe = {
        "schema_version": m20.SCHEMA,
        "project_id": "SYMPY_" + snapshot["commit"][:12]
                      + "_" + case["review_case_id"].replace("-", ""),
        "source_commit": snapshot["commit"],
        "code_snapshot_sha256": hashlib.sha256(
            json.dumps(snapshot["expected"], sort_keys=True).encode()).hexdigest(),
        "requirements": [{
            "requirement_id": case["review_case_id"].replace("-", ""),
            "requirement_text": row["problem_statement"][:4900],
        }],
        "symbols": symbols,
        "observed_links": [],
    }
    queue = m20.build_queue(universe, seed="m57-fixed-file-bm25-v1",
                            hard_per_requirement=5, random_per_requirement=0)
    proxy = m55.fix_file_proxy(
        {"internal_top_five_NOT_GOLD": ranked}, row["patch"], set(snapshot["expected"]))
    reviewers = {
        reviewer: [{**item, "full_requirement_text": row["problem_statement"],
                    "requirement_sha256": case["requirement_sha256"],
                    "reviewer": "reviewer_" + reviewer,
                    "link_label": None, "evidence_notes": None,
                    "behavioral_label": None, "annotation_status": "pending"}
                   for item in queue["queue"]]
        for reviewer in ("A", "B")
    }
    return {
        "review_case_id": case["review_case_id"],
        "instance_id_INTERNAL": case["instance_id"],
        "source_commit": snapshot["commit"],
        "git_tree_sha": snapshot["tree_sha"],
        "license_git_blob": snapshot["license_git_blob"],
        "verified_source_files": len(snapshot["files"]),
        "files_text_capped_at_120k_chars": truncated,
        "requirement_sha256": case["requirement_sha256"],
        "historical_patch_sha256_INTERNAL": case["patch_sha256"],
        "file_ranked_top5_INTERNAL": ranked,
        "patch_file_proxy_INTERNAL_NOT_GOLD": proxy,
        "m20_queue_sha256": queue["manifest"]["blind_queue_sha256"],
        "reviewer_rows": reviewers,
    }


def build(cases: list[dict]) -> dict:
    if len(cases) != 3 or len({c["review_case_id"] for c in cases}) != 3:
        raise ValueError("Expected three distinct development cases")
    reviewers = {reviewer: [] for reviewer in ("A", "B")}
    internal = []
    for case in cases:
        internal.append({k: v for k, v in case.items() if k != "reviewer_rows"})
        for reviewer in reviewers:
            reviewers[reviewer].extend(case["reviewer_rows"][reviewer])
    if any(len(rows) != 15 or len({r["case_id"] for r in rows}) != 15
           or any(r["link_label"] is not None or r["behavioral_label"] is not None
                  for r in rows)
           for rows in reviewers.values()):
        raise ValueError("Reviewer packets must have 15 distinct unlabeled links")
    if {r["case_id"] for r in reviewers["A"]} != {r["case_id"] for r in reviewers["B"]}:
        raise ValueError("Reviewer candidate universes differ")
    eligible = [c["patch_file_proxy_INTERNAL_NOT_GOLD"]["historical_fix_file_hit_at_5_PROXY_NOT_GOLD"]
                for c in internal if c["patch_file_proxy_INTERNAL_NOT_GOLD"]["proxy_eligible"]]
    return {
        "schema": SCHEMA, "project": "sympy/sympy",
        "retrieval": "file-level BM25, fixed parameters, path x4, first 120k chars/file",
        "development_cases": 3,
        "proxy_eligible": len(eligible),
        "patch_file_hit_at_5_DEVELOPMENT_PROXY_NOT_GOLD": sum(eligible),
        "previous_M55_function_BM25_patch_file_hit_at_5_DEVELOPMENT_PROXY_NOT_GOLD": 0,
        "cases": internal,
        "reviewer_rows": reviewers,
        "independent_link_labels": 0, "independent_behavioral_observations": 0,
        "independent_adjudications": 0, "held_out_projects_scored": 0,
        "conformance_accuracy": None, "violation_precision": None,
        "violation_recall": None, "coverage": None, "external_code_executed": False,
        "limitations": [
            "All three cases are previously inspected SymPy development cases.",
            "Historical patch-file overlap is not independently adjudicated trace gold.",
            "File-level candidates do not prove symbol-level trace links or behavior.",
            "Top-five retrieval cannot measure whole-repository recall.",
            "Independent M20 reviewers, runtime observations and adjudication missing.",
            "Untouched held-out project evaluation and contamination assessment missing.",
        ],
    }


def write(report: dict, output: Path) -> None:
    if output.exists():
        raise ValueError("Refusing to overwrite review evidence")
    output.mkdir(parents=True)
    internal = {k: v for k, v in report.items() if k != "reviewer_rows"}
    (output / "INTERNAL_NOT_GOLD.json").write_text(
        json.dumps(internal, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for reviewer, rows in report["reviewer_rows"].items():
        (output / ("reviewer_" + reviewer + ".jsonl")).write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8")
    (output / "REVIEW_PROTOCOL.md").write_text(
        "# M57 independent file-link review — NOT GOLD\n\n"
        "Give reviewers only their own reviewer JSONL. The candidate is a "
        "whole file, not a verified function or behavior. Review all 15 "
        "file links against original requirements and pinned source, cite "
        "source lines, and mark uncertain cases explicitly. Keep historical "
        "patches, rankings and internal file hidden. Two independent M20 "
        "reviewers and separate adjudicator are required. Approved isolated "
        "before/after behavioral observations remain entirely absent. "
        "The three SymPy issues are development cases, not held-out.\n",
        encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    rows = m52.verify_dataset(m52.download(m52.DATASET_URL))
    selected = m52.build_manifest(rows, count=3)["candidate_cases"]
    by_id = {row["instance_id"]: row for row in rows}
    cases = []
    for case in selected:
        snapshot = m54.fetch_snapshot(case)
        cases.append(evaluate(case, by_id[case["instance_id"]], snapshot))
    result = build(cases)
    write(result, args.out_dir)
    print(json.dumps({
        "development_cases": result["development_cases"],
        "proxy_eligible": result["proxy_eligible"],
        "file_level_patch_hit_at_5_NOT_GOLD":
            result["patch_file_hit_at_5_DEVELOPMENT_PROXY_NOT_GOLD"],
        "previous_function_level_patch_hit_at_5_NOT_GOLD": 0,
        "independent_labels": 0, "held_out_projects_scored": 0,
        "conformance_accuracy": None, "external_code_executed": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
