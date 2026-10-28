"""Offline AST tests only: invented snippets are NOT real-world evidence."""
import json

import pytest

from backend.evaluation import m29_pip_historical_regression as m29
from backend.evaluation import m34_pip_source_structure_witness as m34


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


def test_structural_before_and_after_paths():
    pre = m34.inspect_structure(BEFORE, "before")
    post = m34.inspect_structure(AFTER, "after")
    assert [pre["successful_link_extras_yield_sites"],
            post["successful_link_extras_yield_sites"]] == [1, 2]
    assert pre["separate_extras_requirement"] is False
    assert post["separate_extras_requirement"] is True
    assert post["explicit_base_without_extras"] is True
    assert "#L" in post["source_anchors"]["extras_requirement"]


def test_reject_missing_separate_extras_requirement():
    altered = AFTER.replace(
        "self._make_extras_candidate(cand, frozenset(ireq.extras))",
        "cand",
    )
    with pytest.raises(m29.EvidenceError, match="separate extras candidate yield"):
        m34.inspect_structure(altered, "after")


def test_reject_unguarded_extras_requirement():
    altered = AFTER.replace("if ireq.extras:", "if True:")
    with pytest.raises(m29.EvidenceError, match="extras conditional"):
        m34.inspect_structure(altered, "after")


def test_reject_unstripped_base_candidate():
    altered = AFTER.replace(
        "install_req_drop_extras(ireq) if ireq.extras else ireq", "ireq"
    )
    with pytest.raises(m29.EvidenceError, match="extras-free base template"):
        m34.inspect_structure(altered, "after")


def test_reject_pre_fix_extra_yield():
    altered = BEFORE.replace(
        "yield self.make_requirement_from_candidate(cand)",
        "yield self.make_requirement_from_candidate(cand)\n"
        "                yield self.make_requirement_from_candidate(cand)",
    )
    with pytest.raises(m29.EvidenceError, match="one yield"):
        m34.inspect_structure(altered, "before")


def test_reject_wrong_branch():
    with pytest.raises(m29.EvidenceError, match="explicit local/URL link branch"):
        m34.inspect_structure(AFTER.replace("elif not ireq.link:", "elif ireq.link:"), "after")


def test_report_metrics_stay_null_and_review_packets_remain_m29(monkeypatch, tmp_path):
    # Stub only the evidence factory: this does not validate real Git hashes.
    fake_evidence = {"queue": {"queue": [{}] * 6}}
    monkeypatch.setattr(m29, "build_evidence", lambda files: fake_evidence)
    files = {
        "before": {m29.SOURCE: BEFORE.encode()},
        "after": {m29.SOURCE: AFTER.encode()},
    }
    result = m34.build(files)
    report = result["report"]
    assert report["verified_file_revision_objects"] == 6  # Declared production expectation.
    assert report["m20_unlabeled_link_pairs"] == 6
    assert report["behavior_revision_cases_per_reviewer"] == 6
    assert report["independent_adjudications"] == 0
    assert report["external_project_code_executed"] is False
    assert report["held_out_evaluation"] is False
    assert all(value is None for value in report["metrics"].values())
    monkeypatch.setattr(m29, "write_evidence", lambda evidence, out: (
        (out / "internal").mkdir(parents=True, exist_ok=True)
    ))
    m34.write(result, tmp_path)
    assert json.loads((tmp_path / "internal" / "m34_source_structure.json").read_text())["metrics"]["conformance_accuracy"] is None
