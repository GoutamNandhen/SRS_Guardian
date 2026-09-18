from typing import Any
from pydantic import BaseModel, ConfigDict


class EarsResultSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pattern: str
    is_valid_ears: bool
    trigger: str | None = None
    state: str | None = None
    feature: str | None = None
    condition: str | None = None
    system: str | None = None
    modal: str | None = None
    response: str | None = None
    missing_elements: list[str] = []
    explanation: str = ""
    suggestion: str | None = None
    matched_template: str | None = None


class IsoCheckItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    check_id: str
    characteristic: str
    status: str  # "passed", "warning", "failed"
    score_deduction: float
    explanation: str
    suggestion: str | None = None
    spans: list[dict[str, Any]] = []


class RequirementIsoReportSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    requirement_id: int | None = None
    req_key: str
    text: str
    ears_result: EarsResultSchema
    checks: list[IsoCheckItemSchema]
    total_iso_deductions: float
    conformance_summary: str


class DocumentStandardsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: int
    total_requirements: int
    standards_name: str = "Selected machine-checkable checks based on ISO/IEC/IEEE 29148"
    fully_conforming_count: int
    warning_count: int
    failed_count: int
    requirements: list[RequirementIsoReportSchema]
