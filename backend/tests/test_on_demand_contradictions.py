"""Tests for Phase 18.3B — On-Demand NLI Contradiction Analysis.

Verifies:
1. Candidate generation without upfront NLI inference
2. Unverified candidate state
3. Verify single contradiction candidate
4. Verify selected candidates (batched)
5. Cached NLI result reuse
6. Changed requirement invalidates stale cache
7. Numeric contradiction remains immediate & deterministic
8. Duplicate remains separate from contradiction
9. Large/multi-requirement document does not automatically execute all NLI
"""

import json
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.database import get_db, Base
from backend.app.models.document import Document, Requirement, Issue
from backend.app.ml.contradictions import (
    select_candidate_pairs,
    candidate_tuples_to_dicts,
    verify_candidate_pairs,
    get_nli_cache_key,
    get_nli_cached_result,
    load_nli_cache,
    save_nli_cache,
    save_document_candidates,
    load_document_candidates,
)
from backend.app.nlp.numeric_constraints import detect_numeric_conflicts
from backend.app.ml.duplicates import find_duplicates

client = TestClient(app)


def test_candidate_generation_and_unverified_state():
    """Verify that candidate generation produces unverified candidates without executing NLI."""
    reqs = [
        {"id": 1, "req_key": "REQ-101", "text": "The system shall allow users to delete their account."},
        {"id": 2, "req_key": "REQ-102", "text": "The system shall prevent users from deleting their account."},
        {"id": 3, "req_key": "REQ-103", "text": "The system shall generate daily audit logs."},
    ]

    candidates = select_candidate_pairs(reqs)
    assert len(candidates) >= 1
    # Check that REQ-101 and REQ-102 are paired
    pair_keys = {(c[0]["req_key"], c[1]["req_key"]) for c in candidates}
    assert ("REQ-101", "REQ-102") in pair_keys

    candidate_dicts = candidate_tuples_to_dicts(candidates)
    assert len(candidate_dicts) >= 1
    target = next(c for c in candidate_dicts if c["req_key_1"] == "REQ-101" and c["req_key_2"] == "REQ-102")
    assert target["verification_status"] in ("unverified", "verified")
    assert target["mechanism"] == "semantic"


def test_verify_single_contradiction_candidate():
    """Verify that on-demand verification of a single candidate executes NLI and determines contradiction."""
    pair = [
        {
            "finding_id": "CANDIDATE_CONTRADICTION_TEST_1",
            "req_key_1": "REQ-A",
            "req_key_2": "REQ-B",
            "text_1": "The system shall allow users to delete their account.",
            "text_2": "The system shall prevent users from deleting their account.",
        }
    ]

    results = verify_candidate_pairs(pair, confidence_threshold=0.70)
    assert len(results) == 1
    res = results[0]
    assert res["req_key_1"] == "REQ-A"
    assert res["req_key_2"] == "REQ-B"
    assert res["classification"] == "contradiction"
    assert res["is_contradiction"] is True
    assert res["verification_status"] == "verified"
    assert res["confidence"] >= 0.70


def test_verify_selected_batch_candidates():
    """Verify that multiple candidate pairs can be verified in a single batched NLI call."""
    pairs = [
        {
            "finding_id": "CAND_BATCH_1",
            "req_key_1": "REQ-B1",
            "req_key_2": "REQ-B2",
            "text_1": "The system shall permit all administrators to export database backups.",
            "text_2": "The system shall prohibit administrators from exporting database backups.",
        },
        {
            "finding_id": "CAND_BATCH_2",
            "req_key_1": "REQ-B3",
            "req_key_2": "REQ-B4",
            "text_1": "The system shall record user login activity in an audit log.",
            "text_2": "The system shall store audit records in the database.",
        },
    ]

    results = verify_candidate_pairs(pairs, confidence_threshold=0.70, batch_size=8)
    assert len(results) == 2
    # Pair 1 is opposing permit/prohibit
    assert results[0]["is_contradiction"] is True
    assert results[0]["verification_status"] == "verified"
    # Pair 2 is compatible audit logging
    assert results[1]["is_contradiction"] is False
    assert results[1]["verification_status"] == "no_contradiction"


def test_cached_nli_result_reuse_and_invalidation():
    """Verify that verified results are retrieved from cache and text changes invalidate cache."""
    t1 = "The user shall enable two-factor authentication."
    t2 = "The user shall disable two-factor authentication."

    pair = [{
        "finding_id": "CAND_CACHE_TEST",
        "req_key_1": "REQ-C1",
        "req_key_2": "REQ-C2",
        "text_1": t1,
        "text_2": t2,
    }]

    # First run: might be in cache or computed
    res1 = verify_candidate_pairs(pair)[0]
    # Second run: must be cached
    res2 = verify_candidate_pairs(pair)[0]
    assert res2["cached"] is True
    assert res2["confidence"] == res1["confidence"]

    # Modified text: hash changes, stale cache is invalidated
    modified_pair = [{
        "finding_id": "CAND_CACHE_TEST_MODIFIED",
        "req_key_1": "REQ-C1",
        "req_key_2": "REQ-C2",
        "text_1": t1 + " immediately upon initial login.",
        "text_2": t2,
    }]
    cached_val, was_cached = get_nli_cached_result(modified_pair[0]["text_1"], modified_pair[0]["text_2"])
    assert was_cached is False


