"""
SRS Guardian — Schemas for Explainable Visual Review and Comprehensive Reporting (Phase 18).
"""

from typing import Any, List, Optional, Dict
from pydantic import BaseModel, Field


class FindingSpan(BaseModel):
    start: int
    end: int
    text: str
    weight: float = 1.0


def compute_confidence_band(conf: Optional[float]) -> str:
    """
    Computes visualization confidence band without equating confidence with correctness or severity.
    High: >= 0.80
    Medium: >= 0.60 and < 0.80
    Low: < 0.60
    """
    if conf is None:
        return "unavailable"
    if conf >= 0.80:
        return "high"
    if conf >= 0.60:
        return "medium"
    return "low"


class AnnotatedFinding(BaseModel):
    finding_id: str
    issue_id: Optional[int] = None
    requirement_id: int
    req_key: str
    module: str  # "ambiguity", "duplicates", "contradiction", "readability", "standards", "classification"
    type: str    # Rule ID e.g. "CHECK_A_WEAK_TERM", "SEMANTIC_DUPLICATE", "ISO_SINGULAR"
    severity: str  # "info", "warning", "critical"
    confidence: Optional[float] = None
    confidence_band: str = "unavailable"
    source_text: str
    spans: List[FindingSpan] = Field(default_factory=list)
    has_sub_spans: bool = False
    human_explanation: str
    suggestion: Optional[str] = None
    rule_provenance: str
    status: str = "ai_flagged"  # ai_flagged, accepted, rejected, edited, reviewed
    is_pair_finding: bool = False
    target_requirement_id: Optional[int] = None
    target_req_key: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RequirementReviewItem(BaseModel):
    requirement_id: int
    req_key: str
    text: str
    char_start: int
    char_end: int
    section: Optional[str] = None
    source_layer: str
    confidence: float
    classification_label: Optional[str] = None
    classification_prob: Optional[float] = None
    quality_score: float = 100.0
    sub_scores: Dict[str, float] = Field(default_factory=dict)
    waterfall_steps: List[Dict[str, Any]] = Field(default_factory=list)
    ears_pattern: Optional[str] = None
    is_valid_ears: Optional[bool] = None
    findings: List[AnnotatedFinding] = Field(default_factory=list)
    ai_rewrite: Optional[Dict[str, Any]] = None
    gherkin_scenario: Optional[str] = None
    review_status: str = "pending"  # "pending", "accepted", "rejected", "edited", "reviewed"


class ExecutiveReviewRow(BaseModel):
    requirement: str  # e.g. "REQ-001" or "REQ-002 ↔ REQ-003"
    status: str       # "CRITICAL", "WARNING", "OK"
    finding: str      # Concise finding label e.g. "“quickly” is unclear"
    suggested_action: str  # e.g. "Make response time measurable"
    problem_phrase: Optional[str] = None
    short_reason: Optional[str] = None
    is_pair: bool = False
    req_ids: List[int] = Field(default_factory=list)
    confidence: Optional[float] = None
    confidence_band: str = "unavailable"
    text_snippet: Optional[str] = None


class ShapFeatureItem(BaseModel):
    token: str
    shap_value: float
    direction: str  # "positive" (supports predicted class) or "negative" (opposes)


class ShapRequirementAttribution(BaseModel):
    requirement_id: int
    req_key: str
    text: str
    predicted_class: str
    probability: float
    top_features: List[ShapFeatureItem] = Field(default_factory=list)
    human_interpretation: str


class DocumentReviewReportResponse(BaseModel):
    document_id: int
    filename: str
    file_type: str
    page_count: int
    uploaded_at: str
    status: str
    cleaned_text: str
    raw_text: Optional[str] = None
    total_requirements: int
    total_findings: int
    overall_status: str = "ACCEPTABLE"  # "NEEDS ATTENTION", "PASSED WITH WARNINGS", "ACCEPTABLE"
    quality_summary: Dict[str, Any]
    findings_by_severity: Dict[str, int]
    findings_by_module: Dict[str, int]
    findings_by_confidence: Dict[str, int]
    executive_summary_table: List[ExecutiveReviewRow] = Field(default_factory=list)
    requirements: List[RequirementReviewItem]
    all_findings: List[AnnotatedFinding]
    clusters: Optional[List[Dict[str, Any]]] = None
    system_evaluation: Optional[Dict[str, Any]] = None
    shap_attributions: Optional[List[ShapRequirementAttribution]] = None
    dynamic_conclusion: Optional[str] = None
    reviewer_profile: Optional[Dict[str, Any]] = None

