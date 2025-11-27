# core/services/embedder.py
import asyncio
from typing import List, Optional
try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

from config.settings import settings

_st_model: Optional[SentenceTransformer] = None
if SentenceTransformer:
    try:
        _st_model = SentenceTransformer(settings.EMBED_MODEL)
    except Exception:
        _st_model = None

async def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Batch embed a list of texts and return list of vectors (lists of floats).
    Uses SentenceTransformer in a thread to avoid blocking the event loop.
    Returns empty list for each input if the model isn't available.
    """
    if _st_model is None:
        # fallback: return zero vectors to keep downstream code stable
        return [[0.0] * 768 for _ in texts]  # adjust dim if needed
    # run blocking encode in a thread
    def _encode_batch(ts):
        # normalize_embeddings=True yields better cosine comparisons
        return _st_model.encode(ts, normalize_embeddings=True).tolist()
    vectors = await asyncio.to_thread(_encode_batch, texts)
    return vectors

async def embed_text(text: str) -> List[float]:
    """
    Embed a single text (wrapper around embed_texts).
    """
    vecs = await embed_texts([text])
    return vecs[0] if vecs else []
