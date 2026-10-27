"""M16: adversarial link-precision accounting regression.

All labels, code references, and evidence are fabricated unit-test fixtures.
These tests do not measure real-world link or conformance accuracy.
"""
from __future__ import annotations

import pytest

from backend.tests.test_m13_link_integrity_gate import row, prediction, score


def _cases(tmp_path):
    gold = [row("A"), row("B", label="violates"), row("U", linked=False)]
    preds = [
        prediction(gold[0], tmp_path),
        prediction(gold[1], tmp_path, verdict="violates", result="fail"),
        {"case_id": "U", "predicted_link": False},
    ]
    return gold, preds


@pytest.mark.parametrize("field,wrong", [
    ("candidate_code_ref", "src/incorrect.py::handler"),
    ("source_commit", "b" * 40),
])
def test_wrong_positive_edge_counts_both_fp_and_fn(tmp_path, field, wrong):
    gold, preds = _cases(tmp_path)
    preds[1][field] = wrong
    result = score(gold, preds, tmp_path)
    links = result["link_pairwise"]
    assert (links["tp"], links["fp"], links["fn"], links["tn"]) == (1, 1, 1, 1)
    assert links["reference_mismatch_count"] == 1
    assert links["precision"] == 0.5
    assert links["recall"] == 0.5
    assert result["acceptance"]["passed"] is False
    assert result["conformance"]["correct"] == 1


def test_all_wrong_code_references_cannot_report_perfect_precision(tmp_path):
    gold, preds = _cases(tmp_path)
    preds[0]["candidate_code_ref"] = "src/wrong.py::A"
    preds[1]["candidate_code_ref"] = "src/wrong.py::B"
    links = score(gold, preds, tmp_path)["link_pairwise"]
    assert (links["tp"], links["fp"], links["fn"]) == (0, 2, 2)
    assert links["precision"] == 0.0
    assert links["recall"] == 0.0
    assert links["reference_mismatch_count"] == 2


def test_correct_references_preserve_true_positive_precision(tmp_path):
    gold, preds = _cases(tmp_path)
    links = score(gold, preds, tmp_path)["link_pairwise"]
    assert (links["tp"], links["fp"], links["fn"], links["tn"]) == (2, 0, 0, 1)
    assert links["precision"] == 1.0
    assert links["recall"] == 1.0
