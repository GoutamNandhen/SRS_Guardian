"""M19 adversarial regression: negative-link abstention and false-claim loopholes.

All 500 linked cases and 60 negative pairs are SYNTHETIC mock data.
These tests prove scorer arithmetic only; they are not research measurements.
"""
from backend.tests.test_m17_project_robustness import mock_project_benchmark


def test_balanced_mock_negative_rejections_pass_arithmetic(tmp_path):
    result = mock_project_benchmark(tmp_path, [167, 167, 166])
    robust = result["project_robustness"]["mockA"]
    assert robust["m19_negative_link_performance_passed"] is True
    assert robust["gate_passed"] is True
    assert result["project_robustness_policy"]["minimum_unlinked_decision_coverage_per_project"] == 0.95
    assert result["project_robustness_policy"]["minimum_unlinked_rejection_rate_per_project"] == 0.90
    assert all(p["unlinked_decision_coverage"] == 1.0 for p in robust["projects"].values())
    assert all(p["unlinked_abstentions"] == 0 for p in robust["projects"].values())
    assert result["systems"]["mockA"]["acceptance"]["status"] == "PASSED"


def test_all_negative_abstentions_in_one_project_cannot_hide_behind_global_metrics(tmp_path):
    result = mock_project_benchmark(
        tmp_path, [167, 167, 166],
        unlinked_prediction_modes=("reject", "abstain", "reject", "reject"),
    )
    system = result["systems"]["mockA"]
    assert system["conformance"]["accuracy_full_denominator_abstentions_wrong"] == 1.0
    assert system["links"]["precision"] == 1.0
    assert system["links"]["recall"] == 1.0
    assert system["links"]["coverage"] > 0.95
    robust = result["project_robustness"]["mockA"]
    assert robust["m17_conformance_gate_passed"] is True
    assert robust["m18_negative_link_gate_passed"] is True
    assert robust["m19_negative_link_performance_passed"] is False
    project = robust["projects"]["MOCK-PROJECT-1"]
    assert project["unlinked"] == 20
    assert project["unlinked_abstentions"] == 20
    assert project["unlinked_decision_coverage"] == 0.0
    assert project["unlinked_rejection_rate"] == 0.0
    assert system["acceptance"]["passed"] is False
    assert system["acceptance"]["status"] == "BLOCKED_BY_M19_PROJECT_NEGATIVE_LINK_PERFORMANCE"


def test_all_false_link_claims_in_one_project_cannot_hide_behind_pooled_precision(tmp_path):
    result = mock_project_benchmark(
        tmp_path, [167, 167, 166],
        unlinked_prediction_modes=("reject", "claim", "reject", "reject"),
    )
    system = result["systems"]["mockA"]
    assert system["conformance"]["accuracy_full_denominator_abstentions_wrong"] == 1.0
    assert system["links"]["precision"] >= 0.95  # 500 / (500 + 20)
    assert system["links"]["recall"] == 1.0
    robust = result["project_robustness"]["mockA"]
    assert robust["m17_conformance_gate_passed"] is True
    assert robust["m18_negative_link_gate_passed"] is True
    assert robust["m19_negative_link_performance_passed"] is False
    project = robust["projects"]["MOCK-PROJECT-1"]
    assert project["unlinked_decision_coverage"] == 1.0
    assert project["unlinked_false_link_claims"] == 20
    assert project["unlinked_rejection_rate"] == 0.0
    assert system["acceptance"]["passed"] is False
    assert system["acceptance"]["status"] == "BLOCKED_BY_M19_PROJECT_NEGATIVE_LINK_PERFORMANCE"
