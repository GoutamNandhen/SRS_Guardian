"""M7: ranking determinism, data leakage boundaries, and paired review tests."""
import copy
from pathlib import Path
import pytest
from backend.evaluation.m7_hybrid_retrieval import (
    char_rank, rrf_rank, rank, evaluate_all, evaluate_version, paired_comparison,
)
from backend.evaluation.m6_external_trace import load_dataset

PATHS=["core/transaction/TransferLimitValidator.java","core/transaction/TransactionExport.java",
       "ui/ship/NavigationScreen.java","core/billing/AmountCheck.java"]


def test_char_rank_retrieves_obviously_relevant_name():
    assert char_rank("The platform shall validate the transfer amount", PATHS)[0] in [PATHS[0],PATHS[3]]


def test_hybrid_is_deterministic():
    assert rrf_rank("The system shall validate the transfer",PATHS)==rrf_rank("The system shall validate the transfer",PATHS)


def test_absent_similarity_stays_absent_not_fake_positive():
    assert char_rank("zzzqzxz", PATHS)==[]
    assert rrf_rank("zzzqzxz",PATHS)==[]


def test_methods_reject_unknown():
    with pytest.raises(ValueError,match="Unsupported"):
        rank("transfer",PATHS,"oracle_gold_link")


def test_rank_no_candidates():
    assert char_rank("transfer",[])==[]
    assert rrf_rank("transfer",[])==[]


def test_no_labels_leak_into_ranking():
    v=fixture()["versions"][0]
    a=evaluate_version(v,"hybrid_rrf")
    b=copy.deepcopy(v)
    b["requirements"][0]["observed_link_paths"]=[PATHS[1]]
    result=evaluate_version(b,"hybrid_rrf")
    assert a["cases"][0]["returned_count"]==result["cases"][0]["returned_count"]
    # Eligibility is never based on whether an observed link was found.
    assert a["linked_requirements"] == result["linked_requirements"]


def fixture():
    return {"_fixture_sha256":"a"*64,"versions":[
        {"version":v,"candidate_code_paths":list(PATHS),
         "requirements":[{"requirement_id":"REQ-A","text":"Validate transfer limit", "observed_link_paths":[PATHS[0]]},
                         {"requirement_id":"REQ-B","text":"Unknown code, no observed link", "observed_link_paths":[]}]}
        for v in ["V0","V1"]]}


def test_evaluate_all_scope_and_coverage():
    result=evaluate_all(fixture())
    assert result["research_95_eligible"] is False
    assert result["independent_projects"]==1
    assert len(result["runs"])==8
    assert len(result["paired"])==8
    assert all(x["linked_requirements"]==1 for x in result["runs"])
    assert all(x["unobserved_link_requirements"]==1 for x in result["runs"])


def test_no_zero_overlapping_label_as_negative():
    r=evaluate_version(fixture()["versions"][0],"char_tfidf")
    assert r["linked_requirements"]==1


def test_paired_comparison_requires_same_ids():
    a=evaluate_version(fixture()["versions"][0],"hybrid_rrf")
    b=copy.deepcopy(a);b["version"]="V1"
    with pytest.raises(ValueError,match="different versions"):
        paired_comparison(a,b)
    b=copy.deepcopy(a); b["cases"]=[]
    with pytest.raises(ValueError,match="different requirement cohorts"):
        paired_comparison(a,b)


def test_rrf_k_rejects_nonpositive():
    with pytest.raises(ValueError,match="positive"):
        rrf_rank("x",PATHS,k=0)


def test_external_fixture_in_real_repo():
    p=Path("benchmarks/m6/dronology_observed_trace_links.json")
    if not p.is_file():
        pytest.skip("Requires upstream normalized fixture in GitHub Actions")
    result=evaluate_all(load_dataset(p))
    assert result["research_95_eligible"] is False
    assert {x["version"] for x in result["runs"]}=={"V0","V1"}
