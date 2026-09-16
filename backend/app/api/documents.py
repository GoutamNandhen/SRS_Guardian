import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.logging import logger
from backend.app.models.document import Document, DocumentVersion, Requirement
from backend.app.schemas.document import DocumentListItem, DocumentDetail
from backend.app.schemas.requirement import (
    RequirementResponse,
    DocumentExtractResponse,
)
from backend.app.nlp.extractors import extract_text
from backend.app.nlp.cleaning import clean_text
from backend.app.nlp.requirement_extractor import extract_requirements
from backend.app.utils.file_validation import validate_file

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "/upload",
    response_model=DocumentDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Upload, extract, clean, and store an SRS document",
)
async def upload_document(
    file: UploadFile = File(...), db: Session = Depends(get_db)
):
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / file.filename
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}",
        )
    finally:
        file.file.close()

    # Validate file
    is_valid, err_msg = validate_file(file_path, max_mb=settings.MAX_UPLOAD_MB)
    if not is_valid:
        file_path.unlink(missing_ok=True)
        logger.warning(f"File validation failed: {err_msg}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg
        )

    # Ingestion and cleaning
    try:
        extracted = extract_text(file_path)
        cleaned = clean_text(extracted.text, extracted.pages)
    except Exception as e:
        logger.error(f"Extraction failed for {file.filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Text extraction failed: {str(e)}",
        )

    # Database record creation
    db_doc = Document(
        filename=file.filename,
        file_type=file_path.suffix.lower().lstrip("."),
        file_size=file_path.stat().st_size,
        page_count=extracted.page_count,
        status="uploaded",
        raw_text=cleaned.raw_text,
        cleaned_text=cleaned.cleaned_text,
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)

    # Initial version record
    db_version = DocumentVersion(document_id=db_doc.id, version_label="v1.0")
    db.add(db_version)
    db.commit()

    logger.info(f"Document uploaded and ingested: ID {db_doc.id} ({file.filename})")

    return DocumentDetail(
        id=db_doc.id,
        filename=db_doc.filename,
        file_type=db_doc.file_type,
        file_size=db_doc.file_size,
        page_count=db_doc.page_count,
        status=db_doc.status,
        uploaded_at=db_doc.uploaded_at,
        raw_text=db_doc.raw_text,
        cleaned_text=db_doc.cleaned_text,
        version=db_version.version_label,
        requirement_count=0,
    )


@router.get(
    "",
    response_model=list[DocumentListItem],
    summary="List all uploaded documents",
)
def list_documents(db: Session = Depends(get_db)):
    docs = db.query(Document).order_by(Document.uploaded_at.desc()).all()
    results = []
    for doc in docs:
        req_count = len(doc.requirements)
        results.append(
            DocumentListItem(
                id=doc.id,
                filename=doc.filename,
                file_type=doc.file_type,
                file_size=doc.file_size,
                page_count=doc.page_count,
                status=doc.status,
                uploaded_at=doc.uploaded_at,
                requirement_count=req_count,
            )
        )
    return results


@router.get(
    "/{document_id}",
    response_model=DocumentDetail,
    summary="Get document details by ID",
)
def get_document(document_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )

    version_label = doc.versions[-1].version_label if doc.versions else "v1.0"
    req_count = len(doc.requirements)

    return DocumentDetail(
        id=doc.id,
        filename=doc.filename,
        file_type=doc.file_type,
        file_size=doc.file_size,
        page_count=doc.page_count,
        status=doc.status,
        uploaded_at=doc.uploaded_at,
        raw_text=doc.raw_text,
        cleaned_text=doc.cleaned_text,
        version=version_label,
        requirement_count=req_count,
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a document and all related records",
)
def delete_document(document_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )

    db.delete(doc)
    db.commit()
    logger.info(f"Document {document_id} deleted successfully")
    return {"status": "deleted", "id": document_id}


@router.post(
    "/{document_id}/extract",
    response_model=DocumentExtractResponse,
    status_code=status.HTTP_200_OK,
    summary="Run requirement extraction on a document and store results",
)
def extract_document_requirements(
    document_id: int, db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )

    # Delete existing requirements for clean idempotency
    db.query(Requirement).filter(
        Requirement.document_id == document_id
    ).delete()

    # Run extraction engine
    extracted_reqs = extract_requirements(doc.cleaned_text)

    db_reqs: list[Requirement] = []
    for r in extracted_reqs:
        db_req = Requirement(
            document_id=doc.id,
            req_key=r.req_id,
            text=r.text,
            source_layer=r.source_layer,
            confidence=r.confidence,
            char_start=r.char_start,
            char_end=r.char_end,
            section=r.section,
        )
        db.add(db_req)
        db_reqs.append(db_req)

    doc.status = "extracted"
    db.commit()

    # Refresh items to populate IDs and timestamps
    for r in db_reqs:
        db.refresh(r)

    logger.info(
        f"Extracted {len(db_reqs)} requirements for document ID {document_id}"
    )

    response_items = [
        RequirementResponse.model_validate(r) for r in db_reqs
    ]

    return DocumentExtractResponse(
        document_id=doc.id,
        status=doc.status,
        extracted_count=len(response_items),
        requirements=response_items,
    )


@router.get(
    "/{document_id}/requirements",
    response_model=list[RequirementResponse],
    summary="List all extracted requirements for a document",
)
def get_document_requirements(document_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )

    reqs = (
        db.query(Requirement)
        .filter(Requirement.document_id == document_id)
        .order_by(Requirement.id.asc())
        .all()
    )

    return [RequirementResponse.model_validate(r) for r in reqs]
