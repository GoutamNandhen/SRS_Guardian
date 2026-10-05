import json
from pathlib import Path
import pytest
from backend.evaluation.run_evaluation import (
    evaluate_classification,
    evaluate_ambiguity,
    evaluate_duplicates,
    evaluate_contradictions,
)

DATA_DIR = Path("data/test")


def test_classification_evaluation():
    res = evaluate_classification()
    assert "error" not in res
    assert res["sample_count"] > 100
    assert 0.70 <= res["accuracy"] <= 1.0
    assert 0.70 <= res["macro_f1"] <= 1.0


def test_ambiguity_evaluation():
    res = evaluate_ambiguity()
    assert "error" not in res
    assert res["sample_count"] == 40
    assert res["precision"] > 0.60
    assert res["f1_score"] > 0.60


def test_duplicates_evaluation():
    res = evaluate_duplicates()
    assert "error" not in res
    assert res["pair_count"] == 36
    assert res["optimal_f1"] > 0.70
    assert len(res["sweep"]) == 6


def test_contradictions_evaluation():
    res = evaluate_contradictions()
    assert "error" not in res
    assert res["total_pairs"] == 32
    assert res["numeric_layer"]["precision"] == 1.0
    assert res["nli_layer"]["f1_score"] > 0.60
    assert res["combined_pipeline"]["recall"] > 0.80
