# scripts/qdrant_http_test.py
import json, sys, requests

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
    payload = {"points": [{"id": "test-1", "vector": vec, "payload": {"module": "test", "lang": "en", "text": "hello world"}}]}
    r = requests.put(url, json=payload, timeout=10)
    print("UPSERT:", r.status_code, r.text)

def list_points():
    url = f"{URL}/collections/{COL}/points?limit=5"
    r = requests.get(url, timeout=10)
    print("POINTS LIST:", r.status_code)
    try:
        print(json.dumps(r.json(), ensure_ascii=False, indent=2))
    except Exception:
        print(r.text)

if __name__ == "__main__":
    try:
        create_collection()
        upsert_point()
        list_points()
    except Exception as e:
        print("ERROR:", e, file=sys.stderr)
        raise
