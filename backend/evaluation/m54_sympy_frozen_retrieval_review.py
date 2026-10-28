"""M54: one pinned real SymPy issue -> complete source -> frozen M42 BM25 -> M20.
External source is parsed as inert text, never imported or executed. NOT GOLD.
"""
from __future__ import annotations
import argparse
import io
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile

from backend.app.services.code_traceability import _index_python
from backend.evaluation import m20_annotation_queue as m20
from backend.evaluation import m29_pip_historical_regression as m29
from backend.evaluation import m42_pip_first_party_tree_retrieval as m42
from backend.evaluation import m49_ranked_m20_review as m49
from backend.evaluation import m52_swebench_verified_intake as m52

SCHEMA = "m54-sympy-frozen-whole-production-tree-review-1"
REPO = "sympy/sympy"
MAX_ARCHIVE_BYTES = 100_000_000
MAX_TREE_BYTES = 20_000_000
MAX_SOURCE_BYTES = 150_000_000
MAX_FILE_BYTES = 3_000_000
MAX_FILES = 8_000
MAX_ENTRIES = 30_000


def production_source(path: str) -> bool:
    """All first-party non-test Python files; no fix-file oracle."""
    parts = PurePosixPath(path).parts
    return (len(parts) >= 2 and parts[0] == "sympy" and path.endswith(".py")
            and not any(p in {"tests", "test", "__pycache__"} for p in parts)
            and not parts[-1].startswith("test_") and not parts[-1].endswith("_test.py"))


def expected_source_blobs(commit: str, *, get_json=None):
    if get_json is None:
        get_json = lambda url: json.loads(m42.get_bytes(url, MAX_TREE_BYTES))
    root = f"https://api.github.com/repos/{REPO}/git"
    commit_doc = get_json(f"{root}/commits/{commit}")
    if commit_doc.get("sha") != commit:
        raise ValueError("Git commit identity mismatch")
    tree_sha = commit_doc.get("tree", {}).get("sha")
    if not isinstance(tree_sha, str) or len(tree_sha) != 40:
        raise ValueError("Missing commit tree SHA")
    tree_doc = get_json(f"{root}/trees/{tree_sha}?recursive=1")
    if tree_doc.get("sha") != tree_sha or tree_doc.get("truncated") is not False:
        raise ValueError("Incomplete or wrong Git tree")
    expected, license_sha = {}, None
    for obj in tree_doc.get("tree", []):
        path = obj.get("path", "")
        if path == "LICENSE":
            if obj.get("type") != "blob":
                raise ValueError("Unexpected license Git object")
            license_sha = obj.get("sha")
        if production_source(path):
            if obj.get("type") != "blob" or obj.get("mode") not in {"100644", "100755"}:
                raise ValueError("Unexpected source Git object")
            expected[path] = obj.get("sha")
    if not 50 <= len(expected) <= MAX_FILES or not license_sha:
        raise ValueError("Missing or implausible complete production source tree/license")
    return tree_sha, expected, license_sha


def read_archive(raw: bytes, expected: dict[str, str]):
    """Read ZIP in memory; reject tampering, traversal, symlinks and missing files."""
    if len(raw) > MAX_ARCHIVE_BYTES or not zipfile.is_zipfile(io.BytesIO(raw)):
        raise ValueError("Invalid or oversized pinned archive")
    files, roots, total = {}, set(), 0
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        if len(z.infolist()) > MAX_ENTRIES:
            raise ValueError("Archive entry limit exceeded")
        for info in z.infolist():
            if info.is_dir():
                continue
            parts = PurePosixPath(info.filename).parts
            if (len(parts) < 2 or ".." in parts or info.filename.startswith("/")
                    or "\\" in info.filename
                    or stat.S_ISLNK((info.external_attr >> 16) & 65535)):
                raise ValueError("Unsafe archive member")
            roots.add(parts[0])
            path = "/".join(parts[1:])
            if not production_source(path):
                continue
            if path not in expected or path in files:
                raise ValueError("Unexpected or duplicate source")
            if info.file_size > MAX_FILE_BYTES:
                raise ValueError("Oversized source file")
            total += info.file_size
            if total > MAX_SOURCE_BYTES:
                raise ValueError("Source tree too large")
            content = z.read(info)
            if m29.blob_sha(content) != expected[path]:
                raise ValueError("Source Git blob mismatch: " + path)
            files[path] = content
    if len(roots) != 1 or set(files) != set(expected):
        raise ValueError("Incomplete production source snapshot")
    return files


def fetch_snapshot(case: dict, *, get_json=None, get_bytes=None):
    commit = case["source_commit"]
    tree_sha, expected, license_sha = expected_source_blobs(commit, get_json=get_json)
    if get_bytes is None:
        get_bytes = m42.get_bytes
    archive = get_bytes(f"https://codeload.github.com/{REPO}/zip/{commit}", MAX_ARCHIVE_BYTES)
    files = read_archive(archive, expected)
    license_raw = get_bytes(f"https://raw.githubusercontent.com/{REPO}/{commit}/LICENSE", MAX_FILE_BYTES)
    if (m29.blob_sha(license_raw) != license_sha
            or m52.digest(license_raw) != case["license_sha256"]):
        raise ValueError("Pinned source license mismatch")
    m52.validate_license(license_raw)
    return {"commit": commit, "tree_sha": tree_sha, "expected": expected,
            "files": files, "license_git_blob": license_sha}


