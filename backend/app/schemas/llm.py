from typing import Any
from pydantic import BaseModel, Field


class RewriteSuggestionRequest(BaseModel):
    requirement_id: int | None = None
    requirement_text: str = Field(..., min_length=3, description="Original requirement text to be rewritten")
    issues: list[dict[str, Any]] = Field(default_factory=list, description="Detected ambiguity or standard issues")
    ears_pattern: str | None = Field(None, description="Detected or target EARS pattern name")


class RewriteSuggestionResponse(BaseModel):
    enabled: bool = Field(..., description="Whether LLM service is enabled")
    cached: bool = Field(default=False, description="Whether result was retrieved from local disk cache")
    original_text: str
    suggested_text: str | None = None
    rationale: str | None = None
    changes_made: list[str] = Field(default_factory=list)
    conforms_to_ears: bool = False
    error: str | None = None


class GherkinGenerationRequest(BaseModel):
    requirement_id: int | None = None
    requirement_text: str = Field(..., min_length=3, description="Requirement text to convert into Gherkin test scenarios")
    classification_label: str | None = Field(None, description="Functional or Non-Functional classification")


class GherkinGenerationResponse(BaseModel):
    enabled: bool = Field(..., description="Whether LLM service is enabled")
    cached: bool = Field(default=False, description="Whether result was retrieved from local disk cache")
    requirement_id: int | None = None
    requirement_text: str
    gherkin_scenarios: str | None = None
    error: str | None = None
