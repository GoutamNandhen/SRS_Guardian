"""M18: synthetic adversarial tests for project-wise link-negative coverage.

No external labels, source verification or independently measured accuracy.
All provenance strings and test evidence in the helper are fabricated.
"""
from backend.tests.test_m17_project_robustness import mock_project_benchmark


def test_balanced_projects_have_both_link_classes_and_pass_arithmetic(tmp_path):
    report = mock_project_benchmark(tmp_path, [167, 167, 166])
    robust = report["project_robustness"]["mockA"]
    assert robust["gate_passed"] is True
    assert len(robust["projects"]) == 3
    assert report["project_robustness_policy"]["minimum_unlinked_per_project"] == 10
    for project in robust["projects"].values():
        assert project["unlinked"] == 20
        assert project["unlinked_correctly_rejected"] == 20
        assert project["unlinked_false_link_claims"] == 0
        assert project["unlinked_rejection_rate"] == 1.0
        assert project["link_prediction_coverage"] == 1.0
    assert report["systems"]["mockA"]["acceptance"]["status"] == "PASSED"


def test_pooled_negative_cases_cannot_hide_projects_without_negatives(tmp_path):
    # The older M17 benchmark would have accepted this synthetic arrangement:
    # 500 perfectly classified linked cases, 50 negatives in project 0, and
    # ZERO negative candidates in projects 1 and 2.
    report = mock_project_benchmark(
        tmp_path, [167, 167, 166], unlinked_supports=(50, 0, 0),
    )
    robust = report["project_robustness"]["mockA"]
    assert robust["project_macro_accuracy"] == 1.0
    assert robust["worst_project_accuracy"] == 1.0
    assert robust["gate_passed"] is False
    assert robust["projects"]["MOCK-PROJECT-1"]["unlinked"] == 0
    assert robust["projects"]["MOCK-PROJECT-1"]["unlinked_rejection_rate"] is None
    assert robust["projects"]["MOCK-PROJECT-1"]["support_sufficient"] is False
    assert report["systems"]["mockA"]["acceptance"]["status"] == "BLOCKED_BY_M17_PROJECT_ROBUSTNESS"


def test_unlinked_only_project_is_not_silently_dropped(tmp_path):
    # M1 still sees three valid linked projects, but a fourth project has
    # only unlinked candidate pairs. M18 must enumerate and fail it.
    report = mock_project_benchmark(
        tmp_path, [167, 167, 166], extra_unlinked_project=20,
    )
    robust = report["project_robustness"]["mockA"]
    assert len(robust["projects"]) == 4
    only_negative = robust["projects"]["MOCK-PROJECT-3"]
    assert only_negative["linked"] == 0
    assert only_negative["unlinked"] == 20
    assert only_negative["accuracy_full_denominator"] is None
    assert only_negative["support_sufficient"] is False
    assert robust["project_macro_accuracy"] is None
    assert robust["worst_project_accuracy"] is None
    assert robust["gate_passed"] is False
    assert report["systems"]["mockA"]["acceptance"]["status"] == "BLOCKED_BY_M17_PROJECT_ROBUSTNESS"


def test_minimum_unlinked_support_applies_to_each_project(tmp_path):
    report = mock_project_benchmark(
        tmp_path, [167, 167, 166], unlinked_supports=(40, 9, 11),
    )
    robust = report["project_robustness"]["mockA"]
    assert robust["projects"]["MOCK-PROJECT-1"]["unlinked"] == 9
    assert robust["projects"]["MOCK-PROJECT-1"]["support_sufficient"] is False
    assert robust["projects"]["MOCK-PROJECT-2"]["support_sufficient"] is True
    assert robust["gate_passed"] is False
