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
]

