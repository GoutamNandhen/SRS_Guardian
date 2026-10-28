"""M42: real first-party pip implementation-tree retrieval, not oracle file scope.

Fetch immutable upstream Git tree + source archive, verify each Python Git blob,
parse as inert text, and rank all first-party implementation symbols. Never
import/install/execute third-party code. Known historical fix location is
checked strictly AFTER ranking. Development case, not independent gold.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import urllib.request
import zipfile

from backend.app.services.code_traceability import _index_python, rank_candidates
from backend.evaluation import m29_pip_historical_regression as m29
from backend.evaluation import m40_pip_e2e_feasibility as m40
from backend.evaluation.m41_pip_retrieval_ablation import normalize_token, normalized_query

SCHEMA = "m42-pip-first-party-implementation-tree-retrieval-1"
PREFIX = "src/pip/_internal/"
MAX_ZIP_BYTES = 30_000_000
MAX_JSON_BYTES = 8_000_000
MAX_ENTRIES = 10000
MAX_FILES = 500
MAX_FILE_BYTES = 1_000_000
MAX_TOTAL_SOURCE_BYTES = 40_000_000
METHODS = ("original_tokens", "normalized_tokens")


def get_bytes(url: str, max_bytes: int, *, accept: str | None = None) -> bytes:
    headers = {"User-Agent": "srs-guardian-m42-static-pip-tree"}
    if accept:
        headers["Accept"] = accept
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as response:
        if response.status != 200:
            raise m29.EvidenceError("Unexpected upstream HTTP status")
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise m29.EvidenceError("Upstream response exceeds byte cap")
    return data


def get_json(url: str) -> dict:
    result = json.loads(get_bytes(url, MAX_JSON_BYTES, accept="application/vnd.github+json"))
    if not isinstance(result, dict):
        raise m29.EvidenceError("Invalid GitHub API JSON")
    return result


def expected_source_blobs(commit: str) -> tuple[str, dict[str, str]]:
    """Resolve exact pinned commit to tree, enumerate *all* first-party .py files."""
    root = f"https://api.github.com/repos/{m29.REPO}/git"
    commit_data = get_json(f"{root}/commits/{commit}")
    if commit_data.get("sha") != commit:
        raise m29.EvidenceError("Commit SHA mismatch")
    tree_sha = commit_data.get("tree", {}).get("sha")
    if not isinstance(tree_sha, str) or len(tree_sha) != 40:
        raise m29.EvidenceError("Missing commit tree SHA")
    tree = get_json(f"{root}/trees/{tree_sha}?recursive=1")
    if tree.get("sha") != tree_sha or tree.get("truncated") is not False:
        raise m29.EvidenceError("Tree mismatch or truncated recursive listing")
    expected = {}
    for obj in tree.get("tree", []):
        path = obj.get("path", "")
        if path.startswith(PREFIX) and path.endswith(".py"):
            if obj.get("type") != "blob" or obj.get("mode") != "100644":
                raise m29.EvidenceError("Unexpected first-party source object type")
            expected[path] = obj["sha"]
    if not 20 <= len(expected) <= MAX_FILES:
        raise m29.EvidenceError("Unexpected first-party source file count")
    return tree_sha, expected


def read_archive(raw: bytes, expected: dict[str, str]) -> dict[str, bytes]:
    """Read ZIP members in memory; no filesystem extraction or code execution."""
    if len(raw) > MAX_ZIP_BYTES or not zipfile.is_zipfile(io.BytesIO(raw)):
        raise m29.EvidenceError("Invalid or oversized pinned source archive")
    files = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        entries = z.infolist()
        if len(entries) > MAX_ENTRIES:
            raise m29.EvidenceError("Archive entry cap exceeded")
        roots = set()
        total = 0
        for info in entries:
            if info.is_dir():
                continue
            parts = PurePosixPath(info.filename).parts
            if len(parts) < 2 or ".." in parts or info.filename.startswith("/"):
                raise m29.EvidenceError("Unsafe archive member path")
            roots.add(parts[0])
            path = "/".join(parts[1:])
            if not path.startswith(PREFIX) or not path.endswith(".py"):
                continue
            if path not in expected or path in files:
                raise m29.EvidenceError("Unexpected/duplicate first-party Python file")
            if info.file_size > MAX_FILE_BYTES:
                raise m29.EvidenceError("Oversized source file")
            total += info.file_size
            if total > MAX_TOTAL_SOURCE_BYTES:
                raise m29.EvidenceError("Total source bytes exceeded")
            content = z.read(info)
            if m29.blob_sha(content) != expected[path]:
                raise m29.EvidenceError(f"Git blob mismatch: {path}")
            files[path] = content
        if len(roots) != 1 or set(files) != set(expected):
            raise m29.EvidenceError("Incomplete or ambiguous source archive")
    return files


def fetch_snapshot(revision: str) -> dict:
    commit = m29.COMMITS[revision]
    tree_sha, expected = expected_source_blobs(commit)
    archive_url = f"https://codeload.github.com/{m29.REPO}/zip/{commit}"
    raw = get_bytes(archive_url, MAX_ZIP_BYTES)
    files = read_archive(raw, expected)
    return {"commit": commit, "tree_sha": tree_sha, "expected": expected, "files": files}


def index_snapshot(snapshot: dict) -> list[dict]:
    if snapshot["commit"] not in m29.COMMITS.values():
        raise m29.EvidenceError("Unpinned source revision")
    files, expected = snapshot["files"], snapshot["expected"]
    if not files or set(files) != set(expected):
        raise m29.EvidenceError("Incomplete source snapshot")
    symbols = []
    for path in sorted(files):
        raw = files[path]
        if len(raw) > MAX_FILE_BYTES or m29.blob_sha(raw) != expected[path]:
            raise m29.EvidenceError(f"Source hash mismatch: {path}")
        indexed, warning = _index_python(path, raw.decode("utf-8-sig"))
        if warning:
            raise m29.EvidenceError(f"AST parse failed for {path}: {warning}")
        symbols.extend(indexed)
    if not symbols:
        raise m29.EvidenceError("No indexed implementation symbols")
    return symbols


def rank_case(symbols: list[dict], query: str, *, normalized: bool) -> list[dict]:
    if normalized:
        # Copy token lists so original and normalized baselines are isolated.
        indexed = [{**s, "tokens": [normalize_token(t) for t in s["tokens"]]} for s in symbols]
        query = normalized_query(query)
    else:
        indexed = symbols
    return rank_candidates(query, {"symbols": indexed}, top_k=10)


def build(snapshots: dict, evidence: dict) -> dict:
    internal = evidence["internal"]
    if internal["static_file_revision_objects_verified"] != 6:
        raise m29.EvidenceError("M29 pinned license/source/test evidence incomplete")
    if not evidence["reviewer_index"]["license"].startswith("MIT"):
        raise m29.EvidenceError("MIT license not verified")
    if set(snapshots) != {"before", "after"}:
        raise m29.EvidenceError("Missing source revision")
    rows, per_revision = [], {}
    for revision in ("before", "after"):
        snapshot = snapshots[revision]
        if snapshot["commit"] != m29.COMMITS[revision]:
            raise m29.EvidenceError("Wrong source revision")
        symbols = index_snapshot(snapshot)
        per_revision[revision] = {
            "commit": snapshot["commit"],
            "git_tree_sha": snapshot["tree_sha"],
            "verified_first_party_python_files": len(snapshot["files"]),
            "indexed_implementation_symbols": len(symbols),
        }
        for scenario in m29.SCENARIOS:
            ranks = {}
            candidates = {}
            for method in METHODS:
                ranked = rank_case(symbols, scenario["requirement_text"], normalized=(method == METHODS[1]))
                # Fix locus is a post-ranking diagnostic only; never used in ranking.
                ranks[method] = next((i for i, s in enumerate(ranked, 1)
                    if s["path"] == m29.SOURCE and s["qualified_name"] == m40.TARGET), None)
                candidates[method] = [{
                    "rank": i, "path": s["path"], "qualified_name": s["qualified_name"],
                    "score": s["score"],
                    "source_url": m29.source_url(revision, s["path"], s["line_start"]),
                } for i, s in enumerate(ranked, 1)]
            rows.append({
                "case_id": scenario["case_id"], "revision": revision,
                "requirement_origin": scenario["origin"],
                "known_fix_locus_ranks_NOT_GOLD": ranks,
                "top_10_candidates": candidates,
                "behavioral_decision": "insufficient_evidence",
                "independent_gold": None,
            })
    counts = {method: {
        "known_fix_locus_top1_exploratory": sum(row["known_fix_locus_ranks_NOT_GOLD"][method] == 1 for row in rows),
        "known_fix_locus_top5_exploratory": sum(
            (r is not None and r <= 5) for row in rows
            for r in [row["known_fix_locus_ranks_NOT_GOLD"][method]]
        ),
        "known_fix_locus_top10_exploratory": sum(
            row["known_fix_locus_ranks_NOT_GOLD"][method] is not None for row in rows
        ),
    } for method in METHODS}
    return {
        "schema": SCHEMA, "project": m29.REPO,
        "source_license": evidence["reviewer_index"]["license"],
        "issue": m29.ISSUE, "upstream_fix": m29.FIX,
        "source_scope": "all src/pip/_internal/**/*.py at each pinned commit (no preselected fix file)",
        "source_revisions": per_revision, "requirement_revision_pairs": len(rows),
        "methods": counts, "cases": rows,
        "independent_adjudications": 0, "behavioral_decisions": 0,
        "behavioral_abstentions": len(rows), "held_out_project_evaluation": False,
        "external_project_code_executed": False,
        "conformance_accuracy": None, "violation_precision": None,
        "violation_recall": None, "conformance_coverage": None,
        "limitations": [
            "One previously inspected development project; six correlated cases from three scenario families.",
            "Source scope is all first-party pip _internal Python, not vendored libraries or functional tests.",
            "Historical fix locus is a post-ranking diagnostic, not independently adjudicated trace gold.",
            "Git blobs and license are verified; source files are parsed as inert text, never executed.",
            "No independent reviewers, runtime observations, held-out projects, or conformance labels.",
        ],
    }


def write(report: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "m42_first_party_tree_retrieval.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# M42 real first-party pip source-tree retrieval (NOT GOLD)", "",
        "Scope: every Git-blob-verified Python file under `src/pip/_internal/` at both pinned commits.",
        "No oracle selection of factory.py, no upstream code execution, no independent behavioral labels.", "",
        "| Method | Known fix top-1 | Top-5 | Top-10 |", "|---|---:|---:|---:|",
    ]
    for method, count in report["methods"].items():
        lines.append(f"| {method} | {count['known_fix_locus_top1_exploratory']}/6 | "
                     f"{count['known_fix_locus_top5_exploratory']}/6 | "
                     f"{count['known_fix_locus_top10_exploratory']}/6 |")
    lines += ["", "These are previously inspected development-case diagnostics, NOT retrieval accuracy.",
              "All six behavioral cases abstain; independent adjudications: 0.",
              "Conformance accuracy, violation precision/recall, and independent coverage: NOT MEASURED.",
              "Next: independent M20 reviewers and trusted revision-matched behavior; untouched projects for final evaluation."]
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    evidence = m29.build_evidence(m29.fetch_pinned())
    snapshots = {revision: fetch_snapshot(revision) for revision in ("before", "after")}
    report = build(snapshots, evidence)
    write(report, args.out_dir)
    print(json.dumps({
        "files": {k: v["verified_first_party_python_files"] for k, v in report["source_revisions"].items()},
        "symbols": {k: v["indexed_implementation_symbols"] for k, v in report["source_revisions"].items()},
        "methods": report["methods"], "independent_adjudications": 0,
        "conformance_accuracy": None,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