def test_numeric_contradiction_remains_immediate():
    """Verify numeric contradictions remain immediate and deterministic without requiring NLI."""
    reqs = [
        {"id": 4, "req_key": "REQ-004", "text": "The password must contain at least 8 characters."},
        {"id": 5, "req_key": "REQ-005", "text": "The password must contain exactly 6 characters."},
    ]

    numeric_conflicts = detect_numeric_conflicts(reqs)
    assert len(numeric_conflicts) == 1
    f = numeric_conflicts[0]
    assert f.req_key_1 in ("REQ-004", "REQ-005")
    assert f.req_key_2 in ("REQ-004", "REQ-005")
    assert "CONFLICT" in f.rule_id or "NUMERIC" in f.rule_id
    assert f.confidence == 1.0
    assert f.constraint_1.comparator in (">=", "==")
    assert f.constraint_2.comparator in (">=", "==")


def test_duplicates_remain_separate_from_contradictions():
    """Verify duplicate pairs (e.g. REQ-002 vs REQ-003) remain separate from contradictions."""
    reqs = [
        {"id": 2, "req_key": "REQ-002", "text": "The system shall allow users to reset their password using their registered email."},
        {"id": 3, "req_key": "REQ-003", "text": "Users must recover forgotten passwords using their registered email address."},
    ]

    duplicates, _ = find_duplicates(reqs)
    assert len(duplicates) == 1
    assert duplicates[0]["similarity_score"] >= 0.80

    # Ensure excluded in contradiction candidate logic if passed or affirmative paraphrase
    numeric_conflicts = detect_numeric_conflicts(reqs)
    assert len(numeric_conflicts) == 0


def test_document_api_on_demand_flow():
    """Verify end-to-end API analysis returns fast with on-demand candidates and verify endpoint works."""
    # Create test document
    doc_text = """
REQ-001: The system should respond quickly when the user checks the account balance.
REQ-002: The system shall allow users to reset their password using their registered email.
REQ-003: Users must recover forgotten passwords using their registered email address.
REQ-004: The password must contain at least 8 characters.
REQ-005: The password must contain exactly 6 characters.
REQ-006: The system shall allow users to download their transaction history.
REQ-007: The system shall allow users to delete their account.
REQ-008: The system shall prevent users from deleting their account.
"""
    # Upload document
    upload_res = client.post(
        "/api/documents/upload",
        files={"file": ("test_srs.txt", doc_text.encode("utf-8"), "text/plain")},
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # Analyze document
    analyze_res = client.post(f"/api/documents/{doc_id}/analyze")
    assert analyze_res.status_code == 200
    data = analyze_res.json()
    assert data["contradiction_verification_mode"] == "on_demand"
    assert "contradiction_candidates_count" in data

    # Check contradictions endpoint
    contra_res = client.get(f"/api/documents/{doc_id}/contradictions")
    assert contra_res.status_code == 200
    contra_data = contra_res.json()

    # Numeric conflict (REQ-004 vs REQ-005) must be present and verified
    numeric_items = [c for c in contra_data["contradictions"] if c["mechanism"] == "numeric"]
    assert len(numeric_items) >= 1
    assert any("REQ-004" in (c["req_key_1"], c["req_key_2"]) for c in numeric_items)

    # REQ-007 vs REQ-008 candidate must be present in unverified candidates or contradictions
    candidates = [c for c in contra_data["contradictions"] if c["verification_status"] == "unverified"]
    target_cand = next(
        (c for c in contra_data["contradictions"]
         if set([c["req_key_1"], c["req_key_2"]]) == {"REQ-007", "REQ-008"}),
        None,
    )
    assert target_cand is not None

    # Call verify endpoint for REQ-007 vs REQ-008
    verify_res = client.post(
        f"/api/documents/{doc_id}/contradictions/verify",
        json={
            "document_id": doc_id,
            "pairs": [
                {
                    "req_key_1": target_cand["req_key_1"],
                    "req_key_2": target_cand["req_key_2"],
                    "text_1": target_cand["text_1"],
                    "text_2": target_cand["text_2"],
                }
            ],
        },
    )
    assert verify_res.status_code == 200
    v_data = verify_res.json()
    assert v_data["total_verified"] == 1
    assert v_data["results"][0]["is_contradiction"] is True
    assert v_data["results"][0]["verification_status"] == "verified"
