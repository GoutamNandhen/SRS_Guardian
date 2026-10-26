"""Unit tests for observed-positive-only external trace link evaluation."""
import json
from pathlib import Path
import pytest

from backend.evaluation.m6_external_trace import (
    ExternalTraceError, evaluate_all, evaluate_version, load_dataset,
    rank, tokens, wilson,
)


def fixture():
    return {
        "schema_version":"m6-external-trace-v1", "no_negative_labels": True,
        "not_executable_conformance":True, "one_project_two_versions":True,
        "dataset_name":"synthetic checker fixture", "upstream_repository":"https://example.invalid/upstream",
        "versions":[{
            "version":v,"source_blob_sha":"a"*40, "candidate_code_paths":[
                "core/src/bank/transfer_validator.py", "core/src/bank/statement_export.py"],
            "requirements":[
                {"requirement_id":"R1","text":"Transfers require transfer validation", "observed_link_paths":["core/src/bank/transfer_validator.py"]},
                {"requirement_id":"R2","text":"The software shall run quickly", "observed_link_paths":[]}
            ]}
            for v in ("V0","V1")]
    }


def test_load_and_scope_flags(tmp_path):
    p=tmp_path/"f.json";p.write_text(json.dumps(fixture()))
    d=load_dataset(p)
    assert len(d["_fixture_sha256"])==64
    results=evaluate_all(d)
    assert results["research_95_eligible"] is False
    assert results["has_true_negatives"] is False
    assert len(results["runs"])==4
    assert results["runs"][0]["requirements_with_observed_code_link"]==1


def test_dont_treat_unobserved_link_as_negative():
    r=evaluate_version(fixture()["versions"][0],"path_bm25")
    assert r["total_requirements"]==2
    assert r["requirements_with_observed_code_link"]==1
    assert r["observed_link_coverage"]==0.5


def test_positive_missing_fails_closed(tmp_path):
    bad=fixture();bad["versions"][0]["requirements"][0]["observed_link_paths"]=["unknown.py"]
    p=tmp_path/"bad.json";p.write_text(json.dumps(bad))
    with pytest.raises(ExternalTraceError,match="outside candidate"):
        load_dataset(p)


def test_duplicate_or_invalid_rows_rejected(tmp_path):
    bad=fixture();bad["versions"][0]["requirements"].append(dict(bad["versions"][0]["requirements"][0]))
    p=tmp_path/"bad.json";p.write_text(json.dumps(bad))
    with pytest.raises(ExternalTraceError,match="Duplicate"):
        load_dataset(p)


def test_missing_scope_flags_rejected(tmp_path):
    bad=fixture();bad["no_negative_labels"]=False
    p=tmp_path/"bad.json";p.write_text(json.dumps(bad))
    with pytest.raises(ExternalTraceError,match="unknown negatives"):
        load_dataset(p)


def test_rank_returns_no_match_not_alphabetic_guess():
    assert rank("moonbase encryption", ["api/payments.py","core/transfer.py"],"path_bm25")==[]


def test_tokenize_camelcase():
    assert "transfer" in tokens("TransferLimitEndpoint")
    assert "endpoint" in tokens("TransferLimitEndpoint")


def test_ranking_correct_filename_path():
    files=["core/src/bank/transfer_validator.py", "core/src/bank/statement_export.py"]
    assert rank("Transfer validation",files,"filename_bm25")[0]==files[0]


def test_wilson_small_samples_not_equal_certainty():
    lower,upper=wilson(10,10)
    assert lower < 0.95 and upper == 1


def test_unknown_method_rejected():
    with pytest.raises(ExternalTraceError,match="Unrecognized"):
        rank("transfer",["transfer.py"],"pretend_new_model")


def test_real_fixture_when_present():
    p=Path("benchmarks/m6/dronology_observed_trace_links.json")
    if not p.is_file():
        pytest.skip("run against checked-in third-party observed trace dataset in GitHub CI")
    d=load_dataset(p)
    assert [v["version"] for v in d["versions"]]==["V0","V1"]
    assert [len(v["requirements"]) for v in d["versions"]]==[24,25]
    assert all(v["source_blob_sha"] for v in d["versions"])
    assert evaluate_all(d)["research_95_eligible"] is False
