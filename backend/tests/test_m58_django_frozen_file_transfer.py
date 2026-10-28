"""First-party offline tests for M58. Synthetic bytes are never gold labels."""
import io
import json
import zipfile

import pytest

from backend.evaluation import m29_pip_historical_regression as m29
from backend.evaluation import m58_django_frozen_file_transfer as m58


def snapshot():
    files = {
        f"django/core/module_{i}.py":
            (f"def process_{i}(data):\n    return 'alpha beta gamma {i}'\n").encode()
        for i in range(6)
    }
    return {
        "commit": "a" * 40, "tree_sha": "b" * 40,
        "license_git_blob": "c" * 40, "license_sha256": "d" * 64,
        "files": files,
        "expected": {p: m29.blob_sha(raw) for p, raw in files.items()},
    }


def test_selection_deterministic_and_requires_real_issue_fields():
    rows = [
        {"repo": "django/django", "instance_id": "django__django-2",
         "base_commit": "b" * 40, "problem_statement": "two",
         "patch": "patch", "test_patch": "test"},
        {"repo": "django/django", "instance_id": "django__django-1",
         "base_commit": "a" * 40, "problem_statement": "one",
         "patch": "patch", "test_patch": "test"},
        {"repo": "sympy/sympy", "instance_id": "sympy__sympy-1"},
    ]
    assert m58.select_case(rows)["instance_id"] == "django__django-1"
    with pytest.raises(ValueError):
        m58.select_case([{"repo": "django/django", "instance_id": "x"}])


def test_frozen_rank_and_blob_tamper_rejection():
    s = snapshot()
    first, truncated = m58.frozen_file_rank(s, "alpha beta gamma process_3")
    second, _ = m58.frozen_file_rank(s, "alpha beta gamma process_3")
    assert first == second and len(first) == 5 and truncated == 0
    s["files"]["django/core/module_0.py"] = b"tampered"
    with pytest.raises(ValueError, match="Unverified"):
        m58.frozen_file_rank(s, "alpha beta gamma")


def test_inert_archive_requires_exact_git_blobs():
    s = snapshot()
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as z:
        for path, raw in s["files"].items():
            z.writestr("django-test/" + path, raw)
    assert m58.read_archive(bio.getvalue(), s["expected"]) == s["files"]
    wrong = dict(s["expected"])
    wrong["django/core/module_1.py"] = "0" * 40
    with pytest.raises(ValueError, match="blob mismatch"):
        m58.read_archive(bio.getvalue(), wrong)


def test_actual_m20_handoff_is_unlabeled_and_patch_only_proxy(tmp_path):
    s = snapshot()
    row = {
        "repo": "django/django", "instance_id": "django__django-1",
        "base_commit": s["commit"],
        "problem_statement": "alpha beta gamma process_3",
        "patch": "diff --git a/django/core/module_3.py b/django/core/module_3.py\n",
        "test_patch": "diff --git a/tests/test_case.py b/tests/test_case.py\n",
    }
    internal, reviewers = m58.evaluate(row, s)
    assert internal["verified_production_files"] == 6
    assert internal["patch_file_proxy_eligible_NOT_GOLD"] is True
    assert internal["independent_adjudications"] == 0
    assert internal["conformance_accuracy"] is None
    assert all(len(reviewers[r]) == 5 for r in ("A", "B"))
    assert {r["case_id"] for r in reviewers["A"]} == {
        r["case_id"] for r in reviewers["B"]}
    assert all(r["link_label"] is None and r["behavioral_label"] is None
               for rows in reviewers.values() for r in rows)
    out = tmp_path / "m58"
    m58.write(internal, reviewers, out)
    assert json.loads((out / "INTERNAL_NOT_GOLD.json").read_text())[
        "held_out_behavioral_projects_scored"] == 0
    assert len((out / "reviewer_A.jsonl").read_text().splitlines()) == 5
    with pytest.raises(ValueError, match="overwrite"):
        m58.write(internal, reviewers, out)
