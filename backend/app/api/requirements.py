from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.document import Requirement
from backend.app.schemas.requirement import (
    RequirementResponse,
    RequirementDetailResponse,
    TokenExplanation,
)
from backend.app.schemas.scoring import WaterfallStepResponse
from backend.app.schemas.issue import IssueResponse, ReviewResponse
from backend.app.schemas.iso_checks import EarsResultSchema, IsoCheckItemSchema
from backend.app.nlp.ambiguity import analyze_ambiguity
from backend.app.nlp.readability import analyze_readability
from backend.app.nlp.scoring import score_requirement
from backend.app.nlp.iso_checks import analyze_iso_checks
from backend.app.nlp.ears import analyze_ears
from backend.app.ml.explain_classifier import explain
from backend.app.schemas.llm import (
    RewriteSuggestionRequest,
    RewriteSuggestionResponse,
    GherkinGenerationRequest,
    GherkinGenerationResponse,
)
from backend.app.services.llm import suggest_rewrite, generate_gherkin
from backend.app.nlp.gherkin import generate_gherkin_skeleton


router = APIRouter(prefix="/requirements", tags=["requirements"])


@router.get(
    "/{requirement_id}",
    response_model=RequirementDetailResponse,
    summary="Get requirement full detail by ID with findings, quality score waterfall, and issues",
)
def get_requirement(requirement_id: int, db: Session = Depends(get_db)):
    req = db.query(Requirement).filter(Requirement.id == requirement_id).first()
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Requirement with ID {requirement_id} not found",
        )

    # Calculate quality score and waterfall
    ambiguity_findings = analyze_ambiguity(req.text)
    readability_metrics = analyze_readability(req.text)

    # Check if there is an active duplicate issue
    dup_issue = next(
        (i for i in req.issues if i.type == "SEMANTIC_DUPLICATE" and i.status != "rejected"),
        None,
    )
    is_dup = dup_issue is not None
    dup_info = None
    if dup_issue:
        try:
            import json
            exp_data = json.loads(dup_issue.explanation_json)
            dup_info = {"target_req_key": "duplicate requirement", "similarity_score": exp_data.get("confidence", 0.8)}
        except Exception:
            pass

    # Check if there are active contradiction issues
    contra_issues = [
        i for i in req.issues if i.module == "contradiction" and i.status != "rejected"
    ]
    contra_findings = []
    for ci in contra_issues:
        try:
            import json
            c_data = json.loads(ci.explanation_json)
            k1 = c_data.get("req_key_1", "")
            k2 = c_data.get("req_key_2", "")
            target = k2 if req.req_key == k1 else k1
            contra_findings.append({
                "target_req_key": target or "conflicting requirement",
                "reason": c_data.get("human_explanation", ""),
            })
        except Exception:
            pass

    # Run ISO 29148 checks and EARS analysis (Phase 13)
    all_doc_reqs = (
        db.query(Requirement)
        .filter(Requirement.document_id == req.document_id)
        .all()
    )
    all_req_dicts = [
        {"id": r.id, "req_key": r.req_key, "text": r.text, "source_layer": r.source_layer}
        for r in all_doc_reqs
    ]
    current_req_dict = {
        "id": req.id,
        "req_key": req.req_key,
        "text": req.text,
        "source_layer": req.source_layer,
    }
    iso_report = analyze_iso_checks(
        current_req_dict,
        all_reqs=all_req_dicts,
        ambiguity_findings=ambiguity_findings,
    )

    score_res = score_requirement(
        req_key=req.req_key,
        text=req.text,
        ambiguity_findings=ambiguity_findings,
        readability_metrics=readability_metrics,
        is_duplicate=is_dup,
        duplicate_info=dup_info,
        contradiction_findings=contra_findings,
        iso_checks=iso_report.checks,
        requirement_id=req.id,
    )

    issues_list = []
    for issue in req.issues:
        reviews_list = [
            ReviewResponse.model_validate(r)
            for r in sorted(issue.reviews, key=lambda x: x.reviewed_at, reverse=True)
        ]
        issues_list.append(
            IssueResponse(
                id=issue.id,
                requirement_id=issue.requirement_id,
                req_key=req.req_key,
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

    waterfall_resp = [
        WaterfallStepResponse(
            step_number=w.step_number,
            step_name=w.step_name,
            rule_id=w.rule_id,
            deduction=round(w.deduction, 1),
            current_score=round(w.current_score, 1),
            explanation=w.explanation,
        )
        for w in score_res.waterfall
    ]

    ears_schema = EarsResultSchema.model_validate(iso_report.ears_result.to_dict())
    iso_checks_schema = [
        IsoCheckItemSchema.model_validate(c.to_dict()) for c in iso_report.checks
    ]

    return RequirementDetailResponse(
        id=req.id,
        document_id=req.document_id,
        req_key=req.req_key,
        text=req.text,
        source_layer=req.source_layer,
        confidence=req.confidence,
        char_start=req.char_start,
        char_end=req.char_end,
        section=req.section,
        classification_label=req.classification_label,
        classification_prob=req.classification_prob,
        classification_explanation=req.classification_explanation,
        quality_score=round(score_res.overall_score, 1),
        sub_scores={k: round(v, 1) for k, v in score_res.sub_scores.items()},
        waterfall=waterfall_resp,
        issues=issues_list,
        ears_result=ears_schema,
        iso_checks=iso_checks_schema,
        created_at=req.created_at,
    )




@router.get(
    "/{requirement_id}/explain",
    response_model=list[TokenExplanation],
    summary="Get on-demand SHAP token explanation for requirement classification",
)
def get_requirement_explanation(
    requirement_id: int, db: Session = Depends(get_db)
):
    req = db.query(Requirement).filter(Requirement.id == requirement_id).first()
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Requirement with ID {requirement_id} not found",
        )

    tokens = explain(req.text, requirement_id=req.id)
    return [
        TokenExplanation(token=t, shap_value=v) for t, v in tokens
    ]


@router.post(
    "/{requirement_id}/suggest-rewrite",
    response_model=RewriteSuggestionResponse,
    summary="Get an AI rewrite suggestion for a requirement resolving detected issues",
)
def suggest_requirement_rewrite(
    requirement_id: int, db: Session = Depends(get_db)
):
    req = db.query(Requirement).filter(Requirement.id == requirement_id).first()
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Requirement with ID {requirement_id} not found",
        )

    # Gather active issues (excluding rejected ones)
    active_issues = [
        {
            "rule_id": issue.rule_id,
            "human_explanation": issue.human_explanation,
            "severity": issue.severity,
            "suggestion": issue.suggestion,
        }
        for issue in req.issues
        if issue.status != "rejected"
    ]

    ears_result = analyze_ears(req.text)
    pattern_name = ears_result.pattern if ears_result else None

    result = suggest_rewrite(
        requirement_text=req.text,
        issues=active_issues,
        ears_pattern=pattern_name,
    )
    return RewriteSuggestionResponse(**result)


