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
from backend.app.nlp.numeric_constraints import detect_numeric_conflicts
from backend.app.ml.contradictions import detect_semantic_contradictions
from backend.app.schemas.contradiction import (
    DocumentContradictionsResponse,
    ContradictionItem,
    ContradictionConstraintSchema,
)
from backend.app.nlp.iso_checks import analyze_iso_checks
from backend.app.schemas.iso_checks import (
    EarsResultSchema,
    IsoCheckItemSchema,
    RequirementIsoReportSchema,
    DocumentStandardsResponse,
)
from backend.app.utils.file_validation import validate_file
from backend.app.ml.clustering import cluster_requirements
from backend.app.schemas.clustering import (
    DocumentClustersResponse,
    ClusterGroup,
)
from backend.app.nlp.version_comparison import compare_document_versions
from backend.app.schemas.comparison import (
    DocumentComparisonResponse,
    RequirementComparisonItem,
    IssueDiffItem,
)


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

        req_dict = {
            "id": r.id,
            "req_key": r.req_key,
            "text": r.text,
            "source_layer": r.source_layer,
        }
        iso_report = analyze_iso_checks(
            req_dict,
            all_reqs=req_dicts,
            ambiguity_findings=ambiguity_findings,
        )

        score_res = score_requirement(
            req_key=r.req_key,
            text=r.text,
            ambiguity_findings=ambiguity_findings,
            readability_metrics=readability_metrics,
            is_duplicate=is_dup,
            duplicate_info=dup_info,
            iso_checks=iso_report.checks,
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

    # 2b. Run Contradiction Detection across all requirements (Phase 12)
    # Mechanism 1: Deterministic numeric constraint conflict engine
    numeric_findings = detect_numeric_conflicts(req_dicts)
    excluded_pairs = {(f.req_key_1, f.req_key_2) for f in numeric_findings}

    # Mechanism 2: Candidate-blocked NLI semantic contradiction engine
    semantic_findings = detect_semantic_contradictions(req_dicts, excluded_pairs=excluded_pairs)

    contradiction_map: dict[int, list[dict[str, Any]]] = {}
    for nf in numeric_findings:
        if nf.requirement_id_1:
            contradiction_map.setdefault(nf.requirement_id_1, []).append({
                "target_req_key": nf.req_key_2,
                "reason": nf.human_explanation,
                "finding": nf.to_dict(),
            })
        if nf.requirement_id_2:
            contradiction_map.setdefault(nf.requirement_id_2, []).append({
                "target_req_key": nf.req_key_1,
                "reason": nf.human_explanation,
                "finding": nf.to_dict(),
            })

    for sf in semantic_findings:
        if sf.requirement_id_1:
            contradiction_map.setdefault(sf.requirement_id_1, []).append({
                "target_req_key": sf.req_key_2,
                "reason": sf.human_explanation,
                "finding": sf.to_dict(),
            })
        if sf.requirement_id_2:
            contradiction_map.setdefault(sf.requirement_id_2, []).append({
                "target_req_key": sf.req_key_1,
                "reason": sf.human_explanation,
                "finding": sf.to_dict(),
            })

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

        # Persist contradiction issues (Phase 12)
        if r.id in contradiction_map:
            for c_item in contradiction_map[r.id]:
                finding_dict = c_item["finding"]
                rule_id = finding_dict.get("rule_id", "NUMERIC_CONSTRAINT_CONFLICT")
                issue = Issue(
                    requirement_id=r.id,
                    module="contradiction",
                    type=rule_id,
                    severity="critical",
                    explanation_json=json.dumps(finding_dict),
                    status="ai_flagged",
                )
                new_issues.append(issue)

        # Run ISO 29148 checks (Phase 13)
        req_dict = {
            "id": r.id,
            "req_key": r.req_key,
            "text": r.text,
            "source_layer": r.source_layer,
        }
        iso_report = analyze_iso_checks(
            req_dict,
            all_reqs=req_dicts,
            ambiguity_findings=ambiguity_findings,
        )

        # Persist standards / ISO check issues (Phase 13)
        for chk in iso_report.checks:
            if chk.status in ("warning", "failed") and chk.check_id != "ISO_UNAMBIGUOUS":
                issue = Issue(
                    requirement_id=r.id,
                    module="standards",
                    type=chk.check_id,
                    severity="warning" if chk.status == "warning" else "critical",
                    explanation_json=json.dumps(chk.to_dict()),
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
            contradiction_findings=contradiction_map.get(r.id),
            iso_checks=iso_report.checks,
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

    # Calculate compact breakdown counts for Phase 18.2
    all_doc_issues = (
        db.query(Issue)
        .filter(Issue.requirement_id.in_(req_ids))
        .all()
    ) if req_ids else []
    req_ids_needing_attention = {
        i.requirement_id for i in all_doc_issues if i.severity in ("critical", "warning")
    }
    needs_att_cnt = len(req_ids_needing_attention)
    crit_cnt = sum(1 for i in all_doc_issues if i.severity == "critical")
    warn_cnt = sum(1 for i in all_doc_issues if i.severity == "warning")
    no_iss_cnt = max(0, len(reqs) - needs_att_cnt)

    logger.info(
        f"Document {document_id} analyzed: {len(new_issues)} new issues persisted, "
        f"{total_issues} total issues recorded (critical: {crit_cnt}, warning: {warn_cnt})"
    )

    return DocumentAnalysisResponse(
        document_id=doc.id,
        status=doc.status,
        requirements_count=len(reqs),
        issues_count=total_issues,
        quality_summary=summary_response,
        filename=doc.filename,
        needs_attention_count=needs_att_cnt,
        critical_count=crit_cnt,
        warning_count=warn_cnt,
        no_issues_count=no_iss_cnt,
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


@router.get(
    "/{document_id}/contradictions",
    response_model=DocumentContradictionsResponse,
    summary="Get all detected contradiction pairs and conflicts for a document",
)
def get_document_contradictions(
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
    if not reqs:
        return DocumentContradictionsResponse(
            document_id=document_id,
            total_contradictions_count=0,
            numeric_conflicts_count=0,
            semantic_contradictions_count=0,
            contradictions=[],
        )

    req_key_map = {r.req_key: r for r in reqs}
    req_ids = [r.id for r in reqs]

    issues = (
        db.query(Issue)
        .filter(
            Issue.requirement_id.in_(req_ids),
            Issue.module == "contradiction",
        )
        .all()
    )

    items: list[ContradictionItem] = []
    seen_finding_ids = set()

    for issue in issues:
        if not issue.explanation_json:
            continue
        try:
            data = json.loads(issue.explanation_json)
        except Exception:
            continue

        finding_id = data.get("finding_id", f"ISSUE_{issue.id}")
        if finding_id in seen_finding_ids:
            continue
        seen_finding_ids.add(finding_id)

        rule_id = issue.type or data.get("rule_id", "NUMERIC_CONSTRAINT_CONFLICT")
        mechanism = "numeric" if "NUMERIC" in rule_id else "semantic"

        k1 = data.get("req_key_1", "")
        k2 = data.get("req_key_2", "")
        r1 = req_key_map.get(k1)
        r2 = req_key_map.get(k2)

        c1_schema = None
        c2_schema = None
        if "constraint_1" in data and data["constraint_1"]:
            c1_raw = data["constraint_1"]
            c1_schema = ContradictionConstraintSchema(
                entity=c1_raw.get("entity", ""),
                attribute=c1_raw.get("attribute", ""),
                comparator=c1_raw.get("comparator", ""),
                value=float(c1_raw.get("value", 0.0)),
                value_max=float(c1_raw["value_max"]) if c1_raw.get("value_max") is not None else None,
                unit=c1_raw.get("unit", ""),
                range_display=c1_raw.get("range_display", f"{c1_raw.get('comparator', '')} {c1_raw.get('value', '')} {c1_raw.get('unit', '')}"),
                raw_span=c1_raw.get("raw_span", ""),
            )

        if "constraint_2" in data and data["constraint_2"]:
            c2_raw = data["constraint_2"]
            c2_schema = ContradictionConstraintSchema(
                entity=c2_raw.get("entity", ""),
                attribute=c2_raw.get("attribute", ""),
                comparator=c2_raw.get("comparator", ""),
                value=float(c2_raw.get("value", 0.0)),
                value_max=float(c2_raw["value_max"]) if c2_raw.get("value_max") is not None else None,
                unit=c2_raw.get("unit", ""),
                range_display=c2_raw.get("range_display", f"{c2_raw.get('comparator', '')} {c2_raw.get('value', '')} {c2_raw.get('unit', '')}"),
                raw_span=c2_raw.get("raw_span", ""),
            )

        items.append(
            ContradictionItem(
                finding_id=finding_id,
                issue_id=issue.id,
                mechanism=mechanism,
                rule_id=rule_id,
                severity=issue.severity or "critical",
                confidence=float(data.get("confidence", 1.0)),
                requirement_id_1=r1.id if r1 else None,
                req_key_1=k1,
                text_1=r1.text if r1 else data.get("premise_text", ""),
                constraint_1=c1_schema,
                requirement_id_2=r2.id if r2 else None,
                req_key_2=k2,
                text_2=r2.text if r2 else data.get("hypothesis_text", ""),
                constraint_2=c2_schema,
                human_explanation=data.get("human_explanation", ""),
                suggestion=data.get("suggestion", ""),
                status=issue.status or "ai_flagged",
            )
        )

    num_count = sum(1 for it in items if it.mechanism == "numeric")
    sem_count = sum(1 for it in items if it.mechanism == "semantic")

    return DocumentContradictionsResponse(
        document_id=document_id,
        total_contradictions_count=len(items),
        numeric_conflicts_count=num_count,
        semantic_contradictions_count=sem_count,
        contradictions=items,
    )


@router.get(
    "/{document_id}/standards",
    response_model=DocumentStandardsResponse,
    summary="Get ISO 29148 checks and EARS pattern analysis for a document",
)
def get_document_standards(
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
    if not reqs:
        return DocumentStandardsResponse(
            document_id=document_id,
            total_requirements=0,
            fully_conforming_count=0,
            warning_count=0,
            failed_count=0,
            requirements=[],
        )

    req_dicts = [
        {"id": r.id, "req_key": r.req_key, "text": r.text, "source_layer": r.source_layer}
        for r in reqs
    ]

    reports: list[RequirementIsoReportSchema] = []
    fully_conforming = 0
    total_warnings = 0
    total_failed = 0

    for r in reqs:
        r_dict = {"id": r.id, "req_key": r.req_key, "text": r.text, "source_layer": r.source_layer}
        ambiguity_findings = analyze_ambiguity(r.text)
        iso_report = analyze_iso_checks(r_dict, all_reqs=req_dicts, ambiguity_findings=ambiguity_findings)

        has_warnings = any(c.status == "warning" for c in iso_report.checks)
        has_failed = any(c.status == "failed" for c in iso_report.checks)

        if not has_warnings and not has_failed and iso_report.ears_result.is_valid_ears:
            fully_conforming += 1
        if has_warnings:
            total_warnings += 1
        if has_failed:
            total_failed += 1

        reports.append(
            RequirementIsoReportSchema(
                requirement_id=r.id,
                req_key=r.req_key,
                text=r.text,
                ears_result=EarsResultSchema.model_validate(iso_report.ears_result.to_dict()),
                checks=[IsoCheckItemSchema.model_validate(c.to_dict()) for c in iso_report.checks],
                total_iso_deductions=iso_report.total_iso_deductions,
                conformance_summary=iso_report.conformance_summary,
            )
        )

    return DocumentStandardsResponse(
        document_id=document_id,
        total_requirements=len(reqs),
        fully_conforming_count=fully_conforming,
        warning_count=total_warnings,
        failed_count=total_failed,
        requirements=reports,
    )


@router.get(
    "/{document_id}/clusters",
    response_model=DocumentClustersResponse,
    summary="Get thematic requirements clusters with distinctive topic labels for a document",
)
def get_document_clusters(
    document_id: int,
    k: int | None = None,
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
        .order_by(Requirement.id)
        .all()
    )

    req_dicts = [
        {
            "id": r.id,
            "req_key": r.req_key,
            "text": r.text,
            "classification_label": r.classification_label,
            "section": r.section,
        }
        for r in reqs
    ]

    result = cluster_requirements(req_dicts, n_clusters=k)
    return DocumentClustersResponse(
        document_id=document_id,
        total_requirements=result["total_requirements"],
        num_clusters=result["num_clusters"],
        clusters=[ClusterGroup(**c) for c in result["clusters"]],
    )


@router.get(
    "/{document_id}/compare/{other_document_id}",
    response_model=DocumentComparisonResponse,
    summary="Compare two documents or document versions with semantic diffing and score deltas",
)
def compare_documents_endpoint(
    document_id: int,
    other_document_id: int,
    db: Session = Depends(get_db),
):
    try:
        result = compare_document_versions(document_id, other_document_id, db=db)
        return DocumentComparisonResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )



