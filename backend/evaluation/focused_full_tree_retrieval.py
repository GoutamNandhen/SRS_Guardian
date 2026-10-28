"""One predeclared retrieval experiment on the complete hash-pinned pip source tree.

Unlike an evaluator/UI expansion, this compares two generic candidate rankings:
character n-gram TF-IDF and fixed reciprocal-rank fusion. Baselines remain
unchanged. No historical fix path, module, symbol or verdict is used as a
retrieval feature. The known historical fix locus is inspected AFTER ranking.
This is a development-case diagnostic, not independently adjudicated gold.
No upstream Python source is imported or executed.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
from typing import Sequence

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from backend.evaluation import m29_pip_historical_regression as m29
from backend.evaluation import m40_pip_e2e_feasibility as m40
from backend.evaluation import m42_pip_first_party_tree_retrieval as m42

SCHEMA = "focused-full-tree-retrieval-ablation-v1"
METHODS = ("m2_original", "m42_inflection", "char_tfidf", "rrf_normalized_char")
RRF_K = 60
TOP_K = 10
MAX_CHAR_FEATURES = 50000


def normalize_code_text(raw: str) -> str:
    """Generic camel/snake/path segmentation; no task-specific synonyms."""
    raw = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", raw)
    return re.sub(r"[^a-zA-Z0-9]+", " ", raw).lower()


def symbol_text(symbol: dict) -> str:
    """Use only indexed inert source/path metadata, never tests or fix labels."""
    path = normalize_code_text(symbol["path"])
    name = normalize_code_text(symbol["qualified_name"])
    signature = normalize_code_text(symbol["signature"])
    doc = normalize_code_text(symbol.get("docstring") or "")
    source = normalize_code_text(symbol.get("source_excerpt") or "")
    # Predeclared modest weighting for symbol identity; do not retune on pip.
    return " ".join((path, name, name, signature, doc, source[:1200]))


def char_rank_all(symbols: Sequence[dict], queries: Sequence[str]) -> list[list[dict]]:
    """CPU-only source-aware character TF-IDF, descending score, stable ties."""
    if not symbols or not queries:
        return [[] for _ in queries]
    corpus = [symbol_text(s) for s in symbols]
    vectorizer = TfidfVectorizer(
        analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True,
        min_df=1, max_features=MAX_CHAR_FEATURES, dtype=np.float32,
        lowercase=True, norm="l2"
    )
    matrix = vectorizer.fit_transform(corpus)
    qmat = vectorizer.transform([normalize_code_text(q) for q in queries])
    ranked = []
    for q in qmat:
        scores = (matrix @ q.T).toarray().ravel()
        order = sorted(range(len(symbols)),
                       key=lambda i: (-float(scores[i]), symbols[i]["path"],
                                      symbols[i]["line_start"], symbols[i]["qualified_name"]))
        # Do not emit zero-similarity candidates as pseudo-links.
        ranked.append([{
            "path": symbols[i]["path"], "qualified_name": symbols[i]["qualified_name"],
            "line_start": symbols[i]["line_start"], "score": float(scores[i]),
        } for i in order[:TOP_K] if scores[i] > 0])
    return ranked


def _id(s: dict) -> tuple[str, str, int]:
    return (s["path"], s["qualified_name"], s["line_start"])


def reciprocal_rank_fusion(a: Sequence[dict], b: Sequence[dict]) -> list[dict]:
    """RRF fixed k=60, two input lists limited to ten, no training/labels."""
    combined: dict[tuple[str, str, int], dict] = {}
    for ranked in (a, b):
        for rank, item in enumerate(ranked[:TOP_K], 1):
            key = _id(item)
            if key not in combined:
                combined[key] = {**item, "score": 0.0}
            combined[key]["score"] += 1 / (RRF_K + rank)
    return sorted(combined.values(), key=lambda v: (-v["score"], *_id(v)))[:TOP_K]


def _loc_rank(ranked: Sequence[dict]) -> int | None:
    """Post-ranking exploratory check, never accessed by any ranker."""
    return next((i for i, s in enumerate(ranked, 1)
                 if s["path"] == m29.SOURCE and s["qualified_name"] == m40.TARGET), None)


def rank_revision(symbols: list[dict], scenarios: Sequence[dict]) -> list[dict]:
    queries = [s["requirement_text"] for s in scenarios]
    char_ranked = char_rank_all(symbols, queries)
    rows = []
    for scenario, candidate_char in zip(scenarios, char_ranked):
        q = scenario["requirement_text"]
        original = m42.rank_case(symbols, q, normalized=False)
        normalized = m42.rank_case(symbols, q, normalized=True)
        fused = reciprocal_rank_fusion(normalized, candidate_char)
        ranked = dict(zip(METHODS, (original, normalized, candidate_char, fused)))
        rows.append({
            "case_id": scenario["case_id"],
            "requirement_origin": scenario["origin"],
            "known_fix_locus_rank_NOT_GOLD": {key: _loc_rank(value)
                                              for key, value in ranked.items()},
            "top_10": {
                key: [{"path": c["path"], "qualified_name": c["qualified_name"],
                       "line_start": c["line_start"], "score": round(float(c["score"]), 6)}
                      for c in value]
                for key, value in ranked.items()
            },
            "behavioral_decision": "insufficient_evidence",
            "independent_gold": None,
        })
    return rows


def evaluate(snapshots: dict, pinned_evidence: dict) -> dict:
    if pinned_evidence["internal"]["static_file_revision_objects_verified"] != 6:
        raise m29.EvidenceError("Incomplete pinning evidence")
    if not pinned_evidence["reviewer_index"]["license"].startswith("MIT"):
        raise m29.EvidenceError("Pinned source license missing")
    if set(snapshots) != {"before", "after"}:
        raise m29.EvidenceError("Both pinned versions required")
    rows, revision_sizes = [], {}
    for revision in ("before", "after"):
        snapshot = snapshots[revision]
        if snapshot["commit"] != m29.COMMITS[revision]:
            raise m29.EvidenceError("Unexpected source commit")
        symbols = m42.index_snapshot(snapshot)   # verifies every source Git blob
        revision_sizes[revision] = {
            "source_commit": snapshot["commit"],
            "source_tree_sha": snapshot["tree_sha"],
            "python_files": len(snapshot["files"]), "symbols": len(symbols)
        }
        for row in rank_revision(symbols, m29.SCENARIOS):
            rows.append({"revision": revision, **row})
    metrics = {
        method: {
            "known_fix_top1_exploratory": sum(row["known_fix_locus_rank_NOT_GOLD"][method] == 1 for row in rows),
            "known_fix_top5_exploratory": sum(
                row["known_fix_locus_rank_NOT_GOLD"][method] is not None and
                row["known_fix_locus_rank_NOT_GOLD"][method] <= 5 for row in rows),
            "known_fix_top10_exploratory": sum(
                row["known_fix_locus_rank_NOT_GOLD"][method] is not None for row in rows),
        } for method in METHODS
    }
    return {
        "schema": SCHEMA, "project": m29.REPO,
        "source_scope": "all pinned first-party src/pip/_internal/**/*.py",
        "predeclared_methods": METHODS,
        "fixed_settings": {"char_wb_range": [3, 5], "max_features": MAX_CHAR_FEATURES,
                           "RRF_k": RRF_K, "top_k": TOP_K},
        "revision_sizes": revision_sizes, "cases": rows, "diagnostics_NOT_GOLD": metrics,
        "project_count": 1, "linked_locus_diagnostic_only": True,
        "independent_gold": None, "independent_adjudications": 0,
        "held_out_projects": 0, "upstream_code_executed": False,
        "behavioral_abstentions": len(rows), "behavioral_decisions": 0,
        "conformance_accuracy": None, "violation_precision": None,
        "violation_recall": None, "conformance_coverage": None,
        "warning": "Previously inspected six correlated pip development cases; NOT independent retrieval gold or behavior verification."
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    evidence = m29.build_evidence(m29.fetch_pinned())
    snapshots = {revision: m42.fetch_snapshot(revision) for revision in ("before", "after")}
    report = evaluate(snapshots, evidence)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "focused_retrieval_results.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"diagnostics_NOT_GOLD": report["diagnostics_NOT_GOLD"],
                      "independent_gold": None,
                      "conformance_accuracy": None}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
