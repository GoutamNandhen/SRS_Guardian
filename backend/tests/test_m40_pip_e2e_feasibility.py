"""M40 synthetic first-party tests. Real pinned pip evidence is checked by CI."""
from __future__ import annotations

import json

import pytest

from backend.evaluation import m29_pip_historical_regression as m29
from backend.evaluation import m34_pip_source_structure_witness as m34
from backend.evaluation import m40_pip_e2e_feasibility as m40


SOURCE = """
class Factory:
    def _make_requirements_from_install_req(self, ireq, requested_extras):
        \"\"\"Create requirements from local links and optional extras.\"\"\"
        return ireq

    def unrelated(self):
        return None
"""

TEST = """
def test_new_resolver_constraint_on_link_with_extra():
    \"\"\"Test resolver installation of local wheel with extras.\"\"\"
    return True
"""


def fake_files():
    return {
        rev: {m29.SOURCE: SOURCE.encode(), m29.TEST: TEST.encode()}
        for rev in ("before", "after")
    }


def mock_evidence(monkeypatch):
    monkeypatch.setattr(m29, "build_evidence", lambda files: {
        "internal": {"static_file_revision_objects_verified": 6},
        "queue": {"queue": [{}] * 6},
    })
    monkeypatch.setattr(m34, "inspect_structure", lambda source, rev: {
        "revision": rev,
        "explicit_base_without_extras": rev == "after",
        "separate_extras_requirement": rev == "after",
        "source_anchors": {"candidate": m29.source_url(rev, m29.SOURCE, 2)},
    })


def test_real_m2_retrieval_path_and_explicit_abstention(monkeypatch):
    mock_evidence(monkeypatch)
    result = m40.build(fake_files())
    assert result["revision_requirement_pairs"] == 6
    assert len(result["cases"]) == 6
    assert result["behavioral_abstentions"] == 6
    assert result["behavioral_decisions"] == 0
    assert result["independent_adjudications"] == 0
    assert result["held_out_project_evaluation"] is False
    assert result["external_project_code_executed"] is False
    assert all(v is None for v in result["metrics"].values())
    assert result["per_revision"]["before"]["structural_property_present"] is False
    assert result["per_revision"]["after"]["structural_property_present"] is True
    assert all(x["decision"] == "insufficient_evidence" for x in result["cases"])
    assert all(x["independent_gold"] is None for x in result["cases"])
    for row in result["cases"]:
        for candidate in row["retrieved_candidates"]:
            assert candidate["source_url"].startswith("https://github.com/pypa/pip/blob/")
            assert candidate["rank"] >= 1
    assert result["known_fix_locus_top5_count_exploratory"] <= 6


def test_no_known_target_in_index_fails_closed(monkeypatch):
    mock_evidence(monkeypatch)
    altered = fake_files()
    altered["before"][m29.SOURCE] = b"def unrelated():\n    return None\n"
    with pytest.raises(m29.EvidenceError, match="not indexed uniquely"):
        m40.build(altered)


def test_generated_report_preserves_null_metrics(monkeypatch, tmp_path):
    mock_evidence(monkeypatch)
    result = m40.build(fake_files())
    m40.write(result, tmp_path)
    saved = json.loads((tmp_path / "pip_e2e_feasibility.json").read_text())
    assert saved["metrics"]["conformance_accuracy"] is None
    assert saved["behavioral_abstentions"] == 6
    text = (tmp_path / "README.md").read_text()
    assert "NOT independently validated" in text
    assert "NOT link accuracy" in text
    assert "not measured" in text
