"""Offline M54 tests: no external project source imported or executed."""
import io
import json
import zipfile
import pytest

from backend.evaluation import m29_pip_historical_regression as m29
from backend.evaluation import m52_swebench_verified_intake as m52
from backend.evaluation import m54_sympy_frozen_retrieval_review as m54

COMMIT = "a" * 40
TREE = "b" * 40
LICENSE = (b"Redistribution and use in source and binary forms\n"
           b"Neither the name of SymPy\nTHIS SOFTWARE IS PROVIDED\n")


def files():
    return {f"sympy/subpkg/module_{i}.py": (
        f'def source_{i}_fix():\n'
        '    """matrix inverse computation handles zero entries and symbolic division"""\n'
        '    return 1\n\n'
        f'def other_{i}():\n'
        '    """symbolic expression operations"""\n'
        '    return 2\n'
    ).encode() for i in range(50)}


def fake_case():
    text = "Matrix inverse computation should handle zero entries and symbolic division."
    return {"review_case_id": "CASE-001", "project": "sympy/sympy",
            "source_commit": COMMIT, "requirement_text": text,
            "requirement_sha256": m52.digest(text.encode()),
            "license_sha256": m52.digest(LICENSE)}


def archive(items):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for path, raw in items.items():
            z.writestr("sympy-snapshot/" + path, raw)
    return buf.getvalue()


def fake_source():
    src = files()
    shas = {path: m29.blob_sha(raw) for path, raw in src.items()}
    tree = {"sha": TREE, "truncated": False, "tree": [
        {"path": path, "type": "blob", "mode": "100644", "sha": sha}
        for path, sha in shas.items()] + [
        {"path": "LICENSE", "type": "blob", "mode": "100644",
         "sha": m29.blob_sha(LICENSE)}]}
    def get_json(url):
        return {"sha": COMMIT, "tree": {"sha": TREE}} if "/commits/" in url else tree
    def get_bytes(url, max_bytes):
        return LICENSE if url.endswith("/LICENSE") else archive(src)
    return src, shas, get_json, get_bytes


def test_full_tree_verified_and_m20_predictions(tmp_path):
    src, shas, get_json, get_bytes = fake_source()
    case = fake_case()
    snapshot = m54.fetch_snapshot(case, get_json=get_json, get_bytes=get_bytes)
    assert set(snapshot["files"]) == set(src)
    result = m54.build(case, snapshot)
    assert result["verified_production_python_files"] == 50
    assert result["indexed_production_symbols"] == 100
    assert len(result["reviewer_rows"]["A"]) == 5
    assert len(result["reviewer_rows"]["B"]) == 5
    assert result["conformance_accuracy"] is None
    assert result["independent_adjudications"] == 0
    assert result["external_code_executed"] is False
    m54.write(result, tmp_path / "out")
    reviewer = (tmp_path / "out/reviewer_A.jsonl").read_text()
    assert '"link_label": null' in reviewer
    assert '"behavioral_label": null' in reviewer
    assert '"rank":' not in reviewer
    assert "historical_pr_url" not in reviewer
    assert '"full_requirement_text":' in reviewer
    internal = json.loads((tmp_path / "out/INTERNAL_DO_NOT_SHARE.json").read_text())
    assert len(internal["internal_top_five_NOT_GOLD"]) == 5


def test_rejects_tampered_or_incomplete_archive():
    src, shas, _, _ = fake_source()
    altered = dict(src)
    key = next(iter(src))
    altered[key] += b"# altered\n"
    with pytest.raises(ValueError, match="Git blob mismatch"):
        m54.read_archive(archive(altered), shas)
    with pytest.raises(ValueError, match="Incomplete"):
        m54.read_archive(archive({key: src[key]}), shas)


def test_rejects_truncated_git_tree_and_wrong_license():
    src, shas, get_json, get_bytes = fake_source()
    def truncated(url):
        data = get_json(url)
        return {**data, "truncated": True} if "/trees/" in url else data
    with pytest.raises(ValueError, match="Incomplete"):
        m54.fetch_snapshot(fake_case(), get_json=truncated, get_bytes=get_bytes)
    case = fake_case()
    case["license_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="license mismatch"):
        m54.fetch_snapshot(case, get_json=get_json, get_bytes=get_bytes)


def test_rejects_unsafe_archive_and_wrong_revision():
    src, shas, get_json, get_bytes = fake_source()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("../sympy/x.py", b"def f(): pass")
    with pytest.raises(ValueError, match="Unsafe"):
        m54.read_archive(buf.getvalue(), shas)
    snapshot = m54.fetch_snapshot(fake_case(), get_json=get_json, get_bytes=get_bytes)
    case = fake_case()
    case["source_commit"] = "c" * 40
    with pytest.raises(ValueError, match="revision mismatch"):
        m54.build(case, snapshot)


def test_scope_is_project_wide_not_fix_directory():
    assert m54.production_source("sympy/physics/mechanics/body.py")
    assert m54.production_source("sympy/core/basic.py")
    assert not m54.production_source("sympy/core/tests/test_basic.py")
    assert not m54.production_source("sympy/physics/test_motion.py")
    assert not m54.production_source("setup.py")
