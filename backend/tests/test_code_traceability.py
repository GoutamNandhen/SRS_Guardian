"""M2 candidate retrieval tests. Run: python -m pytest backend/tests/test_code_traceability.py -q"""
import io
import zipfile
from pathlib import Path
import pytest
from backend.app.services.code_traceability import index_archive,save_index,load_index,rank_candidates,tokenize

SOURCE='''from fastapi import APIRouter
router=APIRouter(prefix="/payments")
@router.post("/transfer")
async def submit_transfer(amount: int):
    """Reject transfers above the configured payment limit."""
    if amount > 10000:
        raise ValueError("transfer rejected: amount exceeds maximum")
    return {"accepted": True}
@router.get("/balance")
def account_balance():
    """Show customer's current account balance."""
    return {"balance": 100}
'''

def archive(**files):
    out=io.BytesIO()
    with zipfile.ZipFile(out,"w") as z:
        for path,source in files.items():z.writestr(path,source)
    return out.getvalue()

def test_indexes_fastapi_routes():
    idx=index_archive(archive(**{"demo-main/api.py":SOURCE}),"Payments")
    assert idx["files_indexed"]==1
    sym=next(x for x in idx["symbols"] if x["name"]=="submit_transfer")
    assert {"method":"POST","route":"/payments/transfer"} in sym["http"]
    assert sym["line_start"]<sym["line_end"]

def test_traceability_ranks_relevant_endpoint():
    idx=index_archive(archive(**{"app.py":SOURCE}))
    links=rank_candidates("The system shall reject any transfer exceeding the payment limit.",idx)
    assert links[0]["qualified_name"]=="submit_transfer"
    assert links[0]["verification_status"]=="candidate_unverified"
    assert links[0]["score"]>0
    assert "transfer" in links[0]["matched_terms"]

def test_second_requirement_links_to_balance():
    idx=index_archive(archive(**{"app.py":SOURCE}))
    assert rank_candidates("Show customer's account balance",idx)[0]["qualified_name"]=="account_balance"

def test_python_source_never_executed(tmp_path):
    target=tmp_path/"unsafe"
    code=f'''open({str(target)!r},"w").write("unsafe")
async def handler():
    return 1
'''
    idx=index_archive(archive(**{"app.py":code}))
    assert idx["symbols_indexed"]==1
    assert not target.exists()

def test_zip_traversal_is_rejected():
    with pytest.raises(ValueError,match="Unsafe"):
        index_archive(archive(**{"../evil.py":"def x(): pass"}))

def test_absolute_path_rejected():
    with pytest.raises(ValueError,match="Unsafe"):
        index_archive(archive(**{"/tmp/evil.py":"def x(): pass"}))

def test_duplicate_zip_members_rejected():
    b=io.BytesIO()
    with zipfile.ZipFile(b,"w") as z:
        z.writestr("app.py",SOURCE)
        with pytest.warns(UserWarning):z.writestr("app.py",SOURCE)
    with pytest.raises(ValueError,match="Duplicate"):index_archive(b.getvalue())

def test_archive_with_only_non_python_rejected():
    with pytest.raises(ValueError,match="No parsable"):
        index_archive(archive(**{"README.md":"Documentation"}))

def test_invalid_compressed_size_and_non_zip():
    with pytest.raises(ValueError,match="ZIP"):index_archive(b"oops")
    with pytest.raises(ValueError,match="8 MB"):index_archive(b"a"*(8*1024*1024+1))

def test_bad_syntax_warns_and_valid_source_remains():
    idx=index_archive(archive(**{"broken.py":"def ??","good.py":"def valid_check(): return 1"}))
    assert idx["symbols_indexed"]==1
    assert idx["warnings"]

def test_round_trip_rejects_invalid_ids(tmp_path):
    idx=index_archive(archive(**{"app.py":SOURCE}))
    save_index(idx,tmp_path)
    assert load_index(idx["index_id"],tmp_path)["symbols"][0]["symbol_id"]==idx["symbols"][0]["symbol_id"]
    with pytest.raises(ValueError,match="Invalid"):load_index("../../secret",tmp_path)
    with pytest.raises(FileNotFoundError):load_index("0"*64,tmp_path)

def test_no_false_claim_when_no_token_overlap():
    idx=index_archive(archive(**{"app.py":SOURCE}))
    assert rank_candidates("The system shall establish orbital lunar trajectory",idx)==[]

def test_camel_and_snake_case_indexing():
    assert "transfer" in tokenize("submitTransfer_limit")

def test_reproducible_order_and_bounds():
    idx=index_archive(archive(**{"app.py":SOURCE}))
    assert rank_candidates("payment transfer",idx)==rank_candidates("payment transfer",idx)
    assert len(rank_candidates("payment transfer",idx,top_k=100))<=10
