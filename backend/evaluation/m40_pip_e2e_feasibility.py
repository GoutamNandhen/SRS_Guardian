"""M40: honest end-to-end feasibility slice on pinned real pip source, without execution.

Runs the existing M2 requirement-to-code lexical retriever on full pinned Python
source/test text, then the existing M34 source-structure witness. The upstream
fix locus is used ONLY for post-hoc retrieval diagnostics, never to rank.
Behavioral verdicts ABSTAIN because source structure cannot prove installs.
No independent gold, held-out evaluation, or 95% claim is produced.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.app.services.code_traceability import _index_python, rank_candidates
from backend.evaluation import m29_pip_historical_regression as m29
from backend.evaluation import m34_pip_source_structure_witness as m34

SCHEMA = "m40-pip-requirement-to-code-feasibility-1"
TARGET = "Factory._make_requirements_from_install_req"
METRICS = ("conformance_accuracy", "violation_precision", "violation_recall",
           "conformance_coverage")


def build(files: dict[str, dict[str, bytes]]) -> dict:
    """Verify exact Git blobs/license first; index inert text, never import pip."""
    evidence = m29.build_evidence(files)
    results = []
    per_revision = {}
    for revision in ("before", "after"):
        symbols = []
        for path in (m29.SOURCE, m29.TEST):
            indexed, warning = _index_python(
                path, files[revision][path].decode("utf-8")
            )
            if warning:
                raise m29.EvidenceError(warning)
            symbols.extend(indexed)
        target_symbols = [
            s for s in symbols
            if s["path"] == m29.SOURCE and s["qualified_name"] == TARGET
        ]
        if len(target_symbols) != 1:
            raise m29.EvidenceError("Pinned pip fix-locus symbol not indexed uniquely")
        # The known upstream fix locus is NOT inserted into the retrieval query.
        # It is compared to the output only after the original M2 ranker runs.
        index = {"symbols": symbols}
        structural = m34.inspect_structure(
            files[revision][m29.SOURCE].decode("utf-8"), revision
        )
        per_revision[revision] = {
            "source_commit": m29.COMMITS[revision],
            "indexed_python_symbols": len(symbols),
            "known_fix_locus": TARGET,
            "known_fix_locus_source": m29.source_url(
                revision, m29.SOURCE, target_symbols[0]["line_start"]
            ),
            "source_structure": structural,
            "structural_property_only": (
                "Explicit extras-free base candidate and separate extras requirement"
            ),
            "structural_property_present": (
                structural["explicit_base_without_extras"]
                and structural["separate_extras_requirement"]
            ),
            "behavioral_conformance": None,
        }
        for scenario in m29.SCENARIOS:
            # No scenario IDs, known links, test assertions or before/after
            # labels are used as ranker features.
            ranked = rank_candidates(
                scenario["requirement_text"], index, top_k=10
            )
            fix_rank = next(
                (i for i, s in enumerate(ranked, 1)
                 if s["path"] == m29.SOURCE
                 and s["qualified_name"] == TARGET), None
            )
            results.append({
                "project": m29.REPO,
                "case_id": scenario["case_id"],
                "revision": revision,
                "requirement_text": scenario["requirement_text"],
                "requirement_origin": scenario["origin"],
                "known_fix_locus_rank_not_gold": fix_rank,
                "known_fix_locus_in_top_1": fix_rank == 1,
                "known_fix_locus_in_top_5": fix_rank is not None and fix_rank <= 5,
                "retrieved_candidates": [{
                    "rank": i, "path": s["path"],
                    "qualified_name": s["qualified_name"],
                    "line_start": s["line_start"],
                    "score": s["score"],
                    "source_url": m29.source_url(
                        revision, s["path"], s["line_start"]
                    ),
                } for i, s in enumerate(ranked, 1)],
                "structural_property_present_at_known_fix_locus": (
                    per_revision[revision]["structural_property_present"]
                    if fix_rank is not None else None
                ),
                "decision": "insufficient_evidence",
                "behavioral_observation": None,
                "independent_gold": None,
                "review_status": "pending",
            })

    return {
        "schema": SCHEMA,
        "project": m29.REPO,
        "source_license": "MIT (pinned LICENSE.txt, Git-blob verified)",
        "source_commits": m29.COMMITS,
        "verified_static_file_revision_objects":
            evidence["internal"]["static_file_revision_objects_verified"],
        "m20_candidate_links_per_reviewer": len(evidence["queue"]["queue"]),
        "project_count": 1,
        "revision_requirement_pairs": len(results),
        "known_fix_locus_top1_count_exploratory": sum(
            x["known_fix_locus_in_top_1"] for x in results
        ),
        "known_fix_locus_top5_count_exploratory": sum(
            x["known_fix_locus_in_top_5"] for x in results
        ),
        "behavioral_decisions": 0,
        "behavioral_abstentions": len(results),
        "independent_adjudications": 0,
        "held_out_project_evaluation": False,
        "external_project_code_executed": False,
        "metrics": {key: None for key in METRICS},
        "per_revision": per_revision,
        "cases": results,
        "limitations": [
            "Purposively selected historical pip regression, already examined in M29/M34: not held out.",
            "Known upstream fix locus is an exploratory diagnostic, not an independent true link.",
            "M2 lexical retrieval indexes pinned Python files; it does not establish semantic traceability.",
            "M34 AST observations prove source syntax only, not successful dependency resolution.",
            "All six revision/requirement behavioral cases abstain; no runtime evidence or gold labels.",
            "M20 requires two independent link/behavior reviewers and a separate adjudicator.",
            "Freeze a method before testing on genuinely unseen, independently labeled projects.",
        ],
    }


def write(report: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "pip_e2e_feasibility.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# M40: real-source requirement-to-code feasibility",
        "",
        "This is an **exploratory development case**, NOT independently validated conformance.",
        "",
        f"Project: {report['project']} (MIT); pinned source objects: "
        f"{report['verified_static_file_revision_objects']}.",
        f"Actual M2 top-1 retrieval of known upstream fix locus: "
        f"{report['known_fix_locus_top1_count_exploratory']}/"
        f"{report['revision_requirement_pairs']} (NOT link accuracy).",
        f"Actual M2 top-5 retrieval of known upstream fix locus: "
        f"{report['known_fix_locus_top5_count_exploratory']}/"
        f"{report['revision_requirement_pairs']} (NOT link recall).",
        f"Behavioral abstentions: {report['behavioral_abstentions']}/"
        f"{report['revision_requirement_pairs']}. Independent gold: 0.",
        "",
        "| Revision | Case | Fix locus rank | Structural property | Behavioral verdict |",
        "|---|---|---:|---|---|",
    ]
    for row in report["cases"]:
        structural = row["structural_property_present_at_known_fix_locus"]
        lines.append(
            f"| {row['revision']} | {row['case_id']} | "
            f"{row['known_fix_locus_rank_not_gold'] or 'not top-10'} | "
            f"{'present' if structural is True else 'absent' if structural is False else 'not retrieved'} | "
            "abstain |"
        )
    lines.extend([
        "", "## Next experiment",
        "Independent reviewers must validate all six M20 candidate links and "
        "six revision-behavior cases per reviewer with version-matched approved "
        "execution evidence. A third person adjudicates. Keep these development "
        "cases outside final held-out scoring.",
        "", "Conformance accuracy, violation precision/recall, and coverage: **not measured**.",
    ])
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    report = build(m29.fetch_pinned())
    write(report, args.out_dir)
    print(json.dumps({
        "revision_requirement_pairs": report["revision_requirement_pairs"],
        "fix_locus_top1_exploratory": report["known_fix_locus_top1_count_exploratory"],
        "fix_locus_top5_exploratory": report["known_fix_locus_top5_count_exploratory"],
        "behavioral_abstentions": report["behavioral_abstentions"],
        "independent_adjudications": 0,
        "conformance_accuracy": None,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
