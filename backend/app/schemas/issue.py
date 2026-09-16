import json
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, field_validator
from backend.app.schemas.scoring import DocumentQualitySummaryResponse


class ReviewActionRequest(BaseModel):
    action: str  # "accept", "reject", "edit", "mark_reviewed"
    edited_text: str | None = None
    note: str | None = None

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        allowed = {"accept", "reject", "edit", "mark_reviewed"}
        if v.lower() not in allowed:
            raise ValueError(f"Action must be one of {allowed}")
        return v.lower()


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    issue_id: int
    action: str
    edited_text: str | None = None
    note: str | None = None
    reviewed_at: datetime


class IssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    requirement_id: int
    req_key: str | None = None
    module: str
    type: str
    severity: str
    explanation: dict[str, Any]
    status: str
    is_human_reviewed: bool = False
    created_at: datetime
    reviews: list[ReviewResponse] = []

    @field_validator("explanation", mode="before")
    @classmethod
    def parse_explanation(cls, v: Any) -> dict[str, Any]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return {"raw": v}
        return v if isinstance(v, dict) else {}


class DocumentAnalysisResponse(BaseModel):
    document_id: int
    status: str
    requirements_count: int
    issues_count: int
    quality_summary: DocumentQualitySummaryResponse
