from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.document import Requirement
from backend.app.schemas.requirement import (
    RequirementResponse,
    TokenExplanation,
)
from backend.app.ml.explain_classifier import explain

router = APIRouter(prefix="/requirements", tags=["requirements"])


@router.get(
    "/{requirement_id}",
    response_model=RequirementResponse,
    summary="Get requirement detail by ID with classification and SHAP explanation",
)
def get_requirement(requirement_id: int, db: Session = Depends(get_db)):
    req = db.query(Requirement).filter(Requirement.id == requirement_id).first()
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Requirement with ID {requirement_id} not found",
        )
    return RequirementResponse.model_validate(req)


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
