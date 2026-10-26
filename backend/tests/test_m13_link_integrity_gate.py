"""M13 regression: a perfect conformance score must not hide bad code links.

All rows are deliberately synthetic even where dataset_status is set to
real_adjudicated to exercise arithmetic. This is NOT an empirical benchmark.
"""
import json

from backend.evaluation.evaluate_conformance import evaluate


def row(case, *, linked=True, label="conforms"):
    return {
        "case_id": case, "project_id": "MOCK-ONLY", "split": "test",
        "requirement_id": "REQ-" + case,
        "requirement_text": "MOCK requirement " + case,
        "candidate_code_ref": "src/bank.py::" + case,
        "source_commit": "a" * 40,
        "annotation_source": "TEST MOCK NOT INDEPENDENT",
        "adjudication_status": "adjudicated",
        "dataset_status": "real_adjudicated",  # gate arithmetic only
        "gold_link": linked, "gold_conformance": label if linked else None,
    }


def prediction(gold, folder, *, verdict="conforms", result="pass"):
    evidence = {
        "case_id": gold["case_id"], "candidate_code_ref": gold["candidate_code_ref"],
        "source_commit": gold["source_commit"], "test_run_id": "MOCK-RUN",
        "test_case_id": "MOCK-CASE", "status": "completed", "result": result,
        "failure_type": "assertion_mismatch" if result == "fail" else None,
        "expected": "mock expected", "observed": "mock observed",
    }
    file = gold["case_id"] + ".json"
    (folder / file).write_text(json.dumps(evidence), encoding="utf-8")
    return {
        "case_id": gold["case_id"], "predicted_link": True,
        "decision": verdict, "source_commit": gold["source_commit"],
        "candidate_code_ref": gold["candidate_code_ref"], "evidence_path": file,
    }


def score(gold, preds, tmp_path):
    # Relax sample sizes solely for isolated gate unit tests; never publish
    # these mocked cases as actual independent project validation.
    return evaluate(
        gold, preds, evidence_root=tmp_path, minimum_cases=2,
        minimum_projects=1, minimum_per_class=1,
    )


def test_correct_trace_and_correct_conformance_pass_only_mock_arithmetic(tmp_path):
    gold = [
        row("conforming"), row("violating", label="violates"),
        row("unlinked1", linked=False), row("unlinked2", linked=False),
    ]
    preds = [
        prediction(gold[0], tmp_path),
        prediction(gold[1], tmp_path, verdict="violates", result="fail"),
        {"case_id": "unlinked1", "predicted_link": False},
        {"case_id": "unlinked2", "predicted_link": False},
    ]
    result = score(gold, preds, tmp_path)
    assert result["conformance"]["accuracy_full_denominator_abstentions_wrong"] == 1.0
    assert result["link_pairwise"]["precision"] == 1.0
    assert result["link_pairwise"]["recall"] == 1.0
    assert result["acceptance"]["status"] == "PASSED"  # mock arithmetic ONLY
    assert result["acceptance"]["targets"]["link_precision"] == 0.95
    assert result["acceptance"]["targets"]["link_recall"] == 0.95


def test_false_links_block_95_percent_claim_even_with_perfect_conformance(tmp_path):
    gold = [
        row("conforming"), row("violating", label="violates"),
        row("unlinked1", linked=False), row("unlinked2", linked=False),
    ]
    preds = [
        prediction(gold[0], tmp_path),
        prediction(gold[1], tmp_path, verdict="violates", result="fail"),
        {"case_id": "unlinked1", "predicted_link": True},
        {"case_id": "unlinked2", "predicted_link": True},
    ]
    result = score(gold, preds, tmp_path)
    assert result["conformance"]["accuracy_full_denominator_abstentions_wrong"] == 1.0
    assert result["conformance"]["violation_precision"] == 1.0
    assert result["conformance"]["violation_recall"] == 1.0
    assert result["link_pairwise"]["precision"] == 0.5
    assert result["link_pairwise"]["recall"] == 1.0
    assert result["acceptance"]["eligible"] is True
    assert result["acceptance"]["passed"] is False
    assert result["acceptance"]["status"] == "NOT_MET"


def test_wrong_candidate_reference_cannot_count_as_true_link(tmp_path):
    gold = [row("A"), row("B", label="violates"), row("U", linked=False)]
    a = prediction(gold[0], tmp_path)
    b = prediction(gold[1], tmp_path, verdict="violates", result="fail")
    b["candidate_code_ref"] = "src/another.py::different"
    result = score(gold, [a, b, {"case_id": "U", "predicted_link": False}], tmp_path)
    assert result["link_pairwise"]["tp"] == 1
    assert result["link_pairwise"]["fn"] == 1
    assert result["link_pairwise"]["reference_mismatch_count"] == 1
    assert result["link_pairwise"]["recall"] == 0.5
    assert result["acceptance"]["status"] == "NOT_MET"


def test_wrong_source_revision_cannot_count_as_true_link(tmp_path):
    gold = [row("A"), row("B", label="violates"), row("U", linked=False)]
    a = prediction(gold[0], tmp_path)
    b = prediction(gold[1], tmp_path, verdict="violates", result="fail")
    b["source_commit"] = "b" * 40
    result = score(gold, [a, b, {"case_id": "U", "predicted_link": False}], tmp_path)
    assert result["link_pairwise"]["tp"] == 1
    assert result["link_pairwise"]["fn"] == 1
    assert result["link_pairwise"]["reference_mismatch_count"] == 1
    assert result["acceptance"]["passed"] is False
