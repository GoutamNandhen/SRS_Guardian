import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.logging import logger
from backend.app.models.document import Issue
from backend.app.ml.contradictions import explain_semantic_contradiction
from backend.app.schemas.contradiction import ContradictionExplainResponse

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
