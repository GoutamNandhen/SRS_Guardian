"""M59: reviewable Django source excerpts and regression evidence for M20.

This is an evidence handoff, NOT behavioral conformance evaluation. The
historical production fix is never used to choose or annotate code candidates.
No external source, patch, or regression test is executed or applied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

from backend.evaluation import m29_pip_historical_regression as m29
from backend.evaluation import m52_swebench_verified_intake as m52
from backend.evaluation import m57_sympy_file_level_retrieval as m57
from backend.evaluation import m58_django_frozen_file_transfer as m58

SCHEMA = "m59-django-two-stage-human-review-1"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def excerpt(raw: bytes, requirement: str) -> dict:
    """Select a reproducible source window using ONLY the issue text."""
    lines = raw.decode("utf-8-sig").splitlines()
    if not lines:
        raise ValueError("Empty verified source file")
    terms = set(m57.tokens(requirement))
    scores = [len(terms.intersection(m57.tokens(line))) for line in lines]
    center = max(range(len(lines)), key=lambda i: scores[i])
    start = max(0, center - 7)
    end = min(len(lines), center + 8)
    return {
        "start_line": start + 1,
        "end_line": end,
        "source_lines": [
            {"line": i + 1, "text": lines[i][:400]}
            for i in range(start, end)
        ],
        "excerpt_is_not_full_source": True,
        "selection": "maximum issue-token overlap in a single source line",
    }


def test_patch_paths(patch: str) -> list[str]:
    if not isinstance(patch, str) or not patch.strip() or len(patch) > 500_000:
        raise ValueError("Missing or oversized regression patch")
    pairs = m58.DIFF_PATH.findall(patch)
    if not pairs:
        raise ValueError("Regression patch contains no diff headers")
    paths = set()
    for before, after in pairs:
        for path in (before, after):
            parts = PurePosixPath(path).parts
            if (not path or path.startswith("/") or "\\" in path or ".." in parts
                    or any(p in {"", "."} for p in parts)):
                raise ValueError("Unsafe regression patch path")
        paths.add(after)
    return sorted(paths)


def expected_tests(raw: str) -> list[str]:
    """Allow a genuine empty upstream FAIL_TO_PASS list; never invent test IDs."""
    if not isinstance(raw, str):
        raise ValueError("Missing FAIL_TO_PASS metadata")
    try:
        tests = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid FAIL_TO_PASS JSON") from exc
    if (not isinstance(tests, list) or len(tests) > 100
            or any(not isinstance(t, str) or not t.strip() or len(t) > 500
                   for t in tests) or len(tests) != len(set(tests))):
        raise ValueError("Invalid FAIL_TO_PASS test IDs")
    return tests


def build(row: dict, snapshot: dict, internal: dict,
          reviewers: dict[str, list[dict]]) -> dict:
    """Attach source evidence to frozen M58 candidates, then separate tests."""
    if (row.get("repo") != m58.REPO
            or row.get("base_commit") != snapshot.get("commit")
            or internal.get("project") != m58.REPO
            or internal.get("source_commit") != snapshot.get("commit")
            or internal.get("source_tree_sha") != snapshot.get("tree_sha")
            or internal.get("license_git_blob") != snapshot.get("license_git_blob")
            or internal.get("verified_production_files") != len(snapshot["files"])
            or internal.get("requirement_sha256") != sha(row["problem_statement"].encode())
            or internal.get("historical_test_patch_sha256_INTERNAL") != sha(row["test_patch"].encode())
            or internal.get("historical_patch_sha256_INTERNAL") != sha(row["patch"].encode())
            or internal.get("independent_link_labels") != 0
            or internal.get("independent_adjudications") != 0
            or internal.get("external_project_code_executed") is not False):
        raise ValueError("M58 pinned source, issue, license or evidence mismatch")
    if set(reviewers) != {"A", "B"}:
        raise ValueError("Two independent M20 reviewer packets required")
    ids = []
    paths = []
    for reviewer in ("A", "B"):
        items = reviewers[reviewer]
        if (len(items) != 5 or len({x["case_id"] for x in items}) != 5
                or any(x.get("link_label") is not None
                       or x.get("behavioral_label") is not None for x in items)):
            raise ValueError("M20 packet must contain five distinct unlabeled links")
        ids.append({x["case_id"] for x in items})
        paths.append({x["source_path"] for x in items})
    if ids[0] != ids[1] or paths[0] != paths[1]:
        raise ValueError("Reviewer candidate sets differ")

    # Stage 1 uses ONLY the frozen M58 candidate paths and pinned base source.
    stage1 = {}
    for reviewer in ("A", "B"):
        packet = []
        for item in reviewers[reviewer]:
            path = item["source_path"]
            raw = snapshot["files"].get(path)
            if (raw is None or not m58.production_source(path)
                    or m29.blob_sha(raw) != snapshot["expected"].get(path)
                    or item["source_commit"] != snapshot["commit"]
                    or item["requirement_sha256"] != internal["requirement_sha256"]):
                raise ValueError("Candidate path or pinned Git blob mismatch")
            packet.append({
                **item,
                "source_file_sha256": sha(raw),
                "source_git_blob": snapshot["expected"][path],
                "source_url": f"https://github.com/{m58.REPO}/blob/{snapshot['commit']}/{path}",
                "source_excerpt": excerpt(raw, row["problem_statement"]),
                "reviewed_full_source": None,
                "source_line_citations": None,
                "independent_link_decision": None,
                "abstention_reason": None,
            })
        stage1[reviewer] = packet

    # Stage 2 is deliberately separate: regression patches can reveal fix hints.
    tests = expected_tests(row["FAIL_TO_PASS"])
    paths_in_test_patch = test_patch_paths(row["test_patch"])
    stage2 = {}
    for reviewer in ("A", "B"):
        stage2[reviewer] = {
            "reviewer": "reviewer_" + reviewer,
            "review_case_id": "CASE-001",
            "source_commit": snapshot["commit"],
            "m20_pair_ids": sorted(ids[0]),
            "requirement_sha256": internal["requirement_sha256"],
            "candidate_test_patch_UNTRUSTED_TEXT": row["test_patch"],
            "candidate_test_patch_sha256": sha(row["test_patch"].encode()),
            "candidate_test_paths": paths_in_test_patch,
            "upstream_expected_FAIL_TO_PASS_NOT_OBSERVED": tests,
            "upstream_expected_metadata_sha256": sha(row["FAIL_TO_PASS"].encode()),
            "test_relevance_decision": None,
            "test_line_citations": None,
            "approved_execution_protocol": None,
            "before_revision_observation": None,
            "after_revision_observation": None,
            "observation_evidence_sha256": None,
            "independent_behavioral_label": None,
            "abstention_reason": None,
            "review_status": "pending",
        }

    return {
        "schema": SCHEMA,
        "internal": {
            "project": m58.REPO,
            "dataset_revision": m52.DATASET_REV,
            "dataset_sha256": m52.DATASET_SHA256,
            "instance_id_INTERNAL": row["instance_id"],
            "source_commit": snapshot["commit"],
            "source_tree_sha": snapshot["tree_sha"],
            "source_license": internal["source_license"],
            "license_git_blob": snapshot["license_git_blob"],
            "license_sha256": snapshot["license_sha256"],
            "requirement_sha256": internal["requirement_sha256"],
            "historical_patch_sha256_INTERNAL": sha(row["patch"].encode()),
            "regression_test_patch_sha256": sha(row["test_patch"].encode()),
            "upstream_test_metadata_sha256": sha(row["FAIL_TO_PASS"].encode()),
            "m58_queue_sha256": internal["m20_queue_sha256"],
            "source_candidates_per_reviewer": 5,
            "candidate_regression_tests": len(tests),
            "upstream_fail_to_pass_list_empty": not bool(tests),
            "candidate_test_patch_files": len(paths_in_test_patch),
            "independent_link_labels": 0,
            "independent_behavioral_observations": 0,
            "independent_adjudications": 0,
            "held_out_projects_scored": 0,
            "external_project_code_executed": False,
            "conformance_accuracy": None,
            "violation_precision": None,
            "violation_recall": None,
            "coverage": None,
            "limitations": [
                "This is one already inspected cross-project development case, NOT an untouched held-out evaluation.",
                "Source excerpts are lexical navigation aids, not semantic proof or full source.",
                "Stage 2 upstream test patch and expected test identifiers may leak fix information.",
                "Historical patch-file hit is NOT a ground-truth trace or behavioral label.",
                "Independent reviewers, approved before/after observations and third-party adjudication are missing.",
            ],
        },
        "stage1": stage1,
        "stage2": stage2,
    }


def write(result: dict, out: Path) -> None:
    if out.exists():
        raise ValueError("Refusing to overwrite evidence")
    out.mkdir(parents=True)
    (out / "INTERNAL_NOT_GOLD.json").write_text(
        json.dumps(result["internal"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for reviewer in ("A", "B"):
        (out / f"reviewer_{reviewer}_stage1.jsonl").write_text(
            "".join(json.dumps(x, sort_keys=True) + "\n" for x in result["stage1"][reviewer]),
            encoding="utf-8")
        (out / f"reviewer_{reviewer}_stage2.json").write_text(
            json.dumps(result["stage2"][reviewer], indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
    (out / "REVIEW_PROTOCOL.md").write_text(
        "# M59 Django independent review handoff — NOT GOLD\n\n"
        "Stage 1: give each independent reviewer only their own stage1 JSONL. "
        "Review the FULL pinned source file (excerpt is a navigation aid), cite exact "
        "source lines, decide requirement-to-file relevance or abstain. Record decisions "
        "independently before opening stage 2. Do not provide INTERNAL evidence or "
        "historical production fixes. Source files and issue text can themselves leak clues.\n\n"
        "Stage 2: only after stage 1 decisions are preserved, provide that reviewer's "
        "stage2 JSON. Upstream test patch and FAIL_TO_PASS are UNTRUSTED TEXT and "
        "BENCHMARK EXPECTATIONS, not observed results. Judge test relevance and cite "
        "test lines. Only in a separately approved, isolated environment may a reviewer "
        "collect revision-matched before/after behavioral observations; preserve exact "
        "commits, dependencies, inputs, raw outputs, and hashes. CI never executes "
        "upstream code. Abstain if behavior is unobservable.\n\n"
        "A separate adjudicator must resolve disagreements without retroactively "
        "altering independent submissions. No behavioral gold or conformance metrics "
        "exist. Top-five candidate selection cannot establish full-tree coverage. "
        "This inspected Django case is development evidence, not held-out evaluation.\n",
        encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    rows = m52.verify_dataset(m52.download(m52.DATASET_URL))
    row = m58.select_case(rows)
    snapshot = m58.fetch_snapshot(row["base_commit"])
    internal, reviewers = m58.evaluate(row, snapshot)
    result = build(row, snapshot, internal, reviewers)
    write(result, args.out_dir)
    print(json.dumps({
        "project": m58.REPO, "real_issue_cases": 1,
        "verified_source_files": len(snapshot["files"]),
        "m20_candidates_per_reviewer": 5,
        "candidate_regression_tests": result["internal"]["candidate_regression_tests"],
        "independent_labels": 0, "adjudications": 0,
        "held_out_projects_scored": 0, "conformance_accuracy": None,
        "external_project_code_executed": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
