"""Tests only the M1 evaluator, NOT the accuracy of any deployed model."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from backend.evaluation.evaluate_conformance import EvaluationError, evaluate, read_jsonl


def gold(case_id, project, split, text, linked=True, label="conforms", status="synthetic_fixture"):
    return {
        "case_id": case_id, "project_id": project, "split": split,
        "requirement_id": "REQ-" + case_id, "requirement_text": text,
        "candidate_code_ref": f"src/{project}/rules.py::rule_{case_id}",
        "source_commit": "a" * 40,
        "annotation_source": "TEST FIXTURE: synthetic independently reviewed only for test logic",
        "adjudication_status": "adjudicated", "dataset_status": status,
        "gold_link": linked, "gold_conformance": label if linked else None,
    }


def pred(row, evidence_dir, verdict="conforms", linked=True, result="pass", failure_type=None):
    file = f"{row['case_id']}.json"
    artifact = {
        "case_id": row["case_id"], "candidate_code_ref": row["candidate_code_ref"],
        "source_commit": row["source_commit"], "test_run_id": "synthetic-mocked-run",
        "test_case_id": "synthetic-mocked-test", "status": "completed", "result": result,
        "failure_type": failure_type, "expected": "expected fake response", "observed": "mocked fake response"
    }
    (evidence_dir / file).write_text(json.dumps(artifact), encoding="utf-8")
    return {"case_id": row["case_id"], "predicted_link": linked, "decision": verdict,
            "source_commit": row["source_commit"], "candidate_code_ref": row["candidate_code_ref"],
            "evidence_path": file}


class EvaluateConformanceTests(unittest.TestCase):
    def test_realistic_small_dev_fixture_is_not_95_percent_proof(self):
        rows = [gold("a", "bank", "dev", "Reject transfer over 10000.", label="violates"),
                gold("b", "bank", "dev", "Allow a transfer below 10000.", label="conforms"),
                gold("c", "bank", "dev", "Log transfer events.", linked=False)]
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            predictions = [pred(rows[0], p, verdict="violates", result="fail", failure_type="assertion_mismatch"),
                           pred(rows[1], p)]
            result = evaluate(rows, predictions, split="dev", evidence_root=p)
        self.assertEqual(result["conformance"]["accuracy_full_denominator_abstentions_wrong"], 1.0)
        self.assertEqual(result["acceptance"]["status"], "NOT_ELIGIBLE")
        self.assertEqual(result["link_pairwise"]["fn"], 0)
        self.assertEqual(result["link_pairwise"]["tp"], 2)

    def test_missing_prediction_counts_against_full_accuracy_and_coverage(self):
        rows = [gold("a", "one", "test", "Password min eight.", label="violates"),
                gold("b", "one", "test", "Balance display within two seconds.", label="conforms")]
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            a = pred(rows[0], p, verdict="violates", result="fail", failure_type="assertion_mismatch")
            result = evaluate(rows, [a], evidence_root=p)
        self.assertEqual(result["conformance"]["accuracy_full_denominator_abstentions_wrong"], 0.5)
        self.assertEqual(result["conformance"]["coverage"], 0.5)
        self.assertEqual(result["conformance"]["missing_predictions_count"], 1)

    def test_reject_cross_project_split_leakage(self):
        rows = [gold("a", "bank", "train", "Use registered email for recovery."),
                gold("b", "bank", "test", "Only registered email may recover passwords.")]
        with self.assertRaisesRegex(EvaluationError, "Project leakage"):
            evaluate(rows, [], evidence_root=Path("."))

    def test_reject_identical_text_split_leakage(self):
        rows = [gold("a", "bank", "train", "Reject requests after timeout."),
                gold("b", "other", "test", "  reject   requests after timeout. ")]
        with self.assertRaisesRegex(EvaluationError, "Requirement-text leakage"):
            evaluate(rows, [], evidence_root=Path("."))

    def test_reject_duplicate_gold_identifiers(self):
        rows = [gold("a", "bank", "test", "Rule A."), gold("a", "bank", "test", "Rule B.")]
        with self.assertRaisesRegex(EvaluationError, "Duplicate case_id"):
            evaluate(rows, [], evidence_root=Path("."))

    def test_missing_or_invalid_evidence_is_abstention(self):
        rows = [gold("a", "bank", "test", "Reject invalid account.", label="violates")]
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            fake = pred(rows[0], p, verdict="violates", result="fail", failure_type="assertion_mismatch")
            fake["evidence_path"] = "../untrusted.json"
            report = evaluate(rows, [fake], evidence_root=p)
            self.assertEqual(report["conformance"]["decided"], 0)
            self.assertEqual(report["conformance"]["invalid_evidence_count"], 1)
            self.assertEqual(report["conformance"]["accuracy_full_denominator_abstentions_wrong"], 0)

    def test_crashed_test_run_cannot_be_claimed_as_a_violation(self):
        rows = [gold("a", "bank", "test", "Reject oversized transfer.", label="violates")]
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            fake = pred(rows[0], p, verdict="violates", result="fail", failure_type="infrastructure_error")
            report = evaluate(rows, [fake], evidence_root=p)
            self.assertEqual(report["conformance"]["decided"], 0)

    def test_mocked_large_real_status_checks_gate_arithmetic_not_real_performance(self):
        # MOCK ONLY: never interpret these synthetic labels as an empirical result.
        rows = []
        for i in range(550):
            project = f"mock_project_{i % 3}"
            label = "violates" if i % 2 else "conforms"
            rows.append(gold(f"case{i:04}", project, "test", f"Synthetic case requirement {i}.",
                             linked=i < 500, label=label, status="real_adjudicated"))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            preds = [pred(r, root, verdict=r["gold_conformance"],
                          result="fail" if r["gold_conformance"] == "violates" else "pass",
                          failure_type="assertion_mismatch" if r["gold_conformance"] == "violates" else None)
                     for r in rows if r["gold_link"]]
            report = evaluate(rows, preds, evidence_root=root)
        self.assertEqual(report["acceptance"]["status"], "PASSED")
        self.assertEqual(report["conformance"]["coverage"], 1.0)

    def test_empty_gold_or_unknown_predictions_fail_closed(self):
        with self.assertRaises(EvaluationError):
            evaluate([], [], evidence_root=Path("."))
        rows = [gold("a", "bank", "test", "Requirement one.")]
        with self.assertRaisesRegex(EvaluationError, "unknown case_id"):
            evaluate(rows, [{"case_id": "nope", "predicted_link": False}], evidence_root=Path("."))


if __name__ == "__main__":
    unittest.main()