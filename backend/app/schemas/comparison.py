from typing import Any
from pydantic import BaseModel, Field


class IssueDiffItem(BaseModel):
    rule_id: str
    severity: str
    human_explanation: str


class RequirementComparisonItem(BaseModel):
    status: str = Field(..., description="added, removed, modified, or unchanged")
    req_key: str
    text_v1: str | None = None
    text_v2: str | None = None
    score_v1: float | None = None
    score_v2: float | None = None
    score_delta: float | None = None
    similarity: float | None = None
    diff_text: str | None = None
    resolved_issues: list[IssueDiffItem] = Field(default_factory=list)
    new_issues: list[IssueDiffItem] = Field(default_factory=list)
    persistent_issues: list[IssueDiffItem] = Field(default_factory=list)


class DocumentComparisonResponse(BaseModel):
    doc1_id: int
    doc1_filename: str
    doc2_id: int
    doc2_filename: str
    total_v1: int
    total_v2: int
    added_count: int
    removed_count: int
    modified_count: int
    unchanged_count: int
    avg_score_v1: float
    avg_score_v2: float
    score_delta: float
    total_resolved_issues: int
    total_new_issues: int
    items: list[RequirementComparisonItem]
