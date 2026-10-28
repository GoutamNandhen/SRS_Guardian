"""M43 first-party unit tests; invented snippets are NOT external evidence."""
import json

import pytest

from backend.evaluation import m29_pip_historical_regression as m29
from backend.evaluation import m43_pip_retrieval_gated_witness as m43

BEFORE = """
class Factory:
    def _make_requirements_from_install_req(self, ireq, requested_extras):
        if not ireq.match_markers(requested_extras):
            pass
        elif not ireq.link:
            pass
        else:
            cand = self._make_candidate_from_link(
                ireq.link, extras=frozenset(ireq.extras), template=ireq
            )
            if cand is None:
                yield UnsatisfiableRequirement(ireq.name)
            else:
                yield self.make_requirement_from_candidate(cand)
"""
AFTER = """
class Factory:
    def _make_requirements_from_install_req(self, ireq, requested_extras):
        if not ireq.match_markers(requested_extras):
            pass
        elif not ireq.link:
            pass
        else:
            cand = self._make_base_candidate_from_link(
                ireq.link,
                template=install_req_drop_extras(ireq) if ireq.extras else ireq
            )
            if cand is None:
                yield UnsatisfiableRequirement(ireq.name)
            else:
                yield self.make_requirement_from_candidate(cand)
                if ireq.extras:
                    yield self.make_requirement_from_candidate(
                        self._make_extras_candidate(cand, frozenset(ireq.extras))
                    )
"""


def snapshot(revision):
    raw = (BEFORE if revision == "before" else AFTER).encode()
    return {"files": {m29.SOURCE: raw},
            "expected": {m29.SOURCE: m29.blob_sha(raw)}}


def candidate(rank=2, path=m29.SOURCE, symbol=m43.WITNESS_BINDING[1]):
    return {"rank": rank, "path": path, "qualified_name": symbol,
            "score": 0.5, "source_url": "https://example.invalid/source#L1"}


def row(revision, case_id, candidates):
    return {"case_id": case_id, "revision": revision,
            "requirement_origin": "test fixture",
            "top_10_candidates": {m43.METHOD: candidates}}


def test_recognizer_does_not_receive_revision_label():
    pre = m43.recognize_variant_without_revision(BEFORE)
    post = m43.recognize_variant_without_revision(AFTER)
    assert pre["source_pattern"] == "single_candidate_with_extras"
    assert pre["successful_link_extras_yield_sites"] == 1
    assert post["source_pattern"] == "base_and_separate_extras"
    assert post["successful_link_extras_yield_sites"] == 2
    assert m43.recognize_variant_without_revision("def unrelated(): pass") is None


def test_witness_is_retrieval_gated_and_cites_actual_revision():
    r = m43.evaluate_retrieval_row(row("after", "x", [candidate()]), snapshot("after"))
    assert r["witness_status"] == "static_source_pattern_recognized"
    w = r["retrieval_gated_source_witness"]
    assert w["retrieval_rank"] == 2
    assert w["source_git_blob_sha1"] == m29.blob_sha(AFTER.encode())
    assert all(m29.AFTER in url for url in w["source_anchors"].values())
    assert r["behavioral_decision"] == "insufficient_evidence"
    assert r["independent_gold"] is None


def test_absent_or_below_top_five_does_not_inspect_oracle_file():
    other = candidate(1, path="src/pip/_internal/other.py", symbol="other")
    r = m43.evaluate_retrieval_row(row("before", "x", [other]), {"files": {}, "expected": {}})
    assert r["witness_status"] == "not_retrieved"
    assert r["retrieval_gated_source_witness"] is None
    r = m43.evaluate_retrieval_row(
        row("before", "x", [other] * 5 + [candidate(6)]), snapshot("before")
    )
    assert r["witness_status"] == "not_retrieved"


def test_hash_tamper_fails_closed_and_unrecognized_shape_abstains():
    snap = snapshot("before")
    snap["files"][m29.SOURCE] = AFTER.encode()
    with pytest.raises(m29.EvidenceError, match="hash-invalid"):
        m43.evaluate_retrieval_row(row("before", "x", [candidate()]), snap)
    raw = b"class Factory:\n    def unrelated(self): pass\n"
    snap = {"files": {m29.SOURCE: raw},
            "expected": {m29.SOURCE: m29.blob_sha(raw)}}
    r = m43.evaluate_retrieval_row(row("before", "x", [candidate()]), snap)
    assert r["witness_status"] == "unsupported_source_pattern"
    assert r["behavioral_decision"] == "insufficient_evidence"


def test_end_to_end_report_is_non_gold_and_per_revision(monkeypatch, tmp_path):
    rows = []
    for revision in ("before", "after"):
        for i in range(3):
            rows.append(row(revision, f"{revision}-{i}",
                            [candidate()] if i == 0 else []))
    fake_m42 = {
        "source_license": "MIT (pinned LICENSE.txt)",
        "source_revisions": {"before": {}, "after": {}},
        "source_scope": "all first-party pip implementation files",
        "cases": rows,
    }
    monkeypatch.setattr(m43.m42, "build", lambda snapshots, evidence: fake_m42)
    report = m43.build({"before": snapshot("before"),
                        "after": snapshot("after")}, {})
    assert report["retrieval_gated_source_witness_cases"] == 2
    assert report["witness_status_counts"]["not_retrieved"] == 4
    assert report["per_revision"]["before"]["static_source_witnesses"] == 1
    assert report["per_revision"]["after"]["static_source_witnesses"] == 1
    assert report["behavioral_abstentions"] == 6
    assert report["behavioral_decisions"] == 0
    assert report["independent_adjudications"] == 0
    assert report["held_out_project_evaluation"] is False
    assert report["external_project_code_executed"] is False
    assert all(report[k] is None for k in m43.METRICS)
    m43.write(report, tmp_path)
    saved = json.loads((tmp_path / "m43_retrieval_gated_witness.json").read_text())
    assert saved["conformance_accuracy"] is None
    assert "NOT GOLD" in (tmp_path / "README.md").read_text()
