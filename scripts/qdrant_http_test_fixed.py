# scripts/qdrant_http_test_fixed.py
import json, sys, requests
from uuid import uuid4
URL = "http://127.0.0.1:6333"
COL = "kb_chunks"
DIM = 384

def create_collection():
    url = f"{URL}/collections/{COL}"
    body = {"vectors": {"size": DIM, "distance": "Cosine"}}
    r = requests.put(url, json=body, timeout=10)
    print("CREATE:", r.status_code, r.text)

def upsert_point():
    url = f"{URL}/collections/{COL}/points?wait=true"
    vec = [0.0] * DIM
    # Use a proper UUID string for id
    pid = str(uuid4())
    payload = {
        "points": [
            {
                "id": pid, 
                "vector": vec, 
                "payload": {"module": "test", "lang": "en", "text": "hello world"}
                }
            ]}
    r = requests.put(url, json=payload, timeout=10)
    print("UPSERT:", r.status_code, r.text)
    return pid

def list_points():
    url = f"{URL}/collections/{COL}/points?limit=5"
    r = requests.get(url, timeout=10)
    print("POINTS LIST:", r.status_code)
    try:
        print(json.dumps(r.json(), ensure_ascii=False, indent=2))
    except Exception:
        print(r.text)

def search_by_vector(vec):
    url = f"{URL}/collections/{COL}/points/search"
    body = {"vector": vec, "limit": 1, "with_payload": True}
    r = requests.post(url, json=body, timeout=10)
    print("SEARCH:", r.status_code)
    try:
        print(json.dumps(r.json(), ensure_ascii=False, indent=2))
    except Exception:
        print(r.text)

if __name__ == "__main__":
    try:
        create_collection()
        pid = upsert_point()
        list_points()
        # optional quick search using same zero vector:
        search_by_vector([0.0]*DIM)
        print("Upserted point id:", pid)
    except Exception as e:
        print("ERROR:", e, file=sys.stderr)
        raise
