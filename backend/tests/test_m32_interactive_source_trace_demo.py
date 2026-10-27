"""M32 synthetic-fixture unit tests: never independent conformance evidence."""
from __future__ import annotations

import copy
import json

import pytest

from backend.evaluation import m30_static_pagination_witness as m30
from backend.evaluation import m31_two_project_casebook as m31
from backend.evaluation import m32_interactive_source_trace_demo as m32


def _fixtures():
    cases = [
        ("PAG_52_0", 0, 52, 52),
        ("PAG_2_49", 49, 2, 2),
    ]
    witness_cases = []
    book_cases = []
    for case_id, offset, limit, expected in cases:
        before = m30.simulate_before((50, 50), offset, limit)
        after = m30.simulate_after((50, 50), offset, limit)
        witness_cases.append({
            "case_id": case_id, "offset": offset, "limit": limit,
            "asset_counts_assumed": [50, 50],
            "upstream_expected_offers_unadjudicated": expected,
            "before": before, "after": after,
        })
        book_cases.append({
            "case_id": case_id, "static_model_before": before["model_returned_offers"],
            "static_model_after": after["model_returned_offers"],
            "source_before": "https://github.com/example/pinned-before#L1",
            "source_after": "https://github.com/example/pinned-after#L2",
        })
    witness = {
        "schema": m30.MODEL, "independent_adjudications": 0,
        "cases": witness_cases, "assumptions": list(m30.ASSUMPTIONS),
        "verified_source_expression_anchors": {
            rev: [{"expression": marker, "url": "https://github.com/example/source#L1"}
                  for marker in m30.SOURCE_MARKERS[rev]]
            for rev in ("before", "after")
        },
    }
    book = {
        "schema": m31.SCHEMA, "project_count": 2, "historical_scenarios": 5,
        "independent_adjudications": 0,
        "metrics": {key: None for key in m31.METRICS},
        "projects": [
            {"cases": book_cases},
            {"cases": [{
                "case_id": f"PIP_{i}", "requirement": "Resolver must preserve extras",
                "source_before": "https://github.com/example/pip-before",
                "source_after": "https://github.com/example/pip-after",
            } for i in range(3)]},
        ],
    }
    return book, witness


def test_replay_has_source_trace_and_honest_abstention():
    book, witness = _fixtures()
    replay = m32.build_replay(book, witness)
    assert replay["schema"] == m32.SCHEMA
    assert replay["projects"] == 2
    assert len(replay["pagination_scenarios"]) == 2
    assert len(replay["pip_scenarios"]) == 3
    assert all(x["model_status"] == "ABSTAIN_NO_BEHAVIORAL_MODEL" for x in replay["pip_scenarios"])
    assert all(x["independent_labels"] is None for x in replay["pip_scenarios"])
    assert all(x["runtime_observations"] is None for x in replay["pagination_scenarios"])
    assert all(v is None for v in replay["metrics"].values())
    assert replay["independent_adjudications"] == 0
    assert replay["external_project_code_executed"] is False
    assert replay["held_out_evaluation"] is False
    assert [x["before"]["model_returned_offers"] for x in replay["pagination_scenarios"]] == [100, 3]
    assert [x["after"]["model_returned_offers"] for x in replay["pagination_scenarios"]] == [52, 2]


def test_html_is_interactive_and_discloses_unverified_model():
    book, witness = _fixtures()
    html = m32.render_html(m32.build_replay(book, witness))
    assert "data-panel" in html and "aria-pressed" in html and "x.hidden" in html
    assert "NOT VALIDATED" in html and "conditional" in html
    assert "ABSTAIN" in html and "pip" in html
    assert "model returned 100" in html and "model returned 52" in html
    assert "model returned 3" in html and "model returned 2" in html
    assert "https://github.com/example/source#L1" in html
    assert "Machine-readable replay" in html


@pytest.mark.parametrize("tamper", [
    "gold", "missing_anchor", "wrong_case", "wrong_model", "missing_assumption",
    "incomplete_pip",
])
def test_rejects_incomplete_or_misleading_evidence(tamper):
    book, witness = _fixtures()
    book, witness = copy.deepcopy(book), copy.deepcopy(witness)
    if tamper == "gold":
        book["metrics"]["conformance_accuracy"] = 1.0
    elif tamper == "missing_anchor":
        witness["verified_source_expression_anchors"]["before"].pop()
    elif tamper == "wrong_case":
        witness["cases"][0]["case_id"] = "OTHER"
    elif tamper == "wrong_model":
        book["projects"][0]["cases"][0]["static_model_before"] = 99
    elif tamper == "missing_assumption":
        witness["assumptions"].pop()
    elif tamper == "incomplete_pip":
        book["projects"][1]["cases"].pop()
    with pytest.raises(ValueError):
        m32.build_replay(book, witness)


def test_replay_is_machine_readable_without_gold():
    book, witness = _fixtures()
    replay = json.loads(json.dumps(m32.build_replay(book, witness)))
    assert replay["metrics"]["violation_precision"] is None
    assert replay["metrics"]["violation_recall"] is None
    assert replay["metrics"]["conformance_coverage"] is None
