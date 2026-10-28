"""Network-free first-party tests for focused char-based code retrieval."""
from __future__ import annotations

import copy
import json
from backend.evaluation import focused_full_tree_retrieval as experiment
from backend.evaluation import m29_pip_historical_regression as m29
from backend.evaluation import m42_pip_first_party_tree_retrieval as m42

FIX = b"""class Factory:
    def _make_requirements_from_install_req(self, ireq, requested_extras):
        \"\"\"Resolve dependency wheel extras and local installation requirements.\"\"\"
        return ireq
"""
NOISE = b"""def show_unrelated_statistics():
    \"\"\"Render a readable usage chart.\"\"\"
    return 4
"""


def fake_snapshot(revision):
    files = {m29.SOURCE: FIX, "src/pip/_internal/chart.py": NOISE}
    return {"commit": m29.COMMITS[revision], "tree_sha": "a" * 40,
            "files": files.copy(), "expected": {k: m29.blob_sha(v) for k, v in files.items()}}


def symbol(name, tokens, path="src/pip/_internal/core.py"):
    return {"path": path, "qualified_name": name, "line_start": 2,
            "source_excerpt": " ".join(tokens), "signature": name+"(value)",
            "docstring": " ".join(tokens), "tokens": list(tokens), "http": []}


def test_generic_camel_snake_path_segmentation():
    assert experiment.normalize_code_text("PackageResolver._makeRequirements/InstallReq.py") == (
        "package resolver make requirements install req py"
    )


def test_char_ngram_ranking_is_deterministic_and_code_grounded():
    samples = [
        symbol("showUserChart", ["chart", "statistical", "display"]),
        symbol("resolveLocalDependency", ["resolve", "local", "dependency", "install", "wheel"]),
        symbol("parseTimeZone", ["date", "timezone", "time"]),
    ]
    before = copy.deepcopy(samples)
    ranked = experiment.char_rank_all(samples, ["Installing local dependency wheel"])[0]
    assert ranked and ranked[0]["qualified_name"] == "resolveLocalDependency"
    assert samples == before
    assert ranked == experiment.char_rank_all(samples, ["Installing local dependency wheel"])[0]


def test_reranking_does_not_insert_extra_candidates_or_use_gold():
    a = [symbol("first", ["one"]), symbol("second", ["two"])]
    b = [symbol("second", ["two"]), symbol("third", ["three"])]
    result = experiment.reciprocal_rank_fusion(a,b)
    assert {r["qualified_name"] for r in result} == {"first", "second", "third"}
    assert result[0]["qualified_name"] == "second"
    assert all(0 < x["score"] < 1 for x in result)


def test_zero_similarity_makes_no_link():
    src = [symbol("flightPlanner", ["aircraft", "route"])]
    assert experiment.char_rank_all(src, ["💎💎💎"])[0] == []


def test_empty_queries_and_symbols_do_not_raise():
    assert experiment.char_rank_all([], ["payment"]) == [[]]
    assert experiment.char_rank_all([symbol("a",["alpha"])], []) == []


def test_all_methods_retain_abstentions_and_scope_guard():
    evid = {"internal": {"static_file_revision_objects_verified": 6},
            "reviewer_index": {"license": "MIT (verified)"}}
    report = experiment.evaluate({v:fake_snapshot(v) for v in ("before","after")}, evid)
    assert report["project_count"] == 1
    assert report["held_out_projects"] == 0
    assert report["independent_gold"] is None
    assert report["conformance_accuracy"] is None
    assert report["violation_precision"] is None
    assert report["violation_recall"] is None
    assert report["conformance_coverage"] is None
    assert report["upstream_code_executed"] is False
    assert report["behavioral_decisions"] == 0
    assert report["behavioral_abstentions"] == 6
    assert set(report["diagnostics_NOT_GOLD"]) == set(experiment.METHODS)
    assert len(report["cases"]) == 6
    assert all(x["independent_gold"] is None for x in report["cases"])
    assert all(len(x["top_10"])==4 for x in report["cases"])


def test_tampered_pinned_source_fails_closed_before_scoring():
    evid = {"internal": {"static_file_revision_objects_verified": 6},
            "reviewer_index": {"license": "MIT (verified)"}}
    snaps = {v:fake_snapshot(v) for v in ("before","after")}
    snaps["before"]["files"][m29.SOURCE] = b"def modified(): return None"
    import pytest
    with pytest.raises(m29.EvidenceError, match="Source hash mismatch"):
        experiment.evaluate(snaps, evid)


def test_missing_licensed_evidence_refused():
    import pytest
    with pytest.raises(m29.EvidenceError, match="Incomplete"):
        experiment.evaluate({}, {"internal":{"static_file_revision_objects_verified":5},
                                 "reviewer_index":{"license":"MIT"}})
