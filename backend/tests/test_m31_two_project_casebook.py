"""M31 offline unit tests use synthetic dictionaries, NEVER external gold labels."""
from __future__ import annotations

import json

import pytest

from backend.evaluation import m28_historical_pagination_regression as m28
from backend.evaluation import m29_pip_historical_regression as m29
from backend.evaluation import m30_static_pagination_witness as m30
from backend.evaluation import m31_two_project_casebook as m31


def _evidence():
    edc = {
        "schema": m30.MODEL,
        "independent_adjudications": 0,
        "verified_source_expression_anchors": {
            "before": [{} for _ in range(6)], "after": [{} for _ in range(6)]
        },
        "assumptions": list(m30.ASSUMPTIONS),
        "cases": [
            {
                "case_id": case_id, "offset": offset, "limit": limit,
                "upstream_expected_offers_unadjudicated": expected,
                "before": {"model_returned_offers": alleged},
                "after": {"model_returned_offers": expected},
            }
            for case_id, offset, limit, expected, alleged in m28.SCENARIOS
        ],
    }
    pip = {
        "internal": {
            "schema": "m29-pip-historical-regression-evidence-1",
            "independently_adjudicated_behavior_cases": 0,
            "static_file_revision_objects_verified": 6,
            "distinct_git_blobs_verified": 5,
            "m20_link_pairs_pending": 6,
            "behavior_revision_cases_pending_per_reviewer": 6,
        },
        "reviewer_index": {"source_anchors": {"before_resolver": "", "after_resolver": "",
                                               "after_direct_test": "", "after_indirect_test": ""}},
    }
    return edc, pip


def test_two_real_project_sources_are_distinct():
    assert m28.REPO != m29.REPO
    assert m28.BEFORE != m28.AFTER and m29.BEFORE != m29.AFTER
    assert len(m28.FILES["before"]) == len(m29.FILES["before"]) == 3


def test_casebook_exposes_only_unverified_conditional_predictions(tmp_path):
    edc, pip = _evidence()
    book = m31.build_casebook(edc, pip)
    assert book["project_count"] == 2
    assert book["historical_scenarios"] == 5
    assert book["revision_behavior_cases_pending_per_reviewer"] == 10
    assert book["m20_link_pairs_pending_per_reviewer"] == 10
    assert book["static_file_revision_objects_verified"] == 12
    assert book["independent_adjudications"] == 0
    assert book["representative_held_out_evaluation"] is False
    assert book["external_project_code_executed"] is False
    assert all(value is None for value in book["metrics"].values())
    assert len(book["projects"][0]["cases"]) == 2
    assert len(book["projects"][1]["cases"]) == 3
    assert all(case["independent_conformance_label"] is None and
               case["independent_violation_label"] is None and
               case["runtime_before"] is None and case["runtime_after"] is None
               for project in book["projects"] for case in project["cases"])
    assert all(case["static_model_before"] is None for case in book["projects"][1]["cases"])
    m31.write_casebook(book, tmp_path)
    report = (tmp_path / "internal" / "index.html").read_text()
    stored = json.loads((tmp_path / "internal" / "casebook.json").read_text())
    assert stored == book
    assert "NOT VALIDATED" in report and "UNVERIFIED" in report
    assert "No third-party project code executed" in report
    assert m28.ISSUE in report and m29.ISSUE in report
    assert not (tmp_path / "reviewers").exists()


@pytest.mark.parametrize("mutation", ["edc_schema", "pip_schema", "edc_gold", "pip_gold",
                                        "edc_score", "pip_score", "edc_missing_case",
                                        "pip_missing_blob", "edc_missing_anchor"])
def test_incomplete_or_unreviewed_claims_fail_closed(mutation):
    edc, pip = _evidence()
    if mutation == "edc_schema":
        edc["schema"] = "wrong"
    elif mutation == "pip_schema":
        pip["internal"]["schema"] = "wrong"
    elif mutation == "edc_gold":
        edc["independent_adjudications"] = 1
    elif mutation == "pip_gold":
        pip["internal"]["independently_adjudicated_behavior_cases"] = 1
    elif mutation == "edc_score":
        edc["conformance_accuracy"] = 1.0
    elif mutation == "pip_score":
        pip["internal"]["violation_precision"] = 1.0
    elif mutation == "edc_missing_case":
        edc["cases"].pop()
    elif mutation == "pip_missing_blob":
        pip["internal"]["static_file_revision_objects_verified"] = 5
    elif mutation == "edc_missing_anchor":
        edc["verified_source_expression_anchors"]["before"].pop()
    with pytest.raises(ValueError):
        m31.build_casebook(edc, pip)
