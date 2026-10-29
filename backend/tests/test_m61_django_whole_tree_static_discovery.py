"""First-party offline synthetic tests; NOT independent behavioral accuracy."""
import pytest

from backend.evaluation import m29_pip_historical_regression as m29
from backend.evaluation import m60_django_static_userinfo_verification as m60
from backend.evaluation import m61_django_whole_tree_static_discovery as m61


def fake_source(fragment):
    return (
        "class URLValidator(RegexValidator):\n"
        "    regex = _lazy_re_compile(\n"
        "        r'^(?:[a-z0-9]*)://'\n"
        f"        r'{fragment}'\n"
        "        r'(?:' + host_re + ')'\n"
        "    )\n"
    ).encode("utf-8")


def snapshot(revision, source=None, extra=None):
    files = {
        "django/core/validators.py": source or fake_source(r"(?:\\S+(?::\\S*)?@)?"),
        "django/utils/other.py": b"pass\n",
    }
    files.update(extra or {})
    return {
        "commit": m60.REVISIONS[revision]["commit"],
        "tree_sha": "a" * 40,
        "files": files,
        "expected": {path: m29.blob_sha(raw) for path, raw in files.items()},
        "license_git_blob": "b" * 40,
        "license_sha256": "c" * 64,
    }


def test_discovers_symbol_without_source_path_hint():
    s = snapshot("before")
    result = m61.discover(s, "before")
    assert result["source_path"] == "django/core/validators.py"
    assert result["source_line"] == 4
    assert result["static_result"] == "static_rule_violated"
    assert result["verified_production_files_scanned"] == 2
    assert result["source_git_blob"] == s["expected"]["django/core/validators.py"]


def test_after_property_with_same_automatic_discovery():
    s = snapshot("after", fake_source(r"(?:[^\\s:@/]+(?::[^\\s:@/]*)?@)?"))
    result = m61.discover(s, "after")
    assert result["static_result"] == "static_rule_satisfied"
    assert result["candidate_count"] == 1


def test_absent_or_ambiguous_symbol_abstains():
    s = snapshot("before", b"class Other:\n    pass\n")
    assert m61.discover(s, "before")["static_result"] == "abstain"
    duplicate = {"django/forms/duplicate.py": fake_source(r"(?:\\S+(?::\\S*)?@)?")}
    s2 = snapshot("before", extra=duplicate)
    result = m61.discover(s2, "before")
    assert result["static_result"] == "abstain"
    assert result["candidate_count"] == 2


def test_unsupported_regex_abstains():
    s = snapshot("before", fake_source(r"(?:.*@)?"))
    assert m61.discover(s, "before")["static_result"].startswith("abstain")


def test_inert_source_never_executed():
    evil = fake_source(r"(?:\\S+(?::\\S*)?@)?") + b'\nraise RuntimeError("DO NOT EXECUTE")\n'
    assert m61.discover(snapshot("before", evil), "before")["static_result"] == "static_rule_violated"


def test_corrupted_or_incomplete_source_rejected():
    s = snapshot("before")
    s["files"]["django/utils/other.py"] = b"tampered\n"
    with pytest.raises(ValueError, match="Unverified"):
        m61.discover(s, "before")
    s2 = snapshot("before")
    del s2["files"]["django/utils/other.py"]
    with pytest.raises(ValueError, match="Incomplete"):
        m61.discover(s2, "before")


def test_revision_mismatch_rejected():
    with pytest.raises(ValueError, match="Pinned revision mismatch"):
        m61.discover(snapshot("before"), "after")


def test_build_is_explicitly_not_independent_gold():
    def fetch(commit):
        rev = next(key for key, info in m60.REVISIONS.items()
                   if info["commit"] == commit)
        fragment = (r"(?:\\S+(?::\\S*)?@)?" if rev == "before"
                    else r"(?:[^\\s:@/]+(?::[^\\s:@/]*)?@)?")
        return snapshot(rev, fake_source(fragment))

    result = m61.build(fetch)
    assert [r["static_result"] for r in result["revisions"]] == [
        "static_rule_violated", "static_rule_satisfied"
    ]
    assert result["file_path_oracle_used"] is False
    assert result["symbol_and_rule_oracle_informed"] is True
    assert result["independent_link_labels"] == 0
    assert result["independent_behavioral_observations"] == 0
    assert result["independent_adjudications"] == 0
    assert result["held_out_projects_scored"] == 0
    assert result["external_project_code_executed"] is False
    assert all(result[k] is None for k in (
        "conformance_accuracy", "violation_precision", "violation_recall", "coverage"
    ))
