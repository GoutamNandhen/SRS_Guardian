import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.logging import logger
from backend.app.models.document import Issue
from backend.app.ml.contradictions import explain_semantic_contradiction
from backend.app.schemas.contradiction import (
    ContradictionExplainResponse,
    ContradictionVerifyRequest,
    ContradictionVerifyResponse,
    ContradictionVerifyResult,
)

router = APIRouter(prefix="/contradictions", tags=["contradictions"])


@router.get(
    "/{issue_id}/explain",
    response_model=ContradictionExplainResponse,
    summary="Compute or retrieve on-demand token-level attribution for a contradiction finding",
)
def explain_contradiction(
    issue_id: int,
    db: Session = Depends(get_db),
):
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Issue with ID {issue_id} not found",
        )

    if issue.module != "contradiction":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Issue {issue_id} is from module '{issue.module}', not 'contradiction'",
        )

    explanation_data = {}
    if issue.explanation_json:
        try:
            explanation_data = json.loads(issue.explanation_json)
        except Exception:
            explanation_data = {}

    finding_id = explanation_data.get("finding_id", f"ISSUE_{issue.id}")

    if issue.type == "SEMANTIC_CONTRADICTION":
        premise = explanation_data.get("premise_text", "")
        hypothesis = explanation_data.get("hypothesis_text", "")
        if not premise or not hypothesis:
            tokens = []
        else:
            tokens = explain_semantic_contradiction(premise, hypothesis, n_steps=5)
    else:
        # Numeric constraint conflict - return token spans from constraints
        c1 = explanation_data.get("constraint_1", {})
        c2 = explanation_data.get("constraint_2", {})
        tokens = [
            {"token": c1.get("raw_span", c1.get("entity", "")), "attribution": 1.0},
            {"token": c2.get("raw_span", c2.get("entity", "")), "attribution": -1.0},
        ]

    return ContradictionExplainResponse(
        issue_id=issue.id,
        finding_id=finding_id,
        tokens=tokens,
    )


@router.post(
    "/verify",
    response_model=ContradictionVerifyResponse,
    summary="Verify candidate requirement pairs for semantic contradiction on-demand",
)
def verify_contradictions_endpoint(
    request: ContradictionVerifyRequest,
    db: Session = Depends(get_db),
):
    if request.document_id:
        from backend.app.api.documents import verify_document_contradictions
        return verify_document_contradictions(request.document_id, request, db=db)

    from backend.app.ml.contradictions import verify_candidate_pairs
    pairs_data = [
        {
            "finding_id": p.finding_id or f"SEMANTIC_CONTRADICTION_{p.req_key_1}_{p.req_key_2}",
            "req_key_1": p.req_key_1,
            "req_key_2": p.req_key_2,
            "requirement_id_1": p.requirement_id_1,
            "requirement_id_2": p.requirement_id_2,
            "text_1": p.text_1,
            "text_2": p.text_2,
        }
        for p in request.pairs
    ]
    verified_results = verify_candidate_pairs(pairs_data, confidence_threshold=0.70, batch_size=8)
    results = [
        ContradictionVerifyResult(
            finding_id=vr["finding_id"],
            req_key_1=vr["req_key_1"],
            req_key_2=vr["req_key_2"],
            requirement_id_1=vr["requirement_id_1"],
            requirement_id_2=vr["requirement_id_2"],
            classification=vr["nli_classification"],
            confidence=vr["confidence"],
            probabilities=vr.get("nli_probabilities", {}),
            is_contradiction=vr["is_contradiction"],
            verification_status=vr["verification_status"],
            cached=vr["cached"],
            human_explanation=vr["human_explanation"],
            suggestion=vr["suggestion"],
            issue_id=None,
        )
        for vr in verified_results
    ]
    return ContradictionVerifyResponse(
        total_verified=len(results),
        contradictions_found=sum(1 for r in results if r.is_contradiction),
        results=results,
    )
