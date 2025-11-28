# scripts/qdrant_test.py
import asyncio
import json
from pathlib import Path
import sys

# make script runnable directly from project root
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from config.settings import settings
from core.services.embedder import embed_text

COL = settings.QDRANT_COLLECTION
URL = settings.QDRANT_URL

def create_collection_if_not_exists(client: QdrantClient, collection_name: str, vector_size: int):
    try:
        cols = client.get_collections().collections
    except Exception:
        # older/newer client shape handling
        try:
            cols = [c.name for c in client.get_collections()]
        except Exception:
            cols = []
    if not any((getattr(c, "name", c) == collection_name) for c in cols):
        print(f"Creating collection: {collection_name} size: {vector_size}")
        client.recreate_collection(
            collection_name=collection_name,
            vectors_config=rest.VectorParams(size=vector_size, distance=rest.Distance.COSINE)
        )
    else:
        print("Collection already exists:", collection_name)

async def main():
    client = QdrantClient(url=URL)
    print("Using Qdrant URL:", URL)
    # 1) get an embed to determine dim
    vec = await embed_text("hello world")
    if not vec:
        print("Failed to obtain embedding (vec empty). Check embedder/model.")
        return
    dim = len(vec)
    print("Detected embed dim:", dim)

    # 2) create collection if needed
    create_collection_if_not_exists(client, COL, dim)

    # 3) upsert a test point
    point = {
        "id": "test-1",
        "vector": vec,
        "payload": {"module": "test", "lang": "en", "text": "hello world"}
    }
    try:
        client.upsert(collection_name=COL, points=[point])
        print("Upserted test point")
    except Exception as exc:
        print("Upsert failed:", exc)
        return

    # 4) search for similar
    try:
        res = client.search(collection_name=COL, query_vector=vec, limit=1, with_payload=True)
        print("Search results count:", len(res))
        # print payloads in JSON-safe form
        for r in res:
            payload = getattr(r, "payload", None) or (r.get("payload", None) if isinstance(r, dict) else None)
            print("Payload:", json.dumps(payload, ensure_ascii=False))
    except Exception as exc:
        print("Search failed (client.search); attempting scroll/list fallback:", exc)
        try:
            rows = client.scroll(collection_name=COL, limit=5)
            print("Scroll results:")
            for r in rows:
                payload = getattr(r, "payload", None) or (r.get("payload", None) if isinstance(r, dict) else None)
                print(json.dumps(payload, ensure_ascii=False))
        except Exception as exc2:
            print("Scroll fallback failed:", exc2)

if __name__ == "__main__":
    asyncio.run(main())
