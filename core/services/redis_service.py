# core/services/redis_service.py

import redis.asyncio as redis
import hashlib, json

# Create global Redis client
redis_client = redis.Redis(
    host="127.0.0.1",
    port=6379,
    decode_responses=True
)

def key_for_question(q: str):
    return "qa:" + hashlib.md5(q.strip().lower().encode()).hexdigest()

async def get_cached_answer(q: str):
    key = key_for_question(q)
    data = await redis_client.get(key)
    return json.loads(data) if data else None

async def set_cached_answer(q: str, answer: dict, ttl: int = 86400):
    key = key_for_question(q)
    await redis_client.set(key, json.dumps(answer), ex=ttl)
