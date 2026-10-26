"""M2 read-only Python code index and SRS linking API."""
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.document import Document, Requirement
from backend.app.services.code_traceability import (
    MAX_ARCHIVE_BYTES,index_archive,load_index,rank_candidates,save_index
)

router=APIRouter(prefix="/code-traceability",tags=["Code Traceability"])
INDEX_DIR=Path("data/code_indexes")

class CandidateLink(BaseModel):
    symbol_id:str
    path:str
    qualified_name:str
    kind:str
    line_start:int
    line_end:int
    http:list[dict]
    score:float
    matched_terms:list[str]
    evidence_features:list[str]
    signature:str
    source_excerpt:str
    verification_status:str
    explanation:str

class RequirementLinks(BaseModel):
    requirement_id:int
    req_key:str
    text:str
    candidates:list[CandidateLink]

class LinksResponse(BaseModel):
    document_id:int
    index_id:str
    index_label:str
    total_requirements:int
    offset:int
    limit:int
    results:list[RequirementLinks]
    note:str="Ranked code links are unverified candidates, not proof of implementation or conformance."

class IndexResponse(BaseModel):
    index_id:str
    label:str
    files_indexed:int
    symbols_indexed:int
    warnings:list[str]
    methodology:str

@router.post("/index",response_model=IndexResponse)
async def index_source_archive(file:UploadFile=File(...),label:str="Uploaded Python project"):
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(400,"Upload a Python source ZIP archive")
    data=await file.read(MAX_ARCHIVE_BYTES+1)
    await file.close()
    try:
        index=index_archive(data,label)
        save_index(index,INDEX_DIR)
    except (ValueError,OSError) as e:
        raise HTTPException(400,str(e)) from e
    return index

@router.get("/index/{index_id}",response_model=IndexResponse)
def get_index_metadata(index_id:str):
    try:return load_index(index_id,INDEX_DIR)
    except ValueError as e:raise HTTPException(400,str(e)) from e
    except FileNotFoundError as e:raise HTTPException(404,str(e)) from e

@router.get("/documents/{document_id}/links",response_model=LinksResponse)
def get_document_links(
    document_id:int,index_id:str,offset:int=Query(default=0,ge=0),
    limit:int=Query(default=50,ge=1,le=100),
    top_k:int=Query(default=5,ge=1,le=10),db:Session=Depends(get_db)
):
    if db.query(Document).filter(Document.id==document_id).first() is None:
        raise HTTPException(404,"SRS document not found")
    try:index=load_index(index_id,INDEX_DIR)
    except ValueError as e:raise HTTPException(400,str(e)) from e
    except FileNotFoundError as e:raise HTTPException(404,str(e)) from e
    query=db.query(Requirement).filter(Requirement.document_id==document_id)
    total=query.count()
    reqs=query.order_by(Requirement.id.asc()).offset(offset).limit(limit).all()
    return LinksResponse(
        document_id=document_id,index_id=index_id,index_label=index["label"],
        total_requirements=total,offset=offset,limit=limit,
        results=[
            RequirementLinks(requirement_id=r.id,req_key=r.req_key,text=r.text,
                             candidates=rank_candidates(r.text,index,top_k))
            for r in reqs
        ]
    )
