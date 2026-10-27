"""M30: source-grounded, conditional pagination counterexample from pinned M28 Java.

Runs ONLY this Python abstraction. Never executes, imports or builds upstream
Java. Inferred counts are conditional model outputs, NOT runtime observations,
independent annotations, gold labels or conformance accuracy.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.evaluation import m28_historical_pagination_regression as m28

MODEL = "m30-pinned-source-pagination-abstraction-1"
ASSUMPTIONS = (
    "Two contract definitions are visited in order, each matching exactly 50 distinct assets.",
    "All selected assets have valid policies and each produces exactly one offer.",
    "Asset queries honor the requested per-definition offset and limit.",
    "No filters, authorization, duplicates, concurrency or service errors change the result.",
    "The model abstracts only queryContractOffers; it is not a Java execution or complete deployment.",
)
# Literal Java expressions that bind each abstraction to the pinned source.
SOURCE_MARKERS = {
    "before": (
        "var limit = range.getTo() - range.getFrom();",
        ".takeWhile(d -> numSeenAssets.get() < range.getTo())",
        "querySpecBuilder.limit((int) numAssets);",
        "if (numAssets + numSeenAssets.get() > limit)",
        "querySpecBuilder.limit(limit);",
        "skip.addAndGet(Long.valueOf(-numAssets).intValue());",
    ),
    "after": (
        ".takeWhile(d -> numFetchedAssets.get() < limit)",
        "var dynamicOffset = max(0L, offset - numSeenAssets.get());",
        "var dynamicLimit = min(limit - numFetchedAssets.get(), max(0, numAssets - dynamicOffset));",
        "querySpecBuilder.offset(Long.valueOf(dynamicOffset).intValue());",
        "querySpecBuilder.limit(Long.valueOf(dynamicLimit).intValue());",
        "numFetchedAssets.addAndGet(dynamicLimit);",
    ),
}


def validate_inputs(asset_counts: tuple[int, ...], offset: int, limit: int) -> None:
    if not asset_counts or any(type(n) is not int or n < 0 for n in asset_counts):
        raise ValueError("Asset counts must be a nonempty tuple of nonnegative integers")
    if type(offset) is not int or type(limit) is not int or offset < 0 or limit <= 0:
        raise ValueError("Offset must be nonnegative and limit positive")


def simulate_before(asset_counts: tuple[int, ...], offset: int, limit: int) -> dict:
    """Abstract pre-fix queryContractOffers under ASSUMPTIONS."""
    validate_inputs(asset_counts, offset, limit)
    seen, skip, returned, steps = 0, offset, 0, []
    for index, count in enumerate(asset_counts):
        if seen >= offset + limit:  # Java takeWhile uses range.getTo()
            break
        query_offset = skip if skip > 0 else 0
        query_limit = limit if count + seen > limit else count
        emitted = 0 if skip >= count else min(max(0, count - query_offset), query_limit)
        steps.append({
            "definition": index, "assets": count, "seen_before": seen,
            "query_offset": query_offset, "query_limit": query_limit,
            "model_emitted": emitted,
        })
        returned += emitted
        seen += count
        skip -= count
    return {"model_returned_offers": returned, "steps": steps}


def simulate_after(asset_counts: tuple[int, ...], offset: int, limit: int) -> dict:
    """Abstract post-fix queryContractOffers under ASSUMPTIONS."""
    validate_inputs(asset_counts, offset, limit)
    seen, fetched, returned, steps = 0, 0, 0, []
    for index, count in enumerate(asset_counts):
        if fetched >= limit:  # Java takeWhile uses numFetchedAssets
            break
        dynamic_offset = max(0, offset - seen)
        dynamic_limit = min(limit - fetched, max(0, count - dynamic_offset))
        emitted = 0 if dynamic_offset >= count else min(dynamic_limit, count - dynamic_offset)
        steps.append({
            "definition": index, "assets": count, "seen_before": seen,
            "fetched_before": fetched, "query_offset": dynamic_offset,
            "query_limit": dynamic_limit, "model_emitted": emitted,
        })
        returned += emitted
        fetched += dynamic_limit
        seen += count
    return {"model_returned_offers": returned, "steps": steps}


def source_binding(files: dict[str, dict[str, bytes]]) -> dict:
    """Verify M28 pins, then bind the model to exact Java source expressions."""
    evidence = m28.build_evidence(files)  # validates Git blob hashes, license and source changes
    anchors = {}
    for revision, markers in SOURCE_MARKERS.items():
        source = files[revision][m28.SOURCE].decode("utf-8")
        lines = source.splitlines()
        anchors[revision] = []
        for marker in markers:
            matches = [i for i, line in enumerate(lines, 1) if marker in line]
            if len(matches) != 1:
                raise m28.EvidenceError("M30 source expression missing or ambiguous: " + marker)
            anchors[revision].append({
                "expression": marker,
                "url": m28.source_url(revision, m28.SOURCE, matches[0]),
            })
    return {"evidence": evidence, "anchors": anchors}


def build_witness(files: dict[str, dict[str, bytes]]) -> dict:
    binding = source_binding(files)
    cases = []
    for case_id, offset, limit, expected, alleged_before in m28.SCENARIOS:
        pre = simulate_before((50, 50), offset, limit)
        post = simulate_after((50, 50), offset, limit)
        cases.append({
            "case_id": case_id, "offset": offset, "limit": limit,
            "asset_counts_assumed": [50, 50],
            "upstream_expected_offers_unadjudicated": expected,
            "upstream_reported_before_unverified": alleged_before,
            "before": pre, "after": post,
            "model_matches_reporter_claim": pre["model_returned_offers"] == alleged_before,
            "model_matches_postfix_expectation": post["model_returned_offers"] == expected,
            "runtime_observed_before": None, "runtime_observed_after": None,
            "independent_conformance_label": None,
            "independent_violation_label": None,
        })
    return {
        "schema": MODEL,
        "project_id": m28.PROJECT,
        "upstream_issue": m28.ISSUE, "upstream_fix": m28.PATCH,
        "source_commits": m28.COMMITS,
        "source_git_blob_sha1": {r: m28.FILES[r][m28.SOURCE] for r in ("before", "after")},
        "verified_source_expression_anchors": binding["anchors"],
        "assumptions": list(ASSUMPTIONS),
        "cases": cases,
        "external_code_executed": False,
        "independent_adjudications": 0,
        "held_out_evaluation": False,
        "conformance_accuracy": None,
        "violation_precision": None,
        "violation_recall": None,
        "conformance_coverage": None,
        "interpretation": (
            "Conditional static algorithm witness only. Agreement with an upstream report "
            "does not independently verify runtime behavior or establish a gold label."
        ),
        "_m28_evidence": binding["evidence"],
    }


def write_witness(witness: dict, out_dir: Path) -> None:
    # Reuse M20's blinded review packets; never reveal model counts to reviewers.
    m28.write_evidence(witness["_m28_evidence"], out_dir)
    internal = out_dir / "internal"
    clean = {key: value for key, value in witness.items() if key != "_m28_evidence"}
    (internal / "m30_conditional_static_witness.json").write_text(
        json.dumps(clean, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (internal / "M30_REVIEW_HANDOFF.md").write_text(
        "# M30 independent verification handoff\n\n"
        "The source-grounded model predicts offer counts only under five explicit "
        "assumptions. It is not runtime evidence and must remain internal until "
        "independent annotation is complete. Two reviewers should separately "
        "check the pinned Java expressions and the two 50+50 asset scenarios at "
        "both revisions, document source-line citations, independently reproduce "
        "observed counts in an approved isolated environment (or provide trustworthy "
        "version-matched archived logs), and record configuration and asset-query "
        "semantics. A third adjudicator resolves disagreements. Never treat the "
        "issue's reported numbers or this model's predictions as gold. "
        "Leave unknown outcomes null. Later evaluate on unseen projects.\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    witness = build_witness(m28.fetch_pinned())
    write_witness(witness, args.out_dir)
    print(json.dumps({
        "model": MODEL,
        "cases": [{
            "case_id": c["case_id"],
            "before_model": c["before"]["model_returned_offers"],
            "after_model": c["after"]["model_returned_offers"],
        } for c in witness["cases"]],
        "independent_adjudications": 0,
        "conformance_accuracy": None,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
