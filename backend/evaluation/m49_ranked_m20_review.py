"""M49: expose actual M43 top-five retrieval predictions for M20 independent review.

This is a previously inspected pip development case, not held-out, not gold.
Reviewers see only the retrieved candidates, not ranks, scores, fix locus,
revision names, upstream test outcome, or behavioral labels.
Upstream source is verified and parsed as inert text; never executed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from backend.evaluation import m20_annotation_queue as m20
from backend.evaluation import m29_pip_historical_regression as m29
from backend.evaluation import m43_pip_retrieval_gated_witness as m43
from backend.evaluation import m42_pip_first_party_tree_retrieval as m42

SCHEMA = "m49-ranked-candidates-to-m20-review-1"


def snapshot_digest(snapshot: dict) -> str:
    """SHA-256 of length-delimited verified source paths and their bytes."""
    files, expected = snapshot["files"], snapshot["expected"]
    if not files or set(files) != set(expected):
        raise ValueError("Incomplete source tree")
    h = hashlib.sha256()
    for path in sorted(files):
        raw = files[path]
        if m29.blob_sha(raw) != expected[path]:
            raise ValueError("Source blob mismatch: " + path)
        name = path.encode("utf-8")
        h.update(len(name).to_bytes(4, "big"))
        h.update(name)
        h.update(len(raw).to_bytes(8, "big"))
        h.update(raw)
    return h.hexdigest()


def prepare(report: dict, snapshots: dict) -> dict:
    if report.get("schema") != m43.SCHEMA or report.get("retrieval_method") != "normalized_tokens":
        raise ValueError("Unexpected M43 baseline")
    if set(snapshots) != {"before", "after"} or len(report.get("cases", [])) != 6:
        raise ValueError("Expected both revisions and six retrieval cases")
    scenario_text = {s["case_id"]: s["requirement_text"] for s in m29.SCENARIOS}
    digests = {}
    for revision, snapshot in snapshots.items():
        if (snapshot["commit"] != m29.COMMITS[revision]
                or report["source_revisions"][revision]["commit"] != snapshot["commit"]):
            raise ValueError("Revision mismatch")
        digests[revision] = snapshot_digest(snapshot)
    reviewer_rows = {"A": [], "B": []}
    internal = []
    seen = set()
    for row in report["cases"]:
        revision, case = row["revision"], row["case_id"]
        if (revision, case) in seen or case not in scenario_text:
            raise ValueError("Duplicate or unknown requirement case")
        seen.add((revision, case))
        candidates = row["top_five_source_candidates"]
        if len(candidates) != 5:
            raise ValueError("Expected five actual ranked candidates")
        symbols = []
        keys = set()
        for position, candidate in enumerate(candidates, 1):
            path, qual = candidate["path"], candidate["qualified_name"]
            if candidate["rank"] != position or (path, qual) in keys:
                raise ValueError("Invalid candidate ranking")
            keys.add((path, qual))
            if path not in snapshots[revision]["files"]:
                raise ValueError("Candidate absent from pinned source tree")
            url = candidate["source_url"]
            prefix = f"https://github.com/{m29.REPO}/blob/{m29.COMMITS[revision]}/{path}#L"
            if not url.startswith(prefix) or not url[len(prefix):].isdigit():
                raise ValueError("Unpinned source URL")
            sid = "SYM" + hashlib.sha256((path + "\0" + qual).encode()).hexdigest()[:20]
            symbols.append({"symbol_id": sid, "source_path": path,
                            "qualified_name": qual,
                            "description": "Pinned source location: " + url})
        universe = {
            "schema_version": m20.SCHEMA,
            "project_id": "PIP_" + m29.COMMITS[revision][:12] + "_" + case,
            "source_commit": m29.COMMITS[revision],
            "code_snapshot_sha256": digests[revision],
            "requirements": [{"requirement_id": case,
                              "requirement_text": scenario_text[case]}],
            "symbols": symbols, "observed_links": [],
        }
        queue = m20.build_queue(universe, seed="m49-m43-top5-review-v1",
                                hard_per_requirement=5, random_per_requirement=0)
        if len(queue["queue"]) != 5:
            raise ValueError("Missing candidate from M20 queue")
        for reviewer in reviewer_rows:
            reviewer_rows[reviewer].extend({
                **item, "reviewer": "reviewer_" + reviewer,
                "link_label": None, "evidence_notes": None,
                "annotation_status": "pending"
            } for item in queue["queue"])
        internal.append({
            "revision": revision, "case_id": case,
            "m20_queue_sha256": queue["manifest"]["blind_queue_sha256"],
            "ranked_candidates": candidates,
            "known_fix_locus": "NOT SHARED WITH REVIEWERS",
            "behavioral_verdict": None,
        })
    if seen != {(rev, case) for rev in snapshots for case in scenario_text}:
        raise ValueError("Incomplete scenario/revision coverage")
    if any(len(rows) != 30 for rows in reviewer_rows.values()):
        raise ValueError("Expected 30 candidate links per reviewer")
    return {
        "schema": SCHEMA, "project": m29.REPO,
        "method": "M43 normalized_tokens top-five, frozen at M48 parent",
        "source_commits": m29.COMMITS,
        "source_snapshot_sha256": digests,
        "reviewer_rows": reviewer_rows, "internal_ranked": internal,
        "distinct_scenario_families": 3, "revision_scenario_cases": 6,
        "candidate_links_per_reviewer": 30,
        "independent_reviewers_completed": 0,
        "independent_adjudications": 0,
        "behavioral_observations": 0,
        "held_out": False,
        "conformance_accuracy": None, "violation_precision": None,
        "violation_recall": None, "coverage": None,
        "limitations": [
            "Previously inspected pip development cases; not held out.",
            "Only top-five retrieved candidates are reviewed: this cannot estimate whole-repository link recall.",
            "Six correlated revision/scenario cases, not six independent projects.",
            "Source links are unverified candidates; no independent link or behavioral gold.",
            "Reviewer files intentionally omit retrieval rank, score, known fix locus and revision label.",
        ],
    }


def write(result: dict, out_dir: Path) -> None:
    if out_dir.exists():
        raise ValueError("Refusing to overwrite output")
    out_dir.mkdir(parents=True)
    internal = {k: v for k, v in result.items() if k != "reviewer_rows"}
    (out_dir / "INTERNAL_DO_NOT_SHARE.json").write_text(
        json.dumps(internal, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for reviewer, rows in result["reviewer_rows"].items():
        (out_dir / f"reviewer_{reviewer}.jsonl").write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8")
    (out_dir / "REVIEW_PROTOCOL.md").write_text(
        "# M49 pip retrieval-prediction review (PENDING; NOT GOLD)\n\n"
        "Send each reviewer ONLY their reviewer_A.jsonl or reviewer_B.jsonl. "
        "Never share INTERNAL_DO_NOT_SHARE.json with reviewers. "
        "Independently inspect each pinned source link and mark link_label "
        "with cited code evidence using the existing M20 protocol. "
        "Do not infer behavior from a trace link. Revision-matched behavioral "
        "observations require separate approved human execution evidence; "
        "a third independent reviewer adjudicates. These previously inspected "
        "pip cases are development-only and cannot be held-out scoring. "
        "No conformance accuracy, precision, recall or coverage is available.\n",
        encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    evidence = m29.build_evidence(m29.fetch_pinned())
    snapshots = {revision: m42.fetch_snapshot(revision) for revision in ("before", "after")}
    report = m43.build(snapshots, evidence)
    result = prepare(report, snapshots)
    write(result, args.out_dir)
    print(json.dumps({
        "revision_scenario_cases": 6,
        "candidate_links_per_reviewer": 30,
        "independent_adjudications": 0,
        "held_out": False, "conformance_accuracy": None,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
