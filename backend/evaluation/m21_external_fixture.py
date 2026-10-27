"""Pinned external Apache-2.0 source fixture -> M20 independent-review queue.

Downloads static allowlisted text only; never imports/executes upstream code.
Author-declared trace tags are observations, NOT independently adjudicated gold.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import urllib.request
from backend.evaluation.m20_annotation_queue import build_queue, write_outputs

UPSTREAM = "flashtrace/flashtrace"
COMMIT = "834276e6ca543ba505f2455dd460b0b5195a6241"
PREFIX = "examples/polyglot-web/"
BLOBS = {
    "LICENSE": "261eeb9e9f8b2b4b0d119366dda99c6fd7d35c64",
    PREFIX + "spec.md": "d0ff767dcd394cb36f254ab5cb5ea65327119521",
    PREFIX + "metrics.ts": "e01f6af17f6930219add71cb41ff639dffa5ae12",
    PREFIX + "test_metrics.py": "6c8b5441584fa2a9d6c38e4b04fa57c9fffd0795",
    PREFIX + "aggregation.sql": "cdc91d89fab6a604d38935a2dad25246f33a638c",
    PREFIX + "index.html": "992ef8da8953f911f62480f04b90a8bb1ac19f30",
    PREFIX + "dashboard.vue": "6794c4cb48773628cb1658ccee0129cab911f007",
}
IMPLEMENTATION = ("metrics.ts", "aggregation.sql", "index.html", "dashboard.vue")
EXPECTED_NEEDS = {
    "req:web/dashboard#1": {"impl:web/page#1", "impl:web/markup#1", "impl:web/widget#1", "impl:web/theme#1"},
    "req:api/metrics#1": {"impl:api/metrics#1"},
    "req:data/aggregation#1": {"impl:data/aggregation#1"},
}
TAG = re.compile(r"\[(impl:[A-Za-z0-9_/#.-]+)\]")
REQ = re.compile(r"\x60(req:[A-Za-z0-9_/#.-]+)\x60\s*\n\s*([^\n]+)")
NEED = re.compile(r"impl:[A-Za-z0-9_/#.-]+")
MAX_BYTES = 100_000

class EvidenceError(ValueError):
    """External snapshot did not match the reviewed pinned version."""

def git_blob_id(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()

def fetch_pinned(*, source_dir: Path | None = None) -> dict[str, bytes]:
    """Fetch seven static, allowlisted upstream files, fail on any hash drift."""
    files = {}
    for path, expected in BLOBS.items():
        if source_dir is None:
            url = f"https://raw.githubusercontent.com/{UPSTREAM}/{COMMIT}/{path}"
            with urllib.request.urlopen(url, timeout=20) as response:
                raw = response.read(MAX_BYTES + 1)
        else:
            raw = (source_dir / path).read_bytes()
        if len(raw) > MAX_BYTES or git_blob_id(raw) != expected:
            raise EvidenceError(f"Pinned Git blob mismatch: {path}")
        files[path] = raw
    if b"Apache License" not in files["LICENSE"][:300]:
        raise EvidenceError("Apache-2.0 license text missing")
    return files

def build_evidence(files: dict[str, bytes], *, seed: str = "m21-external-preregistered-v1") -> dict:
    """Generate a real externally sourced but UNLABELED review dataset."""
    if set(files) != set(BLOBS):
        raise EvidenceError("Missing or extra upstream files")
    for path, raw in files.items():
        if git_blob_id(raw) != BLOBS[path]:
            raise EvidenceError(f"Unverified upstream file: {path}")
    spec = files[PREFIX + "spec.md"].decode("utf-8")
    requirements, need_map = [], {}
    for match in re.finditer(r"(?ms)^# [^\n]+\n(.*?)(?=^# |\Z)", spec):
        section = match.group(1)
        found = REQ.search(section)
        if not found:
            continue
        rid, statement = found.group(1), found.group(2).strip()
        if rid in need_map:
            raise EvidenceError("Duplicate upstream requirement")
        need_map[rid] = set(NEED.findall(section))
        requirements.append({
            "requirement_id": "REQ_" + re.sub(r"[^A-Za-z0-9]", "_", rid),
            "requirement_text": statement,
        })
    if need_map != EXPECTED_NEEDS:
        raise EvidenceError("Explicit upstream Needs changed; human review required")
    symbols, tag_to_symbol = [], {}
    for path in sorted(PREFIX + name for name in IMPLEMENTATION):
        lines = files[path].decode("utf-8").splitlines()
        for i, line in enumerate(lines):
            for tag in TAG.findall(line):
                if tag in tag_to_symbol:
                    raise EvidenceError(f"Duplicate implementation tag: {tag}")
                sid = f"CODE_{len(symbols)+1:03d}"
                snippet = " ".join(item.strip() for item in lines[i+1:i+5]
                                   if "[impl:" not in item and item.strip())[:220]
                symbols.append({
                    "symbol_id": sid, "source_path": path,
                    "qualified_name": f"code_component_{len(symbols)+1:03d}",
                    "description": snippet or "Source component requires inspection",
                })
                tag_to_symbol[tag] = sid
    if set(tag_to_symbol) != set().union(*EXPECTED_NEEDS.values()) or len(symbols) != 6:
        raise EvidenceError("Implementation tags differ from expected requirements")
    links = [
        {"requirement_id": "REQ_" + re.sub(r"[^A-Za-z0-9]", "_", rid),
         "symbol_id": tag_to_symbol[tag]}
        for rid, tags in sorted(need_map.items()) for tag in sorted(tags)
    ]
    # SHA256 of length-delimited paths and bytes for 5 code/test files.
    # Not a digest of a deployable executable build.
    h = hashlib.sha256()
    for path in sorted(PREFIX + name for name in (*IMPLEMENTATION, "test_metrics.py")):
        raw = files[path]
        h.update(len(path.encode()).to_bytes(4, "big"))
        h.update(path.encode())
        h.update(len(raw).to_bytes(8, "big"))
        h.update(raw)
    universe = {
        "schema_version": "m20-candidate-universe-1",
        "project_id": "FLASH_TRACE_POLYGLOT_FIXTURE",
        "source_commit": COMMIT,
        "code_snapshot_sha256": h.hexdigest(),
        "requirements": requirements, "symbols": symbols,
        "observed_links": links,
    }
    queue = build_queue(universe, seed=seed, hard_per_requirement=1, random_per_requirement=1)
    if len(requirements) != 3 or len(links) != 6 or len(queue["queue"]) != 12:
        raise EvidenceError("Unexpected fixture dimensions")
    evidence = {
        "schema_version": "m21-external-fixture-evidence-1",
        "upstream_repo": UPSTREAM, "upstream_commit": COMMIT,
        "upstream_url": f"https://github.com/{UPSTREAM}/tree/{COMMIT}/{PREFIX}",
        "license": "Apache-2.0", "license_blob_sha1": BLOBS["LICENSE"],
        "source_files_verified": [
            {"path": path, "git_blob_sha1": BLOBS[path],
             "sha256": hashlib.sha256(files[path]).hexdigest()} for path in sorted(files)
        ],
        "code_snapshot_sha256": universe["code_snapshot_sha256"],
        "snapshot_definition": "length-delimited path and bytes for 5 code/test files; not an executable build",
        "requirement_count": len(requirements), "implementation_component_count": len(symbols),
        "author_declared_links_unverified": len(links),
        "sampled_annotation_pairs": len(queue["queue"]),
        "independent_labels_collected": False, "independent_project_count": 0,
        "research_95_eligible": False,
        "conformance_accuracy": None, "violation_precision": None,
        "violation_recall": None, "conformance_coverage": None,
        "limitations": [
            "External authored parser-test fixture, not independently sampled production software.",
            "Developer trace tags are observations, NOT independent ground truth.",
            "Source is intentionally not an integrated runnable application.",
            "Reviewers must inspect source fragments with original trace tags masked.",
            "Two independent link annotators and adjudication are pending; executable conformance oracles are absent.",
            "M20 lexical/random sampling does not establish population-level accuracy.",
        ],
    }
    return {"universe": universe, "queue": queue, "evidence": evidence}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, help="Optional local checkout of pinned upstream commit")
    args = parser.parse_args()
    result = build_evidence(fetch_pinned(source_dir=args.source_dir))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "candidate_universe.json").write_text(
        json.dumps(result["universe"], indent=2) + "\n", encoding="utf-8")
    (args.out_dir / "external_evidence.json").write_text(
        json.dumps(result["evidence"], indent=2) + "\n", encoding="utf-8")
    write_outputs(result["queue"], args.out_dir / "annotation")
    print(json.dumps({
        "verified_files": len(BLOBS),
        "requirements": result["evidence"]["requirement_count"],
        "observed_links_unverified": result["evidence"]["author_declared_links_unverified"],
        "sampled_pairs": result["evidence"]["sampled_annotation_pairs"],
        "research_95_eligible": False,
    }, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
