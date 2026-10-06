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
            _SPACY_NLP = spacy.blank("en")
            if "sentencizer" not in _SPACY_NLP.pipe_names:
                _SPACY_NLP.add_pipe("sentencizer")
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


SRS_BOILERPLATE_LEMMAS = {
    "system", "shall", "must", "should", "will", "allow", "user", "can",
    "able", "provide", "require", "need", "use", "be", "have", "do",
    "datum", "data", "information", "software", "document", "section",
    "table", "item", "case", "process", "specification", "value", "number",
    "applicable", "include", "specify", "accordance", "paragraph", "appendix",
}

OPPOSITION_WORDS = {
    "not", "no", "never", "cannot", "prohibit", "prevent", "disallow",
    "reject", "abort", "terminate", "exclude", "disable", "forbidden",
    "restricted", "withhold", "deny", "refuse",
}


def extract_content_lemmas(text: str) -> set[str]:
    """Extracts informative noun, verb, and adjective lemmas from a requirement."""
    nlp = get_spacy_nlp()
    doc = nlp(text)
    lemmas = set()
    for token in doc:
        if token.pos_ in ("NOUN", "PROPN", "VERB", "ADJ") and not token.is_stop:
            lemma = token.lemma_.lower().strip()
            if len(lemma) > 2 and lemma not in SRS_BOILERPLATE_LEMMAS:
                lemmas.add(lemma)
    return lemmas


def batch_extract_lemmas_and_opposition(texts: list[str]) -> tuple[list[set[str]], list[bool]]:
    """Batched extraction of content lemmas and opposition markers using nlp.pipe."""
    if not texts:
        return [], []
    nlp = get_spacy_nlp()
    pipe_kwargs = {"batch_size": 256}
    disabled = []
    if nlp.has_pipe("ner"):
        disabled.append("ner")
    if disabled:
        pipe_kwargs["disable"] = disabled

    lemma_sets: list[set[str]] = []
    has_opp_list: list[bool] = []

    for doc in nlp.pipe(texts, **pipe_kwargs):
        lemmas = {
            t.lemma_.lower().strip()
            for t in doc
            if t.pos_ in ("NOUN", "PROPN", "VERB", "ADJ")
            and not t.is_stop
            and len(t.text) > 2
            and t.lemma_.lower().strip() not in SRS_BOILERPLATE_LEMMAS
        }
        has_opp = any(
            t.text.lower() in OPPOSITION_WORDS or t.lemma_.lower() in OPPOSITION_WORDS
            for t in doc
        )
        lemma_sets.append(lemmas)
        has_opp_list.append(has_opp)

    return lemma_sets, has_opp_list


ANTONYM_PAIRS = {
    ("enable", "disable"), ("activate", "deactivate"), ("open", "close"),
    ("start", "stop"), ("accept", "reject"), ("lock", "unlock"),
    ("increase", "decrease"), ("allow", "prohibit"), ("permit", "forbid"),
    ("include", "exclude"), ("connect", "disconnect"), ("show", "hide"),
    ("display", "hide"), ("grant", "revoke"), ("encrypt", "decrypt"),
    ("mandatory", "optional"), ("automatic", "manual"), ("synchronous", "asynchronous"),
    ("internal", "external"), ("online", "offline"), ("allow", "deny"),
    ("permit", "deny"), ("allow", "disallow"), ("permit", "prohibit"),
}
ANTONYM_MAP: dict[str, set[str]] = {}
for _w1, _w2 in ANTONYM_PAIRS:
    ANTONYM_MAP.setdefault(_w1, set()).add(_w2)
    ANTONYM_MAP.setdefault(_w2, set()).add(_w1)


