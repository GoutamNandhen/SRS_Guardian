import json
from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator


class TokenExplanation(BaseModel):
    token: str
    shap_value: float


class RequirementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    req_key: str
    text: str
    source_layer: str
    confidence: float
    char_start: int
    char_end: int
    section: str | None = None
    classification_label: str | None = None
    classification_prob: float | None = None
    classification_explanation: list[TokenExplanation] | None = None
    created_at: datetime

    @field_validator("classification_explanation", mode="before")
    @classmethod
    def parse_explanation(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v


class DocumentExtractResponse(BaseModel):
    document_id: int
    status: str
    extracted_count: int
    requirements: list[RequirementResponse]


from backend.app.schemas.scoring import WaterfallStepResponse
from backend.app.schemas.issue import IssueResponse
from backend.app.schemas.iso_checks import EarsResultSchema, IsoCheckItemSchema


class RequirementDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    req_key: str
    text: str
    source_layer: str
    confidence: float
    char_start: int
    char_end: int
    section: str | None = None
    classification_label: str | None = None
    classification_prob: float | None = None
    classification_explanation: list[TokenExplanation] | None = None
    quality_score: float
    sub_scores: dict[str, float]
    waterfall: list[WaterfallStepResponse]
    issues: list[IssueResponse]
    ears_result: EarsResultSchema | None = None
    iso_checks: list[IsoCheckItemSchema] | None = None
    created_at: datetime


    @field_validator("classification_explanation", mode="before")
    @classmethod
    def parse_explanation(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v

