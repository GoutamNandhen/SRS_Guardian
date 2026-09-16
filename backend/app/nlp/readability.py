from dataclasses import dataclass
from typing import Any
import spacy
import textstat

try:
    nlp = spacy.load("en_core_web_sm")
except Exception:
    nlp = spacy.blank("en")


@dataclass
class ReadabilityMetrics:
    word_count: int
    clause_count: int
    max_nesting_depth: int
    passive_voice_ratio: float
    flesch_reading_ease: float
    gunning_fog: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "word_count": self.word_count,
            "clause_count": self.clause_count,
            "max_nesting_depth": self.max_nesting_depth,
            "passive_voice_ratio": round(self.passive_voice_ratio, 4),
            "flesch_reading_ease": round(self.flesch_reading_ease, 2),
            "gunning_fog": round(self.gunning_fog, 2),
        }


def compute_clause_count_and_depth(doc: Any) -> tuple[int, int]:
    clause_deps = {"advcl", "relcl", "ccomp", "xcomp", "acl", "conj"}
    clause_tokens = [
        token
        for token in doc
        if token.dep_ == "ROOT" or token.dep_ in clause_deps
    ]
    clause_count = max(1, len(clause_tokens))

    # Calculate maximum clause nesting depth
    max_depth = 1
    for token in doc:
        current_depth = 1
        curr = token
        while curr.dep_ != "ROOT" and curr.head != curr:
            if curr.dep_ in clause_deps:
                current_depth += 1
            curr = curr.head
        if current_depth > max_depth:
            max_depth = current_depth

    return clause_count, max_depth


def compute_passive_voice_ratio(doc: Any) -> float:
    verbs = [t for t in doc if t.pos_ in ("VERB", "AUX")]
    if not verbs:
        return 0.0

    passive_verbs = set()
    for token in doc:
        if token.dep_ == "nsubjpass":
            passive_verbs.add(token.head)

    return len(passive_verbs) / len(verbs)


def analyze_readability(text: str) -> ReadabilityMetrics:
    doc = nlp(text)
    words = [t for t in doc if not t.is_punct and not t.is_space]
    word_count = len(words) if words else len(text.split())

    clause_count, max_depth = compute_clause_count_and_depth(doc)
    passive_ratio = compute_passive_voice_ratio(doc)

    fre = float(textstat.flesch_reading_ease(text))
    fog = float(textstat.gunning_fog(text))

    return ReadabilityMetrics(
        word_count=word_count,
        clause_count=clause_count,
        max_nesting_depth=max_depth,
        passive_voice_ratio=passive_ratio,
        flesch_reading_ease=fre,
        gunning_fog=fog,
    )
