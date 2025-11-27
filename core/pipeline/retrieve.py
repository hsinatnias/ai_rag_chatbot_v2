from core.services.qdrant_service import search
from config.settings import settings


def run_retrieval(vec, lang=None, top_k=None):
    k = top_k or settings.TOP_K
    # optional: add Filter by 'lang' field here (use qdrant Filter models)
    return search(settings.QDRANT_COLLECTION, vec, limit=k)