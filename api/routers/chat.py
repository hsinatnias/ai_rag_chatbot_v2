# api/routers/chat.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from core.services.embedder import embed_text
from core.pipeline.retrieve import run_retrieval
from core.pipeline.prompt import build_prompt
from core.services.ollama_service import generate
from core.services.redis_service import get_cached_answer, set_cached_answer
from auth.deps import require_user  # optional if you want to require auth for chat
from typing import Optional

router = APIRouter(prefix="/api/chat", tags=["chat"])

class Query(BaseModel):
    text: str
    lang: str = "ja"  # default
    module: Optional[str] = None  # optional module filter

@router.post("/query")
async def query(q: Query):
    # 1 - check cache (cache key could incorporate lang/module for safety)
    cache_key = f"{q.text}||lang:{q.lang}||module:{q.module or ''}"
    cached = await get_cached_answer(cache_key)
    if cached:
        return {"answer": cached["answer"], "cached": True, "sources": cached.get("sources", [])}

    # 2 - embed
    vec = await embed_text(q.text)

    # 3 - retrieve (run_retrieval is sync but quick; it returns qdrant hits)
    results = run_retrieval(vec, lang=q.lang, top_k=None, module=q.module)

    # 4 - build prompt (build_prompt should accept the raw results format)
    prompt = build_prompt(q.text, results, q.lang)

    # 5 - call model
    resp = await generate(prompt)
    # normalize model output (adjust based on your ollama_service output)
    answer = None
    if isinstance(resp, dict):
        answer = resp.get("generated_text") or resp.get("text") or resp.get("answer") or str(resp)
    else:
        answer = str(resp)

    # 6 - cache (serialize sources sensibly)
    try:
        sources = []
        for r in results:
            # qdrant client may return objects; handle common shapes
            payload = None
            if isinstance(r, dict):
                payload = r.get("payload") or r.get("doc") or None
            else:
                # some qdrant-client versions return 'Point' objects with .payload
                payload = getattr(r, "payload", None)
            sources.append(payload)
    except Exception:
        sources = []

    await set_cached_answer(cache_key, {"answer": answer, "sources": sources})

    return {"answer": answer, "cached": False, "sources": sources}
