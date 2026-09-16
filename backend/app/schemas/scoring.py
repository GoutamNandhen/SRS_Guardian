from typing import Any
from pydantic import BaseModel, Field


class WaterfallStepResponse(BaseModel):
    step_number: int
    step_name: str
    rule_id: str | None = None
    deduction: float
    current_score: float
    explanation: str


class PenaltyApplied(BaseModel):
    rule_id: str
    name: str
    deduction: float
    matched_text: str | None = None


class RequirementScoreResponse(BaseModel):
    requirement_id: int | None = None
    req_key: str
    text: str
    overall_score: float
    sub_scores: dict[str, float]
    waterfall: list[WaterfallStepResponse]
    issues_count: int
    penalties_applied: list[PenaltyApplied] = Field(default_factory=list)


class WorstRequirementItem(BaseModel):
    requirement_id: int | None = None
    req_key: str
    overall_score: float
    issues_count: int
    text: str


class DocumentQualitySummaryResponse(BaseModel):
    document_id: int | None = None
    total_requirements: int
    mean_score: float
    median_score: float
    min_score: float
    max_score: float
    distribution: dict[str, int]
    worst_requirements: list[WorstRequirementItem]
    issue_counts: dict[str, int]
    requirements: list[RequirementScoreResponse]
