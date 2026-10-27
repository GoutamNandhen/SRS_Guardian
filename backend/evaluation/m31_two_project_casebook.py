"""M31: one-command, two-project source-linked verification demonstration.

This produces a casebook from immutable, Git-blob-verified static source.
It NEVER imports, builds or executes the third-party EDC or pip projects.
The EDC model is conditional; pip has no behavioral model. No gold labels.
"""
from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path

from backend.evaluation import m28_historical_pagination_regression as m28
from backend.evaluation import m29_pip_historical_regression as m29
from backend.evaluation import m30_static_pagination_witness as m30

SCHEMA = "m31-two-project-casebook-1"
METRICS = ("conformance_accuracy", "violation_precision", "violation_recall", "conformance_coverage")


def build_casebook(edc: dict, pip: dict) -> dict:
    """Join two separately verified evidence objects, without inferring verdicts."""
    if edc.get("schema") != m30.MODEL or pip.get("internal", {}).get("schema") != "m29-pip-historical-regression-evidence-1":
        raise ValueError("Wrong source evidence schema")
    if edc.get("independent_adjudications") != 0 or pip["internal"].get("independently_adjudicated_behavior_cases") != 0:
        raise ValueError("This casebook requires pending independent review")
    if any(edc.get(k) is not None or pip["internal"].get(k) is not None for k in METRICS):
        raise ValueError("Do not combine measured scores with unadjudicated casebook")
    if len(edc.get("cases", [])) != len(m28.SCENARIOS) or len(m29.SCENARIOS) != 3:
        raise ValueError("Incomplete behavioral case set")
    if len(edc.get("verified_source_expression_anchors", {}).get("before", [])) != 6:
        raise ValueError("Missing pinned EDC source anchors")
    if len(edc["verified_source_expression_anchors"].get("after", [])) != 6:
        raise ValueError("Missing pinned post-fix EDC source anchors")
    if pip["internal"].get("static_file_revision_objects_verified") != 6:
        raise ValueError("Missing pinned pip static objects")

    edc_rows = []
    expected_ids = {row[0] for row in m28.SCENARIOS}
    if {row["case_id"] for row in edc["cases"]} != expected_ids:
        raise ValueError("EDC cases do not match pinned scenarios")
    for row in edc["cases"]:
        edc_rows.append({
            "case_id": row["case_id"],
            "requirement_origin": "Upstream issue reporter expectation (unadjudicated)",
            "requirement": (
                f"With two definitions selecting 50 assets each, offset={row['offset']} "
                f"and limit={row['limit']} should return {row['upstream_expected_offers_unadjudicated']} offers."
            ),
            "source_before": m28.source_url("before", m28.SOURCE),
            "source_after": m28.source_url("after", m28.SOURCE),
            "test_after": m28.source_url("after", m28.TEST),
            "static_model_before": row["before"]["model_returned_offers"],
            "static_model_after": row["after"]["model_returned_offers"],
            "static_model_assumptions": edc["assumptions"],
            "runtime_before": None,
            "runtime_after": None,
            "independent_conformance_label": None,
            "independent_violation_label": None,
            "review_required": (
                "Two independent reviewers must verify requirement legitimacy, links, model assumptions "
                "and approved version-matched observed results on both revisions; third-party adjudication."
            ),
        })
    pip_rows = []
    for scenario in m29.SCENARIOS:
        pip_rows.append({
            "case_id": scenario["case_id"],
            "requirement_origin": scenario["origin"],
            "requirement": scenario["requirement_text"],
            "source_before": m29.source_url("before", m29.SOURCE),
            "source_after": m29.source_url("after", m29.SOURCE),
            "test_after": m29.source_url("after", m29.TEST),
            "static_model_before": None,
            "static_model_after": None,
            "static_model_assumptions": None,
            "runtime_before": None,
            "runtime_after": None,
            "independent_conformance_label": None,
            "independent_violation_label": None,
            "review_required": (
                "Two independent reviewers must validate requirement/test intent and source links, "
                "then obtain approved revision-specific runtime evidence; third-party adjudication. "
                "The two upstream added tests are not exact reproductions of the reporter's gitlint case."
            ),
        })

    projects = [
        {
            "project_id": m28.PROJECT, "repository": m28.REPO, "license": "Apache-2.0",
            "issue": m28.ISSUE, "fix": m28.PATCH, "commits": m28.COMMITS,
            "static_file_revision_objects_verified": 6,
            "distinct_git_blobs_verified": len({sha for files in m28.FILES.values() for sha in files.values()}),
            "source_expression_anchors_verified": 12,
            "m20_link_pairs_pending_per_reviewer": 4,
            "behavior_revision_cases_pending_per_reviewer": 4,
            "cases": edc_rows,
        },
        {
            "project_id": m29.PROJECT, "repository": m29.REPO, "license": "MIT",
            "issue": m29.ISSUE, "fix": m29.FIX, "commits": m29.COMMITS,
            "static_file_revision_objects_verified": pip["internal"]["static_file_revision_objects_verified"],
            "distinct_git_blobs_verified": pip["internal"]["distinct_git_blobs_verified"],
            "source_expression_anchors_verified": len(pip["reviewer_index"]["source_anchors"]),
            "m20_link_pairs_pending_per_reviewer": pip["internal"]["m20_link_pairs_pending"],
            "behavior_revision_cases_pending_per_reviewer": pip["internal"]["behavior_revision_cases_pending_per_reviewer"],
            "cases": pip_rows,
        },
    ]
    return {
        "schema": SCHEMA,
        "projects": projects,
        "project_count": len(projects),
        "historical_scenarios": sum(len(p["cases"]) for p in projects),
        "revision_behavior_cases_pending_per_reviewer": sum(p["behavior_revision_cases_pending_per_reviewer"] for p in projects),
        "m20_link_pairs_pending_per_reviewer": sum(p["m20_link_pairs_pending_per_reviewer"] for p in projects),
        "static_file_revision_objects_verified": sum(p["static_file_revision_objects_verified"] for p in projects),
        "independent_adjudications": 0,
        "external_project_code_executed": False,
        "representative_held_out_evaluation": False,
        "metrics": {key: None for key in METRICS},
        "limitation": (
            "Purposively selected upstream bug/fix cases, not a representative held-out evaluation. "
            "Only EDC has conditional source-grounded static predictions; neither project has "
            "independent runtime observations or adjudicated conformance/violation labels."
        ),
    }


