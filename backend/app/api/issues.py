from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.logging import logger
from backend.app.models.document import Issue, Review, Requirement
from backend.app.schemas.issue import ReviewActionRequest, IssueResponse, ReviewResponse

router = APIRouter(prefix="/issues", tags=["issues"])


@router.post(
    "/{issue_id}/review",
    response_model=IssueResponse,
    summary="Record human review decision on an issue (accept, reject, edit, mark_reviewed)",
)
def review_issue(
    issue_id: int,
    payload: ReviewActionRequest,
    db: Session = Depends(get_db),
):
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Issue with ID {issue_id} not found",
        )

    action = payload.action.lower()

    # Update issue status
    if action == "accept":
        issue.status = "accepted"
    elif action == "reject":
        issue.status = "rejected"
    elif action == "edit":
        issue.status = "edited"
        if payload.edited_text and payload.edited_text.strip():
            req = db.query(Requirement).filter(Requirement.id == issue.requirement_id).first()
            if req:
                req.text = payload.edited_text.strip()
    elif action == "mark_reviewed":
        issue.status = "reviewed"

    # Create immutable review record
    review = Review(
        issue_id=issue.id,
        action=action,
        edited_text=payload.edited_text,
        note=payload.note,
    )
    db.add(review)
    db.commit()
    db.refresh(issue)

    logger.info(
        f"Issue {issue_id} reviewed by human: action='{action}', new_status='{issue.status}'"
    )

    reviews_list = [
        ReviewResponse.model_validate(r)
        for r in sorted(issue.reviews, key=lambda x: x.reviewed_at, reverse=True)
    ]

    return IssueResponse(
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
