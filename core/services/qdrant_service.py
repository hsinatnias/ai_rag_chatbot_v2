# core/services/qdrant_service.py (extend scaffold)
from qdrant_client import QdrantClient
from config.settings import settings
qc = QdrantClient(url=settings.QDRANT_URL)

def search(collection, vector, limit=5, with_payload=True, query_filter=None):
    return qc.search(collection_name=collection, query_vector=vector,
                     limit=limit, with_payload=with_payload, query_filter=query_filter)

def upsert(collection, points):
    return qc.upsert(collection_name=collection, points=points)

def delete_by_module(collection, module_name):
    # uses qdrant delete API with a filter on payload 'module'
    from qdrant_client.models import Filter, FieldCondition, MatchValue, Condition
    filt = Filter(must=[FieldCondition(key="module", match=MatchValue(value=module_name))])
    return qc.delete(collection_name=collection, filter=filt)
