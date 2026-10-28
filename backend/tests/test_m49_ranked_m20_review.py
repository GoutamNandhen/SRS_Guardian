"""First-party synthetic unit checks; do not execute pip or assert gold labels."""
from __future__ import annotations

import copy
import json

import pytest

from backend.evaluation import m29_pip_historical_regression as m29
from backend.evaluation import m43_pip_retrieval_gated_witness as m43
from backend.evaluation import m49_ranked_m20_review as m49


def fixture():
    snapshots = {}
    for revision, commit in m29.COMMITS.items():
        files = {f"src/pip/_internal/review_{i}.py": f"def example_{i}(): pass\n".encode()
                 for i in range(5)}
        snapshots[revision] = {
            "commit": commit, "files": files,
            "expected": {p: m29.blob_sha(raw) for p, raw in files.items()},
        }
    rows = []
    for revision, commit in m29.COMMITS.items():
        for scenario in m29.SCENARIOS:
            candidates = [{
                "rank": i + 1, "path": f"src/pip/_internal/review_{i}.py",
                "qualified_name": f"example_{i}", "score": 1.0 / (i + 1),
                "source_url": (
                    f"https://github.com/{m29.REPO}/blob/{commit}/"
                    f"src/pip/_internal/review_{i}.py#L1")
            } for i in range(5)]
            rows.append({
                "revision": revision, "case_id": scenario["case_id"],
                "top_five_source_candidates": candidates,
            })
    report = {
        "schema": m43.SCHEMA, "retrieval_method": "normalized_tokens",
        "source_revisions": {rev: {"commit": commit}
                             for rev, commit in m29.COMMITS.items()},
        "cases": rows,
    }
    return report, snapshots


def test_retrieval_candidates_are_blinded_and_pending(tmp_path):
    report, snapshots = fixture()
    result = m49.prepare(report, snapshots)
    assert result["candidate_links_per_reviewer"] == 30
    assert result["independent_adjudications"] == 0
    assert result["conformance_accuracy"] is None
    assert result["held_out"] is False
    for reviewer, rows in result["reviewer_rows"].items():
        assert len(rows) == 30
        assert len({row["case_id"] for row in rows}) == 30
        assert all(row["link_label"] is None and row["annotation_status"] == "pending"
                   for row in rows)
        assert all("rank" not in row and "score" not in row
                   and "known_fix_locus" not in row and "revision" not in row
                   for row in rows)
        assert all(row["reviewer"] == "reviewer_" + reviewer for row in rows)
    m49.write(result, tmp_path / "packets")
    assert len((tmp_path / "packets" / "reviewer_A.jsonl").read_text().splitlines()) == 30
    assert (tmp_path / "packets" / "INTERNAL_DO_NOT_SHARE.json").exists()
    with pytest.raises(ValueError, match="overwrite"):
        m49.write(result, tmp_path / "packets")


def test_rejects_tampered_source_hash():
    report, snapshots = fixture()
    path = next(iter(snapshots["before"]["files"]))
    snapshots["before"]["files"][path] = b"changed"
    with pytest.raises(ValueError, match="blob mismatch"):
        m49.prepare(report, snapshots)


def test_rejects_unpinned_candidate_link():
    report, snapshots = fixture()
    report["cases"][0]["top_five_source_candidates"][0]["source_url"] = (
        "https://github.com/other/project/blob/main/file.py#L1")
    with pytest.raises(ValueError, match="Unpinned source URL"):
        m49.prepare(report, snapshots)


def test_rejects_missing_ranked_case():
    report, snapshots = fixture()
    report["cases"].pop()
    with pytest.raises(ValueError, match="six retrieval cases"):
        m49.prepare(report, snapshots)