def select_candidate_pairs(
    requirements: list[dict[str, Any]],
    excluded_pairs: set[tuple[str, str]] | None = None,
    min_similarity: float = 0.55,
) -> list[tuple[dict[str, Any], dict[str, Any], float]]:
    """Selects candidate requirement pairs for NLI evaluation.

    Candidate blocking criteria (to keep execution bounded, fast, and technically defensible):
    1. Not already identified by Mechanism 1 (numeric conflicts).
    2. Embedding cosine similarity >= min_similarity.
    3. Shared content lemmas >= 1.
    4. Obvious non-contradictions are filtered:
       - Purely affirmative pairs with similarity >= 0.80 are duplicates/paraphrases, not contradictions.
       - Purely affirmative pairs with similarity < 0.70 lack conflicting semantics.
       - Pairs with polarity difference or antonymous predicates are retained down to min_similarity.
    """
    if excluded_pairs is None:
        excluded_pairs = set()

    n = len(requirements)
    if n < 2:
        return []

    texts = [r.get("text", "") for r in requirements]
    embeddings = encode(texts) if texts else np.empty((0, 384), dtype=np.float32)

    # Batched lemma extraction
    lemma_sets, has_opp_list = batch_extract_lemmas_and_opposition(texts)

    # Precomputed antonym sets
    antonym_sets = [
        {ant for l in lemmas for ant in ANTONYM_MAP.get(l, ())}
        for lemmas in lemma_sets
    ]

    # Vectorized cosine similarity computation
    sim_matrix = np.dot(embeddings, embeddings.T)

    candidates: list[tuple[dict[str, Any], dict[str, Any], float]] = []

    for i in range(n):
        r1 = requirements[i]
        k1 = r1.get("req_key", str(r1.get("id", "")))
        lemmas1 = lemma_sets[i]
        has_opp1 = has_opp_list[i]
        ants1 = antonym_sets[i]

        for j in range(i + 1, n):
            sim = float(sim_matrix[i, j])
            if sim < min_similarity:
                continue

            r2 = requirements[j]
            k2 = r2.get("req_key", str(r2.get("id", "")))

            # Check exclusion (e.g. numeric conflicts)
            if (k1, k2) in excluded_pairs or (k2, k1) in excluded_pairs:
                continue

            # Criterion 1: Lemma overlap
            shared = lemmas1.intersection(lemma_sets[j])
            if not shared:
                continue

            # Defensible polarity & opposition check
            has_opp = (has_opp1 and not has_opp_list[j]) or (has_opp_list[j] and not has_opp1)
            has_antonym = bool(ants1.intersection(lemma_sets[j]))

            if has_opp or has_antonym:
                # Strong contradiction candidate: opposing polarity or antonyms
                candidates.append((r1, r2, sim))
            elif sim >= 0.80:
                # Both purely affirmative, very high similarity: duplicate paraphrase
                continue
            elif sim >= 0.70 and len(shared) >= 2:
                # Affirmative statements with substantial concept overlap
                candidates.append((r1, r2, sim))

    return candidates


def get_nli_cache_key(text_a: str, text_b: str) -> str:
    """Returns a deterministic SHA-256 hash for a pair of texts and model."""
    pair_str = f"{text_a}:::{text_b}:::{MODEL_NAME}"
    return hashlib.sha256(pair_str.encode("utf-8")).hexdigest()


def get_nli_cached_result(text_a: str, text_b: str) -> tuple[dict[str, float] | None, bool]:
    """Checks the NLI cache in both directions since inference is bidirectional."""
    cache = load_nli_cache()
    key_fwd = get_nli_cache_key(text_a, text_b)
    if key_fwd in cache:
        return cache[key_fwd], True
    key_rev = get_nli_cache_key(text_b, text_a)
    if key_rev in cache:
        return cache[key_rev], True
    return None, False


def evaluate_nli_batch_with_cache_info(
    pairs: list[tuple[str, str]],
    batch_size: int = 8,
) -> list[tuple[dict[str, float], bool]]:
    """Runs batched bidirectional NLI inference for text pairs with disk caching.

    Returns:
        List of tuples: (probability_dict, was_cached: bool)
    """
    if not pairs:
        return []

    cache = load_nli_cache()
    results: list[tuple[dict[str, float], bool] | None] = [None] * len(pairs)
    uncached_indices: list[int] = []
    uncached_pairs: list[tuple[str, str]] = []
    uncached_keys: list[str] = []

    for idx, (text_a, text_b) in enumerate(pairs):
        cached_res, was_cached = get_nli_cached_result(text_a, text_b)
        if was_cached and cached_res is not None:
            results[idx] = (cached_res, True)
        else:
            uncached_indices.append(idx)
            uncached_pairs.append((text_a, text_b))
            cache_key = get_nli_cache_key(text_a, text_b)
            uncached_keys.append(cache_key)

    if uncached_pairs:
        model, tokenizer = get_nli_model_and_tokenizer()

        try:
            for start_idx in range(0, len(uncached_pairs), batch_size):
                chunk_pairs = uncached_pairs[start_idx : start_idx + batch_size]
                chunk_keys = uncached_keys[start_idx : start_idx + batch_size]
                chunk_indices = uncached_indices[start_idx : start_idx + batch_size]
                m = len(chunk_pairs)

                # Bidirectional batch: forward A->B and backward B->A
                premises = [p[0] for p in chunk_pairs] + [p[1] for p in chunk_pairs]
                hypotheses = [p[1] for p in chunk_pairs] + [p[0] for p in chunk_pairs]

                inputs = tokenizer(
                    premises,
                    hypotheses,
                    return_tensors="pt",
                    truncation=True,
                    max_length=128,
                    padding=True,
                )
                with torch.no_grad():
                    outputs = model(**inputs)
                    probs = torch.softmax(outputs.logits, dim=-1).cpu().numpy()

                probs_ab = probs[:m]
                probs_ba = probs[m:]
                avg_probs = (probs_ab + probs_ba) / 2.0

                for k in range(m):
                    res = {
                        "contradiction": float(avg_probs[k][0]),
                        "neutral": float(avg_probs[k][1]),
                        "entailment": float(avg_probs[k][2]),
                    }
                    cache[chunk_keys[k]] = res
                    results[chunk_indices[k]] = (res, False)
        finally:
            save_nli_cache()

    return results  # type: ignore


