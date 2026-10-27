"""M23 offline tests. Live pinned upstream fetch is separately checked in CI."""
from __future__ import annotations

import hashlib
import pytest

from backend.evaluation.m23_teastore_external import (
    CODE_FILES, CODE_REPO, CODE_COMMIT, DOC_FILES, DOC_REPO, DOC_COMMIT,
    SourceError, _description, _snapshot_digest, fetch_pinned,
    git_blob_id, observed_subset, build_evidence,
)


def test_git_blob_known_reference():
    assert git_blob_id(b"hello\n") == hashlib.sha1(b"blob 6\0hello\n").hexdigest()


def test_exact_allowlist_rejects_unapproved_upstream_without_fetch():
    with pytest.raises(SourceError, match="Unapproved"):
        fetch_pinned(DOC_REPO, DOC_COMMIT, {"arbitrary.py": "0" * 40})
    with pytest.raises(SourceError, match="Unapproved"):
        fetch_pinned(CODE_REPO, "0" * 40, CODE_FILES)


def test_pinned_files_fail_closed_on_modified_local_contents(tmp_path):
    for path in DOC_FILES:
        file = tmp_path / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(b"forged")
    with pytest.raises(SourceError, match="Pinned Git blob mismatch"):
        fetch_pinned(DOC_REPO, DOC_COMMIT, DOC_FILES, source_dir=tmp_path)


def test_observed_links_are_only_selected_positive_observations():
    paths = [p for p in CODE_FILES if p.endswith(".java")]
    registry = [p for p in paths if ".registry/" in p]
    recommender = [p for p in paths if ".recommender/" in p]
    assert len(registry) == len(recommender) == 2
    lines = ["SentenceId,CodeElementId", "999,irrelevant/Other.java"]
    for rid, selected in ((1, registry), (27, recommender), (28, recommender)):
        for path in selected:
            lines.append(f"{rid},{path}")
    result = observed_subset("\n".join(lines), set(paths))
    assert len(result) == 6
    assert all(rid in (1, 27, 28) for rid, _ in result)
    assert all(path in paths for _, path in result)


def test_missing_paper_links_are_not_silently_inferred():
    registry = next(p for p in CODE_FILES if ".registry/" in p)
    with pytest.raises(SourceError, match="counts"):
        observed_subset("SentenceId,CodeElementId\n1," + registry + "\n", {registry})


def test_wrong_gold_schema_rejected():
    with pytest.raises(SourceError, match="header"):
        observed_subset("requirement,code\n1,foo\n", set())


def test_java_declaration_summary_is_static():
    src = b"/* comment */\npublic class Registry {\n public void start() {\n }\n}\n"
    assert "class Registry" in _description(src)
    assert "void start" in _description(src)


def test_subset_digest_is_order_independent_and_changes_with_source():
    paths = [p for p in CODE_FILES if p.endswith(".java")]
    files = {paths[0]: b"first", paths[1]: b"second"}
    a = _snapshot_digest(files)
    assert a == _snapshot_digest(dict(reversed(list(files.items()))))
    assert a != _snapshot_digest({paths[0]: b"first!", paths[1]: b"second"})


def test_unverified_upstream_cannot_be_converted_to_gold():
    docs = {p: b"wrong" for p in DOC_FILES}
    code = {p: b"wrong" for p in CODE_FILES}
    with pytest.raises(SourceError, match="Unverified"):
        build_evidence(docs, code)
