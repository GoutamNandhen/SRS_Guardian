"""M24 offline tests; actual pinned TeaStore fetch and scoring run in CI."""
from __future__ import annotations

import copy
import pytest

from backend.evaluation.m23_teastore_external import CODE_COMMIT, PROJECT_ID
from backend.evaluation.m24_cross_corpus_baseline import (
    BaselineError, _cohort, _teastore_cohort, evaluate, NO_CONFORMANCE,
)


def fixture():
    paths = [
        "src/RegistryREST.java", "src/Registry.java",
        "src/RecommenderSelector.java", "src/IRecommender.java",
        "src/ShaSecurityProvider.java",
    ]
    reqs = [
        {"requirement_id": "SAD_001", "requirement_text": "The registry registers services"},
        {"requirement_id": "SAD_027", "requirement_text": "A recommender selects algorithms"},
        {"requirement_id": "SAD_028", "requirement_text": "A recommender provides recommendations"},
    ]
    symbols = [{"symbol_id": f"JAVA_{i:03d}", "source_path": p,
                "qualified_name": p.rsplit("/", 1)[-1].replace(".java", ""),
                "description": ""} for i, p in enumerate(paths, 1)]
    links = [
        {"requirement_id": rid, "symbol_id": sid}
        for rid, sids in (
            ("SAD_001", ("JAVA_001", "JAVA_002")),
            ("SAD_027", ("JAVA_003", "JAVA_004")),
            ("SAD_028", ("JAVA_003", "JAVA_004")))
        for sid in sids
    ]
    universe = {
        "schema_version": "m20-candidate-universe-1",
        "project_id": PROJECT_ID, "source_commit": CODE_COMMIT,
        "code_snapshot_sha256": "a" * 64,
        "requirements": reqs, "symbols": symbols, "observed_links": links,
    }
    evidence = {
        "schema_version": "m23-teastore-external-evidence-1",
        "code_commit": CODE_COMMIT, "source_subset_sha256": "a" * 64,
        "licenses_verified_by_pinned_git_blob": True,
        "independently_reviewed_link_pairs": 0, "research_95_eligible": False,
    }
    v = {
        "version": "V0", "candidate_code_paths": paths,
        "requirements": [
            {"requirement_id": "REQ-1", "text": "Register services",
             "observed_link_paths": [paths[0]]},
            {"requirement_id": "REQ-2", "text": "Unknown mapping",
             "observed_link_paths": []},
        ],
    }
    dronology = {
        "schema_version": "m6-external-trace-v1",
        "no_negative_labels": True, "_fixture_sha256": "b" * 64,
        "versions": [v, {**v, "version": "V1"}],
    }
    return dronology, universe, evidence


def test_two_distinct_projects_three_cohorts_and_no_conformance_claim():
    result = evaluate(*fixture())
    assert result["independent_project_count"] == 2
    assert result["evaluation_cohorts"] == 3
    assert len(result["runs"]) == 6
    assert result["independently_adjudicated_link_pairs"] == 0
    assert result["independently_adjudicated_conformance_cases"] == 0
    assert result["research_95_eligible"] is False
    assert all(result[k] is None for k in NO_CONFORMANCE)
    assert all(all(run[k] is None for k in NO_CONFORMANCE) for run in result["runs"])


def test_observed_positive_recall_uses_only_known_links_not_absent_links():
    paths = ["code/registry/Register.java", "code/billing/Billing.java"]
    r = _cohort("Test", "v1", [
        {"id": "REQ-1", "text": "Register", "observed_paths": [paths[0]]},
        {"id": "REQ-2", "text": "No observed link", "observed_paths": []},
    ], paths, "path_bm25")
    assert r["total_statements"] == 2
    assert r["statements_with_observed_positive"] == 1
    assert r["statements_without_observed_positive_unknown"] == 1
    assert r["observed_positive_links_unverified"] == 1
    assert r["observed_positive_link_recall_at_k"]["1"] == 1.0
    assert r["has_true_negative_labels"] is False


def test_no_known_links_produces_null_recall_not_false_accuracy():
    r = _cohort("Test", "v1", [
        {"id": "R1", "text": "some requirement", "observed_paths": []},
    ], ["src/One.java"], "path_bm25")
    assert r["hit_at_k_among_observed_linked_statements"]["1"] is None
    assert r["observed_positive_link_recall_at_k"]["5"] is None
    assert r["conformance_accuracy"] is None


def test_tea_store_manifest_and_source_digest_must_match():
    _, universe, evidence = fixture()
    _teastore_cohort(universe, evidence)
    forged = dict(evidence, source_subset_sha256="f" * 64)
    with pytest.raises(BaselineError, match="mismatch"):
        _teastore_cohort(universe, forged)
    forged = dict(evidence, licenses_verified_by_pinned_git_blob=False)
    with pytest.raises(BaselineError, match="mismatch"):
        _teastore_cohort(universe, forged)


def test_published_links_never_silently_promoted_to_gold():
    _, universe, evidence = fixture()
    forged = dict(evidence, independently_reviewed_link_pairs=15)
    with pytest.raises(BaselineError, match="independent gold"):
        _teastore_cohort(universe, forged)


def test_bad_or_duplicated_candidates_fail_closed():
    paths = ["src/A.java", "src/A.java"]
    with pytest.raises(BaselineError, match="duplicate"):
        _cohort("X", "v1", [{"id": "R", "text": "a", "observed_paths": []}],
                paths, "path_bm25")
    with pytest.raises(BaselineError, match="outside"):
        _cohort("X", "v1", [{"id": "R", "text": "a", "observed_paths": ["src/Z.java"]}],
                ["src/A.java"], "path_bm25")


def test_observed_labels_not_used_to_rank_or_choose_hyperparameters():
    paths = ["code/Registry.java", "code/Other.java"]
    req = [{"id": "R", "text": "registry", "observed_paths": [paths[0]]}]
    a = _cohort("X", "v1", req, paths, "path_bm25")
    modified = copy.deepcopy(req)
    modified[0]["observed_paths"] = [paths[1]]
    b = _cohort("X", "v1", modified, paths, "path_bm25")
    assert a["cases"][0]["returned_candidate_count"] == b["cases"][0]["returned_candidate_count"]
    assert a["ranking_nonempty_statement_count"] == b["ranking_nonempty_statement_count"]
