from dataclasses import dataclass
from typing import Any
import numpy as np
import spacy
from backend.app.core.config import settings
from backend.app.ml.embeddings import encode

try:
    nlp = spacy.load("en_core_web_sm")
except Exception:
    nlp = spacy.blank("en")


@dataclass
class KeyPhrase:
    text: str
    start: int
    end: int
    phrase_type: str  # "noun_chunk", "verb_phrase", or "token"


_PHRASE_CACHE: dict[str, list[KeyPhrase]] = {}


def extract_key_phrases(text: str) -> list[KeyPhrase]:
    """Extracts informative noun chunks and verb-object action phrases from text."""
    if text in _PHRASE_CACHE:
        return _PHRASE_CACHE[text]

    doc = nlp(text)
    phrases: list[KeyPhrase] = []
    seen_spans: set[tuple[int, int]] = set()

    # 1. Noun chunks
    for chunk in doc.noun_chunks:
        clean_text = chunk.text.strip()
        if len(clean_text) <= 1:
            continue
        span = (chunk.start_char, chunk.end_char)
        if span not in seen_spans:
            seen_spans.add(span)
            phrases.append(
                KeyPhrase(
                    text=clean_text,
                    start=chunk.start_char,
                    end=chunk.end_char,
                    phrase_type="noun_chunk",
                )
            )

    # 2. Verb-object phrases (e.g., "reset their password", "recover forgotten passwords")
    for token in doc:
        if token.pos_ == "VERB":
            dobjs = [c for c in token.children if c.dep_ in ("dobj", "pobj")]
            for dobj in dobjs:
                start_char = min(token.idx, dobj.left_edge.idx)
                end_char = max(
                    token.idx + len(token.text),
                    dobj.right_edge.idx + len(dobj.right_edge.text),
                )
                phrase_str = text[start_char:end_char].strip()
                span = (start_char, end_char)
                if span not in seen_spans and len(phrase_str) > 3:
                    seen_spans.add(span)
                    phrases.append(
                        KeyPhrase(
                            text=phrase_str,
                            start=start_char,
                            end=end_char,
                            phrase_type="verb_phrase",
                        )
                    )

    # Fallback if no chunks/phrases found: non-stop words
    if not phrases:
        for token in doc:
            if not token.is_stop and not token.is_punct and len(token.text) > 2:
                phrases.append(
                    KeyPhrase(
                        text=token.text,
                        start=token.idx,
                        end=token.idx + len(token.text),
                        phrase_type="token",
                    )
                )

    _PHRASE_CACHE[text] = phrases
    return phrases


