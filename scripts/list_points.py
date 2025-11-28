# scripts/list_points.py
import sys
import json
from pathlib import Path

# Ensure project root is on sys.path so "import config" works
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qdrant_client import QdrantClient
from config.settings import settings

COL = settings.QDRANT_COLLECTION
URL = settings.QDRANT_URL
LIMIT = 5

client = QdrantClient(url=URL)

def _get_payload_from_hit(hit):
    """
    Normalize payload extraction across possible return shapes:
    - objects with .payload
    - dicts with ['payload']
    - Point structs from scroll with .payload
    """
    try:
        # object-like (dataclass/attrs)
        payload = getattr(hit, "payload", None)
        if payload is not None:
            return payload
    except Exception:
        pass

    try:
        # dict-like
        if isinstance(hit, dict):
            return hit.get("payload", None) or hit.get("payload", {})
    except Exception:
        pass

    # last resort
    return None

def try_search_with_vector(vec, limit=LIMIT):
    """
    Try multiple search method names that different qdrant-client versions expose.
    Returns a list of hits or raises if nothing works.
    """
    # 1) direct client.search if available
    if hasattr(client, "search"):
        try:
            return client.search(collection_name=COL, query_vector=vec, limit=limit, with_payload=True)
        except Exception as e:
            print("client.search present but raised:", e)

    # 2) older/newer variant names
    if hasattr(client, "search_points"):
        try:
            # signature may vary; try a common one
            return client.search_points(collection_name=COL, query_vector=vec, limit=limit, with_payload=True)
        except Exception as e:
            print("client.search_points present but raised:", e)

    # 3) some versions expose http client wrapper
    if hasattr(client, "http") and hasattr(client.http, "search"):
        try:
            return client.http.search(collection_name=COL, query_vector=vec, limit=limit, with_payload=True)
        except Exception as e:
            print("client.http.search present but raised:", e)

    # 4) qdrant-client may not have search helper available; return None so caller can fallback to scroll
    return None

def list_some_points(limit=LIMIT):
    try:
        # prefer a vector search if collection vectors size is available
        col_info = None
        try:
            col_info = client.get_collection(COL)
        except Exception as exc:
            print("Warning: get_collection failed or collection not found:", exc)

        if col_info and getattr(col_info, "vectors", None):
            dim = col_info.vectors.size
            # try a zero vector search first (some clients allow it)
            zero_vec = [0.0] * dim
            hits = try_search_with_vector(zero_vec, limit=limit)
            if hits is None:
                # fallback to scroll listing
                print("Search helper not available — falling back to scroll() to list points.")
                try:
                    rows = client.scroll(collection_name=COL, limit=limit)
                except Exception as exc:
                    print("scroll() failed:", exc)
                    return
                for r in rows:
                    payload = _get_payload_from_hit(r) or {}
                    print(json.dumps(payload, ensure_ascii=False, indent=2))
                return
            # If we got hits from a search method, print payloads
            for r in hits:
                payload = _get_payload_from_hit(r) or {}
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            return
        else:
            # No collection info — try a scroll listing anyway
            print("Collection info unavailable. Trying scroll() to list points.")
            rows = client.scroll(collection_name=COL, limit=limit)
            for r in rows:
                payload = _get_payload_from_hit(r) or {}
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            return

    except Exception as exc:
        print("Error listing points:", exc)

if __name__ == "__main__":
    print(f"Connecting to Qdrant at {URL}, collection: {COL}")
    list_some_points()