def build(case: dict, snapshot: dict):
    """Rank using unchanged M42 normalized BM25, without patch-derived oracle."""
    if case["source_commit"] != snapshot["commit"] or case["project"] != REPO:
        raise ValueError("Requirement/source revision mismatch")
    if set(snapshot["expected"]) != set(snapshot["files"]):
        raise ValueError("Incomplete source snapshot")
    symbols = []
    for path in sorted(snapshot["files"]):
        raw = snapshot["files"][path]
        if not production_source(path) or m29.blob_sha(raw) != snapshot["expected"][path]:
            raise ValueError("Source provenance mismatch")
        parsed, warning = _index_python(path, raw.decode("utf-8-sig"))
        if warning:
            raise ValueError("Unparseable pinned source: " + path)
        symbols.extend(parsed)
    if len(symbols) < 5:
        raise ValueError("Insufficient source symbols")
    ranked = m42.rank_case(symbols, case["requirement_text"], normalized=True)
    if len(ranked) < 5:
        raise ValueError("Fewer than five retrieved candidates")
    digest = m49.snapshot_digest(snapshot)
    candidates = []
    for item in ranked[:5]:
        url = (f"https://github.com/{REPO}/blob/{snapshot['commit']}/"
               f"{item['path']}#L{item['line_start']}")
        candidates.append({"symbol_id": item["symbol_id"],
                           "source_path": item["path"],
                           "qualified_name": item["qualified_name"],
                           "description": "Pinned source location: " + url})
    full_text = case["requirement_text"]
    # M20 accepts <=5000 characters. Keep original full text in reviewer rows.
    review_excerpt = full_text[:4900]
    universe = {"schema_version": m20.SCHEMA,
                "project_id": "SYMPY_" + snapshot["commit"][:12] + "_CASE001",
                "source_commit": snapshot["commit"],
                "code_snapshot_sha256": digest,
                "requirements": [{"requirement_id": "CASE001",
                                  "requirement_text": review_excerpt}],
                "symbols": candidates, "observed_links": []}
    queue = m20.build_queue(universe, seed="m54-frozen-m42-sympy-v1",
                            hard_per_requirement=5, random_per_requirement=0)
    if len(queue["queue"]) != 5:
        raise ValueError("Incomplete M20 queue")
    reviewers = {}
    for reviewer in ("A", "B"):
        reviewers[reviewer] = [{**row, "full_requirement_text": full_text,
                                "requirement_sha256": case["requirement_sha256"],
                                "reviewer": "reviewer_" + reviewer,
                                "link_label": None, "evidence_notes": None,
                                "behavioral_label": None, "annotation_status": "pending"}
                               for row in queue["queue"]]
    return {"schema": SCHEMA, "project": REPO,
            "review_case_id": case["review_case_id"],
            "source_commit": snapshot["commit"], "git_tree_sha": snapshot["tree_sha"],
            "license": "BSD-3-Clause; verified at pinned source revision",
            "license_git_blob": snapshot["license_git_blob"],
            "source_snapshot_sha256": digest,
            "verified_production_python_files": len(snapshot["files"]),
            "indexed_production_symbols": len(symbols),
            "source_scope": "all sympy/**/*.py excluding tests/test modules, not a selected fix folder",
            "retrieval_method": "unchanged M42 normalized BM25",
            "m20_queue_sha256": queue["manifest"]["blind_queue_sha256"],
            "reviewer_rows": reviewers,
            "internal_top_five_NOT_GOLD": [
                {"rank": i, "path": s["path"], "qualified_name": s["qualified_name"],
                 "uncalibrated_score": s["score"]} for i, s in enumerate(ranked[:5], 1)],
            "requirement_text_truncated_in_m20_queue": len(full_text) > 4900,
            "independent_link_labels": 0, "independent_behavioral_labels": 0,
            "independent_adjudications": 0, "held_out_projects_scored": 0,
            "external_code_executed": False,
            "conformance_accuracy": None, "violation_precision": None,
            "violation_recall": None, "coverage": None,
            "limitations": [
                "One SymPy issue and one project, not held-out project scoring.",
                "SWE-bench Verified issue screening is not conformance gold.",
                "Only top-five candidates are reviewed; no whole-repository recall.",
                "No approved behavior observations, independent review or adjudication.",
                "BM25 returns code links, not behavioral verdicts.",
                "Training contamination and source-history unblinding remain unresolved."]}


def write(report: dict, output: Path):
    if output.exists():
        raise ValueError("Refusing to overwrite evidence")
    output.mkdir(parents=True)
    internal = {k: v for k, v in report.items() if k != "reviewer_rows"}
    (output / "INTERNAL_DO_NOT_SHARE.json").write_text(
        json.dumps(internal, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for reviewer, rows in report["reviewer_rows"].items():
        (output / f"reviewer_{reviewer}.jsonl").write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    (output / "REVIEW_PROTOCOL.md").write_text(
        "# M54 SymPy review: pending, NOT GOLD\n\n"
        "Give reviewers only their separate JSONL files. Keep internal rankings "
        "and historical patches private. Read the full original issue and inspect "
        "each pinned source candidate. Mark link_label with cited source lines. "
        "The top-five set is not whole-repository recall. Do not infer behavior "
        "from code links or patches. Two independent reviewers, separate approved "
        "revision-matched behavioral observations and third-party adjudication "
        "are outstanding. Not untouched held-out evaluation.\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = m52.build_manifest(m52.verify_dataset(m52.download(m52.DATASET_URL)))
    case = manifest["candidate_cases"][0]
    snapshot = fetch_snapshot(case)
    report = build(case, snapshot)
    write(report, args.out_dir)
    print(json.dumps({"project": REPO, "case": case["review_case_id"],
                      "source_files": report["verified_production_python_files"],
                      "symbols": report["indexed_production_symbols"],
                      "m20_candidates_per_reviewer": 5, "independent_labels": 0,
                      "conformance_accuracy": None}, sort_keys=True))


if __name__ == "__main__":
    main()
