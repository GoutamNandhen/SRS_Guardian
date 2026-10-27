"""M32: interactive source-grounded pagination trace demo, not conformance validation.

Builds on M31's pinned/hash-verified evidence and M30's conditional Python
abstraction. No external project code is executed; all labels remain unknown.
"""
from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path

from backend.evaluation import m30_static_pagination_witness as m30
from backend.evaluation import m31_two_project_casebook as m31

SCHEMA = "m32-interactive-source-trace-demo-1"


def build_replay(casebook: dict, witness: dict) -> dict:
    if casebook.get("schema") != m31.SCHEMA or witness.get("schema") != m30.MODEL:
        raise ValueError("Expected M31 casebook and M30 pinned witness")
    if casebook.get("project_count") != 2 or casebook.get("historical_scenarios") != 5:
        raise ValueError("Incomplete two-project source evidence")
    if casebook.get("independent_adjudications") != 0 or witness.get("independent_adjudications") != 0:
        raise ValueError("Independently adjudicated material requires a separate evaluation")
    if any(value is not None for value in casebook.get("metrics", {}).values()) or len(casebook.get("metrics", {})) != len(m31.METRICS):
        raise ValueError("Unreviewed casebook must not contain research scores")
    if len(witness.get("cases", [])) != 2:
        raise ValueError("Missing pinned pagination cases")
    anchors = witness.get("verified_source_expression_anchors", {})
    if any(len(anchors.get(rev, [])) != 6 for rev in ("before", "after")):
        raise ValueError("Missing verified Java source-line anchors")
    if len(witness.get("assumptions", [])) != 5:
        raise ValueError("Missing conditional model assumptions")
    edc, pip = casebook["projects"]
    if len(edc.get("cases", [])) != 2 or len(pip.get("cases", [])) != 3:
        raise ValueError("Unexpected source-linked case inventory")
    if {c["case_id"] for c in edc["cases"]} != {c["case_id"] for c in witness["cases"]}:
        raise ValueError("Case IDs do not match M30 source witness")
    cases = []
    for case in witness["cases"]:
        record = next(row for row in edc["cases"] if row["case_id"] == case["case_id"])
        if (record["static_model_before"] != case["before"]["model_returned_offers"]
                or record["static_model_after"] != case["after"]["model_returned_offers"]):
            raise ValueError("M31 casebook and M30 source model disagree")
        cases.append({
            "case_id": case["case_id"], "offset": case["offset"], "limit": case["limit"],
            "asset_counts_assumed": case["asset_counts_assumed"],
            "upstream_expected_unadjudicated": case["upstream_expected_offers_unadjudicated"],
            "before": case["before"], "after": case["after"],
            "source_before": record["source_before"], "source_after": record["source_after"],
            "runtime_observations": None, "independent_labels": None,
        })
    return {
        "schema": SCHEMA, "source_casebook_schema": m31.SCHEMA,
        "source_witness_schema": m30.MODEL, "projects": 2,
        "pagination_scenarios": cases,
        "pip_scenarios": [{
            "case_id": c["case_id"], "requirement": c["requirement"],
            "source_before": c["source_before"], "source_after": c["source_after"],
            "model_status": "ABSTAIN_NO_BEHAVIORAL_MODEL", "runtime_observations": None,
            "independent_labels": None,
        } for c in pip["cases"]],
        "java_source_anchors": anchors, "assumptions": witness["assumptions"],
        "independent_adjudications": 0,
        "metrics": {key: None for key in m31.METRICS},
        "external_project_code_executed": False,
        "held_out_evaluation": False,
        "interpretation": (
            "Interactive step replay of a conditional first-party Python abstraction, "
            "not Java runtime verification, independent labels, or measured conformance. "
            "Historical upstream expected values are unadjudicated."
        ),
    }


def _link(url: str, label: str) -> str:
    return '<a target="_blank" rel="noopener noreferrer" href="' + escape(url, quote=True) + '">' + escape(label) + "</a>"


def _steps(steps: list[dict]) -> str:
    if not steps:
        return "<p>No definition visited by this conditional model.</p>"
    keys = ("definition", "assets", "seen_before", "fetched_before",
            "query_offset", "query_limit", "model_emitted")
    header = "".join("<th>" + escape(k.replace("_", " ")) + "</th>" for k in keys)
    rows = "".join(
        "<tr>" + "".join("<td>" + escape(str(step.get(key, "—"))) + "</td>" for key in keys) + "</tr>"
        for step in steps
    )
    return "<div class='scroll'><table><thead><tr>" + header + "</tr></thead><tbody>" + rows + "</tbody></table></div>"


