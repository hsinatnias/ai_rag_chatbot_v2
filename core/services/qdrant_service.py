# core/services/qdrant_service.py
from typing import List, Optional, Any
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from config.settings import settings

qc = QdrantClient(url=settings.QDRANT_URL)

# Simple thin wrapper (kept for compatibility)
def search(collection: str, vector: List[float], limit: int = 5, with_payload: bool = True, query_filter: Optional[Filter] = None):
    return qc.search(collection_name=collection, query_vector=vector,
                     limit=limit, with_payload=with_payload, query_filter=query_filter)

def upsert(collection: str, points: List[dict]):
    return qc.upsert(collection_name=collection, points=points)

def delete_by_module(collection: str, module_name: str):
    """
    Delete all points whose payload.module == module_name
    """
    filt = Filter(must=[FieldCondition(key="module", match=MatchValue(value=module_name))])
    return qc.delete(collection_name=collection, filter=filt)


# New: language-aware search with fallback
def search_vectors(
    collection: str,
    vector: List[float],
    top_k: int = 6,
    module: Optional[str] = None,
    user_lang: Optional[str] = None,
    with_payload: bool = True
) -> List[Any]:
    """
    Search vectors with optional 'module' and 'user_lang' filters.
    - If user_lang is provided, tries module+lang search first.
    - If that returns no results and module is provided, retries module-only search as fallback.
    - If module not provided, just searches with or without lang filter.
    Returns the list of hits from qdrant_client.search.
    """
    # build must conditions
    must_conditions = []
    if module:
        must_conditions.append(FieldCondition(key="module", match=MatchValue(value=module)))
    if user_lang:
        must_conditions.append(FieldCondition(key="lang", match=MatchValue(value=user_lang)))

    primary_filter = Filter(must=must_conditions) if must_conditions else None

    # primary search
    results = qc.search(
        collection_name=collection,
        query_vector=vector,
        limit=top_k,
        with_payload=with_payload,
        query_filter=primary_filter
    )

    # fallback: if no results and we used language filter and module exists, try module-only
    if (not results or len(results) == 0) and user_lang and module:
        module_filter = Filter(must=[FieldCondition(key="module", match=MatchValue(value=module))])
        results = qc.search(
            collection_name=collection,
            query_vector=vector,
            limit=top_k,
            with_payload=with_payload,
            query_filter=module_filter
        )

    return results
