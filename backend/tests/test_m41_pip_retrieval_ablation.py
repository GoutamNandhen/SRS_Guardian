"""First-party tests for M41 retrieval diagnosis; no third-party execution."""
from __future__ import annotations

import json

import pytest

from backend.evaluation import m29_pip_historical_regression as m29
from backend.evaluation import m40_pip_e2e_feasibility as m40
from backend.evaluation import m41_pip_retrieval_ablation as m41


SOURCE = """
class Factory:
    def _make_requirements_from_install_req(self, ireq, requested_extras):
        \"\"\"Install link requirements with optional extras and a constraint.\"\"\"
        return ireq

    def unrelated(self):
        return None
"""
TEST = """
def test_new_resolver_constraint_on_link_with_extra():
    \"\"\"Test installing a local wheel with extra constraints.\"\"\"
    return True
"""


def fake_files():
    return {
        rev: {m29.SOURCE: SOURCE.encode(), m29.TEST: TEST.encode()}
        for rev in ("before", "after")
    }


def patch_evidence(monkeypatch):
    monkeypatch.setattr(m29, "build_evidence", lambda files: {
        "internal": {"static_file_revision_objects_verified": 6},
        "queue": {"queue": [{}] * 6},
    })
    monkeypatch.setattr(m40.m34, "inspect_structure", lambda source, revision: {
        "explicit_base_without_extras": revision == "after",
        "separate_extras_requirement": revision == "after",
    })


def test_general_inflection_normalization():
    assert m41.normalize_token("installing") == "install"
    assert m41.normalize_token("resolved") == "resolv"
    assert m41.normalize_token("wheel") == "wheel"
    assert m41.normalize_token("extras") == "extras"
    assert "install" in m41.normalized_query("Installing a local wheel")


def test_test_functions_excluded_from_implementation_candidates():
    ranked = m41.ranked_implementation_symbols(
        SOURCE, "Installing a wheel with extra constraints", normalize=True)
    assert ranked
    assert all(x["path"] == m29.SOURCE for x in ranked)
    assert not any(x["qualified_name"].startswith("test_") for x in ranked)


def test_ablation_preserves_m40_baseline_and_no_gold(monkeypatch):
    patch_evidence(monkeypatch)
    result = m41.build(fake_files())
    assert result["verified_static_file_revision_objects"] == 6
    assert result["requirement_revision_pairs"] == 6
    assert set(result["ablation"]) == set(m41.METHODS)
    assert result["behavioral_decisions"] == 0
    assert result["behavioral_abstentions"] == 6
    assert result["independent_adjudications"] == 0
    assert result["held_out_project_evaluation"] is False
    assert result["external_project_code_executed"] is False
    assert result["conformance_accuracy"] is None
    assert result["violation_precision"] is None
    assert result["violation_recall"] is None
    assert result["conformance_coverage"] is None
    assert all(row["independent_gold"] is None for row in result["cases"])
    assert any("ORACLE FILE SCOPE" in note for note in result["limitations"])
    for method, counts in result["ablation"].items():
        assert 0 <= counts["known_fix_locus_top1_exploratory"] <= 6
        assert 0 <= counts["known_fix_locus_top5_exploratory"] <= 6
    assert result["ablation"][m41.METHODS[0]]["known_fix_locus_top5_exploratory"] == (
        m40.build(fake_files())["known_fix_locus_top5_count_exploratory"])


def test_generated_evidence_is_explicitly_not_gold(monkeypatch, tmp_path):
    patch_evidence(monkeypatch)
    result = m41.build(fake_files())
    m41.write(result, tmp_path)
    saved = json.loads((tmp_path / "m41_retrieval_ablation.json").read_text())
    assert saved["conformance_accuracy"] is None
    assert saved["independent_adjudications"] == 0
    text = (tmp_path / "README.md").read_text()
    assert "preselected-file" in text
    assert "not measured" in text
    assert "whole-repository retrieval" in text


def test_missing_known_fix_symbol_fails_closed(monkeypatch):
    patch_evidence(monkeypatch)
    altered = fake_files()
    altered["before"][m29.SOURCE] = b"def unrelated():\n    return None\n"
    with pytest.raises(m29.EvidenceError, match="not indexed uniquely"):
        m41.build(altered)
