"""M38 first-party offline handoff checks; no upstream code execution."""
from __future__ import annotations

import json
from pathlib import Path
import re

import pytest

from backend.evaluation import m37_werkzeug_holdout as m37
from backend.evaluation import m38_werkzeug_offline_review as m38


@pytest.fixture(scope="module")
def pinned():
    return m37.fetch_pinned()


def test_complete_offline_reviewers_and_null_metrics(pinned, tmp_path):
    manifest = m38.generate(tmp_path / "out", pinned)
    root = tmp_path / "out"
    assert manifest["source_file_revision_objects_hash_verified"] == 8
    assert manifest["independent_reviewer_packages"] == 2
    assert manifest["independent_reviewer_submissions"] == 0
    assert manifest["approved_runtime_observations"] == 0
    assert manifest["independent_adjudications"] == 0
    assert manifest["external_project_code_executed"] is False
    assert all(v is None for v in manifest["metrics"].values())
    for reviewer in ("A", "B"):
        folder = root / f"reviewer_{reviewer}"
        html = (folder / "workspace.html").read_text(encoding="utf-8")
        assert "Open verified source snapshots" in html
        match = re.search(r'<script type="application/json" id="seed">(.*?)</script>',
                          html, re.DOTALL)
        assert match is not None
        payload = json.loads(match.group(1))
        assert payload["reviewer"] == reviewer
        assert len(payload["links"]) == 6
        assert len(payload["behaviors"]) == 4
        assert all(x["link_label"] is None for x in payload["links"])
        assert all(x["conformance_label"] is None and x["violation_label"] is None
                   for x in payload["behaviors"])
        assert "sampling_provenance" not in html
        assert "static_model_before" not in html
        assert not (folder / "internal").exists()
        index = (folder / "source_index.html").read_text(encoding="utf-8")
        assert "Pinned upstream line" in index
        assert "not runtime results" in index
        for revision, paths in m37.FILES.items():
            for path, expected in paths.items():
                copied = folder / "source" / revision / (path + ".txt")
                assert copied.is_file()
                assert copied.read_bytes() == pinned[revision][path]
                assert m37.blob_sha(copied.read_bytes()) == expected
    assert (root / "internal" / "m20" / "manifest.json").is_file()
    assert not (root / "reviewers").exists()


def test_rejects_modified_source_without_publishing_reviewers(pinned, tmp_path):
    tampered = {revision: dict(paths) for revision, paths in pinned.items()}
    tampered["after"][m37.PARSER] += b"tamper\n"
    with pytest.raises(m37.EvidenceError, match="Git blob mismatch"):
        m38.generate(tmp_path / "bad", tampered)
    assert not (tmp_path / "bad").exists()


def test_rejects_existing_output_to_avoid_mixup(pinned, tmp_path):
    target = tmp_path / "existing"
    target.mkdir()
    (target / "old.txt").write_text("old", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        m38.generate(target, pinned)


def test_source_index_contains_exact_revision_links_and_no_labels(pinned):
    html = m38._source_index(pinned)
    assert m37.BEFORE in html and m37.AFTER in html
    assert "source/before/src/werkzeug/http.py.txt" in html
    assert "source/after/src/werkzeug/http.py.txt" in html
    assert "adjudications" in html
    assert "conformance_accuracy" not in html
