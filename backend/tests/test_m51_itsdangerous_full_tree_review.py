"""First-party, offline tests; never import or execute upstream itsdangerous."""
from __future__ import annotations

import io
import json
from unittest.mock import patch
import zipfile

import pytest

from backend.evaluation import m29_pip_historical_regression as m29
from backend.evaluation import m51_itsdangerous_full_tree_review as m51


def synthetic_snapshots():
    files = {
        "src/itsdangerous/signer.py": (
            'def sha1_digest_default():\n'
            '    """hashlib sha1 FIPS import digest alternate signing"""\n'
            '    return "static"\n\n'
            'def configure_digest():\n'
            '    """select alternate digest before signing"""\n'
            '    return "static"\n\n'
            'def import_signer():\n'
            '    """import succeeds without sha1 available"""\n'
            '    return "static"\n'
        ).encode(),
        "src/itsdangerous/serializer.py": (
            'def import_serializer():\n'
            '    """import itsdangerous without hashlib sha1"""\n'
            '    return "static"\n\n'
            'def serialize_digest():\n'
            '    """select alternate digest method"""\n'
            '    return "static"\n'
        ).encode(),
        "src/itsdangerous/encoding.py": (
            'def fips_import():\n'
            '    """FIPS environment unavailable sha1 import"""\n'
            '    return "static"\n\n'
            'def safe_digest():\n'
            '    """digest method before signing"""\n'
            '    return "static"\n'
        ).encode(),
    }
    license_raw = (
        "Redistribution and use in source and binary forms\n"
        "Neither the name of the copyright holder\n"
        "THIS SOFTWARE IS PROVIDED\n"
    ).encode()
    pyproject = b'license = { file = "LICENSE.txt" }\n'
    pinned_bytes = {
        "LICENSE.txt": license_raw,
        "pyproject.toml": pyproject,
        "src/itsdangerous/signer.py": files["src/itsdangerous/signer.py"],
        "tests/test_itsdangerous/test_serializer.py": b"# inert synthetic test text\n",
    }
    pinned_shas = {p: m29.blob_sha(v) for p, v in pinned_bytes.items()}
    snapshots = {
        rev: {
            "commit": commit,
            "tree_sha": "a" * 40,
            "files": dict(files),
            "expected": {p: m29.blob_sha(v) for p, v in files.items()},
            "pinned": dict(pinned_bytes),
        }
        for rev, commit in m51.COMMITS.items()
    }
    return snapshots, {rev: dict(pinned_shas) for rev in m51.COMMITS}


def test_frozen_full_tree_handoff_never_creates_gold(monkeypatch, tmp_path):
    snapshots, shas = synthetic_snapshots()
    monkeypatch.setattr(m51, "PINNED", shas)
    report = m51.build(snapshots)
    assert report["revision_cases"] == 2
    assert report["candidates_per_reviewer"] == 10
    assert report["independent_annotations"] == 0
    assert report["independent_adjudications"] == 0
    assert report["held_out"] is False
    assert report["external_code_executed"] is False
    assert all(report[k] is None for k in (
        "conformance_accuracy", "violation_precision", "violation_recall", "coverage"
    ))
    assert len(report["reviewer_rows"]["A"]) == 10
    assert len(report["reviewer_rows"]["B"]) == 10
    assert all(row["link_label"] is None and row["behavior_label"] is None
               for row in report["reviewer_rows"]["A"])
    assert "known_fix_locus" not in json.dumps(report)
    assert all(len(x["ranked_top_five_NOT_GOLD"]) == 5 for x in report["internal_ranked"])
    out = tmp_path / "evidence"
    m51.write(report, out)
    assert (out / "reviewer_A.jsonl").read_text().count("\n") == 10
    assert "ranked_top_five" not in (out / "reviewer_A.jsonl").read_text()
    assert "ranked_top_five" in (out / "INTERNAL_DO_NOT_SHARE.json").read_text()
    with pytest.raises(ValueError, match="overwrite"):
        m51.write(report, out)


def test_source_tamper_is_rejected(monkeypatch):
    snapshots, shas = synthetic_snapshots()
    monkeypatch.setattr(m51, "PINNED", shas)
    snapshots["before"]["files"]["src/itsdangerous/encoding.py"] += b"\n# tampered"
    with pytest.raises(ValueError, match="Git blob"):
        m51.build(snapshots)


def test_license_tamper_is_rejected(monkeypatch):
    snapshots, shas = synthetic_snapshots()
    monkeypatch.setattr(m51, "PINNED", shas)
    snapshots["after"]["pinned"]["LICENSE.txt"] = b"MIT\n"
    with pytest.raises(ValueError, match="Git blob"):
        m51.build(snapshots)


def test_missing_revision_is_rejected(monkeypatch):
    snapshots, shas = synthetic_snapshots()
    monkeypatch.setattr(m51, "PINNED", shas)
    with pytest.raises(ValueError, match="Both immutable"):
        m51.build({"before": snapshots["before"]})


def test_zip_reader_checks_all_source_blobs():
    files = {
        "src/itsdangerous/signer.py": b"def a(): pass\n",
        "src/itsdangerous/encoding.py": b"def b(): pass\n",
        "src/itsdangerous/serializer.py": b"def c(): pass\n",
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path, raw in files.items():
            archive.writestr("itsdangerous-immutable/" + path, raw)
        archive.writestr("itsdangerous-immutable/README.md", "unrelated")
    expected = {p: m29.blob_sha(v) for p, v in files.items()}
    assert m51.read_source_archive(buffer.getvalue(), expected) == files
    expected["src/itsdangerous/signer.py"] = "0" * 40
    with pytest.raises(ValueError, match="Git blob"):
        m51.read_source_archive(buffer.getvalue(), expected)


def test_no_oracle_retrieval_location_in_source():
    import inspect
    source = inspect.getsource(m51.build)
    assert "m42.rank_case(symbols, REQUIREMENT, normalized=True)" in source
    assert "known_fix_locus" not in source
