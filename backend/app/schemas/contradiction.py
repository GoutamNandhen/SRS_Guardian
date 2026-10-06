from typing import Any
from pydantic import BaseModel, Field


class ContradictionConstraintSchema(BaseModel):
    entity: str
    attribute: str
    comparator: str
    value: float
    value_max: float | None = None
    unit: str
    range_display: str
    raw_span: str = ""


class ContradictionItem(BaseModel):
    finding_id: str
    issue_id: int | None = None
    mechanism: str  # "numeric" | "semantic"
    rule_id: str
    severity: str = "critical"
    confidence: float
    requirement_id_1: int | None = None
    req_key_1: str
    text_1: str
    constraint_1: ContradictionConstraintSchema | None = None
    requirement_id_2: int | None = None
    req_key_2: str
    text_2: str
    constraint_2: ContradictionConstraintSchema | None = None
    human_explanation: str
    suggestion: str
    status: str = "ai_flagged"
    verification_status: str = "verified"  # "verified", "unverified", "no_contradiction"
    nli_classification: str | None = None  # "contradiction", "neutral", "entailment"
    cached: bool = False


class DocumentContradictionsResponse(BaseModel):
    document_id: int
    total_contradictions_count: int
    numeric_conflicts_count: int
    semantic_contradictions_count: int
    candidates_count: int = 0
    contradictions: list[ContradictionItem]


class ContradictionExplainResponse(BaseModel):
    issue_id: int
    finding_id: str
    tokens: list[dict[str, Any]]


class ContradictionVerifyPairInput(BaseModel):
    req_key_1: str
    req_key_2: str
    text_1: str
    text_2: str
    requirement_id_1: int | None = None
    requirement_id_2: int | None = None
    finding_id: str | None = None


class ContradictionVerifyRequest(BaseModel):
    document_id: int | None = None
    pairs: list[ContradictionVerifyPairInput]


class ContradictionVerifyResult(BaseModel):
    finding_id: str
    req_key_1: str
    req_key_2: str
    requirement_id_1: int | None = None
    requirement_id_2: int | None = None
    classification: str  # "contradiction" | "neutral" | "entailment"
    confidence: float
    probabilities: dict[str, float]
    is_contradiction: bool
    verification_status: str = "verified"
    cached: bool
    human_explanation: str
    suggestion: str
    issue_id: int | None = None


class ContradictionVerifyResponse(BaseModel):
    total_verified: int
    contradictions_found: int
    results: list[ContradictionVerifyResult]
