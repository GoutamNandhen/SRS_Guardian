from backend.app.schemas.document import DocumentBase, DocumentListItem, DocumentDetail
from backend.app.schemas.requirement import (
    RequirementResponse,
    DocumentExtractResponse,
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

__all__ = [
    "DocumentBase",
    "DocumentListItem",
    "DocumentDetail",
    "RequirementResponse",
    "DocumentExtractResponse",
    "PhraseSpan",
    "AlignedPhrase",
    "DuplicatePair",
    "DocumentDuplicatesResponse",
    "WaterfallStepResponse",
    "PenaltyApplied",
    "RequirementScoreResponse",
    "WorstRequirementItem",
    "DocumentQualitySummaryResponse",
]


