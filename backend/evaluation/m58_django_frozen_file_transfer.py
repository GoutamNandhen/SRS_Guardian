"""M58: frozen M57 file-level retrieval on a NEW Django project candidate.

One pinned SWE-bench Verified issue; complete Git-blob-verified production
source, unchanged M57 lexical BM25 parameters, M20 unlabeled review. Historical
patch files are inspected ONLY AFTER retrieval as a weak diagnostic.
No external source is imported, installed, applied, or executed.
This is NOT independent behavioral conformance or adjudicated trace gold.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile

from backend.evaluation import m20_annotation_queue as m20
from backend.evaluation import m29_pip_historical_regression as m29
from backend.evaluation import m42_pip_first_party_tree_retrieval as m42
from backend.evaluation import m52_swebench_verified_intake as m52
from backend.evaluation import m54_sympy_frozen_retrieval_review as m54
from backend.evaluation import m57_sympy_file_level_retrieval as m57

SCHEMA = "m58-django-frozen-m57-cross-project-1"
REPO = "django/django"
DIFF_PATH = re.compile(r"^diff --git a/(.+) b/(.+)$", re.MULTILINE)
COMMIT = re.compile(r"[0-9a-f]{40}\Z")


def production_source(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return (len(parts) >= 2 and parts[0] == "django" and path.endswith(".py")
            and not any(p in {"tests", "test", "__pycache__"} for p in parts)
            and not parts[-1].startswith("test_") and not parts[-1].endswith("_test.py"))


def select_case(rows: list[dict]) -> dict:
    """Predeclared deterministic selection; no retrieval or patch inspection."""
    eligible = sorted((r for r in rows if r.get("repo") == REPO),
                      key=lambda r: r["instance_id"])
    for row in eligible:
        if (isinstance(row.get("base_commit"), str)
                and COMMIT.fullmatch(row["base_commit"])
                and all(isinstance(row.get(k), str) and row[k].strip()
                        for k in ("problem_statement", "patch", "test_patch"))):
            return row
    raise ValueError("No complete Django issue in pinned external dataset")


def read_archive(raw: bytes, expected: dict[str, str]) -> dict[str, bytes]:
    """Read untrusted archive as inert bytes, with exact Git blob verification."""
    if len(raw) > m54.MAX_ARCHIVE_BYTES or not zipfile.is_zipfile(io.BytesIO(raw)):
        raise ValueError("Invalid or oversized archive")
    files, roots, total = {}, set(), 0
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if len(archive.infolist()) > m54.MAX_ENTRIES:
            raise ValueError("Too many archive entries")
        for item in archive.infolist():
            if item.is_dir():
                continue
            parts = PurePosixPath(item.filename).parts
            if (len(parts) < 2 or ".." in parts or item.filename.startswith("/")
                    or "\\" in item.filename
                    or stat.S_ISLNK((item.external_attr >> 16) & 65535)):
                raise ValueError("Unsafe archive entry")
            roots.add(parts[0])
            path = "/".join(parts[1:])
            if not production_source(path):
                continue
            if path not in expected or path in files:
                raise ValueError("Unexpected or duplicate production file")
            if item.file_size > m54.MAX_FILE_BYTES:
                raise ValueError("Oversized source file")
            total += item.file_size
            if total > m54.MAX_SOURCE_BYTES:
                raise ValueError("Source size cap exceeded")
            raw_file = archive.read(item)
            if m29.blob_sha(raw_file) != expected[path]:
                raise ValueError("Git blob mismatch: " + path)
            files[path] = raw_file
    if len(roots) != 1 or set(files) != set(expected):
        raise ValueError("Incomplete production source tree")
    return files


def fetch_snapshot(commit: str, *, get_json=None, get_bytes=None) -> dict:
    if not isinstance(commit, str) or not COMMIT.fullmatch(commit):
        raise ValueError("Invalid pinned source commit")
    if get_bytes is None:
        get_bytes = m42.get_bytes
    if get_json is None:
        get_json = lambda url: json.loads(get_bytes(url, m54.MAX_TREE_BYTES))
    root = f"https://api.github.com/repos/{REPO}/git"
    commit_doc = get_json(f"{root}/commits/{commit}")
    if commit_doc.get("sha") != commit:
        raise ValueError("Commit identity mismatch")
    tree_sha = commit_doc.get("tree", {}).get("sha")
    if not isinstance(tree_sha, str) or not COMMIT.fullmatch(tree_sha):
        raise ValueError("Missing Git tree")
    tree_doc = get_json(f"{root}/trees/{tree_sha}?recursive=1")
    if tree_doc.get("sha") != tree_sha or tree_doc.get("truncated") is not False:
        raise ValueError("Incomplete Git tree")
    expected, license_sha = {}, None
    for obj in tree_doc.get("tree", []):
        path = obj.get("path", "")
        if path == "LICENSE":
            if obj.get("type") != "blob":
                raise ValueError("Invalid license Git object")
            license_sha = obj.get("sha")
        if production_source(path):
            if obj.get("type") != "blob" or obj.get("mode") not in {"100644", "100755"}:
                raise ValueError("Invalid production Git object")
            expected[path] = obj.get("sha")
    if not 100 <= len(expected) <= m54.MAX_FILES or not license_sha:
        raise ValueError("Incomplete source or license metadata")
    archive = get_bytes(f"https://codeload.github.com/{REPO}/zip/{commit}",
                        m54.MAX_ARCHIVE_BYTES)
    files = read_archive(archive, expected)
    license_raw = get_bytes(
        f"https://raw.githubusercontent.com/{REPO}/{commit}/LICENSE",
        m54.MAX_FILE_BYTES)
    if m29.blob_sha(license_raw) != license_sha:
        raise ValueError("Pinned license blob mismatch")
    license_text = license_raw.decode("utf-8")
    if not all(s in license_text for s in (
            "Django", "Redistribution and use in source and binary forms",
            "THIS SOFTWARE IS PROVIDED")):
        raise ValueError("BSD-3-Clause license text not established")
    return {"commit": commit, "tree_sha": tree_sha, "expected": expected,
            "files": files, "license_git_blob": license_sha,
            "license_sha256": hashlib.sha256(license_raw).hexdigest()}


def frozen_file_rank(snapshot: dict, requirement: str) -> tuple[list[dict], int]:
    """Exact M57 BM25 formula, tokenization, path x4 and 120k text cap."""
    if not snapshot.get("files") or set(snapshot["files"]) != set(snapshot["expected"]):
        raise ValueError("Incomplete source snapshot")
    q = set(m57.tokens(requirement))
    if not q:
        raise ValueError("No usable requirement terms")
    docs, df, truncated = [], Counter(), 0
    for path in sorted(snapshot["files"]):
        raw = snapshot["files"][path]
        if not production_source(path) or m29.blob_sha(raw) != snapshot["expected"][path]:
            raise ValueError("Unverified production source")
        source = raw.decode("utf-8-sig")
        truncated += len(source) > m57.MAX_INDEX_CHARS_PER_FILE
        terms = m57.tokens((" ".join(path.replace(".py", "").split("/")) + " ") * 4
                           + source[:m57.MAX_INDEX_CHARS_PER_FILE])
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
            score += idf * (tf * 2.2) / (
                tf + 1.2 * (0.25 + 0.75 * length / avgdl))
        ranked.append({"path": path, "score": score})
    ranked.sort(key=lambda item: (-item["score"], item["path"]))
    return ranked[:5], truncated


def evaluate(row: dict, snapshot: dict) -> dict:
    """Freeze retrieval before opening patch; return M20 packets and diagnostics."""
    if (row["repo"] != REPO or row["base_commit"] != snapshot["commit"]):
        raise ValueError("Issue/source revision mismatch")
    requirement = row["problem_statement"]
    requirement_hash = m52.digest(requirement.encode("utf-8"))
    ranked, truncated = frozen_file_rank(snapshot, requirement)
    if len(ranked) != 5:
        raise ValueError("Insufficient candidates")
    symbols = [{
        "symbol_id": "FILE-" + hashlib.sha256(x["path"].encode()).hexdigest()[:24],
        "source_path": x["path"], "qualified_name": x["path"],
        "description": f"Pinned source: https://github.com/{REPO}/blob/{snapshot['commit']}/{x['path']}",
    } for x in ranked]
    universe = {
        "schema_version": m20.SCHEMA,
        "project_id": "DJANGO_" + snapshot["commit"][:12],
        "source_commit": snapshot["commit"],
        "code_snapshot_sha256": hashlib.sha256(json.dumps(
            snapshot["expected"], sort_keys=True).encode()).hexdigest(),
        "requirements": [{"requirement_id": "CASE001",
                          "requirement_text": requirement[:4900]}],
        "symbols": symbols, "observed_links": [],
    }
    queue = m20.build_queue(universe, seed="m58-frozen-m57-django-v1",
                            hard_per_requirement=5, random_per_requirement=0)
    if len(queue["queue"]) != 5:
        raise ValueError("Incomplete M20 packet")
    reviewers = {r: [{**x, "review_case_id": "CASE-001",
                       "full_requirement_text": requirement,
                       "requirement_sha256": requirement_hash,
                       "reviewer": "reviewer_" + r, "link_label": None,
                       "behavioral_label": None, "evidence_notes": None,
                       "annotation_status": "pending"} for x in queue["queue"]]
                 for r in ("A", "B")}
    # Historical patches enter only here, after rank and reviewer selection.
    matches = DIFF_PATH.findall(row["patch"])
    if not matches:
        raise ValueError("Historical patch has no diff paths")
    changed = {b for a, b in matches if a == b and production_source(b)}
    eligible = changed & set(snapshot["expected"])
    hit = bool(eligible & {x["path"] for x in ranked}) if eligible else None
    internal = {
        "schema": SCHEMA, "project": REPO, "source_commit": snapshot["commit"],
        "source_tree_sha": snapshot["tree_sha"],
        "source_license": "BSD-3-Clause (verified pinned LICENSE Git blob)",
        "license_git_blob": snapshot["license_git_blob"],
        "license_sha256": snapshot["license_sha256"],
        "dataset_revision": m52.DATASET_REV,
        "dataset_sha256": m52.DATASET_SHA256,
        "instance_id_INTERNAL": row["instance_id"],
        "requirement_sha256": requirement_hash,
        "historical_patch_sha256_INTERNAL": m52.digest(row["patch"].encode()),
        "historical_test_patch_sha256_INTERNAL": m52.digest(row["test_patch"].encode()),
        "verified_production_files": len(snapshot["files"]),
        "truncated_index_files": truncated,
        "retrieval": "frozen M57 file BM25 (path x4, first 120k chars/file)",
        "ranked_top5_INTERNAL": ranked,
        "patch_file_proxy_eligible_NOT_GOLD": bool(eligible),
        "patch_file_hit_at5_NOT_GOLD": hit,
        "historical_base_indexable_fix_files_INTERNAL": sorted(eligible),
        "m20_queue_sha256": queue["manifest"]["blind_queue_sha256"],
        "independent_link_labels": 0, "independent_behavioral_observations": 0,
        "independent_adjudications": 0, "external_project_code_executed": False,
        "held_out_project_candidate": True,
        "held_out_behavioral_projects_scored": 0,
        "conformance_accuracy": None, "violation_precision": None,
        "violation_recall": None, "coverage": None,
        "limitations": [
            "New cross-project retrieval transfer; not adjudicated held-out conformance.",
            "Historical patch-file overlap is a weak post-retrieval diagnostic, not gold.",
            "Top-five sampling does not measure full-tree recall or coverage.",
            "Two independent M20 reviewers and third-person adjudication are absent.",
            "Approved revision-compatible behavioral observations are absent.",
            "Project-level contamination audit and full verifier freeze are outstanding.",
        ],
    }
    return internal, reviewers


def write(internal: dict, reviewers: dict, out: Path) -> None:
    if out.exists():
        raise ValueError("Refusing to overwrite evidence")
    out.mkdir(parents=True)
    (out / "INTERNAL_NOT_GOLD.json").write_text(
        json.dumps(internal, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for reviewer in ("A", "B"):
        (out / f"reviewer_{reviewer}.jsonl").write_text(
            "".join(json.dumps(x, sort_keys=True) + "\n" for x in reviewers[reviewer]),
            encoding="utf-8")
    (out / "REVIEW_PROTOCOL.md").write_text(
        "# M58 new-project M20 review — NOT GOLD\n\n"
        "Give reviewers only their own reviewer JSONL, not the INTERNAL file. "
        "Review all five pinned Django source files against the issue requirement; "
        "record cited source lines, uncertainty and abstentions. The candidate "
        "universe is only the top five and cannot establish retrieval recall. "
        "Do not use upstream historical fixes to label links. Independently "
        "review the real regression-test relevance and collect approved isolated "
        "before/after behavioral observations (exact commits, inputs, outputs, "
        "dependencies and hashes). Neither this script nor CI executes external "
        "code. Two independent reviewers and a separate adjudicator are required. "
        "No conformance or violation metrics can be computed yet.\n",
        encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    rows = m52.verify_dataset(m52.download(m52.DATASET_URL))
    row = select_case(rows)
    snapshot = fetch_snapshot(row["base_commit"])
    internal, reviewers = evaluate(row, snapshot)
    write(internal, reviewers, args.out_dir)
    print(json.dumps({
        "project": REPO, "real_cases": 1,
        "verified_production_files": internal["verified_production_files"],
        "patch_proxy_eligible_NOT_GOLD": internal["patch_file_proxy_eligible_NOT_GOLD"],
        "patch_file_hit_at5_NOT_GOLD": internal["patch_file_hit_at5_NOT_GOLD"],
        "m20_unlabeled_candidates_per_reviewer": 5,
        "independent_labels": 0, "held_out_behavioral_projects_scored": 0,
        "conformance_accuracy": None, "external_code_executed": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
