"""M23: pinned external TeaStore architecture-documentation-to-Java annotation pilot.

Static files only; no third-party code execution, training, or automatic labels.
Source subset is intentionally small and not a representative conformance benchmark.
The published SAD-code links are author/paper-provided observations, not our gold.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
from io import StringIO
import json
from pathlib import Path
import re
import urllib.request

from backend.evaluation.m20_annotation_queue import build_queue, write_outputs

DOC_REPO = "ArDoCo/Replication-Package-ICSE24_Recovering-Trace-Links-Between-Software-Documentation-And-Code"
DOC_COMMIT = "a4b221733fb43938f130636db8d5434bd30ec28d"
CODE_REPO = "ArDoCo/TeaStore"
CODE_COMMIT = "bdc49020a55cfa97eaabbb25744fefbc2697defa"
GOLD_PATH = "data/SAD-Code-goldstandards/goldstandard-teastore.csv"
DOC_FILES = {
    "LICENSE.md": "9178636db5328bbf687ec0cb85f95406c7f725cb",
    GOLD_PATH: "fb559e5f5f26092c1e2a8c28b3702366ef63cd8c",
    "data/ftlr-texts/teastore/1.txt": "0c4ac6ef96de591b06242d58586d8390519c5258",
    "data/ftlr-texts/teastore/27.txt": "d2dfa10323b7c8f5e2b34b21452c8ec52d466c72",
    "data/ftlr-texts/teastore/28.txt": "b9cdd51114ee54b82d811db6a3bedeebfb2a4673",
}
ROOT = "services/tools.descartes.teastore."
CODE_FILES = {
    "LICENSE": "8dada3edaf50dbc082c9a125058f25def75e625a",
    ROOT + "registry/src/main/java/tools/descartes/teastore/registry/rest/RegistryREST.java": "61a7260c958bc8a7ccbae1b39a9722d18e28ce9b",
    ROOT + "registry/src/main/java/tools/descartes/teastore/registry/rest/Registry.java": "16a1d40be6f44aee6daec388316de6f0d535cd43",
    ROOT + "recommender/src/main/java/tools/descartes/teastore/recommender/algorithm/RecommenderSelector.java": "a02208b455f2633595f97ed457f4e1a9267954d1",
    ROOT + "recommender/src/main/java/tools/descartes/teastore/recommender/algorithm/IRecommender.java": "e63a33a98d685c05ca1a498e5d5ca64d16d1a246",
    ROOT + "auth/src/main/java/tools/descartes/teastore/auth/security/ShaSecurityProvider.java": "c3730f199bd4b1030792906c80ff53eecdaa8311",
}
REQ_IDS = (1, 27, 28)
MAX_BYTES = 2_000_000
PROJECT_ID = "TEASTORE_ARCH_DOC_JAVA_SUBSET_M23"


class SourceError(ValueError):
    """External evidence is incomplete or fails its pinned hash check."""


def git_blob_id(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()


def _url(repo: str, commit: str, path: str) -> str:
    return f"https://raw.githubusercontent.com/{repo}/{commit}/{path}"


def fetch_pinned(repo: str, commit: str, paths: dict[str, str],
                 *, source_dir: Path | None = None) -> dict[str, bytes]:
    """Only two fixed upstream repositories and exact allowlisted paths."""
    if (repo, commit, paths) not in (
        (DOC_REPO, DOC_COMMIT, DOC_FILES), (CODE_REPO, CODE_COMMIT, CODE_FILES)
    ):
        raise SourceError("Unapproved source selection")
    out = {}
    for path, expected in paths.items():
        if source_dir is None:
            request = urllib.request.Request(_url(repo, commit, path), headers={
                "User-Agent": "srs-guardian-m23-static-evidence",
            })
            with urllib.request.urlopen(request, timeout=25) as response:
                raw = response.read(MAX_BYTES + 1)
        else:
            raw = (source_dir / path).read_bytes()
        if len(raw) > MAX_BYTES or git_blob_id(raw) != expected:
            raise SourceError(f"Pinned Git blob mismatch: {repo}/{path}")
        out[path] = raw
    return out


def observed_subset(csv_text: str, paths: set[str]) -> list[tuple[int, str]]:
    """Extract only explicitly recorded author/paper trace links, not negatives."""
    reader = csv.DictReader(StringIO(csv_text))
    if reader.fieldnames != ["SentenceId", "CodeElementId"]:
        raise SourceError("Unexpected SAD-to-code CSV header")
    found = set()
    for row in reader:
        try:
            rid = int(row["SentenceId"])
        except (ValueError, TypeError) as exc:
            raise SourceError("Malformed sentence ID") from exc
        path = row["CodeElementId"]
        if rid in REQ_IDS and path in paths:
            found.add((rid, path))
    result = sorted(found)
    expected = {1: 2, 27: 2, 28: 2}
    if {rid: sum(k == rid for k, _ in result) for rid in REQ_IDS} != expected:
        raise SourceError("Selected paper link counts differ from pinned review plan")
    return result


def _description(raw: bytes) -> str:
    """Display limited source declarations; never import or execute Java."""
    src = raw.decode("utf-8")
    declarations = []
    for line in src.splitlines():
        line = line.strip()
        if re.search(r"\b(class|interface|enum)\s+[A-Za-z_]\w*", line) or (
            re.search(r"\b(public|protected)\b", line)
            and "(" in line and ")" in line and not line.startswith("*")
        ):
            declarations.append(re.sub(r"\s+", " ", line)[:180])
        if len(declarations) >= 3:
            break
    return " | ".join(declarations)[:450] or "Read pinned Java source file for context"


def _snapshot_digest(files: dict[str, bytes]) -> str:
    h = hashlib.sha256()
    for path in sorted(p for p in files if p.endswith(".java")):
        raw = files[path]
        name = path.encode("utf-8")
        h.update(len(name).to_bytes(4, "big"))
        h.update(name)
        h.update(len(raw).to_bytes(8, "big"))
        h.update(raw)
    return h.hexdigest()


def build_evidence(docs: dict[str, bytes], code: dict[str, bytes]) -> dict:
    if set(docs) != set(DOC_FILES) or set(code) != set(CODE_FILES):
        raise SourceError("Incomplete or additional external source files")
    for repo, files, expected in ((DOC_REPO, docs, DOC_FILES), (CODE_REPO, code, CODE_FILES)):
        for path, raw in files.items():
            if git_blob_id(raw) != expected[path]:
                raise SourceError(f"Unverified file: {repo}/{path}")
    if not docs["LICENSE.md"].startswith(b"MIT License"):
        raise SourceError("Replication-package MIT license missing")
    if b"Apache License" not in code["LICENSE"][:150]:
        raise SourceError("TeaStore Apache-2.0 license missing")
    selected_paths = sorted(path for path in code if path.endswith(".java"))
    selected = observed_subset(docs[GOLD_PATH].decode("utf-8"), set(selected_paths))
    symbols = [{
        "symbol_id": f"JAVA_{n:03d}", "source_path": path,
        "qualified_name": Path(path).stem,
        "description": _description(code[path]),
    } for n, path in enumerate(selected_paths, 1)]
    sid = {s["source_path"]: s["symbol_id"] for s in symbols}
    requirements = [{
        "requirement_id": f"SAD_{rid:03d}",
        "requirement_text": docs[f"data/ftlr-texts/teastore/{rid}.txt"].decode("utf-8").strip(),
    } for rid in REQ_IDS]
    universe = {
        "schema_version": "m20-candidate-universe-1",
        "project_id": PROJECT_ID,
        "source_commit": CODE_COMMIT,
        "code_snapshot_sha256": _snapshot_digest(code),
        "requirements": requirements, "symbols": symbols,
        "observed_links": [
            {"requirement_id": f"SAD_{rid:03d}", "symbol_id": sid[path]}
            for rid, path in selected
        ],
    }
    queue = build_queue(universe, seed="m23-teastore-sad-subset-v1",
                        hard_per_requirement=2, random_per_requirement=2)
    if len(queue["queue"]) != 15 or len(selected) != 6:
        raise SourceError("Unexpected candidate queue dimensions")
    evidence = {
        "schema_version": "m23-teastore-external-evidence-1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "project": "TeaStore",
        "project_kind": "externally authored research benchmark / test application",
        "artifact_kind": "software architecture documentation (SAD) to Java file",
        "documentation_repo": DOC_REPO, "documentation_commit": DOC_COMMIT,
        "code_repo": CODE_REPO, "code_commit": CODE_COMMIT,
        "documentation_license": "MIT", "code_license": "Apache-2.0",
        "licenses_verified_by_pinned_git_blob": True,
        "source_files": [{
            "repository": repo, "commit": commit, "path": path,
            "git_blob_sha1": expected[path],
            "sha256": hashlib.sha256(files[path]).hexdigest(),
            "source_url": f"https://github.com/{repo}/blob/{commit}/{path}",
        } for repo, commit, files, expected in (
            (DOC_REPO, DOC_COMMIT, docs, DOC_FILES),
            (CODE_REPO, CODE_COMMIT, code, CODE_FILES),
        ) for path in sorted(files)],
        "source_subset_sha256": universe["code_snapshot_sha256"],
        "snapshot_scope": "Five selected Java files, not the complete TeaStore application",
        "selected_sad_sentences": len(requirements),
        "selected_java_files": len(symbols),
        "paper_declared_links_unverified": len(selected),
        "possible_pairs_in_subset": len(requirements) * len(symbols),
        "blinded_review_pairs": len(queue["queue"]),
        "independently_reviewed_link_pairs": 0,
        "independently_reviewed_behavioral_cases": 0,
        "conformance_accuracy": None,
        "violation_precision": None, "violation_recall": None,
        "conformance_coverage": None, "research_95_eligible": False,
        "review_required": [
            "Two reviewers independently inspect each SAD sentence and exact pinned Java file, without seeing paper links or selection strata.",
            "Reviewers mark linked, not linked, or uncertain and cite concrete source lines; a third reviewer adjudicates disagreements.",
            "Document independent adjudication and keep held-out evaluation separate from method selection.",
            "Collect actual requirement-level executable conformance/violation evidence; SAD-to-code links do not establish behavioral conformance.",
            "Expand to complete independently licensed project snapshots and unseen projects; the five-file purposive subset cannot support population accuracy.",
        ],
        "warnings": [
            "Architecture statements are not executable software requirements or behavioral oracles.",
            "Paper-provided links are observed candidates only; all 15 queue cases remain unlabeled.",
            "The original paper's benchmark is NOT a new independent adjudication by SRS Guardian.",
            "Neither missing links nor source file naming is evidence of negative conformance.",
        ],
    }
    return {"universe": universe, "queue": queue, "evidence": evidence,
            "licenses": {"replication_MIT.txt": docs["LICENSE.md"],
                         "TeaStore_Apache-2.0.txt": code["LICENSE"]}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    result = build_evidence(fetch_pinned(DOC_REPO, DOC_COMMIT, DOC_FILES),
                            fetch_pinned(CODE_REPO, CODE_COMMIT, CODE_FILES))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "candidate_universe.json").write_text(
        json.dumps(result["universe"], indent=2) + "\n", encoding="utf-8")
    (args.out_dir / "external_evidence.json").write_text(
        json.dumps(result["evidence"], indent=2) + "\n", encoding="utf-8")
    for filename, raw in result["licenses"].items():
        (args.out_dir / filename).write_bytes(raw)
    write_outputs(result["queue"], args.out_dir / "annotation")
    print(json.dumps({
        "selected_sad_sentences": result["evidence"]["selected_sad_sentences"],
        "selected_java_files": result["evidence"]["selected_java_files"],
        "paper_declared_links_unverified": result["evidence"]["paper_declared_links_unverified"],
        "blinded_review_pairs": result["evidence"]["blinded_review_pairs"],
        "research_95_eligible": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
