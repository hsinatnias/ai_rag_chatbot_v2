import httpx
from config.settings import settings


client = httpx.AsyncClient(timeout=300)


async def generate(prompt: str, model: str = None):
    model = model or settings.LLM_MODEL
    url = f"{settings.OLLAMA_URL.rstrip('/')}/api/generate"
    payload = {"model": model, "prompt": prompt, "stream": False}
    r = await client.post(url, json=payload)
    r.raise_for_status()
    return r.json()