def evaluate_nli_batch(
    pairs: list[tuple[str, str]],
    batch_size: int = 8,
) -> list[dict[str, float]]:
    """Runs batched bidirectional NLI inference for text pairs with disk caching.

    Returns list of dicts mapping label to average probability:
    [{'contradiction': float, 'neutral': float, 'entailment': float}, ...]
    """
    evaluated = evaluate_nli_batch_with_cache_info(pairs, batch_size=batch_size)
    return [res for res, _ in evaluated]


def evaluate_nli_pair(text_a: str, text_b: str) -> dict[str, float]:
    """Runs bidirectional NLI inference for a pair of texts with disk caching.

    Returns dict mapping label to average probability:
    {'contradiction': float, 'neutral': float, 'entailment': float}
    """
    return evaluate_nli_batch([(text_a, text_b)])[0]


def get_document_candidates_path(document_id: int) -> Path:
    """Returns the JSON file path for caching document contradiction candidates."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"contradiction_candidates_{document_id}.json"


def save_document_candidates(document_id: int, candidates: list[dict[str, Any]]) -> None:
    """Persists generated contradiction candidates for on-demand review."""
    path = get_document_candidates_path(document_id)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(candidates, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to persist candidates for document {document_id}: {e}")


def load_document_candidates(document_id: int) -> list[dict[str, Any]]:
    """Loads contradiction candidates from disk."""
    path = get_document_candidates_path(document_id)
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load candidates for document {document_id}: {e}")
        return []


def candidate_tuples_to_dicts(
    candidates: list[tuple[dict[str, Any], dict[str, Any], float]],
) -> list[dict[str, Any]]:
    """Converts candidate tuples to structured candidate records, checking cache for already-verified pairs."""
    records: list[dict[str, Any]] = []
    for r1, r2, sim in candidates:
        k1 = r1.get("req_key", str(r1.get("id", "")))
        k2 = r2.get("req_key", str(r2.get("id", "")))
        t1 = r1.get("text", "")
        t2 = r2.get("text", "")
        finding_id = f"CANDIDATE_CONTRADICTION_{k1}_{k2}"

        cached_res, was_cached = get_nli_cached_result(t1, t2)
        if was_cached and cached_res is not None:
            c_prob = cached_res.get("contradiction", 0.0)
            n_prob = cached_res.get("neutral", 0.0)
            e_prob = cached_res.get("entailment", 0.0)
            if c_prob >= 0.70:
                v_status = "verified"
                nli_class = "contradiction"
                conf = c_prob
                sev = "critical"
                expl = (
                    f"POTENTIAL contradiction: Requirement {k1} and Requirement {k2} "
                    f"have conflicting semantic meaning (contradiction confidence: {c_prob:.1%})."
                )
                sugg = "Review and harmonize the conflicting statements or restrict operational conditions."
            else:
                v_status = "no_contradiction"
                sev = "info"
                if c_prob > n_prob and c_prob > e_prob:
                    nli_class = "contradiction"
                    conf = c_prob
                elif n_prob >= e_prob:
                    nli_class = "neutral"
                    conf = n_prob
                else:
                    nli_class = "entailment"
                    conf = e_prob
                expl = (
                    f"No semantic contradiction detected between {k1} and {k2}. "
                    f"Classified as {nli_class} (confidence: {conf:.1%})."
                )
                sugg = "No action required."
        else:
            v_status = "unverified"
            nli_class = None
            conf = round(float(sim), 4)
            sev = "warning"
            expl = (
                f"Contradiction candidate: Requirement {k1} and Requirement {k2} "
                f"share semantic context and require verification."
            )
            sugg = "Verify semantic contradiction with NLI model."

        records.append({
            "finding_id": finding_id,
            "req_key_1": k1,
            "req_key_2": k2,
            "requirement_id_1": r1.get("id"),
            "requirement_id_2": r2.get("id"),
            "text_1": t1,
            "text_2": t2,
            "similarity": round(float(sim), 4),
            "confidence": round(float(conf), 4),
            "verification_status": v_status,
            "nli_classification": nli_class,
            "cached": was_cached,
            "rule_id": "SEMANTIC_CONTRADICTION" if (v_status == "verified") else "SEMANTIC_CONTRADICTION_CANDIDATE",
            "mechanism": "semantic",
            "severity": sev,
            "human_explanation": expl,
            "suggestion": sugg,
        })
    return records


def verify_candidate_pairs(
    pairs: list[dict[str, Any]],
    confidence_threshold: float = 0.70,
    batch_size: int = 8,
) -> list[dict[str, Any]]:
    """Evaluates NLI for the given candidate pairs on-demand."""
    if not pairs:
        return []

    text_pairs = [(p.get("text_1", ""), p.get("text_2", "")) for p in pairs]
    results_with_cache = evaluate_nli_batch_with_cache_info(text_pairs, batch_size=batch_size)

    verified_list: list[dict[str, Any]] = []
    for p, (nli_res, was_cached) in zip(pairs, results_with_cache):
        k1 = p.get("req_key_1", "")
        k2 = p.get("req_key_2", "")
        c_prob = nli_res.get("contradiction", 0.0)
        n_prob = nli_res.get("neutral", 0.0)
        e_prob = nli_res.get("entailment", 0.0)

        is_contradiction = (c_prob >= confidence_threshold)
        if is_contradiction:
            classification = "contradiction"
            v_status = "verified"
            confidence = c_prob
            severity = "critical"
            explanation = (
                f"POTENTIAL contradiction: Requirement {k1} and Requirement {k2} "
                f"have conflicting semantic meaning (contradiction confidence: {c_prob:.1%})."
            )
            suggestion = "Review and harmonize the conflicting statements or restrict operational conditions."
        else:
            if c_prob > n_prob and c_prob > e_prob:
                classification = "contradiction"
                confidence = c_prob
            elif n_prob >= e_prob:
                classification = "neutral"
                confidence = n_prob
            else:
                classification = "entailment"
                confidence = e_prob
            v_status = "no_contradiction"
            severity = "info"
            explanation = (
                f"No semantic contradiction detected between {k1} and {k2}. "
                f"Classified as {classification} (confidence: {confidence:.1%})."
            )
            suggestion = "No action required."

        verified_record = {
            "finding_id": p.get("finding_id", f"SEMANTIC_CONTRADICTION_{k1}_{k2}"),
            "req_key_1": k1,
            "req_key_2": k2,
            "requirement_id_1": p.get("requirement_id_1"),
            "requirement_id_2": p.get("requirement_id_2"),
            "text_1": p.get("text_1", ""),
            "text_2": p.get("text_2", ""),
            "is_contradiction": is_contradiction,
            "confidence": round(float(confidence), 4),
            "nli_classification": classification,
            "classification": classification,
            "verification_status": v_status,
            "cached": was_cached,
            "mechanism": "semantic",
            "rule_id": "SEMANTIC_CONTRADICTION" if is_contradiction else "SEMANTIC_NO_CONTRADICTION",
            "severity": severity,
            "human_explanation": explanation,
            "suggestion": suggestion,
            "nli_probabilities": {
                "contradiction": round(c_prob, 4),
                "neutral": round(n_prob, 4),
                "entailment": round(e_prob, 4),
            },
        }
        verified_list.append(verified_record)

    return verified_list


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
    batch_size: int = 16,
) -> list[SemanticContradictionFinding]:
    """Detects semantic contradictions across requirements using candidate blocking and batched NLI.

    Args:
        requirements: List of requirement dicts ('id', 'req_key', 'text').
        excluded_pairs: Pairs already flagged by Mechanism 1 to exclude.
        confidence_threshold: Minimum NLI contradiction probability (default 0.70).
        batch_size: Batch size for parallelized NLI evaluation.

    Returns:
        List of SemanticContradictionFinding objects.
    """
    candidates = select_candidate_pairs(requirements, excluded_pairs=excluded_pairs)
    if not candidates:
        return []

    pairs_to_eval = [(r1.get("text", ""), r2.get("text", "")) for r1, r2, _ in candidates]
    nli_results = evaluate_nli_batch(pairs_to_eval, batch_size=batch_size)

    findings: list[SemanticContradictionFinding] = []

    for (r1, r2, sim), nli_res in zip(candidates, nli_results):
        contra_prob = nli_res.get("contradiction", 0.0)

        if contra_prob >= confidence_threshold:
            k1 = r1.get("req_key", str(r1.get("id", "")))
            k2 = r2.get("req_key", str(r2.get("id", "")))
            text1 = r1.get("text", "")
            text2 = r2.get("text", "")

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
