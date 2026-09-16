import hashlib
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"
CACHE_DIR = Path("data/cache/embeddings")

_MODEL: SentenceTransformer | None = None
_MEMORY_CACHE: dict[str, np.ndarray] = {}


def get_embedding_model() -> SentenceTransformer:
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer(MODEL_NAME, device="cpu")
    return _MODEL


def compute_text_hash(text: str) -> str:
    normalized = " ".join(text.strip().lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def get_cached_embedding(text: str) -> np.ndarray | None:
    text_hash = compute_text_hash(text)
    if text_hash in _MEMORY_CACHE:
        return _MEMORY_CACHE[text_hash]

    cache_file = CACHE_DIR / f"{text_hash}.npy"
    if cache_file.exists():
        try:
            emb = np.load(cache_file)
            _MEMORY_CACHE[text_hash] = emb
            return emb
        except Exception:
            return None
    return None


def save_cached_embedding(text: str, embedding: np.ndarray) -> None:
    text_hash = compute_text_hash(text)
    _MEMORY_CACHE[text_hash] = embedding

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{text_hash}.npy"
    try:
        np.save(cache_file, embedding)
    except Exception:
        pass


def encode(texts: list[str], batch_size: int = 32) -> np.ndarray:
    """Encodes a list of texts into embedding vectors with persistent disk caching.

    Never recomputes an embedding that already exists in cache.
    """
    if not texts:
        return np.empty((0, 384), dtype=np.float32)

    results: list[np.ndarray | None] = [None] * len(texts)
    missing_indices: list[int] = []
    missing_texts: list[str] = []

    for i, text in enumerate(texts):
        cached = get_cached_embedding(text)
        if cached is not None:
            results[i] = cached
        else:
            missing_indices.append(i)
            missing_texts.append(text)

    if missing_texts:
        model = get_embedding_model()
        computed = model.encode(
            missing_texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        for idx, text, emb in zip(missing_indices, missing_texts, computed):
            save_cached_embedding(text, emb)
            results[idx] = emb

    return np.vstack(results).astype(np.float32)