@router.post(
    "/{requirement_id}/generate-gherkin",
    response_model=GherkinGenerationResponse,
    summary="Generate standard Gherkin Given/When/Then acceptance criteria for a requirement",
)
def generate_requirement_gherkin(
    requirement_id: int, db: Session = Depends(get_db)
):
    req = db.query(Requirement).filter(Requirement.id == requirement_id).first()
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Requirement with ID {requirement_id} not found",
        )

    result = generate_gherkin_skeleton(
        requirement_text=req.text,
        classification_label=req.classification_label,
        requirement_id=req.id,
    )
    return GherkinGenerationResponse(**result)


@router.post(
    "/suggest-rewrite",
    response_model=RewriteSuggestionResponse,
    summary="Ad-hoc AI rewrite suggestion for arbitrary requirement text",
)
def suggest_adhoc_rewrite(request: RewriteSuggestionRequest):
    result = suggest_rewrite(
        requirement_text=request.requirement_text,
        issues=request.issues,
        ears_pattern=request.ears_pattern,
    )
    return RewriteSuggestionResponse(**result)


@router.post(
    "/generate-gherkin",
    response_model=GherkinGenerationResponse,
    summary="Ad-hoc Gherkin scenario generation for arbitrary requirement text",
)
def generate_adhoc_gherkin(request: GherkinGenerationRequest):
    result = generate_gherkin_skeleton(
        requirement_text=request.requirement_text,
        classification_label=request.classification_label,
        requirement_id=request.requirement_id,
    )
    return GherkinGenerationResponse(**result)

