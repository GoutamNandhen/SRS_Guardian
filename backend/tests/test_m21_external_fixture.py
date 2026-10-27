"""M21 offline tests: pinned fixture ingestion without executing upstream code."""
import json
import pytest
from backend.evaluation import m21_external_fixture as m21

def fixture_files(monkeypatch):
    spec = """# Web dashboard

\x60req:web/dashboard#1\x60

Renders the live metrics dashboard in the browser.

| Needs | Tags |
|---|---|
| impl:web/page#1 | web |
| impl:web/markup#1 | |
| impl:web/widget#1 | |
| impl:web/theme#1 | |

# Metrics API

\x60req:api/metrics#1\x60

Serves aggregated metrics as JSON.

Needs: impl:api/metrics#1, utest:api/metrics#1

# Metrics aggregation

\x60req:data/aggregation#1\x60

Aggregates raw events into per-minute metrics.

Needs: impl:data/aggregation#1
"""
    files = {
        "LICENSE": b"Apache License\nVersion 2.0\n",
        m21.PREFIX + "spec.md": spec.encode(),
        m21.PREFIX + "metrics.ts": b"// [impl:api/metrics#1]\nexport function metrics() { return []; }\n",
        m21.PREFIX + "test_metrics.py": b"# [utest:api/metrics#1]\ndef test_metrics(): pass\n",
        m21.PREFIX + "aggregation.sql": b"-- [impl:data/aggregation#1]\nSELECT COUNT(*) FROM events;\n",
        m21.PREFIX + "index.html": b"<!-- [impl:web/page#1] -->\n<div>dashboard</div>\n",
        m21.PREFIX + "dashboard.vue": (
            b"<!-- [impl:web/markup#1] -->\n<template>metrics</template>\n"
            b"// [impl:web/widget#1]\n<script>export default {}</script>\n"
            b"/* [impl:web/theme#1] */\n<style>body{display:grid}</style>\n"
        ),
    }
    monkeypatch.setattr(m21, "BLOBS", {p: m21.git_blob_id(v) for p, v in files.items()})
    return files

def test_external_fixture_becomes_unlabeled_review_queue(monkeypatch, tmp_path):
    files = fixture_files(monkeypatch)
    result = m21.build_evidence(files)
    evidence = result["evidence"]
    assert (evidence["requirement_count"], evidence["implementation_component_count"],
            evidence["author_declared_links_unverified"], evidence["sampled_annotation_pairs"]) == (3, 6, 6, 12)
    assert evidence["independent_labels_collected"] is False
    assert evidence["research_95_eligible"] is False
    assert all(evidence[x] is None for x in (
        "conformance_accuracy", "violation_precision", "violation_recall", "conformance_coverage"))
    assert result["queue"] == m21.build_evidence(files)["queue"]
    assert all("origin" not in row and "link_label" not in row for row in result["queue"]["queue"])
    assert all("[impl:" not in row["description"] for row in result["queue"]["queue"])
    m21.write_outputs(result["queue"], tmp_path)
    for reviewer in ("reviewer_A", "reviewer_B"):
        rows = [json.loads(line) for line in (tmp_path / f"{reviewer}.jsonl").read_text().splitlines()]
        assert len(rows) == 12
        assert all(row["annotation_status"] == "pending" and row["link_label"] is None for row in rows)

def test_blob_mismatch_rejected_before_parsing(monkeypatch):
    files = fixture_files(monkeypatch)
    files[m21.PREFIX + "metrics.ts"] += b"// tamper\n"
    with pytest.raises(m21.EvidenceError, match="Unverified"):
        m21.build_evidence(files)

def test_missing_link_cannot_silently_become_negative(monkeypatch):
    files = fixture_files(monkeypatch)
    path = m21.PREFIX + "spec.md"
    files[path] = files[path].replace(b"impl:web/theme#1", b"impl:web/theme#2")
    monkeypatch.setitem(m21.BLOBS, path, m21.git_blob_id(files[path]))
    with pytest.raises(m21.EvidenceError, match="Needs changed"):
        m21.build_evidence(files)

def test_source_snapshot_digest_changes_with_source_content(monkeypatch):
    files = fixture_files(monkeypatch)
    first = m21.build_evidence(files)["universe"]["code_snapshot_sha256"]
    path = m21.PREFIX + "metrics.ts"
    files[path] += b"\n"
    monkeypatch.setitem(m21.BLOBS, path, m21.git_blob_id(files[path]))
    second = m21.build_evidence(files)["universe"]["code_snapshot_sha256"]
    assert first != second
    assert len(first) == len(second) == 64
