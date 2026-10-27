"""M28 offline tests: real-source provenance contract, no unreviewed labels."""
import copy
import json

import pytest

from backend.evaluation import m28_historical_pagination_regression as m


def fixtures(monkeypatch):
    pre_src = (
        "// SPDX-License-Identifier: Apache-2.0\n"
        "public class ContractOfferResolverImpl {\n"
        "  void queryContractOffers(ContractOfferQuery query) { int limit = 1; }\n"
        "}\n"
    ).encode()
    post_src = (
        "// SPDX-License-Identifier: Apache-2.0\n"
        "public class ContractOfferResolverImpl {\n"
        "  void queryContractOffers(ContractOfferQuery query) {\n"
        "    var dynamicLimit = 2;\n"
        "  }\n"
        "}\n"
    ).encode()
    pre_test = (
        "// SPDX-License-Identifier: Apache-2.0\n"
        "public class ContractOfferResolverImplIntegrationTest { void originalTest() {} }\n"
    ).encode()
    post_test = (
        "// SPDX-License-Identifier: Apache-2.0\n"
        "public class ContractOfferResolverImplIntegrationTest {\n"
        "  void should_return_offers_subset_when_across_multiple_contract_definitions(int from, int to) {}\n"
        "}\n"
    ).encode()
    result = {
        "before": {m.LICENSE: b"Apache License\n", m.SOURCE: pre_src, m.TEST: pre_test},
        "after": {m.LICENSE: b"Apache License\n", m.SOURCE: post_src, m.TEST: post_test},
    }
    monkeypatch.setattr(m, "FILES", {
        revision: {path: m.blob_sha(raw) for path, raw in paths.items()}
        for revision, paths in result.items()
    })
    return result


def test_git_blob_vector():
    assert m.blob_sha(b"test\n") == "9daeafb9864cf43055ae93beb0afd6c7d144bfa4"


def test_historical_report_and_review_are_not_gold(monkeypatch):
    files = fixtures(monkeypatch)
    evidence = m.build_evidence(files)
    internal = evidence["internal"]
    assert internal["static_file_revision_objects_verified"] == 6
    assert internal["historical_bug_report_scenarios"] == 2
    assert internal["m20_link_pairs_pending"] == 4
    assert internal["behavior_revision_cases_pending"] == 4
    assert internal["independent_reviewed_links"] == 0
    assert internal["independent_reviewed_behavior_cases"] == 0
    assert internal["representative_held_out"] is False
    assert internal["external_code_executed"] is False
    assert all(internal[k] is None for k in (
        "conformance_accuracy", "violation_precision", "violation_recall", "conformance_coverage"))
    assert len(evidence["queue"]["queue"]) == 4
    assert all("link_label" not in row and "origin" not in row for row in evidence["queue"]["queue"])
    assert "reported_observed_before" not in json.dumps(evidence["reviewer_index"])


def test_tampered_pinned_file_rejected(monkeypatch):
    files = fixtures(monkeypatch)
    altered = copy.deepcopy(files)
    altered["after"][m.SOURCE] += b"\n// altered\n"
    with pytest.raises(m.EvidenceError, match="Git blob mismatch"):
        m.build_evidence(altered)


def test_wrong_license_rejected_even_when_hash_updated(monkeypatch):
    files = fixtures(monkeypatch)
    altered = copy.deepcopy(files)
    altered["before"][m.LICENSE] = b"All rights reserved\n"
    monkeypatch.setattr(m, "FILES", {
        revision: {path: m.blob_sha(raw) for path, raw in paths.items()}
        for revision, paths in altered.items()
    })
    with pytest.raises(m.EvidenceError, match="license missing"):
        m.build_evidence(altered)


def test_missing_historical_test_change_rejected(monkeypatch):
    files = fixtures(monkeypatch)
    altered = copy.deepcopy(files)
    altered["after"][m.TEST] = altered["before"][m.TEST]
    monkeypatch.setattr(m, "FILES", {
        revision: {path: m.blob_sha(raw) for path, raw in paths.items()}
        for revision, paths in altered.items()
    })
    with pytest.raises(m.EvidenceError, match="No source-and-test change"):
        m.build_evidence(altered)


def test_review_packets_leave_all_behavior_unanswered(monkeypatch, tmp_path):
    evidence = m.build_evidence(fixtures(monkeypatch))
    m.write_evidence(evidence, tmp_path)
    review = tmp_path / "reviewers"
    internal = tmp_path / "internal"
    assert not (review / "manifest.json").exists()
    assert "reported_observed_before" not in (review / "source_index.json").read_text()
    assert "reported_observed_before" in (internal / "internal.json").read_text()
    for reviewer in ("A", "B"):
        link_rows = [json.loads(line) for line in
                     (review / f"reviewer_{reviewer}.jsonl").read_text().splitlines()]
        behavior_rows = [json.loads(line) for line in
                         (review / f"behavior_reviewer_{reviewer}.jsonl").read_text().splitlines()]
        assert len(link_rows) == 4 and len(behavior_rows) == 4
        assert all(row["link_label"] is None and row["annotation_status"] == "pending"
                   for row in link_rows)
        assert all(row["observed_offers"] is None and row["conformance_label"] is None
                   and row["violation_label"] is None and row["status"] == "pending"
                   for row in behavior_rows)
