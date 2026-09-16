from typing import Any
from pydantic import BaseModel, Field


class PhraseSpan(BaseModel):
    start: int
    end: int
    text: str


class AlignedPhrase(BaseModel):
    phrase_1: str
    phrase_2: str
    similarity: float
    span_1: PhraseSpan
    span_2: PhraseSpan


class DuplicatePair(BaseModel):
    requirement_id_1: int
    req_key_1: str
    text_1: str
    requirement_id_2: int
    req_key_2: str
    text_2: str
    similarity_score: float
    is_potential_duplicate: bool = True
    aligned_phrases: list[AlignedPhrase] = Field(default_factory=list)
    explanation: dict[str, Any]


class DocumentDuplicatesResponse(BaseModel):
    document_id: int
    threshold: float
    total_pairs_checked: int
    duplicate_pairs_count: int
    duplicates: list[DuplicatePair]
