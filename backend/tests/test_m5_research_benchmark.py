"""Tests of M5 leakage, provenance, evidence comparison and honest synthetic gating."""
from __future__ import annotations

import json
import asyncio
from pathlib import Path

import pytest

from backend.evaluation.evaluate_conformance import EvaluationError
from backend.evaluation.m5_research_benchmark import (
    audit_benchmark, canonical_digest, compare_systems,
)
from backend.evaluation.m5_controlled_pilot import (
    _case_amounts, approved_fixture, run_one, run_pilot,
)


def make_gold(case_id: str, project: str = "bank", split: str = "test", truth="violates",
              dataset="synthetic_fixture") -> dict:
    return {
        "case_id": case_id, "project_id": project, "split": split,
        "requirement_id": f"R-{case_id}",
        "requirement_text": f"The system shall reject {case_id} transfers exceeding 10000 rupees",
        "candidate_code_ref": f"api/{case_id}.py::transfer", "source_commit": "a" * 40,
        "annotation_source": "author constructed simulation",
        "adjudication_status": "adjudicated", "dataset_status": dataset,
        "gold_link": True, "gold_conformance": truth,
    }


def make_pred(g: dict, folder: Path, *, decision="violates", good_evidence=True) -> dict:
    artifact = {
        "case_id": g["case_id"], "candidate_code_ref": g["candidate_code_ref"],
        "source_commit": g["source_commit"], "test_run_id": "fixture-run",
        "test_case_id": "boundary-check", "status": "completed",
        "result": "fail" if decision == "violates" else "pass",
        "failure_type": "assertion_mismatch" if decision == "violates" else None,
        "expected": "rejected", "observed": "accepted",
    }
    if not good_evidence:
        artifact["source_commit"] = "b" * 40
    path = folder / (g["case_id"] + ".json")
    path.write_text(json.dumps(artifact), encoding="utf-8")
    return {
        "case_id": g["case_id"], "predicted_link": True, "decision": decision,
        "source_commit": g["source_commit"], "candidate_code_ref": g["candidate_code_ref"],
        "evidence_path": path.name,
    }


def test_fingerprint_lock_and_synthetic_gate():
    gold = [make_gold("A")]
    digest = canonical_digest(gold)
    a = audit_benchmark(gold, expected_sha256=digest)
    assert a["source_kinds"] == {"synthetic_fixture": 1}
    assert a["research_eligible_by_provenance"] is False
    with pytest.raises(EvaluationError, match="fingerprint"):
        audit_benchmark(gold, expected_sha256="0"*64)


def test_m1_project_leakage_still_rejected():
    gold = [make_gold("A", project="same", split="train"),
            make_gold("B", project="same", split="test")]
    with pytest.raises(EvaluationError, match="Project leakage"):
        audit_benchmark(gold)


def test_cross_split_same_code_ref_rejected():
    a = make_gold("A", "project1", "train")
    b = make_gold("B", "project2", "test")
    b["candidate_code_ref"] = a["candidate_code_ref"]
    out = audit_benchmark([a, b])
    assert "Same code snapshot" in out["critical_issues"][0]


def test_claimed_real_rows_need_review_provenance():
    data = [make_gold("A", dataset="real_adjudicated")]
    a = audit_benchmark(data)
    assert a["critical_issues"]
    assert a["research_eligible_by_provenance"] is False


def test_provenance_separate_annotators_needed():
    g = make_gold("A", dataset="real_adjudicated")
    for key in (
        "public_source_url", "source_license", "code_snapshot_sha256",
        "annotator_1", "annotator_2", "adjudication_record",
        "oracle_provenance", "reproduction_instructions",
    ):
        g[key] = "a" * 64 if key == "code_snapshot_sha256" else "example"
    a = audit_benchmark([g])
    assert any("independent" in error for error in a["critical_issues"])
    g["annotator_2"] = "different person"
    assert not audit_benchmark([g])["critical_issues"]


def test_near_duplicate_cross_split_is_warned():
    a = make_gold("A", "one", "train")
    b = make_gold("B", "two", "test")
    a["requirement_text"] = "The service shall reject transfers above eight thousand rupees for customers"
    b["requirement_text"] = "The service shall reject transfers above eight thousand rupees for customers today"
    audit = audit_benchmark([a,b])
    assert audit["warnings"]


def test_comparison_requires_two_methods(tmp_path):
    gold = [make_gold("A")]
    with pytest.raises(EvaluationError, match="at least two"):
        compare_systems(gold, {"single": []}, evidence_roots={"single":tmp_path})


def test_pairwise_counts_and_bad_evidence(tmp_path):
    gold = [make_gold("A", truth="violates"), make_gold("B", truth="conforms")]
    one = tmp_path / "one"; two = tmp_path / "two"
    one.mkdir(); two.mkdir()
    predictions_a = [make_pred(gold[0], one), make_pred(gold[1], one, decision="conforms")]
    predictions_b = [make_pred(gold[0], two, good_evidence=False),
                     make_pred(gold[1], two, decision="conforms")]
    r = compare_systems(gold, {"A":predictions_a,"B":predictions_b},
                        evidence_roots={"A":one,"B":two})
    assert r["systems"]["A"]["conformance"]["accuracy_full_denominator_abstentions_wrong"] == 1.0
    assert r["systems"]["A"]["acceptance"]["status"] == "BLOCKED_BY_M5_PROVENANCE_OR_LOCK"
    assert r["systems"]["B"]["conformance"]["invalid_evidence_count"] == 1
    assert r["paired"]["A__vs__B"]["only_first_correct"] == 1
    assert r["status"] == "COMPARISON_ONLY_NOT_PUBLICATION_READY"


def test_real_http_pilot_catches_narrow_plus_two_violation():
    app = approved_fixture(10000, "accept_at_plus_2")
    old = asyncio.run(run_one(app, 10000, "m3_two_probes"))
    new = asyncio.run(run_one(app, 10000, "m5_three_probes"))
    assert old["decision"] == "conforms_on_probes_only"
    assert new["decision"] == "violates"
    assert new["observations"][1]["observed_accepted"] is True


def test_pilot_never_qualified_as_real_accuracy():
    report = asyncio.run(run_pilot())
    assert report["fixture_count"] == 20
    assert report["benchmark_95_eligible"] is False
    assert report["method_comparison"]["m3_two_probes"]["fn"] == 5
    assert report["method_comparison"]["m5_three_probes"]["fn"] == 0
    assert all(x["pilot_type"] != "real_adjudicated" for x in [report])


def test_case_budget_is_bounded_and_distinct():
    for t in (2500,5000,10000):
        assert _case_amounts(t,"m5_three_probes")[0] == t+1
        assert len(set(_case_amounts(t,"m5_three_probes"))) == 3
