"""First-party, network-free M42 tests. No external project code is executed."""
from __future__ import annotations

import io
import json
import zipfile

import pytest

from backend.evaluation import m29_pip_historical_regression as m29
from backend.evaluation import m42_pip_first_party_tree_retrieval as m42


SOURCE = b"""class Factory:
    def _make_requirements_from_install_req(self, ireq, requested_extras):
        \"\"\"Install local wheel with extras and constraints.\"\"\"
        return ireq
"""
OTHER = b"""def unrelated_function():
    \"\"\"Unrelated functionality.\"\"\"
    return None
"""


def fake_evidence():
    return {"internal": {"static_file_revision_objects_verified": 6},
            "reviewer_index": {"license": "MIT (pinned LICENSE.txt)"}}


def fake_snapshots():
    files = {m29.SOURCE: SOURCE, "src/pip/_internal/other.py": OTHER}
    return {rev: {"commit": m29.COMMITS[rev], "tree_sha": "a" * 40,
                  "expected": {p: m29.blob_sha(raw) for p, raw in files.items()},
                  "files": files.copy()}
            for rev in ("before", "after")}


def make_archive(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for path, data in files.items():
            z.writestr("pip-pinned/" + path, data)
    return buf.getvalue()


def test_static_zip_verifies_git_blob_and_complete_file_set():
    files = {m29.SOURCE: SOURCE, "src/pip/_internal/other.py": OTHER}
    expected = {p: m29.blob_sha(raw) for p, raw in files.items()}
    assert m42.read_archive(make_archive(files), expected) == files
    with pytest.raises(m29.EvidenceError, match="Incomplete"):
        m42.read_archive(make_archive({m29.SOURCE: SOURCE}), expected)
    tampered = dict(files)
    tampered[m29.SOURCE] = SOURCE + b"# modified\n"
    with pytest.raises(m29.EvidenceError, match="Git blob mismatch"):
        m42.read_archive(make_archive(tampered), expected)


def test_zip_rejects_path_traversal_and_duplicate_source():
    expected = {m29.SOURCE: m29.blob_sha(SOURCE)}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("../src/pip/_internal/factory.py", SOURCE)
    with pytest.raises(m29.EvidenceError, match="Unsafe"):
        m42.read_archive(buf.getvalue(), expected)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("pip-a/" + m29.SOURCE, SOURCE)
        z.writestr("pip-b/" + m29.SOURCE, SOURCE)
    with pytest.raises(m29.EvidenceError, match="duplicate"):
        m42.read_archive(buf.getvalue(), expected)


def test_fetch_snapshot_checks_commit_tree_and_archive(monkeypatch):
    files = {"src/pip/_internal/file_%02d.py" % i: OTHER for i in range(20)}
    tree_sha = "b" * 40
    commit = m29.COMMITS["before"]
    expected = {p: m29.blob_sha(raw) for p, raw in files.items()}
    def fake_json(url):
        if "/commits/" in url:
            return {"sha": commit, "tree": {"sha": tree_sha}}
        return {"sha": tree_sha, "truncated": False,
                "tree": [{"path": p, "sha": sha, "type": "blob", "mode": "100644"}
                         for p, sha in expected.items()]}
    monkeypatch.setattr(m42, "get_json", fake_json)
    monkeypatch.setattr(m42, "get_bytes", lambda *args, **kwargs: make_archive(files))
    snap = m42.fetch_snapshot("before")
    assert snap["tree_sha"] == tree_sha
    assert len(snap["files"]) == 20


def test_rank_all_first_party_files_without_known_locus_in_query():
    snapshots = fake_snapshots()
    report = m42.build(snapshots, fake_evidence())
    assert report["requirement_revision_pairs"] == 6
    assert report["behavioral_abstentions"] == 6
    assert report["behavioral_decisions"] == 0
    assert report["independent_adjudications"] == 0
    assert report["held_out_project_evaluation"] is False
    assert report["external_project_code_executed"] is False
    assert report["conformance_accuracy"] is None
    assert report["violation_precision"] is None
    assert report["violation_recall"] is None
    assert report["conformance_coverage"] is None
    assert all(row["independent_gold"] is None for row in report["cases"])
    assert all(s["verified_first_party_python_files"] == 2 for s in report["source_revisions"].values())
    assert all(row["top_10_candidates"]["original_tokens"] for row in report["cases"])
    assert m42.PREFIX == "src/pip/_internal/"


def test_hash_mismatch_fails_before_ranking():
    snapshots = fake_snapshots()
    snapshots["before"]["files"][m29.SOURCE] = b"def tampered(): pass\n"
    with pytest.raises(m29.EvidenceError, match="Source hash mismatch"):
        m42.build(snapshots, fake_evidence())


def test_output_explicitly_denies_ground_truth(tmp_path):
    report = m42.build(fake_snapshots(), fake_evidence())
    m42.write(report, tmp_path)
    saved = json.loads((tmp_path / "m42_first_party_tree_retrieval.json").read_text())
    assert saved["conformance_accuracy"] is None
    assert saved["independent_adjudications"] == 0
    assert "NOT GOLD" in (tmp_path / "README.md").read_text()
