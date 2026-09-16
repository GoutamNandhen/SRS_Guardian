from datetime import datetime
from pydantic import BaseModel, ConfigDict


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
    created_at: datetime


class DocumentExtractResponse(BaseModel):
    document_id: int
    status: str
    extracted_count: int
    requirements: list[RequirementResponse]
