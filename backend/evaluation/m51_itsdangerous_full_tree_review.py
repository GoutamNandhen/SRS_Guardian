"""M51: transfer frozen M42 lexical retrieval to a fifth real external project.

The whole first-party itsdangerous source tree is verified as inert bytes at
two immutable Git revisions. No third-party source is imported or executed.
This is an unadjudicated development transfer case, NOT held-out or gold.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import zipfile

from backend.app.services.code_traceability import _index_python
from backend.evaluation import m20_annotation_queue as m20
from backend.evaluation import m29_pip_historical_regression as m29
from backend.evaluation import m42_pip_first_party_tree_retrieval as m42
from backend.evaluation import m49_ranked_m20_review as m49

SCHEMA = "m51-itsdangerous-full-tree-m20-transfer-1"
REPO = "pallets/itsdangerous"
ISSUE = "https://github.com/pallets/itsdangerous/issues/375"
FIX = "https://github.com/pallets/itsdangerous/pull/378"
COMMITS = {
    "before": "93ae366874bbd4f69d90495c45b2cd336387496c",
    "after": "2f69e841d2a979c616a55b226e444694f5d9c962",
}
PINNED = {
    "before": {
        "LICENSE.txt": "7b190ca6712aa09eede3e6de79f68d7fa29072da",
        "pyproject.toml": "966c86258cd5adfd8d1074050b357044cacfe2f4",
        "src/itsdangerous/signer.py": "6410e652f0d340677c32b25f638d5efe047d6d64",
        "tests/test_itsdangerous/test_serializer.py": "283712110440c5d9c5809125953fa6c41ad7692e",
    },
    "after": {
        "LICENSE.txt": "7b190ca6712aa09eede3e6de79f68d7fa29072da",
        "pyproject.toml": "966c86258cd5adfd8d1074050b357044cacfe2f4",
        "src/itsdangerous/signer.py": "e324dc03da90d9002200b68088f501df62777cd6",
        "tests/test_itsdangerous/test_serializer.py": "2c511cd202978f79a4e2f381f37b2b036b2b8370",
    },
}
PREFIX = "src/itsdangerous/"
REQUIREMENT = (
    "Importing itsdangerous should not fail merely because hashlib.sha1 is "
    "unavailable in a FIPS environment; callers must have a chance to select "
    "an alternate digest method before signing."
)


def verify_snapshot(snapshot: dict, revision: str) -> None:
    """Fail closed on source, license, test or declared-revision mismatches."""
    if revision not in COMMITS or snapshot.get("commit") != COMMITS[revision]:
        raise ValueError("Wrong immutable source revision")
    expected = snapshot.get("expected")
    files = snapshot.get("files")
    pinned = snapshot.get("pinned")
    if not isinstance(expected, dict) or not isinstance(files, dict) or not files:
        raise ValueError("Missing full source tree")
    if set(expected) != set(files) or not all(
        p.startswith(PREFIX) and p.endswith(".py") for p in expected
    ):
        raise ValueError("Incomplete or out-of-scope first-party source tree")
    if not 3 <= len(files) <= 100:
        raise ValueError("Unexpected source tree size")
    for path, raw in files.items():
        if len(raw) > m42.MAX_FILE_BYTES or m29.blob_sha(raw) != expected[path]:
            raise ValueError("Source Git blob mismatch: " + path)
    if not isinstance(pinned, dict) or set(pinned) != set(PINNED[revision]):
        raise ValueError("Missing pinned license/metadata/test objects")
    for path, raw in pinned.items():
        if m29.blob_sha(raw) != PINNED[revision][path]:
            raise ValueError("Pinned Git blob mismatch: " + path)
    if files.get("src/itsdangerous/signer.py") != pinned["src/itsdangerous/signer.py"]:
        raise ValueError("Signer does not match verified full source tree")
    license_text = pinned["LICENSE.txt"].decode("utf-8")
    if not all(s in license_text for s in (
        "Redistribution and use in source and binary forms",
        "Neither the name of the copyright holder",
        "THIS SOFTWARE IS PROVIDED",
    )):
        raise ValueError("BSD-3-Clause license evidence missing")
    metadata = pinned["pyproject.toml"].decode("utf-8")
    if 'license = { file = "LICENSE.txt" }' not in metadata:
        raise ValueError("Project license metadata inconsistent")



def read_source_archive(raw: bytes, expected: dict[str, str]) -> dict[str, bytes]:
    """Read inert Python source from pinned ZIP; reject ambiguous or unsafe members."""
    if len(raw) > m42.MAX_ZIP_BYTES or not zipfile.is_zipfile(io.BytesIO(raw)):
        raise ValueError("Invalid pinned ZIP")
    files = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        if len(entries) > m42.MAX_ENTRIES:
            raise ValueError("Too many archive entries")
        roots = set()
        total = 0
        for item in entries:
            if item.is_dir():
                continue
            parts = PurePosixPath(item.filename).parts
            if len(parts) < 2 or ".." in parts or item.filename.startswith("/"):
                raise ValueError("Unsafe ZIP member path")
            roots.add(parts[0])
            path = "/".join(parts[1:])
            if not path.startswith(PREFIX) or not path.endswith(".py"):
                continue
            if path not in expected or path in files:
                raise ValueError("Unexpected or duplicate source file")
            if item.file_size > m42.MAX_FILE_BYTES:
                raise ValueError("Oversized source file")
            total += item.file_size
            if total > m42.MAX_TOTAL_SOURCE_BYTES:
                raise ValueError("Oversized source tree")
            data = archive.read(item)
            if m29.blob_sha(data) != expected[path]:
                raise ValueError("Source Git blob mismatch: " + path)
            files[path] = data
    if len(roots) != 1 or set(files) != set(expected):
        raise ValueError("Incomplete or ambiguous source archive")
    return files


def fetch_snapshot(revision: str) -> dict:
    """Retrieve public immutable Git objects; never import or run their code."""
    if revision not in COMMITS:
        raise ValueError("Unknown revision")
    commit = COMMITS[revision]
    root = f"https://api.github.com/repos/{REPO}/git"
    metadata = m42.get_json(f"{root}/commits/{commit}")
    if metadata.get("sha") != commit:
        raise ValueError("Commit identity mismatch")
    tree_sha = metadata.get("tree", {}).get("sha")
    if not isinstance(tree_sha, str) or len(tree_sha) != 40:
        raise ValueError("Invalid commit tree")
    tree = m42.get_json(f"{root}/trees/{tree_sha}?recursive=1")
    if tree.get("sha") != tree_sha or tree.get("truncated") is not False:
        raise ValueError("Truncated or incorrect Git tree")
    expected = {}
    objects = {}
    for obj in tree.get("tree", []):
        path = obj.get("path", "")
        if obj.get("type") == "blob":
            objects[path] = obj.get("sha")
        if path.startswith(PREFIX) and path.endswith(".py"):
            if obj.get("type") != "blob" or obj.get("mode") not in ("100644", "100755"):
                raise ValueError("Unexpected source object")
            expected[path] = obj["sha"]
    if not 3 <= len(expected) <= 100:
        raise ValueError("Unexpected complete source tree")
    if any(objects.get(p) != sha for p, sha in PINNED[revision].items()):
        raise ValueError("Pinned source/license/test object not present in Git tree")
    archive = m42.get_bytes(
        f"https://codeload.github.com/{REPO}/zip/{commit}", m42.MAX_ZIP_BYTES
    )
    files = read_source_archive(archive, expected)
    pinned = {
        path: m42.get_bytes(
            f"https://raw.githubusercontent.com/{REPO}/{commit}/{path}",
            m42.MAX_FILE_BYTES,
        )
        for path in PINNED[revision]
    }
    snapshot = {
        "commit": commit, "tree_sha": tree_sha,
        "expected": expected, "files": files, "pinned": pinned,
    }
    verify_snapshot(snapshot, revision)
    return snapshot


def build(snapshots: dict) -> dict:
    """Frozen M42 ranker, no oracle target inserted; prepare M20 review rows."""
    if set(snapshots) != set(COMMITS):
        raise ValueError("Both immutable revisions required")
    reviewer_rows = {"A": [], "B": []}
    internal = []
    revisions = {}
    for revision in ("before", "after"):
        snapshot = snapshots[revision]
        verify_snapshot(snapshot, revision)
        symbols = []
        for path in sorted(snapshot["files"]):
            parsed, warning = _index_python(
                path, snapshot["files"][path].decode("utf-8-sig")
            )
            if warning:
                raise ValueError("Unparseable inert source: " + path)
            symbols.extend(parsed)
        if len(symbols) < 5:
            raise ValueError("Insufficient first-party symbols")
        # M42 normalized BM25 is fixed before this project is inspected.
        ranked = m42.rank_case(symbols, REQUIREMENT, normalized=True)
        if len(ranked) < 5:
            raise ValueError("Baseline retrieved fewer than five candidates")
        digest = m49.snapshot_digest(snapshot)
        candidate_symbols = []
        for candidate in ranked[:5]:
            path = candidate["path"]
            source_url = (
                f"https://github.com/{REPO}/blob/{snapshot['commit']}/"
                f"{path}#L{candidate['line_start']}"
            )
            candidate_symbols.append({
                "symbol_id": candidate["symbol_id"],
                "source_path": path,
                "qualified_name": candidate["qualified_name"],
                "description": "Pinned source location: " + source_url,
            })
        universe = {
            "schema_version": m20.SCHEMA,
            "project_id": "ITSDANGER_" + snapshot["commit"][:12],
            "source_commit": snapshot["commit"],
            "code_snapshot_sha256": digest,
            "requirements": [{
                "requirement_id": "FIPS_IMPORT_SHA1",
                "requirement_text": REQUIREMENT,
            }],
            "symbols": candidate_symbols,
            "observed_links": [],
        }
        queue = m20.build_queue(
            universe, seed="m51-fixed-m42-normalized-bm25-v1",
            hard_per_requirement=5, random_per_requirement=0,
        )
        if len(queue["queue"]) != 5:
            raise ValueError("Incomplete M20 candidate handoff")
        for reviewer in reviewer_rows:
            reviewer_rows[reviewer].extend({
                **row, "reviewer": "reviewer_" + reviewer,
                "link_label": None, "evidence_notes": None,
                "behavior_label": None, "annotation_status": "pending",
            } for row in queue["queue"])
        revisions[revision] = {
            "commit": snapshot["commit"],
            "tree_sha": snapshot["tree_sha"],
            "first_party_python_files": len(snapshot["files"]),
            "indexed_symbols": len(symbols),
            "source_snapshot_sha256": digest,
            "pinned_blob_shas": PINNED[revision],
            "m20_queue_sha256": queue["manifest"]["blind_queue_sha256"],
        }
        internal.append({
            "revision": revision,
            "ranked_top_five_NOT_GOLD": [{
                "rank": pos, "source_path": item["path"],
                "qualified_name": item["qualified_name"],
                "score_uncalibrated": item["score"],
            } for pos, item in enumerate(ranked[:5], 1)],
        })
    return {
        "schema": SCHEMA, "project": REPO,
        "requirement_source": ISSUE, "historical_fix": FIX,
        "license": "BSD-3-Clause, pinned LICENSE.txt at both revisions",
        "retrieval_method": "unchanged M42 normalized BM25; full first-party source tree",
        "revisions": revisions, "internal_ranked": internal,
        "reviewer_rows": reviewer_rows, "revision_cases": 2,
        "candidates_per_reviewer": 10, "independent_annotations": 0,
        "independent_adjudications": 0, "approved_behavioral_observations": 0,
        "held_out": False, "external_code_executed": False,
        "conformance_accuracy": None, "violation_precision": None,
        "violation_recall": None, "coverage": None,
        "limitations": [
            "Historical fix was inspected when selecting this case: not untouched held-out.",
            "Upstream issue, patch and test do not independently prove behavior.",
            "Only retrieved top-five links are sent to M20 reviewers; no whole-tree recall estimate.",
            "No independently observed FIPS environment, reviewer labels or adjudication.",
            "Frozen lexical predictions are uncalibrated and not behavioral verdicts.",
        ],
    }


def write(report: dict, out_dir: Path) -> None:
    if out_dir.exists():
        raise ValueError("Refusing to overwrite evidence")
    out_dir.mkdir(parents=True)
    internal = {k: v for k, v in report.items() if k != "reviewer_rows"}
    (out_dir / "INTERNAL_DO_NOT_SHARE.json").write_text(
        json.dumps(internal, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    for reviewer, rows in report["reviewer_rows"].items():
        (out_dir / f"reviewer_{reviewer}.jsonl").write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8",
        )
    (out_dir / "REVIEW_PROTOCOL.md").write_text(
        "# M51 independent review handoff — NOT GOLD\n\n"
        "Give reviewer A ONLY reviewer_A.jsonl and reviewer B ONLY "
        "reviewer_B.jsonl. Keep INTERNAL_DO_NOT_SHARE.json separate. "
        "Each reviewer must independently inspect each pinned source candidate, "
        "mark the M20 link label and cite exact source lines. Neither a patch "
        "nor a candidate link establishes behavior. Separately obtain approved "
        "revision-compatible observations in a FIPS-like environment with SHA-1 "
        "unavailable, recording environment and import outcome; no such run "
        "is authorized or performed here. A third independent person must "
        "adjudicate disagreements. Do not use this inspected development "
        "project as held-out scoring. Accuracy, precision, recall and coverage "
        "are undefined until independently adjudicated evidence exists.\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    snapshots = {rev: fetch_snapshot(rev) for rev in COMMITS}
    report = build(snapshots)
    write(report, args.out_dir)
    print(json.dumps({
        "revision_cases": report["revision_cases"],
        "candidates_per_reviewer": report["candidates_per_reviewer"],
        "first_party_files": {k: v["first_party_python_files"]
                              for k, v in report["revisions"].items()},
        "independent_adjudications": 0,
        "conformance_accuracy": None,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
