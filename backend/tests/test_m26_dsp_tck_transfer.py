"""M26 offline tests: external files never executed; unverified links never gold."""
import copy

import pytest

from backend.evaluation import m26_dsp_tck_transfer as m26


def _fake(monkeypatch):
    # Synthetic unit fixture only; CI also checks eight real pinned Git objects.
    code_paths = [p for p in m26.FILES if p.endswith(".java")]
    readme = "\n".join(m26.MODULE_TEXT.values()).encode()
    files = {
        "LICENSE.md": b"Apache License\nVersion 2.0\n",
        "NOTICE.md": b"SPDX-License-Identifier: Apache-2.0\n",
        "README.md": readme,
    }
    for p in code_paths:
        files[p] = (
            "// SPDX-License-Identifier: Apache-2.0\n"
            "public class " + p.rsplit("/", 1)[-1].removesuffix(".java") +
            " { @MandatoryTest void verify() {} }\n"
        ).encode()
    monkeypatch.setattr(m26, "FILES", {p: m26.git_blob_id(raw) for p, raw in files.items()})
    return files


def test_git_blob_has_nul_delimiter():
    import hashlib
    assert m26.git_blob_id(b"hello") == hashlib.sha1(b"blob 5\0hello").hexdigest()


def test_complete_module_test_universe_and_m20_queue(monkeypatch):
    files = _fake(monkeypatch)
    result = m26.build_evidence(files)
    baseline = result["internal"]["baseline"]
    assert baseline["pinned_static_files"] == 8
    assert baseline["module_descriptions"] == 4
    assert baseline["java_test_classes"] == 5
    assert baseline["documentation_derived_associations_unverified"] == 5
    assert baseline["blinded_pairs_pending_review"] == 20
    assert len(result["reviewer"]["queue"]["queue"]) == 20
    assert len(result["reviewer"]["index"]["review_pairs"]) == 20
    assert len(baseline["comparison"]["runs"]) == 3
    assert all(run["independent_gold"] is False for run in baseline["comparison"]["runs"])
    assert all(baseline[k] is None for k in m26.NO_CONFORMANCE)
    assert baseline["research_95_eligible"] is False
    assert "observed_links" not in result["reviewer"]["index"]


def test_pinned_hash_tampering_fails_closed(monkeypatch):
    files = _fake(monkeypatch)
    files["README.md"] += b"\ntampered"
    with pytest.raises(m26.SourceError, match="hash mismatch"):
        m26.build_evidence(files)


def test_license_and_mandatory_test_required(monkeypatch):
    files = _fake(monkeypatch)
    files["NOTICE.md"] = b"unlicensed"
    monkeypatch.setattr(m26, "FILES", {p: m26.git_blob_id(raw) for p, raw in files.items()})
    with pytest.raises(m26.SourceError, match="NOTICE"):
        m26.build_evidence(files)
    files = _fake(monkeypatch)
    path = next(p for p in files if p.endswith(".java"))
    files[path] = files[path].replace(b"@MandatoryTest", b"@OrdinaryTest")
    monkeypatch.setattr(m26, "FILES", {p: m26.git_blob_id(raw) for p, raw in files.items()})
    with pytest.raises(m26.SourceError, match="mandatory test"):
        m26.build_evidence(files)


def test_documentation_must_contain_exact_pinned_module_descriptions(monkeypatch):
    files = _fake(monkeypatch)
    files["README.md"] = b"Unrelated generic documentation"
    monkeypatch.setattr(m26, "FILES", {p: m26.git_blob_id(raw) for p, raw in files.items()})
    with pytest.raises(m26.SourceError, match="module description changed"):
        m26.build_evidence(files)


def test_queue_deterministic_and_no_gold_in_reviewer_packet(monkeypatch):
    files = _fake(monkeypatch)
    a = m26.build_evidence(files)
    b = m26.build_evidence(dict(reversed(list(files.items()))))
    assert a["reviewer"] == b["reviewer"]
    assert a["internal"]["universe"]["observed_links"] != []
    assert all("origin" not in row and "link_label" not in row for row in a["reviewer"]["queue"]["queue"])
    assert "sampling_provenance" not in str(a["reviewer"]["index"])
    assert a["reviewer"]["queue"]["manifest"]["independent_labels_collected"] is False
