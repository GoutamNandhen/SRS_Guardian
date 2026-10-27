"""M20 queue reproducibility and blind-labeling safety tests (synthetic inputs only)."""
import copy
import hashlib
import json

import pytest

from backend.evaluation.m20_annotation_queue import QueueError, build_queue, write_outputs


def universe():
    return {
        "schema_version": "m20-candidate-universe-1",
        "project_id": "SYNTHETIC-BANK",
        "source_commit": "a" * 40,
        "code_snapshot_sha256": hashlib.sha256(b"synthetic fixture").hexdigest(),
        "requirements": [
            {"requirement_id": "R2", "requirement_text": "Reject invalid transfers above daily limit"},
            {"requirement_id": "R1", "requirement_text": "Verify user login credentials"},
        ],
        "symbols": [
            {"symbol_id": "S4", "source_path": "bank/limits.py", "qualified_name": "check_daily_limit", "description": "reject transfers"},
            {"symbol_id": "S1", "source_path": "auth/login.py", "qualified_name": "verify_credentials", "description": "user login"},
            {"symbol_id": "S3", "source_path": "auth/session.py", "qualified_name": "refresh_session", "description": "refresh session"},
            {"symbol_id": "S2", "source_path": "bank/transfer.py", "qualified_name": "make_transfer", "description": "daily bank transfer"},
        ],
        "observed_links": [{"requirement_id": "R1", "symbol_id": "S1"}],
    }


def test_order_independent_reproducibility_and_no_gold_labels():
    first = build_queue(universe(), seed="locked-seed", hard_per_requirement=1, random_per_requirement=1)
    changed = universe()
    changed["requirements"].reverse()
    changed["symbols"].reverse()
    second = build_queue(changed, seed="locked-seed", hard_per_requirement=1, random_per_requirement=1)
    assert first == second
    assert len(first["queue"]) == 5
    assert len({r["case_id"] for r in first["queue"]}) == 5
    assert first["manifest"]["possible_pairs"] == 8
    assert first["manifest"]["research_95_eligible"] is False
    assert first["manifest"]["independent_labels_collected"] is False
    assert first["manifest"]["stratum_counts"] == {
        "observed_unverified": 1,
        "lexical_confusable_unverified": 2,
        "seeded_random_unverified": 2,
    }
    assert all("origin" not in r and "gold_link" not in r and "link_label" not in r for r in first["queue"])


def test_two_reviewer_files_remain_unlabeled_and_blinded(tmp_path):
    result = build_queue(universe(), seed="study-2026")
    write_outputs(result, tmp_path)
    a = [json.loads(line) for line in (tmp_path / "reviewer_A.jsonl").read_text().splitlines()]
    b = [json.loads(line) for line in (tmp_path / "reviewer_B.jsonl").read_text().splitlines()]
    assert len(a) == len(b) == result["manifest"]["sampled_pairs"]
    assert {r["case_id"] for r in a} == {r["case_id"] for r in b}
    assert all(r["link_label"] is None and r["annotation_status"] == "pending" for r in a + b)
    assert all("origin" not in r and "gold_link" not in r for r in a + b)
    assert len((tmp_path / "manifest.json").read_text()) > 100


@pytest.mark.parametrize("mutation", [
    lambda d: d["requirements"].append(copy.deepcopy(d["requirements"][0])),
    lambda d: d["symbols"].append(copy.deepcopy(d["symbols"][0])),
    lambda d: d["observed_links"].append({"requirement_id": "R1", "symbol_id": "S999"}),
    lambda d: d["observed_links"].append(copy.deepcopy(d["observed_links"][0])),
    lambda d: d.update({"code_snapshot_sha256": "not-a-digest"}),
    lambda d: d.update({"source_commit": "wrong"}),
    lambda d: d.update({"schema_version": "unknown"}),
])
def test_invalid_or_ambiguous_universe_rejected(mutation):
    data = universe()
    mutation(data)
    with pytest.raises(QueueError):
        build_queue(data, seed="fixed")


def test_empty_sample_and_oversized_cartesian_universe_rejected():
    data = universe()
    data["observed_links"] = []
    with pytest.raises(QueueError):
        build_queue(data, seed="fixed", hard_per_requirement=0, random_per_requirement=0)
    with pytest.raises(QueueError):
        build_queue(data, seed="fixed", hard_per_requirement=-1)
    with pytest.raises(QueueError):
        build_queue(data, seed="fixed", random_per_requirement=21)


def test_observed_links_are_unverified_not_automatically_positive():
    result = build_queue(universe(), seed="locked", hard_per_requirement=0, random_per_requirement=0)
    assert result["manifest"]["sampled_pairs"] == 1
    assert result["manifest"]["stratum_counts"]["observed_unverified"] == 1
    assert "gold_link" not in result["queue"][0]
