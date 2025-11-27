# auth/sessions.py
import secrets
from typing import Optional

# In-memory sessions for dev. Replace with Redis in prod.
_sessions: dict = {}

async def create_session(user_id: str) -> str:
    sid = secrets.token_urlsafe(32)
    _sessions[sid] = {"user_id": user_id}
    return sid

def get_session(sid: str) -> Optional[dict]:
    return _sessions.get(sid)

def delete_session(sid: str):
    _sessions.pop(sid, None)
