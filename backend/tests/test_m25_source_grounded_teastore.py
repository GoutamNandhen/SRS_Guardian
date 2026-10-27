"""M25 tests: no untrusted execution, no label leakage, no invented conformance."""
import copy
import hashlib

import pytest

from backend.evaluation.m25_source_grounded_teastore import (
    EvidenceError, NO_CONFORMANCE, evaluate_cohort, rank_source, score_ranked,
    source_index,
)
from backend.evaluation.m23_teastore_external import CODE_FILES, DOC_FILES


def _sources():
    return {
        "src/registry/Registry.java":
            b"public class Registry { void registerService() { registerService(); } }",
        "src/auth/Security.java":
            b"public class Security { boolean checkPassword() { return true; } }",
    }


def test_source_rank_reads_java_bodies_not_paths():
    ranked = rank_source("register service", _sources())
    assert ranked[0] == "src/registry/Registry.java"
    assert len(ranked) == len(set(ranked))


def test_empty_query_returns_abstention_not_fabricated_match():
    assert rank_source("   ", _sources()) == []


def test_non_java_and_invalid_utf8_fail_closed():
    with pytest.raises(EvidenceError):
        rank_source("service", {"source.py": b"print(1)"})
    with pytest.raises(EvidenceError):
        rank_source("service", {"source.java": b"\xff"})


def test_source_rank_deterministic_across_input_order():
    sources = _sources()
    assert rank_source("password", sources) == rank_source(
        "password", dict(reversed(list(sources.items())))
    )


def test_scoring_only_observed_positives_no_false_negative_inference():
    paths = {"src/registry/Registry.java", "src/auth/Security.java"}
    score = score_ranked(["src/auth/Security.java"], set(), paths)
    assert score["observed_positive_hits_at_k"]["1"] == 0
    assert "false_positive" not in score and "true_negative" not in score
    with pytest.raises(EvidenceError):
        score_ranked(["other.java"], set(), paths)
    with pytest.raises(EvidenceError):
        score_ranked(["src/auth/Security.java"] * 2, set(), paths)


def test_rankings_independent_of_observed_link_labels():
    sources = _sources()
    reqs = [{"id": "R1", "text": "register service",
             "observed_paths": ["src/registry/Registry.java"]}]
    first = evaluate_cohort(reqs, sources)
    changed = copy.deepcopy(reqs)
    changed[0]["observed_paths"] = ["src/auth/Security.java"]
    second = evaluate_cohort(changed, sources)
    assert [x["cases"][0]["ranked_paths"] for x in first["runs"]] == [
        x["cases"][0]["ranked_paths"] for x in second["runs"]
    ]
    assert first["runs"][0]["observed_positive_links_unverified"] == 1
    assert all(x["conformance_accuracy"] is None for x in first["runs"])
    assert all(x["violation_precision"] is None for x in first["runs"])
    assert all(x["violation_recall"] is None for x in first["runs"])


def test_source_index_rejects_missing_pinned_evidence():
    with pytest.raises(EvidenceError):
        source_index({}, {}, {"queue": []})


def test_source_index_rejects_tampered_file_without_download():
    docs = {p: b"tampered" for p in DOC_FILES}
    code = {p: b"tampered" for p in CODE_FILES}
    with pytest.raises(EvidenceError, match="Source hash mismatch"):
        source_index(docs, code, {"queue": []})


def test_no_conformance_metrics_ever_inferred_from_observed_links():
    assert all(NO_CONFORMANCE[key] is None for key in (
        "conformance_accuracy", "violation_precision", "violation_recall",
        "conformance_coverage"
    ))
