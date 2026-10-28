"""M43: retrieval-gated static witness on hash-verified, full-tree pip snapshots.

A specialist source-pattern witness is attempted ONLY when an ordinary M42
whole-implementation-tree retrieval ranks its bound symbol in top five.
Source-pattern variants are inferred from AST text without receiving the
revision label. The historical locus is not inserted into retrieval.
This is development-case source evidence, NOT behavioral conformance.
No third-party code is imported, installed, or executed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.evaluation import m29_pip_historical_regression as m29
from backend.evaluation import m34_pip_source_structure_witness as m34
from backend.evaluation import m40_pip_e2e_feasibility as m40
from backend.evaluation import m42_pip_first_party_tree_retrieval as m42

SCHEMA = "m43-retrieval-gated-source-witness-1"
METHOD = "normalized_tokens"
TOP_K = 5
# A predeclared, bug-specific static witness binding, NOT a retrieval feature.
# This specialist does not generalize to arbitrary requirements or projects.
WITNESS_BINDING = (m29.SOURCE, m40.TARGET)
METRICS = ("conformance_accuracy", "violation_precision",
           "violation_recall", "conformance_coverage")


def recognize_variant_without_revision(source: str) -> dict | None:
    """Try both source-pattern variants without passing the actual revision.

    This is a known-regression-specific source-pattern recognizer, not a
    trained model or an independent behavioral oracle.
    """
    recognized = []
    for variant in ("before", "after"):
        try:
            observation = m34.inspect_structure(source, variant)
        except (m29.EvidenceError, SyntaxError, ValueError):
            continue
        recognized.append((variant, observation))
    if len(recognized) != 1:
        return None
    variant, observation = recognized[0]
    return {
        "source_pattern": ("base_and_separate_extras" if variant == "after"
                           else "single_candidate_with_extras"),
        "successful_link_extras_yield_sites": observation["successful_link_extras_yield_sites"],
        "explicit_base_without_extras": observation["explicit_base_without_extras"],
        "separate_extras_requirement": observation["separate_extras_requirement"],
        "source_line_anchors": {
            key: int(url.rsplit("#L", 1)[1])
            for key, url in observation["source_anchors"].items()
        },
    }


def evaluate_retrieval_row(row: dict, snapshot: dict) -> dict:
    """Only a retrieved top-five candidate may trigger the source witness."""
    candidates = row["top_10_candidates"][METHOD][:TOP_K]
    matches = [
        c for c in candidates
        if (c["path"], c["qualified_name"]) == WITNESS_BINDING
    ]
    if len(matches) > 1:
        raise m29.EvidenceError("Duplicate witness binding in ranked candidates")
    result = {
        "case_id": row["case_id"],
        "revision": row["revision"],
        "requirement_origin": row["requirement_origin"],
        "top_five_source_candidates": candidates,
        "retrieval_gated_source_witness": None,
        "witness_status": "not_retrieved",
        "behavioral_decision": "insufficient_evidence",
        "behavioral_observation": None,
        "independent_gold": None,
        "independent_review_status": "pending",
    }
    if not matches:
        return result

    path = matches[0]["path"]
    raw = snapshot["files"].get(path)
    expected = snapshot["expected"].get(path)
    if raw is None or expected is None or m29.blob_sha(raw) != expected:
        raise m29.EvidenceError("Retrieved witness source is missing or hash-invalid")
    witness = recognize_variant_without_revision(raw.decode("utf-8-sig"))
    if witness is None:
        result["witness_status"] = "unsupported_source_pattern"
        return result

    # The actual revision is used ONLY to build the pinned citation, never to
    # choose the recognized source-pattern variant.
    witness["source_anchors"] = {
        key: m29.source_url(row["revision"], path, line)
        for key, line in witness.pop("source_line_anchors").items()
    }
    witness["retrieval_rank"] = matches[0]["rank"]
    witness["source_path"] = path
    witness["qualified_name"] = matches[0]["qualified_name"]
    witness["source_git_blob_sha1"] = expected
    result["retrieval_gated_source_witness"] = witness
    result["witness_status"] = "static_source_pattern_recognized"
    return result


def build(snapshots: dict, evidence: dict) -> dict:
    # M42 verifies the complete first-party Python Git tree and pinned MIT
    # license BEFORE any retrieval, including completeness of all source files.
    m42_report = m42.build(snapshots, evidence)
    rows = [
        evaluate_retrieval_row(row, snapshots[row["revision"]])
        for row in m42_report["cases"]
    ]
    if len(rows) != 6:
        raise m29.EvidenceError("Expected six development-case revision pairs")
    counts = {status: sum(r["witness_status"] == status for r in rows)
              for status in ("not_retrieved", "unsupported_source_pattern",
                             "static_source_pattern_recognized")}
    return {
        "schema": SCHEMA,
        "project": m29.REPO,
        "license": m42_report["source_license"],
        "source_revisions": m42_report["source_revisions"],
        "source_scope": m42_report["source_scope"],
        "requirement_revision_pairs": len(rows),
        "retrieval_method": METHOD,
        "retrieval_top_k": TOP_K,
        "retrieval_gated_source_witness_cases": counts["static_source_pattern_recognized"],
        "witness_status_counts": counts,
        "per_revision": {
            revision: {
                "cases": sum(r["revision"] == revision for r in rows),
                "static_source_witnesses": sum(
                    r["revision"] == revision
                    and r["witness_status"] == "static_source_pattern_recognized"
                    for r in rows
                ),
            } for revision in ("before", "after")
        },
        "cases": rows,
        "independent_adjudications": 0,
        "behavioral_decisions": 0,
        "behavioral_abstentions": len(rows),
        "held_out_project_evaluation": False,
        "external_project_code_executed": False,
        **{metric: None for metric in METRICS},
        "review_required": (
            "Two independent M20 reviewers must verify requirement legitimacy, "
            "candidate trace links, and revision-matched behavioral observations "
            "from approved trusted evidence. A third reviewer adjudicates. "
            "These pip development cases must not be scored as held out."
        ),
        "limitations": [
            "One previously inspected pip issue, three correlated scenarios, two revisions.",
            "The specialist AST witness is hard-coded to a known historical resolver source pattern.",
            "The bound symbol is not injected into ranking; the checker runs only if retrieved.",
            "Static source structure does not prove installation success or failure.",
            "No independently adjudicated conformance labels or trusted runtime observations.",
            "No general-purpose source verifier or held-out accuracy measurement.",
        ],
    }


def write(report: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "m43_retrieval_gated_witness.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# M43: whole-tree retrieval to gated source-pattern witness (NOT GOLD)",
        "",
        "This is a real, pinned MIT-licensed pip development example.",
        "Only top-five M42 retrieved implementation symbols can trigger a "
        "bug-specific static AST witness. No oracle-selected file is used in retrieval.",
        "",
        "| Revision | Case | Witness status | Structural pattern | Behavioral verdict |",
        "|---|---|---|---|---|",
    ]
    for row in report["cases"]:
        witness = row["retrieval_gated_source_witness"]
        lines.append(
            f'| {row["revision"]} | {row["case_id"]} | {row["witness_status"]} | '
            f'{witness["source_pattern"] if witness else "none"} | abstain |'
        )
    lines.extend([
        "",
        "Source-pattern coverage: "
        f'{report["retrieval_gated_source_witness_cases"]}/{report["requirement_revision_pairs"]} '
        "(exploratory, not behavioral verification coverage).",
        "All six behavioral decisions abstain; zero independently adjudicated labels.",
        "Conformance accuracy, violation precision/recall, coverage: NOT MEASURED.",
        "",
        report["review_required"],
    ])
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    evidence = m29.build_evidence(m29.fetch_pinned())
    snapshots = {revision: m42.fetch_snapshot(revision)
                 for revision in ("before", "after")}
    report = build(snapshots, evidence)
    write(report, args.out_dir)
    print(json.dumps({
        "retrieval_gated_source_witness_cases": report["retrieval_gated_source_witness_cases"],
        "per_revision": report["per_revision"],
        "behavioral_abstentions": report["behavioral_abstentions"],
        "independent_adjudications": 0,
        "conformance_accuracy": None,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
