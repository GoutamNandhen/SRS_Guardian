"""Offline M27 tests: provenance, full review universe, no fabricated outcomes."""
import copy
import json

import pytest

from backend.evaluation import m27_normative_edc_catalog as m


def fixtures(monkeypatch):
    lines = ["# intentionally synthetic offline fixture"] * 100
    for _, excerpt, _, start, _ in m.REQUIREMENTS:
        lines[start - 1] = excerpt
    spec = ("\n".join(lines) + "\n").encode()
    sources = {
        m.SPEC_REPO: {"LICENSE": b"Apache License\n", m.SPEC_PATH: spec},
        m.CODE_REPO: {"LICENSE": b"Apache License\n"},
        m.TCK_REPO: {"LICENSE.md": b"Apache License\n",
                     m.TCK_PATH: b"// SPDX-License-Identifier: Apache-2.0\n@MandatoryTest class Catalog01Test {}"},
    }
    for i, path in enumerate(m.CODE_PATHS):
        sources[m.CODE_REPO][path] = (
            "// SPDX-License-Identifier: Apache-2.0\n"
            + f"public class Test{i} {{ String catalog = \"request response pagination filter\"; }}\n"
        ).encode()
    monkeypatch.setattr(m, "FILES", {
        repo: {path: m.git_blob_id(raw) for path, raw in paths.items()}
        for repo, paths in sources.items()
    })
    return sources


def test_git_blob_sha1_known_vector():
    assert m.git_blob_id(b"test\n") == "9daeafb9864cf43055ae93beb0afd6c7d144bfa4"


def test_complete_normative_to_real_implementation_review_unlabeled(monkeypatch):
    sources = fixtures(monkeypatch)
    result = m.build_evidence(sources)
    assert result["internal"]["static_files_git_hash_verified"] == 9
    assert result["internal"]["normative_requirements"] == 4
    assert result["internal"]["real_implementation_java_files"] == 4
    assert result["internal"]["candidate_links_pending_independent_review"] == 16
    assert result["internal"]["behavioral_cases_pending_independent_review"] == 4
    assert result["queue"]["manifest"]["observed_links_in_universe"] == 0
    assert len({row["case_id"] for row in result["queue"]["queue"]}) == 16
    assert set(result["rankings_unscored"]) == {r[0] for r in m.REQUIREMENTS}
    assert all(result["internal"][metric] is None for metric in (
        "conformance_accuracy", "violation_precision", "violation_recall", "conformance_coverage"))
    assert result["internal"]["held_out_project_accuracy_eligible"] is False
    assert result["internal"]["independently_adjudicated_link_pairs"] == 0


def test_source_tampering_fails_closed(monkeypatch):
    sources = fixtures(monkeypatch)
    changed = copy.deepcopy(sources)
    changed[m.CODE_REPO][m.CODE_PATHS[0]] += b"// unreviewed change"
    with pytest.raises(m.EvidenceError, match="Git blob mismatch"):
        m.build_evidence(changed)


def test_normative_clause_drift_fails_closed(monkeypatch):
    sources = fixtures(monkeypatch)
    changed = copy.deepcopy(sources)
    changed[m.SPEC_REPO][m.SPEC_PATH] = changed[m.SPEC_REPO][m.SPEC_PATH].replace(
        b"HTTP 400", b"HTTP 201")
    monkeypatch.setattr(m, "FILES", {
        repo: {path: m.git_blob_id(raw) for path, raw in paths.items()}
        for repo, paths in changed.items()
    })
    with pytest.raises(m.EvidenceError, match="Normative excerpt"):
        m.build_evidence(changed)


def test_license_must_be_verified_even_with_matching_hashes(monkeypatch):
    sources = fixtures(monkeypatch)
    changed = copy.deepcopy(sources)
    changed[m.SPEC_REPO]["LICENSE"] = b"All rights reserved"
    monkeypatch.setattr(m, "FILES", {
        repo: {path: m.git_blob_id(raw) for path, raw in paths.items()}
        for repo, paths in changed.items()
    })
    with pytest.raises(m.EvidenceError, match="license not verified"):
        m.build_evidence(changed)


def test_blinded_queue_has_no_origin_or_gold(monkeypatch):
    sources = fixtures(monkeypatch)
    result = m.build_evidence(sources)
    rows = result["queue"]["queue"]
    assert all("origin" not in row and "link_label" not in row for row in rows)
    assert result["reviewer_index"]["warning"].find("UNADJUDICATED") >= 0
    assert "sampling_provenance" not in json.dumps(result["reviewer_index"])
