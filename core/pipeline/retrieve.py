# core/pipeline/retrieve.py
from typing import Optional, List, Any
from core.services.qdrant_service import search_vectors
from config.settings import settings

def run_retrieval(
    vector: List[float],
    lang: Optional[str] = None,
    top_k: Optional[int] = None,
    module: Optional[str] = None
) -> List[Any]:
    """
    Run retrieval using qdrant_service.search_vectors.

    - vector: embedding vector of the query
    - lang: preferred language code (e.g. 'ja' or 'en')
    - top_k: override for number of hits
    - module: optional module name to restrict search
    """
    k = top_k or settings.TOP_K
    # call the qdrant helper (synchronous)
    hits = search_vectors(
        collection=settings.QDRANT_COLLECTION,
        vector=vector,
        top_k=k,
        module=module,
        user_lang=lang,
        with_payload=True
    )
    return hits
