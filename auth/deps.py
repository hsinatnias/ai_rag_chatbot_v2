# auth/deps.py
from typing import Dict, Optional
from fastapi import Request, HTTPException, Depends
from db.users import get_user_by_id
from auth.sessions import get_session

async def require_user(request: Request) -> Dict:
    """
    Validate session cookie -> server session -> database user.
    Raises 401 if not authenticated.
    Returns the user dict from db.users.get_user_by_id.
    """
    sid = request.cookies.get("session_id")
    if not sid:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # get_session currently synchronous (in-memory). If you move sessions to Redis,
    # change this call to await get_session(sid) and update implementation.
    s = get_session(sid)
    if not s:
        raise HTTPException(status_code=401, detail="Invalid session")

    user = await get_user_by_id(s["user_id"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user

async def require_admin(user: Dict = Depends(require_user)) -> Dict:
    """
    Ensure the authenticated user has role 'admin'. Returns the user dict.
    """
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    return user
