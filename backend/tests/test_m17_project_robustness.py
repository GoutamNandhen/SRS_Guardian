"""M17 regression: independent-project support and project-balanced accuracy gate.

All cases, provenance strings, labels, and evidence are MOCK fixtures.
Even when their metadata says 'real_adjudicated' to exercise the gate,
these tests DO NOT constitute real-world validation or 95% evidence.
"""
from __future__ import annotations

import hashlib

from backend.evaluation.m5_research_benchmark import canonical_digest, compare_systems
from backend.tests.test_m5_research_benchmark import make_gold, make_pred


def mock_project_benchmark(tmp_path, supports, *, wrong_on=None,
                           unlinked_supports=(20, 20, 20),
                           extra_unlinked_project=0):
    assert len(supports) == 3 and sum(supports) == 500
    gold = []
    predictions = []
    for project_index, n in enumerate(supports):
        project = f"MOCK-PROJECT-{project_index}"
        for i in range(n):
            label = "conforms" if i % 2 == 0 else "violates"
            row = make_gold(f"{project}-{i:04d}", project=project, truth=label,
                            dataset="real_adjudicated")
            row.update({
                "annotation_source": "MOCK_ONLY_NOT_EXTERNAL",
                "public_source_url": "MOCK_ONLY_NOT_A_PUBLIC_SOURCE",
                "source_license": "MOCK_ONLY",
                "code_snapshot_sha256": hashlib.sha256(project.encode()).hexdigest(),
                "annotator_1": "MOCK_A", "annotator_2": "MOCK_B",
                "adjudication_record": "MOCK_ADJUDICATION",
                "oracle_provenance": "MOCK_ORACLE",
                "reproduction_instructions": "MOCK_NOT_REPRODUCIBLE",
            })
            gold.append(row)
            # In the small project, deliberately misclassify 10 conforming
            # cases as violations, keeping valid but fabricated evidence.
            wrong = wrong_on == project_index and i < 20 and i % 2 == 0
            verdict = "violates" if wrong else label
            predictions.append(make_pred(row, tmp_path, decision=verdict))
    # Each mock project now includes link-negative candidates. M18 checks
    # these explicitly; their labels and evidence are entirely synthetic.
    assert len(unlinked_supports) == 3
    for project_index, n in enumerate((*unlinked_supports, extra_unlinked_project)):
        project = f"MOCK-PROJECT-{project_index}"
        for i in range(n):
            row = make_gold(f"MOCK-UNLINKED-{project_index}-{i}", project=project,
                            dataset="real_adjudicated")
            row.update({
                "gold_link": False, "gold_conformance": None,
                "annotation_source": "MOCK_ONLY_NOT_EXTERNAL",
                "public_source_url": "MOCK_ONLY_NOT_A_PUBLIC_SOURCE",
                "source_license": "MOCK_ONLY",
                "code_snapshot_sha256": hashlib.sha256(project.encode()).hexdigest(),
                "annotator_1": "MOCK_A", "annotator_2": "MOCK_B",
                "adjudication_record": "MOCK_ADJUDICATION",
                "oracle_provenance": "MOCK_ORACLE",
                "reproduction_instructions": "MOCK_NOT_REPRODUCIBLE",
            })
            gold.append(row)
            predictions.append({"case_id": row["case_id"], "predicted_link": False})
    # Identical mock methods are intentional: we test a gate, not systems.
    return compare_systems(
        gold, {"mockA": predictions, "mockB": predictions},
        evidence_roots={"mockA": tmp_path, "mockB": tmp_path},
        benchmark_lock=canonical_digest(gold),
    )


def test_balanced_mock_projects_pass_m17_arithmetic_only(tmp_path):
    result = mock_project_benchmark(tmp_path, [167, 167, 166])
    robust = result["project_robustness"]["mockA"]
    assert robust["minimum_support_met"] is True
    assert robust["project_macro_accuracy"] == 1.0
    assert robust["worst_project_accuracy"] == 1.0
    assert robust["gate_passed"] is True
    # MOCK metadata and evidence: NEVER interpret as an empirical result.
    assert result["systems"]["mockA"]["acceptance"]["status"] == "PASSED"


def test_one_dominant_project_cannot_hide_unsupported_projects(tmp_path):
    result = mock_project_benchmark(tmp_path, [490, 5, 5])
    assert result["systems"]["mockA"]["conformance"]["accuracy_full_denominator_abstentions_wrong"] == 1.0
    robust = result["project_robustness"]["mockA"]
    assert robust["minimum_support_met"] is False
    assert robust["gate_passed"] is False
    assert result["systems"]["mockA"]["acceptance"]["status"] == "BLOCKED_BY_M17_PROJECT_ROBUSTNESS"
    assert result["systems"]["mockA"]["acceptance"]["passed"] is False


def test_global_98_percent_cannot_hide_80_percent_small_project(tmp_path):
    result = mock_project_benchmark(tmp_path, [225, 225, 50], wrong_on=2)
    conf = result["systems"]["mockA"]["conformance"]
    assert conf["accuracy_full_denominator_abstentions_wrong"] == 0.98
    assert conf["violation_precision"] >= 0.95
    assert conf["violation_recall"] >= 0.90
    robust = result["project_robustness"]["mockA"]
    assert robust["minimum_support_met"] is True
    assert abs(robust["project_macro_accuracy"] - (1 + 1 + 0.8) / 3) < 1e-12
    assert robust["worst_project_accuracy"] == 0.8
    assert robust["gate_passed"] is False
    assert result["systems"]["mockA"]["acceptance"]["status"] == "BLOCKED_BY_M17_PROJECT_ROBUSTNESS"
    assert result["systems"]["mockA"]["acceptance"]["passed"] is False