def attribute_similarity(
    text_1: str,
    text_2: str,
    top_k: int = 4,
    min_phrase_sim: float = 0.50,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Computes phrase-level similarity attribution between two requirement texts.

    Returns:
        aligned_pairs: list of dicts with phrase_1, phrase_2, similarity, span_1, span_2
        spans: combined list of highlighted spans for both requirements
        factors: list of explanation factors for the unified schema
    """
    phrases_1 = extract_key_phrases(text_1)
    phrases_2 = extract_key_phrases(text_2)

    if not phrases_1 or not phrases_2:
        return [], [], []

    texts_to_encode = [p.text for p in phrases_1] + [p.text for p in phrases_2]
    embeddings = encode(texts_to_encode)

    n1 = len(phrases_1)
    embs_1 = embeddings[:n1]
    embs_2 = embeddings[n1:]

    # Cosine similarity matrix between phrases of text_1 and phrases of text_2
    sim_matrix = np.dot(embs_1, embs_2.T)

    aligned_candidates = []
    for i, p1 in enumerate(phrases_1):
        for j, p2 in enumerate(phrases_2):
            sim = float(sim_matrix[i, j])
            if sim >= min_phrase_sim:
                aligned_candidates.append((sim, i, j))

    # Sort descending by similarity
    aligned_candidates.sort(key=lambda x: x[0], reverse=True)

    # Greedy non-overlapping matching
    used_1: set[int] = set()
    used_2: set[int] = set()
    aligned_pairs: list[dict[str, Any]] = []
    factors: list[dict[str, Any]] = []
    spans: list[dict[str, Any]] = []

    for sim, i, j in aligned_candidates:
        if i in used_1 or j in used_2:
            continue
        p1 = phrases_1[i]
        p2 = phrases_2[j]

        used_1.add(i)
        used_2.add(j)

        pair_info = {
            "phrase_1": p1.text,
            "phrase_2": p2.text,
            "similarity": round(sim, 4),
            "span_1": {"start": p1.start, "end": p1.end, "text": p1.text},
            "span_2": {"start": p2.start, "end": p2.end, "text": p2.text},
        }
        aligned_pairs.append(pair_info)

        factors.append(
            {
                "name": f"'{p1.text}' <-> '{p2.text}'",
                "contribution": round(sim, 4),
                "direction": "positive",
            }
        )

        spans.append(
            {
                "start": p1.start,
                "end": p1.end,
                "text": p1.text,
                "weight": round(sim, 4),
                "requirement": "req_1",
            }
        )
        spans.append(
            {
                "start": p2.start,
                "end": p2.end,
                "text": p2.text,
                "weight": round(sim, 4),
                "requirement": "req_2",
            }
        )

        if len(aligned_pairs) >= top_k:
            break

    return aligned_pairs, spans, factors


def extract_content_lemmas(text: str) -> set[str]:
    """Extracts content lemmas (nouns, proper nouns, verbs) for candidate blocking."""
    doc = nlp(text)
    return {
        token.lemma_.lower()
        for token in doc
        if token.pos_ in ("NOUN", "PROPN", "VERB")
        and not token.is_stop
        and len(token.text) > 2
    }


def batch_extract_content_lemmas(texts: list[str]) -> list[set[str]]:
    """Batched extraction of content lemmas using spaCy nlp.pipe with parser/ner disabled."""
    if not texts:
        return []
    pipe_kwargs = {"batch_size": 256}
    disabled = []
    if nlp.has_pipe("ner"):
        disabled.append("ner")
    if nlp.has_pipe("parser"):
        disabled.append("parser")
    if disabled:
        pipe_kwargs["disable"] = disabled

    results: list[set[str]] = []
    for doc in nlp.pipe(texts, **pipe_kwargs):
        lemmas = {
            token.lemma_.lower()
            for token in doc
            if token.pos_ in ("NOUN", "PROPN", "VERB")
            and not token.is_stop
            and len(token.text) > 2
        }
        results.append(lemmas)
    return results


def find_duplicates(
    requirements: list[dict[str, Any]],
    threshold: float | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Detects semantic duplicate pairs among a collection of requirements.

    Args:
        requirements: List of dicts with keys: 'id', 'req_key', 'text'
        threshold: Cosine similarity cutoff (defaults to settings.DUPLICATE_SIMILARITY_THRESHOLD)

    Returns:
        (duplicate_pairs, total_pairs_checked)
    """
    if threshold is None:
        threshold = settings.DUPLICATE_SIMILARITY_THRESHOLD

    n = len(requirements)
    if n < 2:
        return [], 0

    # 1. Encode all requirement texts with cached embeddings
    texts = [r["text"] for r in requirements]
    embeddings = encode(texts)

    # 2. Candidate pair selection (blocking for >50 requirements)
    use_blocking = n > 50
    lemma_sets = batch_extract_content_lemmas(texts) if use_blocking else []

    candidate_i: list[int] = []
    candidate_j: list[int] = []

    if use_blocking:
        for i in range(n):
            l1 = lemma_sets[i]
            for j in range(i + 1, n):
                if l1.intersection(lemma_sets[j]):
                    candidate_i.append(i)
                    candidate_j.append(j)
    else:
        for i in range(n):
            for j in range(i + 1, n):
                candidate_i.append(i)
                candidate_j.append(j)

    total_pairs_checked = len(candidate_i)
    if total_pairs_checked == 0:
        return [], 0

    # 3. Vectorized similarity calculation across all candidates in one shot
    i_arr = np.array(candidate_i, dtype=np.int32)
    j_arr = np.array(candidate_j, dtype=np.int32)
    # Cosine similarity for normalized embeddings: dot product of row pairs
    sims = np.sum(embeddings[i_arr] * embeddings[j_arr], axis=1)

    # 4. Filter only pairs exceeding threshold
    match_mask = sims >= threshold
    matching_indices = np.where(match_mask)[0]

    duplicate_results: list[dict[str, Any]] = []

    for idx in matching_indices:
        i = candidate_i[idx]
        j = candidate_j[idx]
        sim = float(sims[idx])

        r1 = requirements[i]
        r2 = requirements[j]

        # Perform similarity attribution
        aligned_pairs, spans, factors = attribute_similarity(
            r1["text"], r2["text"]
        )

        matched_phrases_summary = ", ".join(
            f"'{p['phrase_1']}' <-> '{p['phrase_2']}'"
            for p in aligned_pairs[:2]
        ) or "overall semantic meaning"

        explanation = {
            "finding_id": f"DUP-{r1['id']}-{r2['id']}",
            "module": "duplicates",
            "method": "embedding_similarity",
            "rule_id": "SEMANTIC_DUPLICATE",
            "spans": spans,
            "factors": factors,
            "human_explanation": (
                f"POTENTIAL duplicate detected between {r1['req_key']} and "
                f"{r2['req_key']} with semantic similarity of {sim * 100:.1f}%. "
                f"Aligned concepts: {matched_phrases_summary}."
            ),
            "suggestion": (
                "Review both requirements to consolidate duplicate "
                "functionality or clearly differentiate their scope."
            ),
            "confidence": round(sim, 4),
        }

        duplicate_results.append(
            {
                "requirement_id_1": r1["id"],
                "req_key_1": r1["req_key"],
                "text_1": r1["text"],
                "requirement_id_2": r2["id"],
                "req_key_2": r2["req_key"],
                "text_2": r2["text"],
                "similarity_score": round(sim, 4),
                "is_potential_duplicate": True,
                "aligned_phrases": aligned_pairs,
                "explanation": explanation,
            }
        )

    duplicate_results.sort(key=lambda x: x["similarity_score"], reverse=True)
    return duplicate_results, total_pairs_checked
