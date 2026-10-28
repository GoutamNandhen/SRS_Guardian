"""M41: isolate code/test competition and inflection mismatch on pinned pip.

Development-only ablation: the implementation-file scope is known in advance,
so this is an ORACLE FILE-SCOPED diagnostic, NOT repository-wide retrieval.
No known fix symbol, label, test assertion, or revision outcome enters ranking.
Only verified static text is parsed; no external pip code is executed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.app.services.code_traceability import _index_python, rank_candidates, tokenize
from backend.evaluation import m29_pip_historical_regression as m29
from backend.evaluation import m40_pip_e2e_feasibility as m40

SCHEMA = "m41-pip-code-only-retrieval-ablation-1"
METHODS = ("m40_mixed_source_and_tests", "source_only_original_tokens",
           "source_only_inflection_normalized")


def normalize_token(token: str) -> str:
    """General lexical inflection rule, without case-specific synonyms."""
    if token.endswith("ing") and len(token) > 6:
        return token[:-3]
    if token.endswith("ed") and len(token) > 5:
        return token[:-2]
    return token


def normalized_query(text: str) -> str:
    return " ".join(normalize_token(t) for t in tokenize(text))


def ranked_implementation_symbols(source: str, requirement: str, *, normalize: bool) -> list[dict]:
    """Rank only implementation symbols, not test definitions.

    The source file is intentionally preselected in this development diagnostic.
    This cannot establish whole-repository retrieval effectiveness.
    """
    symbols, warning = _index_python(m29.SOURCE, source)
    if warning:
        raise m29.EvidenceError(warning)
    if normalize:
        for symbol in symbols:
            symbol["tokens"] = [normalize_token(t) for t in symbol["tokens"]]
        requirement = normalized_query(requirement)
    return rank_candidates(requirement, {"symbols": symbols}, top_k=10)


def fix_locus_rank(ranked: list[dict]) -> int | None:
    """Post-ranking diagnostic only. Never used as a feature or query."""
    return next((i for i, s in enumerate(ranked, 1)
                 if s["path"] == m29.SOURCE
                 and s["qualified_name"] == m40.TARGET), None)


def build(files: dict[str, dict[str, bytes]]) -> dict:
    # This call verifies the six pinned Git blobs and MIT license and runs
    # the unchanged M40 baseline. Do not use any fix locus to rank candidates.
    baseline = m40.build(files)
    rows = []
    for revision in ("before", "after"):
        source = files[revision][m29.SOURCE].decode("utf-8")
        symbols, warning = _index_python(m29.SOURCE, source)
        if warning:
            raise m29.EvidenceError(warning)
        for scenario in m29.SCENARIOS:
            query = scenario["requirement_text"]
            original = rank_candidates(query, {"symbols": symbols}, top_k=10)
            normalized = ranked_implementation_symbols(source, query, normalize=True)
            old = next(row for row in baseline["cases"]
                       if row["revision"] == revision and row["case_id"] == scenario["case_id"])
            ranks = {
                METHODS[0]: old["known_fix_locus_rank_not_gold"],
                METHODS[1]: fix_locus_rank(original),
                METHODS[2]: fix_locus_rank(normalized),
            }
            rows.append({
                "project": m29.REPO,
                "case_id": scenario["case_id"],
                "revision": revision,
                "requirement_origin": scenario["origin"],
                "ranks_of_known_fix_locus_NOT_GOLD": ranks,
                "source_only_candidates_indexed": len(symbols),
                "source_only_top_candidates": {
                    METHODS[1]: [{"name": s["qualified_name"], "line": s["line_start"],
                                  "source_url": m29.source_url(revision, s["path"], s["line_start"])}
                                 for s in original[:5]],
                    METHODS[2]: [{"name": s["qualified_name"], "line": s["line_start"],
                                  "source_url": m29.source_url(revision, s["path"], s["line_start"])}
                                 for s in normalized[:5]],
                },
                "behavioral_decision": "insufficient_evidence",
                "independent_gold": None,
            })
    counts = {
        method: {
            "known_fix_locus_top1_exploratory": sum(row["ranks_of_known_fix_locus_NOT_GOLD"][method] == 1
                                                   for row in rows),
            "known_fix_locus_top5_exploratory": sum(
                (rank is not None and rank <= 5)
                for row in rows
                for name, rank in row["ranks_of_known_fix_locus_NOT_GOLD"].items()
                if name == method
            ),
        } for method in METHODS
    }
    if counts[METHODS[0]]["known_fix_locus_top5_exploratory"] != baseline["known_fix_locus_top5_count_exploratory"]:
        raise m29.EvidenceError("M40 baseline changed unexpectedly")
    return {
        "schema": SCHEMA,
        "project": m29.REPO,
        "source_license": baseline["source_license"],
        "source_commits": m29.COMMITS,
        "verified_static_file_revision_objects": baseline["verified_static_file_revision_objects"],
        "requirement_revision_pairs": len(rows),
        "ablation": counts,
        "cases": rows,
        "independent_adjudications": 0,
        "behavioral_decisions": 0,
        "behavioral_abstentions": len(rows),
        "held_out_project_evaluation": False,
        "external_project_code_executed": False,
        "conformance_accuracy": None,
        "violation_precision": None,
        "violation_recall": None,
        "conformance_coverage": None,
        "limitations": [
            "All three scenarios and both revisions are previously inspected development material.",
            "The source-only candidate pool is the preselected factory.py file containing the fix: ORACLE FILE SCOPE.",
            "Removing tests reduces candidate competition but does not solve repository-wide file retrieval.",
            "The historical fix locus is a post-ranking diagnostic anchor, not independently adjudicated gold.",
            "Six observations share three scenarios and one project; do not treat them as independent samples.",
            "Source structure and retrieval cannot establish behavioral conformance.",
            "No external project code executed; no independent reviewers or runtime observations.",
        ],
    }


def write(report: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "m41_retrieval_ablation.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# M41 pip retrieval bottleneck diagnosis (NOT GOLD)",
        "",
        "This is a **preselected-file development ablation**, not independent traceability or conformance.",
        "",
        "| Method | Known fix locus top-1 | Known fix locus top-5 |",
        "|---|---:|---:|",
    ]
    for name, metrics in report["ablation"].items():
        lines.append(
            f"| {name} | {metrics['known_fix_locus_top1_exploratory']}/6 | "
            f"{metrics['known_fix_locus_top5_exploratory']}/6 |")
    lines.extend([
        "",
        "M40 mixes resolver implementation and upstream test functions. The code-only "
        "variant excludes test functions, while the normalized variant additionally "
        "removes general '-ing'/'-ed' inflections. No hand-authored bug vocabulary "
        "or known fix symbol is inserted into ranking.",
        "",
        "**CRITICAL: the implementation file is selected with prior knowledge.** "
        "Improved ranks, if any, do not demonstrate whole-repository retrieval, "
        "generalization, behavioral correctness, or independently measured accuracy.",
        "",
        "All six behavioral cases abstain. Independently adjudicated labels: **0**. "
        "Conformance accuracy, violation precision/recall and coverage: **not measured**.",
        "",
        "Next blocker: broaden to a prospectively chosen repository-wide candidate pool, "
        "then obtain independent M20 reviewer/adjudicator judgments and approved "
        "version-compatible behavioral evidence before held-out conformance scoring.",
    ])
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    report = build(m29.fetch_pinned())
    write(report, args.out_dir)
    print(json.dumps({
        "verified_objects": report["verified_static_file_revision_objects"],
        "ablation": report["ablation"],
        "behavioral_abstentions": report["behavioral_abstentions"],
        "independent_adjudications": 0,
        "conformance_accuracy": None,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
