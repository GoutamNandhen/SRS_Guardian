import json
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Response
from sqlalchemy.orm import Session
from backend.app.services.reports import (
    generate_html_report,
    generate_csv_report,
    generate_pdf_report,
)
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.logging import logger
from backend.app.models.document import (
    Document,
    DocumentVersion,
    Requirement,
    Issue,
    Review,
)
from backend.app.schemas.document import DocumentListItem, DocumentDetail
from backend.app.schemas.requirement import (
    RequirementResponse,
    DocumentExtractResponse,
)
from backend.app.schemas.duplicate import DocumentDuplicatesResponse
from backend.app.schemas.scoring import (
    DocumentQualitySummaryResponse,
    RequirementScoreResponse,
    WaterfallStepResponse,
    PenaltyApplied,
    WorstRequirementItem,
)
from backend.app.schemas.issue import (
    IssueResponse,
    ReviewResponse,
    DocumentAnalysisResponse,
)


from backend.app.nlp.extractors import extract_text
from backend.app.nlp.cleaning import clean_text
from backend.app.nlp.requirement_extractor import extract_requirements
from backend.app.nlp.ambiguity import analyze_ambiguity
from backend.app.nlp.readability import analyze_readability
from backend.app.nlp.scoring import score_requirement, score_document
from backend.app.ml.classifier import classify
from backend.app.ml.explain_classifier import explain
from backend.app.ml.duplicates import find_duplicates
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
        # Run Phase 4 Classification & SHAP token explanation
        label, prob = classify(r.text)
        exp_tokens = explain(r.text)
        exp_data = [{"token": t, "shap_value": v} for t, v in exp_tokens]

        db_req = Requirement(
            document_id=doc.id,
            req_key=r.req_id,
            text=r.text,
            source_layer=r.source_layer,
            confidence=r.confidence,
            char_start=r.char_start,
            char_end=r.char_end,
            section=r.section,
            classification_label=label,
            classification_prob=prob,
            classification_explanation=json.dumps(exp_data),
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


@router.get(
    "/{document_id}/duplicates",
    response_model=DocumentDuplicatesResponse,
    summary="Detect potential semantic duplicate requirements with similarity attribution",
)
def get_document_duplicates(
    document_id: int,
    threshold: float | None = None,
    db: Session = Depends(get_db),
):
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

    req_dicts = [
        {"id": r.id, "req_key": r.req_key, "text": r.text}
        for r in reqs
    ]

    active_threshold = (
        threshold
        if threshold is not None
        else settings.DUPLICATE_SIMILARITY_THRESHOLD
    )
    duplicates, total_pairs = find_duplicates(
        req_dicts, threshold=active_threshold
    )

    logger.info(
        f"Duplicate check on doc {document_id}: {len(duplicates)} pairs found "
        f"out of {total_pairs} pairs checked (threshold={active_threshold})"
    )

    return DocumentDuplicatesResponse(
        document_id=doc.id,
        threshold=active_threshold,
        total_pairs_checked=total_pairs,
        duplicate_pairs_count=len(duplicates),
        duplicates=duplicates,
    )


@router.get(
    "/{document_id}/quality",
    response_model=DocumentQualitySummaryResponse,
    summary="Compute deterministic quality scores and waterfall breakdowns for document requirements",
)
def get_document_quality(
    document_id: int,
    db: Session = Depends(get_db),
):
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

    req_dicts = [
        {"id": r.id, "req_key": r.req_key, "text": r.text}
        for r in reqs
    ]

    # Find duplicates to incorporate duplicate penalties
    duplicates, _ = find_duplicates(req_dicts)
    duplicate_map: dict[int, dict[str, Any]] = {}
    for d in duplicates:
        r1_id = d["requirement_id_1"]
        r2_id = d["requirement_id_2"]
        if r1_id not in duplicate_map:
            duplicate_map[r1_id] = {
                "target_req_key": d["req_key_2"],
                "similarity_score": d["similarity_score"],
            }
        if r2_id not in duplicate_map:
            duplicate_map[r2_id] = {
                "target_req_key": d["req_key_1"],
                "similarity_score": d["similarity_score"],
            }

    scored_reqs = []
    for r in reqs:
        ambiguity_findings = analyze_ambiguity(r.text)
        readability_metrics = analyze_readability(r.text)
        is_dup = r.id in duplicate_map
        dup_info = duplicate_map.get(r.id)

        score_res = score_requirement(
            req_key=r.req_key,
            text=r.text,
            ambiguity_findings=ambiguity_findings,
            readability_metrics=readability_metrics,
            is_duplicate=is_dup,
            duplicate_info=dup_info,
            requirement_id=r.id,
        )
        scored_reqs.append(score_res)

    doc_summary = score_document(scored_reqs, document_id=doc.id)

    logger.info(
        f"Quality score computed for doc {document_id}: mean {doc_summary.mean_score:.1f}, "
        f"{doc_summary.total_requirements} requirements analyzed"
    )

    return DocumentQualitySummaryResponse(
        document_id=doc_summary.document_id,
        total_requirements=doc_summary.total_requirements,
        mean_score=round(doc_summary.mean_score, 1),
        median_score=round(doc_summary.median_score, 1),
        min_score=round(doc_summary.min_score, 1),
        max_score=round(doc_summary.max_score, 1),
        distribution=doc_summary.distribution,
        worst_requirements=[
            WorstRequirementItem(
                requirement_id=w["requirement_id"],
                req_key=w["req_key"],
                overall_score=round(w["overall_score"], 1),
                issues_count=w["issues_count"],
                text=w["text"],
            )
            for w in doc_summary.worst_requirements
        ],
        issue_counts=doc_summary.issue_counts,
        requirements=[
            RequirementScoreResponse(
                requirement_id=r.requirement_id,
                req_key=r.req_key,
                text=r.text,
                overall_score=round(r.overall_score, 1),
                sub_scores={k: round(v, 1) for k, v in r.sub_scores.items()},
                waterfall=[
                    WaterfallStepResponse(
                        step_number=w.step_number,
                        step_name=w.step_name,
                        rule_id=w.rule_id,
                        deduction=round(w.deduction, 1),
                        current_score=round(w.current_score, 1),
                        explanation=w.explanation,
                    )
                    for w in r.waterfall
                ],
                issues_count=r.issues_count,
                penalties_applied=[
                    PenaltyApplied(
                        rule_id=p["rule_id"],
                        name=p["name"],
                        deduction=round(p["deduction"], 1),
                        matched_text=p.get("matched_text"),
                    )
                    for p in r.penalties_applied
                ],
            )
            for r in scored_reqs
        ],
    )


@router.post(
    "/{document_id}/analyze",
    response_model=DocumentAnalysisResponse,
    summary="Run full end-to-end analysis pipeline and persist detected issues",
)
def analyze_document(
    document_id: int,
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )

    # 1. Ensure requirements are extracted
    reqs = (
        db.query(Requirement)
        .filter(Requirement.document_id == document_id)
        .order_by(Requirement.id.asc())
        .all()
    )
    if not reqs:
        extracted_reqs = extract_requirements(doc.cleaned_text)
        reqs = []
        for r in extracted_reqs:
            label, prob = classify(r.text)
            exp_tokens = explain(r.text)
            exp_data = [{"token": t, "shap_value": v} for t, v in exp_tokens]
            db_req = Requirement(
                document_id=doc.id,
                req_key=r.req_id,
                text=r.text,
                source_layer=r.source_layer,
                confidence=r.confidence,
                char_start=r.char_start,
                char_end=r.char_end,
                section=r.section,
                classification_label=label,
                classification_prob=prob,
                classification_explanation=json.dumps(exp_data),
            )
            db.add(db_req)
            reqs.append(db_req)
        db.commit()
        for r in reqs:
            db.refresh(r)
    else:
        for r in reqs:
            if not r.classification_label:
                label, prob = classify(r.text)
                exp_tokens = explain(r.text)
                exp_data = [{"token": t, "shap_value": v} for t, v in exp_tokens]
                r.classification_label = label
                r.classification_prob = prob
                r.classification_explanation = json.dumps(exp_data)
        db.commit()

    # 2. Run Duplicate Detection across all requirements
    req_dicts = [{"id": r.id, "req_key": r.req_key, "text": r.text} for r in reqs]
    duplicates, _ = find_duplicates(req_dicts)

    duplicate_map: dict[int, dict[str, Any]] = {}
    for d in duplicates:
        r1_id = d["requirement_id_1"]
        r2_id = d["requirement_id_2"]
        if r1_id not in duplicate_map:
            duplicate_map[r1_id] = {
                "target_req_key": d["req_key_2"],
                "similarity_score": d["similarity_score"],
                "explanation": d["explanation"],
            }
        if r2_id not in duplicate_map:
            duplicate_map[r2_id] = {
                "target_req_key": d["req_key_1"],
                "similarity_score": d["similarity_score"],
                "explanation": d["explanation"],
            }

    # 3. Clear previous ai_flagged issues for idempotency (preserve human-reviewed issues)
    req_ids = [r.id for r in reqs]
    db.query(Issue).filter(
        Issue.requirement_id.in_(req_ids),
        Issue.status == "ai_flagged"
    ).delete(synchronize_session=False)
    db.commit()

    # 4. Generate & persist issues and calculate scores
    new_issues: list[Issue] = []
    scored_reqs = []

    for r in reqs:
        ambiguity_findings = analyze_ambiguity(r.text)
        readability_metrics = analyze_readability(r.text)
        is_dup = r.id in duplicate_map
        dup_info = duplicate_map.get(r.id)

        # Persist ambiguity issues
        for f in ambiguity_findings:
            issue = Issue(
                requirement_id=r.id,
                module="ambiguity",
                type=f.rule_id,
                severity="warning",
                explanation_json=json.dumps(f.to_dict()),
                status="ai_flagged",
            )
            new_issues.append(issue)

        # Persist duplicate issue
        if is_dup and dup_info:
            issue = Issue(
                requirement_id=r.id,
                module="duplicates",
                type="SEMANTIC_DUPLICATE",
                severity="warning",
                explanation_json=json.dumps(dup_info["explanation"]),
                status="ai_flagged",
            )
            new_issues.append(issue)

        # Calculate requirement score
        score_res = score_requirement(
            req_key=r.req_key,
            text=r.text,
            ambiguity_findings=ambiguity_findings,
            readability_metrics=readability_metrics,
            is_duplicate=is_dup,
            duplicate_info=dup_info,
            requirement_id=r.id,
        )
        scored_reqs.append(score_res)

    db.add_all(new_issues)
    doc.status = "analyzed"
    db.commit()

    # Calculate document quality summary
    doc_summary = score_document(scored_reqs, document_id=doc.id)

    # Count total active issues for document
    total_issues = (
        db.query(Issue)
        .filter(Issue.requirement_id.in_(req_ids))
        .count()
    )

    summary_response = DocumentQualitySummaryResponse(
        document_id=doc_summary.document_id,
        total_requirements=doc_summary.total_requirements,
        mean_score=round(doc_summary.mean_score, 1),
        median_score=round(doc_summary.median_score, 1),
        min_score=round(doc_summary.min_score, 1),
        max_score=round(doc_summary.max_score, 1),
        distribution=doc_summary.distribution,
        worst_requirements=[
            WorstRequirementItem(
                requirement_id=w["requirement_id"],
                req_key=w["req_key"],
                overall_score=round(w["overall_score"], 1),
                issues_count=w["issues_count"],
                text=w["text"],
            )
            for w in doc_summary.worst_requirements
        ],
        issue_counts=doc_summary.issue_counts,
        requirements=[
            RequirementScoreResponse(
                requirement_id=r.requirement_id,
                req_key=r.req_key,
                text=r.text,
                overall_score=round(r.overall_score, 1),
                sub_scores={k: round(v, 1) for k, v in r.sub_scores.items()},
                waterfall=[
                    WaterfallStepResponse(
                        step_number=w.step_number,
                        step_name=w.step_name,
                        rule_id=w.rule_id,
                        deduction=round(w.deduction, 1),
                        current_score=round(w.current_score, 1),
                        explanation=w.explanation,
                    )
                    for w in r.waterfall
                ],
                issues_count=r.issues_count,
                penalties_applied=[
                    PenaltyApplied(
                        rule_id=p["rule_id"],
                        name=p["name"],
                        deduction=round(p["deduction"], 1),
                        matched_text=p.get("matched_text"),
                    )
                    for p in r.penalties_applied
                ],
            )
            for r in scored_reqs
        ],
    )

    logger.info(
        f"Document {document_id} analyzed: {len(new_issues)} new issues persisted, "
        f"{total_issues} total issues recorded"
    )

    return DocumentAnalysisResponse(
        document_id=doc.id,
        status=doc.status,
        requirements_count=len(reqs),
        issues_count=total_issues,
        quality_summary=summary_response,
    )


@router.get(
    "/{document_id}/issues",
    response_model=list[IssueResponse],
    summary="Get all issues for a document with optional filtering by module, type, and status",
)
def get_document_issues(
    document_id: int,
    module: str | None = None,
    type: str | None = None,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )

    query = (
        db.query(Issue)
        .join(Requirement, Requirement.id == Issue.requirement_id)
        .filter(Requirement.document_id == document_id)
    )

    if module:
        query = query.filter(Issue.module == module.lower())
    if type:
        query = query.filter(Issue.type == type)
    if status_filter:
        query = query.filter(Issue.status == status_filter.lower())

    issues = query.order_by(Issue.id.asc()).all()

    results = []
    for issue in issues:
        reviews_list = [
            ReviewResponse.model_validate(r)
            for r in sorted(issue.reviews, key=lambda x: x.reviewed_at, reverse=True)
        ]
        results.append(
            IssueResponse(
                id=issue.id,
                requirement_id=issue.requirement_id,
                req_key=issue.requirement.req_key if issue.requirement else None,
                module=issue.module,
                type=issue.type,
                severity=issue.severity,
                explanation=issue.explanation_json,
                status=issue.status,
                is_human_reviewed=(issue.status != "ai_flagged"),
                created_at=issue.created_at,
                reviews=reviews_list,
            )
        )

    return results


@router.get(
    "/{document_id}/report",
    summary="Generate and export comprehensive quality and review report (HTML, CSV, PDF)",
)
def get_document_report(
    document_id: int,
    format: str = "html",
    type: str = "requirements",
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )

    clean_filename = Path(doc.filename).stem
    fmt = format.lower()

    if fmt == "html":
        html_content = generate_html_report(document_id, db)
        return Response(content=html_content, media_type="text/html")
    elif fmt == "csv":
        csv_content = generate_csv_report(document_id, db, csv_type=type)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{clean_filename}_report_{type}.csv"'
            },
        )
    elif fmt == "pdf":
        pdf_bytes = generate_pdf_report(document_id, db)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{clean_filename}_report.pdf"'
            },
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format '{format}'. Supported formats: html, csv, pdf.",
        )