def render_html(replay: dict) -> str:
    if replay.get("schema") != SCHEMA:
        raise ValueError("Unexpected replay schema")
    tabs = []
    sections = []
    for i, case in enumerate(replay["pagination_scenarios"]):
        case_id = escape(case["case_id"])
        tabs.append('<button type="button" data-panel="scenario-' + str(i) + '"' +
                    (' aria-pressed="true"' if i == 0 else ' aria-pressed="false"') +
                    ">" + case_id + "</button>")
        blocks = []
        for rev in ("before", "after"):
            blocks.append("<article><h3>" + rev.title() + " revision — model returned " +
                          str(case[rev]["model_returned_offers"]) + "</h3>" +
                          _link(case["source_" + rev], "Pinned Java source") +
                          _steps(case[rev]["steps"]) + "</article>")
        sections.append(
            '<section id="scenario-' + str(i) + '" class="panel"' +
            ("" if i == 0 else " hidden") + "><h2>" + case_id + "</h2><p>Assumed assets: " +
            escape(str(case["asset_counts_assumed"])) + " · Offset: " + str(case["offset"]) +
            " · Limit: " + str(case["limit"]) + " · Upstream expected (NOT independently reviewed): " +
            str(case["upstream_expected_unadjudicated"]) + "</p><div class='grid'>" +
            "".join(blocks) + "</div><p class='notice'>These are conditional Python model traces, "
            "not actual Java observations or independently verified violations.</p></section>"
        )
    anchor_html = "".join(
        "<article><h3>" + rev.title() + " source anchors</h3><ol>" +
        "".join("<li>" + _link(a["url"], a["expression"]) + "</li>" for a in replay["java_source_anchors"][rev]) +
        "</ol></article>" for rev in ("before", "after")
    )
    pip_html = "".join(
        "<li><strong>" + escape(c["case_id"]) + "</strong>: " + escape(c["requirement"]) +
        " — <strong>ABSTAIN</strong> (no behavioral model). " +
        _link(c["source_before"], "Before") + " / " + _link(c["source_after"], "After") + "</li>"
        for c in replay["pip_scenarios"]
    )
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>SRS Guardian 2.0 — M32 source-grounded trace replay</title>"
        "<style>body{font:16px system-ui,sans-serif;max-width:1200px;margin:24px auto;padding:0 18px;"
        "background:#f5f7fa;color:#182536}header,section{background:white;border:1px solid #d8e0e8;"
        "border-radius:12px;padding:22px;margin:16px 0}h1,h2{margin-top:0}.notice{background:#fff4df;"
        "border-left:4px solid #b26b18;padding:12px}.grid{display:grid;grid-template-columns:"
        "repeat(auto-fit,minmax(340px,1fr));gap:14px}article{min-width:0;border:1px solid #e0e5ea;"
        "border-radius:8px;padding:12px}.scroll{overflow:auto}table{border-collapse:collapse;"
        "font-size:13px;width:100%;margin-top:12px}th,td{border:1px solid #ddd;padding:7px;"
        "text-align:left}button{margin:5px;padding:10px 14px;cursor:pointer;border-radius:7px;"
        "border:1px solid #7089a4;background:#fff}button[aria-pressed=true]{background:#194e87;"
        "color:white}a{color:#07599e}li{margin:8px 0}</style></head><body>"
        "<header><h1>SRS Guardian 2.0 — source-grounded verification replay</h1>"
        "<p>Choose a real reported Eclipse EDC pagination scenario and inspect every modeled "
        "definition-level query step beside its pinned before/after Java source. The pip project "
        "is explicitly abstained from because no behavioral model exists.</p>"
        "<p class='notice'><strong>NOT VALIDATED:</strong> 0 independent adjudications. "
        "All conformance/violation accuracy metrics unavailable. This replays a conditional "
        "Python abstraction; it does not execute external Java or pip source.</p></header>"
        "<section><h2>Eclipse EDC — conditional pagination replay</h2><nav aria-label='Choose scenario'>" +
        "".join(tabs) + "</nav>" + "".join(sections) + "</section>"
        "<section><h2>Verified Java source-expression anchors</h2><div class='grid'>" +
        anchor_html + "</div></section>"
        "<section><h2>Five explicit model assumptions</h2><ol>" +
        "".join("<li>" + escape(a) + "</li>" for a in replay["assumptions"]) +
        "</ol></section><section><h2>Independent project: pip</h2>"
        "<p>Three historical requirement candidates. No inferred conformance or violation verdicts.</p><ul>" +
        pip_html + "</ul></section>"
        "<section><h2>Independent review required</h2><p>Use the separate M20 blinded reviewer "
        "packets, not this internal replay. Two independent reviewers must assess links and "
        "behavior on both revisions with version-compatible observed evidence; a third must "
        "adjudicate. Evaluate frozen methods on unseen projects before reporting accuracy.</p>"
        "<p>See <a href='replay.json'>Machine-readable replay</a> and "
        "<a href='casebook.json'>M31 casebook</a>.</p></section>"
        "<script>document.querySelectorAll('button[data-panel]').forEach(b=>"
        "b.addEventListener('click',()=>{document.querySelectorAll('button[data-panel]')"
        ".forEach(x=>x.setAttribute('aria-pressed',String(x===b)));"
        "document.querySelectorAll('.panel').forEach(x=>x.hidden=x.id!==b.dataset.panel);"
        "}));</script></body></html>"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    # M31 obtains pinned, hash-verified source and prepares separate blinded M20 packets.
    m31.main(["--out-dir", str(args.out_dir)])
    internal = args.out_dir / "internal"
    casebook = json.loads((internal / "casebook.json").read_text(encoding="utf-8"))
    witness = json.loads((args.out_dir / "edc" / "internal" /
                          "m30_conditional_static_witness.json").read_text(encoding="utf-8"))
    replay = build_replay(casebook, witness)
    (internal / "replay.json").write_text(json.dumps(replay, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (internal / "replay.html").write_text(render_html(replay), encoding="utf-8")
    print(json.dumps({"interactive_demo": str(internal / "replay.html"),
                      "conditional_edc_scenarios": len(replay["pagination_scenarios"]),
                      "pip_abstentions": len(replay["pip_scenarios"]),
                      "independent_adjudications": 0, "conformance_accuracy": None}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
