# api/routers/chat.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from core.services.embedding_service import embed_text
from core.pipeline.retrieve import run_retrieval
from core.pipeline.prompt import build_prompt
from core.services.ollama_service import generate
from core.services.redis_service import get_cached_answer, set_cached_answer

router = APIRouter(prefix="/api/chat")

class Query(BaseModel):
    text: str
    lang: str = "ja"  # default

@router.post("/query")
async def query(q: Query):
    # 1 - check cache
    cached = await get_cached_answer(q.text)
    if cached:
        return {"answer": cached["answer"], "cached": True, "sources": cached.get("sources", [])}

    # 2 - embed
    vec = await embed_text(q.text)

    # 3 - retrieve
    results = run_retrieval(vec, lang=q.lang)  # returns list of qdrant hits

    # 4 - build prompt
    prompt = build_prompt(q.text, results, q.lang)

    # 5 - call model
    resp = await generate(prompt)
    # resp might be complex depending on ollama output shape
    answer = resp.get("generated_text") or resp.get("text") or resp

    # 6 - cache
    await set_cached_answer(q.text, {"answer": answer, "sources": [r["payload"] for r in results]})

    return {"answer": answer, "cached": False, "sources": [r["payload"] for r in results]}
