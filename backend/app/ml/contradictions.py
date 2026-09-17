"""SRS Guardian - Semantic Contradiction Detection with NLI and On-Demand Captum Attribution.

Mechanism 2 of Phase 12 (Contradiction Detection).
Uses a pretrained MNLI model (facebook/bart-large-mnli from local cache)
with candidate pair blocking (entity overlap + embedding cosine similarity >= 0.55),
hard disk caching to avoid recomputation, and on-demand Captum LayerIntegratedGradients.
All outputs are labeled 'POTENTIAL contradiction'.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
import logging
from pathlib import Path
import re
from typing import Any

import numpy as np
import spacy
import torch

from backend.app.ml.embeddings import encode

logger = logging.getLogger(__name__)

# Cache directory & paths
CACHE_DIR = Path("data/cache")
NLI_CACHE_PATH = CACHE_DIR / "nli_cache.json"
ATTRIBUTION_CACHE_PATH = CACHE_DIR / "nli_attributions_cache.json"

_NLI_CACHE: dict[str, dict[str, Any]] | None = None
_ATTRIBUTION_CACHE: dict[str, Any] | None = None

_TOKENIZER = None
_MODEL = None
_SPACY_NLP = None

MODEL_NAME = "facebook/bart-large-mnli"


def get_spacy_nlp():
    """Lazily loads spaCy model for entity/noun extraction."""
    global _SPACY_NLP
    if _SPACY_NLP is None:
        try:
            _SPACY_NLP = spacy.load("en_core_web_sm")
        except Exception:
            import spacy.cli
            spacy.cli.download("en_core_web_sm")
            _SPACY_NLP = spacy.load("en_core_web_sm")
    return _SPACY_NLP


def load_nli_cache() -> dict[str, dict[str, Any]]:
    """Loads NLI inference cache from disk."""
    global _NLI_CACHE
    if _NLI_CACHE is None:
        if NLI_CACHE_PATH.exists():
            try:
                with open(NLI_CACHE_PATH, "r", encoding="utf-8") as f:
                    _NLI_CACHE = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load NLI cache: {e}")
                _NLI_CACHE = {}
        else:
            _NLI_CACHE = {}
    return _NLI_CACHE


def save_nli_cache() -> None:
    """Flushes NLI inference cache to disk."""
    global _NLI_CACHE
    if _NLI_CACHE is not None:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(NLI_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(_NLI_CACHE, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to persist NLI cache: {e}")


def load_attribution_cache() -> dict[str, Any]:
    """Loads on-demand token attribution cache from disk."""
    global _ATTRIBUTION_CACHE
    if _ATTRIBUTION_CACHE is None:
        if ATTRIBUTION_CACHE_PATH.exists():
            try:
                with open(ATTRIBUTION_CACHE_PATH, "r", encoding="utf-8") as f:
                    _ATTRIBUTION_CACHE = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load attribution cache: {e}")
                _ATTRIBUTION_CACHE = {}
        else:
            _ATTRIBUTION_CACHE = {}
    return _ATTRIBUTION_CACHE


def save_attribution_cache() -> None:
    """Flushes attribution cache to disk."""
    global _ATTRIBUTION_CACHE
    if _ATTRIBUTION_CACHE is not None:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(ATTRIBUTION_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(_ATTRIBUTION_CACHE, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to persist attribution cache: {e}")


def get_nli_model_and_tokenizer():
    """Lazily loads the pretrained MNLI model and tokenizer on CPU."""
    global _MODEL, _TOKENIZER
    if _MODEL is None or _TOKENIZER is None:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        logger.info(f"Loading MNLI model {MODEL_NAME} on CPU...")
        _TOKENIZER = AutoTokenizer.from_pretrained(MODEL_NAME)
        _MODEL = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
        _MODEL.eval()
    return _MODEL, _TOKENIZER


@dataclass
class SemanticContradictionFinding:
    """Represents a potential semantic contradiction detected by the NLI model."""
    finding_id: str
    req_key_1: str
    req_key_2: str
    requirement_id_1: int | None
    requirement_id_2: int | None
    confidence: float
    premise_text: str
    hypothesis_text: str
    module: str = "contradiction"
    rule_id: str = "SEMANTIC_CONTRADICTION"
    severity: str = "critical"
    human_explanation: str = ""
    suggestion: str = ""
    attributions: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["confidence"] = round(self.confidence, 4)
        return d


def extract_content_lemmas(text: str) -> set[str]:
    """Extracts informative noun, verb, and adjective lemmas from a requirement."""
    nlp = get_spacy_nlp()
    doc = nlp(text)
    lemmas = set()
    stopwords = {
        "system", "shall", "must", "should", "will", "allow", "user", "can",
        "able", "provide", "require", "need", "use", "be", "have", "do",
    }
    for token in doc:
        if token.pos_ in ("NOUN", "PROPN", "VERB", "ADJ") and not token.is_stop:
            lemma = token.lemma_.lower().strip()
            if len(lemma) > 2 and lemma not in stopwords:
                lemmas.add(lemma)
    return lemmas


def select_candidate_pairs(
    requirements: list[dict[str, Any]],
    excluded_pairs: set[tuple[str, str]] | None = None,
    min_similarity: float = 0.55,
) -> list[tuple[dict[str, Any], dict[str, Any], float]]:
    """Selects candidate requirement pairs for NLI evaluation.

    Candidate blocking criteria (to keep execution bounded and cheap):
    1. Not already identified by Mechanism 1 (numeric conflicts).
    2. Shared main entity/subject lemmas >= 1.
    3. Sentence-transformers embedding cosine similarity >= min_similarity.
    """
    if excluded_pairs is None:
        excluded_pairs = set()

    # Pre-extract lemmas and compute/retrieve embeddings in one cached batch
    texts = [r.get("text", "") for r in requirements]
    embeddings = encode(texts) if texts else np.empty((0, 384), dtype=np.float32)

    req_data = []
    for idx, r in enumerate(requirements):
        text = r.get("text", "")
        lemmas = extract_content_lemmas(text)
        emb = embeddings[idx] if len(embeddings) > idx else np.zeros(384, dtype=np.float32)
        req_data.append((r, lemmas, emb))

    candidates: list[tuple[dict[str, Any], dict[str, Any], float]] = []

    n = len(req_data)
    for i in range(n):
        r1, lemmas1, emb1 = req_data[i]
        k1 = r1.get("req_key", str(r1.get("id", "")))

        for j in range(i + 1, n):
            r2, lemmas2, emb2 = req_data[j]
            k2 = r2.get("req_key", str(r2.get("id", "")))

            # Check exclusion
            if (k1, k2) in excluded_pairs or (k2, k1) in excluded_pairs:
                continue

            # Criterion 1: Lemma overlap
            shared_lemmas = lemmas1.intersection(lemmas2)
            if not shared_lemmas:
                continue

            # Criterion 2: Embedding cosine similarity (embeddings from encode are L2 normalized)
            sim = float(np.dot(emb1, emb2))
            if sim >= min_similarity:
                candidates.append((r1, r2, sim))

    return candidates


def evaluate_nli_pair(text_a: str, text_b: str) -> dict[str, float]:
    """Runs bidirectional NLI inference for a pair of texts with disk caching.

    Returns dict mapping label to average probability:
    {'contradiction': float, 'neutral': float, 'entailment': float}
    """
    cache = load_nli_cache()
    pair_str = f"{text_a}:::{text_b}:::{MODEL_NAME}"
    cache_key = hashlib.sha256(pair_str.encode("utf-8")).hexdigest()

    if cache_key in cache:
        return cache[cache_key]

    model, tokenizer = get_nli_model_and_tokenizer()

    def _infer(premise: str, hypothesis: str) -> np.ndarray:
        inputs = tokenizer(premise, hypothesis, return_tensors="pt", truncation=True)
        with torch.no_grad():
            outputs = model(**inputs)
            probs = torch.softmax(outputs.logits, dim=-1)[0].cpu().numpy()
        return probs

    # Bidirectional evaluation: A -> B and B -> A
    # Model id2label: {0: 'contradiction', 1: 'neutral', 2: 'entailment'}
    probs_ab = _infer(text_a, text_b)
    probs_ba = _infer(text_b, text_a)
    avg_probs = (probs_ab + probs_ba) / 2.0

    result = {
        "contradiction": float(avg_probs[0]),
        "neutral": float(avg_probs[1]),
        "entailment": float(avg_probs[2]),
    }

    cache[cache_key] = result
    save_nli_cache()
    return result


def explain_semantic_contradiction(
    premise: str,
    hypothesis: str,
    n_steps: int = 5,
) -> list[dict[str, Any]]:
    """Calculates token-level attribution using Captum LayerIntegratedGradients on-demand."""
    cache = load_attribution_cache()
    cache_key = hashlib.sha256(f"{premise}:::{hypothesis}:::{n_steps}".encode("utf-8")).hexdigest()

    if cache_key in cache:
        return cache[cache_key]

    from captum.attr import LayerIntegratedGradients

    model, tokenizer = get_nli_model_and_tokenizer()
    model.eval()

    inputs = tokenizer(premise, hypothesis, return_tensors="pt", truncation=True)
    input_ids = inputs["input_ids"]

    # Baseline with pad tokens while preserving EOS tokens to satisfy BART constraints
    baseline = torch.full_like(input_ids, tokenizer.pad_token_id)
    baseline[0, -1] = tokenizer.eos_token_id
    eos_indices = (input_ids == tokenizer.eos_token_id).nonzero()
    for idx in eos_indices:
        baseline[tuple(idx)] = tokenizer.eos_token_id

    def predict(ids):
        return model(ids).logits

    lig = LayerIntegratedGradients(predict, model.model.encoder.embed_tokens)
    # Target 0 corresponds to the contradiction class
    attributions = lig.attribute(input_ids, baselines=baseline, target=0, n_steps=n_steps)

    tokens = tokenizer.convert_ids_to_tokens(input_ids[0])
    scores = attributions.sum(dim=-1).squeeze(0).detach().cpu().numpy()

    result: list[dict[str, Any]] = []
    for token, score in zip(tokens, scores):
        clean_token = token.replace("\u0120", " ").strip()
        if clean_token and clean_token not in ("<s>", "</s>", "<pad>"):
            result.append({
                "token": clean_token,
                "attribution": round(float(score), 4),
            })

    cache[cache_key] = result
    save_attribution_cache()
    return result


def detect_semantic_contradictions(
    requirements: list[dict[str, Any]],
    excluded_pairs: set[tuple[str, str]] | None = None,
    confidence_threshold: float = 0.70,
) -> list[SemanticContradictionFinding]:
    """Detects semantic contradictions across requirements using candidate blocking and NLI.

    Args:
        requirements: List of requirement dicts ('id', 'req_key', 'text').
        excluded_pairs: Pairs already flagged by Mechanism 1 to exclude.
        confidence_threshold: Minimum NLI contradiction probability (default 0.70).

    Returns:
        List of SemanticContradictionFinding objects.
    """
    candidates = select_candidate_pairs(requirements, excluded_pairs=excluded_pairs)
    findings: list[SemanticContradictionFinding] = []

    for r1, r2, sim in candidates:
        k1 = r1.get("req_key", str(r1.get("id", "")))
        k2 = r2.get("req_key", str(r2.get("id", "")))
        text1 = r1.get("text", "")
        text2 = r2.get("text", "")

        nli_res = evaluate_nli_pair(text1, text2)
        contra_prob = nli_res.get("contradiction", 0.0)

        if contra_prob >= confidence_threshold:
            finding_id = f"SEMANTIC_CONTRADICTION_{k1}_{k2}"
            explanation = (
                f"POTENTIAL contradiction: Requirement {k1} and Requirement {k2} have conflicting "
                f"semantic logic (NLI contradiction probability: {contra_prob * 100:.1f}%, "
                f"embedding similarity: {sim * 100:.1f}%)."
            )
            suggestion = (
                f"Review {k1} and {k2} to ensure that their functional statements are mutually compatible "
                f"and do not prescribe contradictory operational behavior."
            )

            findings.append(
                SemanticContradictionFinding(
                    finding_id=finding_id,
                    req_key_1=k1,
                    req_key_2=k2,
                    requirement_id_1=r1.get("id"),
                    requirement_id_2=r2.get("id"),
                    confidence=contra_prob,
                    premise_text=text1,
                    hypothesis_text=text2,
                    human_explanation=explanation,
                    suggestion=suggestion,
                )
            )

    return findings
