"""SRS Guardian 2.0 M1: held-out requirement-to-code benchmark evaluation.

This module performs NO model inference and NO code execution. It scores previously
recorded predictions against independently adjudicated labels. Test-run evidence
metadata is inspected for consistency; actual execution must happen in M3.

Run: python -m backend.evaluation.evaluate_conformance --gold ... --predictions ...
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

DECISIONS = {"conforms", "violates", "insufficient_evidence", "needs_clarification", "unsupported"}
OUTCOMES = ("conforms", "violates")


class EvaluationError(ValueError):
    """Invalid benchmark or unsafe scoring configuration."""


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise EvaluationError(f"Missing file: {path}")
    records = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            record = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise EvaluationError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        if not isinstance(record, dict):
            raise EvaluationError(f"{path}:{line_no}: expected JSON object")
        records.append(record)
    if not records:
        raise EvaluationError(f"No records in {path}")
    return records


def require_nonempty(rec: dict[str, Any], field: str, where: str) -> str:
    value = rec.get(field)
    if not isinstance(value, str) or not value.strip():
        raise EvaluationError(f"{where}: missing/non-string '{field}'")
    return value.strip()


def norm_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold().strip())


def validate_gold(rows: list[dict[str, Any]]) -> None:
    ids: set[str] = set()
    projects: dict[str, str] = {}
    text_splits: dict[str, tuple[str, str]] = {}
    for i, r in enumerate(rows, 1):
        where = f"gold line {i}"
        case_id = require_nonempty(r, "case_id", where)
        project = require_nonempty(r, "project_id", where)
        split = require_nonempty(r, "split", where)
        requirement = require_nonempty(r, "requirement_text", where)
        require_nonempty(r, "requirement_id", where)
        require_nonempty(r, "candidate_code_ref", where)
        require_nonempty(r, "source_commit", where)
        require_nonempty(r, "annotation_source", where)
        status = require_nonempty(r, "adjudication_status", where)
        dataset_status = require_nonempty(r, "dataset_status", where)
        if case_id in ids:
            raise EvaluationError(f"Duplicate case_id: {case_id}")
        ids.add(case_id)
        if split not in {"train", "validation", "test", "dev"}:
            raise EvaluationError(f"{where}: invalid split '{split}'")
        if status not in {"adjudicated", "draft"}:
            raise EvaluationError(f"{where}: invalid adjudication_status")
        if dataset_status not in {"synthetic_fixture", "real_adjudicated"}:
            raise EvaluationError(f"{where}: invalid dataset_status")
        if type(r.get("gold_link")) is not bool:
            raise EvaluationError(f"{where}: gold_link must be a JSON boolean")
        label = r.get("gold_conformance")
        if r["gold_link"] and label not in OUTCOMES:
            raise EvaluationError(f"{where}: linked cases require gold_conformance")
        if not r["gold_link"] and label is not None:
            raise EvaluationError(f"{where}: unlinked candidates must have null gold_conformance")
        if project in projects and projects[project] != split:
            raise EvaluationError(f"Project leakage: project_id {project!r} occurs in both {projects[project]} and {split}")
        projects[project] = split
        normalized = norm_text(requirement)
        # Same requirement text across different data splits can leak test content.
        if normalized in text_splits and text_splits[normalized][0] != split:
            old_split, old_case = text_splits[normalized]
            raise EvaluationError(f"Requirement-text leakage: {old_case} ({old_split}) vs {case_id} ({split})")
        text_splits[normalized] = (split, case_id)


def validate_predictions(rows: list[dict[str, Any]], known_ids: set[str]) -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    for i, r in enumerate(rows, 1):
        where = f"prediction line {i}"
        case_id = require_nonempty(r, "case_id", where)
        if case_id not in known_ids:
            raise EvaluationError(f"{where}: unknown case_id {case_id!r}")
        if case_id in mapping:
            raise EvaluationError(f"{where}: duplicate prediction for {case_id!r}")
        if r.get("predicted_link") is not None and type(r.get("predicted_link")) is not bool:
            raise EvaluationError(f"{where}: predicted_link must be boolean or null")
        decision = r.get("decision", "insufficient_evidence")
        if decision not in DECISIONS:
            raise EvaluationError(f"{where}: invalid decision {decision!r}")
        confidence = r.get("confidence")
        if confidence is not None and (type(confidence) not in (int, float) or not math.isfinite(confidence) or not 0 <= confidence <= 1):
            raise EvaluationError(f"{where}: confidence must be a finite number from 0 to 1")
        if decision in OUTCOMES and r.get("predicted_link") is not True:
            raise EvaluationError(f"{where}: a conformance decision requires predicted_link=true")
        mapping[case_id] = r
    return mapping


def _evidence_ok(pred: dict[str, Any], gold: dict[str, Any], evidence_root: Path) -> bool:
    """Require a locally present, readable, matching run artifact, not merely a string ID.

    This checks a manifest, not the honesty of the test runner. Actual execution is
    a separate engineering and research milestone.
    """
    ref = pred.get("evidence_path")
    if not isinstance(ref, str) or not ref or Path(ref).is_absolute():
        return False
    root = evidence_root.resolve()
    path = (root / ref).resolve()
    if not path.is_relative_to(root) or not path.is_file() or path.suffix.lower() != ".json":
        return False
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(obj, dict) or obj.get("case_id") != pred.get("case_id"):
        return False
    if obj.get("source_commit") != pred.get("source_commit") or obj.get("source_commit") != gold.get("source_commit"):
        return False
    if obj.get("candidate_code_ref") != gold.get("candidate_code_ref") or pred.get("candidate_code_ref") != gold.get("candidate_code_ref"):
        return False
    if obj.get("status") != "completed" or obj.get("result") not in {"pass", "fail"}:
        return False
    if obj["result"] == "fail" and obj.get("failure_type") != "assertion_mismatch":
        return False
    if not all(isinstance(obj.get(key), str) and obj[key].strip() for key in
               ("test_run_id", "test_case_id", "expected", "observed")):
        return False
    return (pred["decision"] == "conforms") == (obj["result"] == "pass")


def _ratio(num: int, den: int) -> float | None:
    return num / den if den else None


def _wilson(success: int, total: int, z: float = 1.96) -> tuple[float, float] | None:
    if total == 0:
        return None
    p = success / total
    d = 1 + z * z / total
    c = (p + z * z / (2 * total)) / d
    h = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / d
    return max(0.0, c - h), min(1.0, c + h)


def _prf(tp: int, fp: int, fn: int) -> dict[str, Any]:
    precision = _ratio(tp, tp + fp)
    recall = _ratio(tp, tp + fn)
    f1 = 2 * precision * recall / (precision + recall) if precision is not None and recall is not None and precision + recall else None
    return {"precision": precision, "recall": recall, "f1": f1}


def evaluate(gold_rows: list[dict[str, Any]], predictions: list[dict[str, Any]], *,
             split: str = "test", evidence_root: Path = Path("."),
             minimum_cases: int = 500, minimum_projects: int = 3,
             minimum_per_class: int = 50) -> dict[str, Any]:
    validate_gold(gold_rows)
    preds = validate_predictions(predictions, {r["case_id"] for r in gold_rows})
    rows = [r for r in gold_rows if r["split"] == split]
    if not rows:
        raise EvaluationError(f"No gold records for split={split!r}")
    if any(r["adjudication_status"] != "adjudicated" for r in rows):
        raise EvaluationError("Selected split includes non-adjudicated gold labels")

    # Pairwise link evaluation across all adjudicated candidate pairs.
    link_tp = link_fp = link_fn = link_tn = link_abstain = 0
    link_reference_mismatch = 0
    for r in rows:
        p = preds.get(r["case_id"], {})
        pred_link = p.get("predicted_link")
        if pred_link is None:
            link_abstain += 1
            if r["gold_link"]:
                link_fn += 1
        elif pred_link is True and r["gold_link"]:
            # A claimed link to the WRONG symbol/revision is not a true
            # positive for the gold candidate pair. Previously the scorer
            # counted any predicted_link=true as a TP, even when its
            # candidate_code_ref/source_commit pointed elsewhere.
            if (p.get("candidate_code_ref") == r["candidate_code_ref"]
                    and p.get("source_commit") == r["source_commit"]):
                link_tp += 1
            else:
                # The true gold edge was missed AND a different edge/revision
                # was asserted. Counting only FN inflates link precision to
                # 100% when every prediction targets the wrong source symbol.
                # A mismatched claimed edge contributes both FP and FN.
                link_fp += 1
                link_fn += 1
                link_reference_mismatch += 1
        elif pred_link is True and not r["gold_link"]:
            link_fp += 1
        elif r["gold_link"]:
            link_fn += 1
        else:
            link_tn += 1

    # Only actually linked, labeled examples have a meaningful code-conformance target.
    eligible = [r for r in rows if r["gold_link"]]
    correct = decided = invalid_evidence = missed = 0
    confusion = {cls: {c: 0 for c in (*OUTCOMES, "abstain")} for cls in OUTCOMES}
    missing_predictions = 0
    predicted_violation = 0
    true_violation_detected = 0
    for r in eligible:
        p = preds.get(r["case_id"])
        if p is None:
            missing_predictions += 1
            p = {}
        decision = p.get("decision", "insufficient_evidence")
        valid = decision in OUTCOMES and p.get("predicted_link") is True and p.get("source_commit") == r["source_commit"] and _evidence_ok(p, r, evidence_root)
        if decision in OUTCOMES and not valid:
            invalid_evidence += 1
        if valid:
            decided += 1
            confusion[r["gold_conformance"]][decision] += 1
            correct += int(decision == r["gold_conformance"])
            predicted_violation += int(decision == "violates")
            true_violation_detected += int(decision == "violates" and r["gold_conformance"] == "violates")
        else:
            missed += 1
            confusion[r["gold_conformance"]]["abstain"] += 1

    class_scores = {}
    for cls in OUTCOMES:
        tp = confusion[cls][cls]
        fp = sum(confusion[other][cls] for other in OUTCOMES if other != cls)
        fn = sum(count for predicted, count in confusion[cls].items() if predicted != cls)
        class_scores[cls] = _prf(tp, fp, fn)
    f1_values = [v["f1"] for v in class_scores.values()]
    macro_f1 = sum(v if v is not None else 0 for v in f1_values) / len(f1_values)
    accuracy = _ratio(correct, len(eligible))
    decided_accuracy = _ratio(correct, decided)
    violation_precision = class_scores["violates"]["precision"]
    violation_recall = class_scores["violates"]["recall"]
    test_projects = len({r["project_id"] for r in eligible})
    categories = Counter(r["gold_conformance"] for r in eligible)
    all_real = all(r["dataset_status"] == "real_adjudicated" for r in rows)
    eligible_gate = (split == "test" and all_real and len(eligible) >= minimum_cases
                     and test_projects >= minimum_projects
                     and all(categories[c] >= minimum_per_class for c in OUTCOMES)
                     and sum(not r["gold_link"] for r in rows) >= minimum_per_class)
    link_precision = _prf(link_tp, link_fp, link_fn)["precision"]
    link_recall = _prf(link_tp, link_fp, link_fn)["recall"]
    # Conformance accuracy alone must not certify a requirement-to-CODE
    # verifier whose trace links are unreliable. A method could otherwise
    # pass while predicting a link for every unlinked candidate pair.
    meets = (eligible_gate and accuracy is not None and accuracy >= 0.95
             and link_precision is not None and link_precision >= 0.95
             and link_recall is not None and link_recall >= 0.95
             and violation_precision is not None and violation_precision >= 0.95
             and violation_recall is not None and violation_recall >= 0.90
             and _ratio(decided, len(eligible)) is not None and _ratio(decided, len(eligible)) >= 0.70)

    return {
        "benchmark": "SRS Guardian 2.0 — requirement-to-code evidence-grounded verification",
        "split": split,
        "source_fingerprint": hashlib.sha256(json.dumps(sorted(gold_rows, key=lambda r: r["case_id"]), sort_keys=True).encode()).hexdigest(),
        "gold_cases_in_split": len(rows),
        "conformance_eligible": len(eligible),
        "projects_in_conformance": test_projects,
        "class_distribution": dict(categories),
        "dataset_real_adjudicated": all_real,
        "link_pairwise": {**_prf(link_tp, link_fp, link_fn), "tp": link_tp, "fp": link_fp, "fn": link_fn, "tn": link_tn,
                            "abstained": link_abstain, "reference_mismatch_count": link_reference_mismatch,
                            "coverage": _ratio(len(rows) - link_abstain, len(rows))},
        "conformance": {
            "accuracy_full_denominator_abstentions_wrong": accuracy,
            "accuracy_wilson_95_interval": _wilson(correct, len(eligible)),
            "accuracy_decided_only": decided_accuracy,
            "coverage": _ratio(decided, len(eligible)),
            "macro_f1_including_abstention_misses": macro_f1,
            "violation_precision": violation_precision,
            "violation_recall": violation_recall,
            "per_class": class_scores,
            "confusion_with_abstention": confusion,
            "correct": correct,
            "decided": decided,
            "abstained_or_invalid": missed,
            "invalid_evidence_count": invalid_evidence,
            "missing_predictions_count": missing_predictions,
        },
        "acceptance": {
            "eligible": eligible_gate,
            "passed": bool(meets),
            "status": "PASSED" if meets else "NOT_MET" if eligible_gate else "NOT_ELIGIBLE",
            "targets": {"full_accuracy": 0.95, "link_precision": 0.95, "link_recall": 0.95,
                        "violation_precision": 0.95,
                        "violation_recall": 0.90, "coverage": 0.70,
                        "minimum_conformance_cases": minimum_cases, "minimum_projects": minimum_projects,
                        "minimum_cases_per_conformance_class": minimum_per_class,
                        "minimum_unlinked_pairs": minimum_per_class},
        },
        "limitations": [
            "The evaluator does not execute tests; it checks that recorded evidence artifacts exist and agree with submitted decisions.",
            "The evidence artifact is not cryptographically authenticated; an independent test runner and audit are required.",
            "An acceptance pass is a benchmark result on the stated scope, not proof of correctness for arbitrary software.",
            "Synthetic fixtures, non-test splits, missing evidence and small samples cannot satisfy the acceptance gate.",
            "Link metrics require the exact gold candidate code reference and source commit; the acceptance gate requires >=95% link precision and recall.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gold", type=Path, required=True)
    p.add_argument("--predictions", type=Path, required=True)
    p.add_argument("--evidence-root", type=Path, default=Path("."))
    p.add_argument("--split", choices=["train", "validation", "test", "dev"], default="test")
    p.add_argument("--output", type=Path, help="Optional JSON report path")
    args = p.parse_args(argv)
    try:
        report = evaluate(read_jsonl(args.gold), read_jsonl(args.predictions), split=args.split,
                          evidence_root=args.evidence_root)
    except EvaluationError as exc:
        p.error(str(exc))
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())