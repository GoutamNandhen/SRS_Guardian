from backend.app.schemas.document import DocumentBase, DocumentListItem, DocumentDetail
from backend.app.schemas.requirement import (
    RequirementResponse,
    DocumentExtractResponse,
    RequirementDetailResponse,
)
from backend.app.schemas.duplicate import (
    PhraseSpan,
    AlignedPhrase,
    DuplicatePair,
    DocumentDuplicatesResponse,
)
from backend.app.schemas.scoring import (
    WaterfallStepResponse,
    PenaltyApplied,
    RequirementScoreResponse,
    WorstRequirementItem,
    DocumentQualitySummaryResponse,
)
from backend.app.schemas.issue import (
    ReviewActionRequest,
    ReviewResponse,
    IssueResponse,
    DocumentAnalysisResponse,
)

__all__ = [
    "DocumentBase",
    "DocumentListItem",
    "DocumentDetail",
    "RequirementResponse",
    "DocumentExtractResponse",
    "RequirementDetailResponse",
    "PhraseSpan",
    "AlignedPhrase",
    "DuplicatePair",
    "DocumentDuplicatesResponse",
    "WaterfallStepResponse",
    "PenaltyApplied",
    "RequirementScoreResponse",
    "WorstRequirementItem",
    "DocumentQualitySummaryResponse",
    "ReviewActionRequest",
    "ReviewResponse",
    "IssueResponse",
    "DocumentAnalysisResponse",
]