def render_html(casebook: dict) -> str:
    """Self-contained internal-only HTML for a faculty/research demonstration."""
    def link(url: str, label: str) -> str:
        return '<a href="' + escape(url, quote=True) + '" rel="noopener noreferrer">' + escape(label) + "</a>"

    sections = []
    for project in casebook["projects"]:
        rows = []
        for case in project["cases"]:
            prediction = (
                f"Before: {case['static_model_before']}; after: {case['static_model_after']} "
                "(conditional static model, NOT runtime)"
                if case["static_model_before"] is not None else "No static behavioral prediction"
            )
            rows.append(
                "<tr><td>" + escape(case["case_id"]) + "</td><td>" +
                escape(case["requirement"]) + "<small>" + escape(case["requirement_origin"]) + "</small></td><td>" +
                link(case["source_before"], "Before source") + " · " +
                link(case["source_after"], "After source") + " · " +
                link(case["test_after"], "After test") + "</td><td>" +
                escape(prediction) + "</td><td><strong>UNVERIFIED</strong><small>" +
                escape(case["review_required"]) + "</small></td></tr>"
            )
        sections.append(
            "<section><h2>" + escape(project["repository"]) + "</h2><p>License: " +
            escape(project["license"]) + " · " + link(project["issue"], "Upstream issue") +
            " · " + link(project["fix"], "Upstream fix") + "</p><p>Before: " +
            escape(project["commits"]["before"]) + "<br>After: " +
            escape(project["commits"]["after"]) + "</p><table><thead><tr>"
            "<th>Case</th><th>Behavioral requirement candidate</th><th>Pinned source</th>"
            "<th>Model evidence</th><th>Independent status</th></tr></thead><tbody>" +
            "".join(rows) + "</tbody></table></section>"
        )
    return (
        "<!doctype html><html lang='en'><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>SRS Guardian M31 — Source-grounded casebook</title>"
        "<style>body{font:16px system-ui,sans-serif;max-width:1250px;margin:35px auto;padding:0 18px;"
        "color:#17202a;background:#f6f8fa}header,section{background:white;padding:24px;margin:18px 0;"
        "border:1px solid #d9e0e6;border-radius:12px}h1,h2{margin-top:0}table{border-collapse:collapse;"
        "width:100%}td,th{border:1px solid #d9e0e6;padding:12px;text-align:left;vertical-align:top}"
        "th{background:#eef3f8}small{display:block;color:#555;margin-top:8px}a{color:#0956a4}"
        ".warning{border-left:5px solid #ba6421;padding:12px;background:#fff5e8}</style>"
        "<header><h1>SRS Guardian 2.0 — M31 external verification casebook</h1>"
        "<p>Two real projects · five upstream scenarios · ten before/after review cases per reviewer."
        " Twelve pinned static file/revision objects. Zero independent adjudications.</p>"
        "<p class='warning'><strong>Research status: NOT VALIDATED.</strong> "
        "Conformance accuracy, violation precision/recall and conformance coverage: unavailable. "
        "Do not treat conditional models, reporter observations or merged tests as gold.</p>"
        "<p>Source-only verification. No third-party project code executed. "
        "This internal report must NOT be included in blinded reviewer packets.</p></header>" +
        "".join(sections) +
        "<section><h2>Independent review handoff</h2><p>Use the separate M20 blinded packets "
        "for each project. Two independent reviewers must assess 10 candidate links and 10 "
        "behavior/revision cases each. A third reviewer adjudicates disagreements. "
        "Provide source-line citations, independent version-compatible execution or archived "
        "logs, fixture/configuration details and explicit unknowns. Then evaluate on unseen projects.</p>"
        "<p>Historical selection is not representative held-out evaluation.</p></section></html>"
    )


def write_casebook(casebook: dict, out_dir: Path) -> None:
    internal = out_dir / "internal"
    internal.mkdir(parents=True, exist_ok=True)
    (internal / "casebook.json").write_text(json.dumps(casebook, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (internal / "index.html").write_text(render_html(casebook), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    # Only static, immutable, hash-verified text is downloaded. No upstream execution.
    edc = m30.build_witness(m28.fetch_pinned())
    pip = m29.build_evidence(m29.fetch_pinned())
    casebook = build_casebook(edc, pip)
    # Reviewer packets are generated by M20 and remain strictly separate from model predictions.
    m30.write_witness(edc, args.out_dir / "edc")
    m29.write_evidence(pip, args.out_dir / "pip")
    write_casebook(casebook, args.out_dir)
    print(json.dumps({
        "projects": casebook["project_count"],
        "scenarios": casebook["historical_scenarios"],
        "review_cases_per_reviewer": casebook["revision_behavior_cases_pending_per_reviewer"],
        "independent_adjudications": 0,
        "conformance_accuracy": None,
        "internal_demo": str(args.out_dir / "internal" / "index.html"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
