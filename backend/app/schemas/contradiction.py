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


class DocumentContradictionsResponse(BaseModel):
    document_id: int
    total_contradictions_count: int
    numeric_conflicts_count: int
    semantic_contradictions_count: int
    contradictions: list[ContradictionItem]


class ContradictionExplainResponse(BaseModel):
    issue_id: int
    finding_id: str
    tokens: list[dict[str, Any]]
