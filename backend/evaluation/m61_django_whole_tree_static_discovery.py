"""M61: whole-tree static source discovery and a bounded property witness (NOT GOLD).

Unlike M60, this step does not supply the historical fix file path to the
verifier. It scans *all* Git-verified production Python files in each pinned
Django revision for a uniquely named URLValidator class, then applies M60's
non-executing regex-character-class rule. The URLValidator symbol and rule
were learned from an already inspected issue: this is a DEVELOPMENT
demonstration, not blinded general-purpose trace retrieval or behavioral gold.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re

from backend.evaluation import m29_pip_historical_regression as m29
from backend.evaluation import m58_django_frozen_file_transfer as m58
from backend.evaluation import m60_django_static_userinfo_verification as m60

SCHEMA = "m61-whole-tree-static-symbol-discovery-development-NOT-GOLD-1"
SYMBOL = "URLValidator"
CLASS_LINE = re.compile(r"(?m)^\s*class\s+URLValidator\b")
RESULTS = ("static_rule_violated", "static_rule_satisfied")


def discover(snapshot: dict, revision: str) -> dict:
    """Read verified source bytes only; never import, evaluate, or execute them."""
    if revision not in m60.REVISIONS:
        raise ValueError("Unknown revision")
    commit = m60.REVISIONS[revision]["commit"]
    if snapshot.get("commit") != commit:
        raise ValueError("Pinned revision mismatch")
    expected, files = snapshot.get("expected"), snapshot.get("files")
    if (not isinstance(expected, dict) or not isinstance(files, dict)
            or not expected or set(expected) != set(files)):
        raise ValueError("Incomplete verified source tree")
    candidates = []
    for path in sorted(files):
        raw = files[path]
        if (not m58.production_source(path) or not isinstance(raw, bytes)
                or m29.blob_sha(raw) != expected[path]):
            raise ValueError("Unverified production file: " + path)
        # This is a cheap symbol prefilter, NOT an execution or a source path hint.
        if b"URLValidator" not in raw:
            continue
        source = raw.decode("utf-8-sig")
        if not CLASS_LINE.search(source):
            continue
        try:
            tree = ast.parse(source, filename=path)
        except SyntaxError:
            return _abstain(snapshot, revision, len(files), "candidate_source_syntax_error")
        if any(isinstance(node, ast.ClassDef) and node.name == SYMBOL
               for node in tree.body):
            candidates.append((path, raw, source))
    if len(candidates) != 1:
        return _abstain(snapshot, revision, len(files),
                        "no_unique_top_level_URLValidator_class",
                        candidate_paths=[path for path, _, _ in candidates])
    path, raw, source = candidates[0]
    try:
        fragment, line = m60.extract_userinfo(source)
        property_result = m60.check_fragment(fragment)
    except ValueError:
        return _abstain(snapshot, revision, len(files),
                        "unsupported_URLValidator_regex_source",
                        candidate_paths=[path])
    return {
        **_base(snapshot, revision, len(files)),
        "source_path": path,
        "source_line": line,
        "source_git_blob": expected[path],
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_url": f"https://github.com/{m60.REPO}/blob/{commit}/{path}#L{line}",
        "candidate_paths": [path],
        "candidate_count": 1,
        "extracted_literal_userinfo_regex": fragment,
        **property_result,
    }


def _base(snapshot: dict, revision: str, file_count: int) -> dict:
    return {
        "revision": revision,
        "source_commit": snapshot["commit"],
        "source_tree_sha": snapshot.get("tree_sha"),
        "verified_production_files_scanned": file_count,
        "license": "BSD-3-Clause (pinned LICENSE verified by M58 snapshot reader)",
        "license_git_blob": snapshot.get("license_git_blob"),
        "license_sha256": snapshot.get("license_sha256"),
        "symbol_anchor": SYMBOL,
        "symbol_anchor_provenance": "Previously inspected historical issue; NOT blind",
    }


def _abstain(snapshot: dict, revision: str, file_count: int, reason: str,
             candidate_paths: list[str] | None = None) -> dict:
    return {
        **_base(snapshot, revision, file_count),
        "candidate_paths": candidate_paths or [],
        "candidate_count": len(candidate_paths or []),
        "static_result": "abstain",
        "reason": reason,
    }


def build(fetch_snapshot=m58.fetch_snapshot) -> dict:
    records = []
    for revision, info in m60.REVISIONS.items():
        # M58 verifies the immutable Git commit/tree, every indexed production
        # blob, and the pinned BSD-3-Clause license before returning source bytes.
        snapshot = fetch_snapshot(info["commit"])
        records.append(discover(snapshot, revision))
    return {
        "schema": SCHEMA,
        "project": m60.REPO,
        "requirement_source": "https://github.com/django/django/pull/10097",
        "requirement_property": (
            "Unescaped colon, at-sign and slash must not be allowed in the "
            "username/password character classes of URLValidator."
        ),
        "discovery": "whole verified production tree; unique top-level URLValidator AST class",
        "file_path_oracle_used": False,
        "symbol_and_rule_oracle_informed": True,
        "case_selection": "previously inspected Django development case; NOT held-out",
        "independent_link_labels": 0,
        "independent_behavioral_observations": 0,
        "independent_adjudications": 0,
        "held_out_projects_scored": 0,
        "conformance_accuracy": None,
        "violation_precision": None,
        "violation_recall": None,
        "coverage": None,
        "external_project_code_executed": False,
        "limitations": [
            "Known URLValidator symbol and rule were obtained from an inspected historical issue.",
            "Automatic source discovery is not a general requirement-to-code retrieval algorithm.",
            "Only a narrow static regex character-class property is checked; no Django runtime behavior is observed.",
            "Production-file scan count is not independently adjudicated requirement coverage.",
            "M20 independent link and regression-test relevance reviews are not completed.",
            "No approved behavioral observations, separate adjudication, or held-out accuracy exist.",
        ],
        "revisions": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    result = build()
    if args.out_dir.exists():
        raise ValueError("Refusing to overwrite evidence")
    args.out_dir.mkdir(parents=True)
    (args.out_dir / "INTERNAL_WHOLE_TREE_STATIC_NOT_GOLD.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.out_dir / "INDEPENDENT_REVIEW_HANDOFF.md").write_text(
        "# M61 development witness — NOT GOLD\n\n"
        "Do not expose this oracle-informed internal witness to M20 reviewers "
        "before their stage-1 link decisions are frozen. Use existing M59 "
        "reviewer packets for independent link and test relevance assessments. "
        "Each of two reviewers must cite requirement text, candidate source "
        "line(s), link relevance, uncertainty, and regression-test relevance "
        "without historical patch hints. Separately approved isolated "
        "before/after behavioral observations must record pinned source/deps, "
        "exact inputs, outputs, hashes, and run provenance. A distinct third "
        "reviewer adjudicates disagreements. No such labels or observations "
        "are present in this artifact. The static property is NOT runtime "
        "conformance; no behavioral metrics or held-out coverage exist.\n",
        encoding="utf-8")
    print(json.dumps({
        "revisions": len(result["revisions"]),
        "verified_files_scanned": [x["verified_production_files_scanned"]
                                  for x in result["revisions"]],
        "static_results": {x["revision"]: x["static_result"]
                           for x in result["revisions"]},
        "independent_labels": 0,
        "behavioral_accuracy": None,
        "external_project_code_executed": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
