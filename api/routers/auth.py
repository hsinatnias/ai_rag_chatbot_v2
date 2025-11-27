# api/routers/auth.py
from fastapi import APIRouter, Response, Request, HTTPException, Depends
from pydantic import BaseModel
import uuid
from auth.deps import require_user
from auth.sessions import create_session, delete_session, get_session
from config.settings import settings
from db import users as user_db
from core.utils import logger as event_logger

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
async def login(req: LoginRequest, resp: Response, request: Request):
    """
    Authenticate a user and set an HTTP-only session cookie.
    Returns basic user info (no password hash).
    Logs success/failure to logs table.
    """
    # 1) Verify credentials
    user = await user_db.authenticate(req.username, req.password)
    if not user:
        # log failed attempt
        await event_logger.log_action(None, "AUTH_LOGIN_FAILED", {
            "username": req.username,
            "ip": request.client.host if request.client else None
        })
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 2) Create session id and set cookie
    sid = await create_session(user["user_id"])
    # Secure cookie settings: adjust secure=True when behind HTTPS
    resp.set_cookie(
        key="session_id",
        value=sid,
        httponly=True,
        secure=settings.SECURE_COOKIE,
        samesite="lax",
        max_age=60*60*24     # 1 day TTL (seconds)
    )

    # 3) Log success
    await event_logger.log_action(user["user_id"], "AUTH_LOGIN_SUCCESS", {
        "username": user["username"],
        "ip": request.client.host if request.client else None
    })

    # 4) Return user info
    return {"ok": True, "user": {"user_id": user["user_id"], "username": user["username"], "role": user["role"]}}

@router.post("/logout")
async def logout(resp: Response, request: Request):
    """
    Clear the session both server-side and client-side (cookie).
    """
    sid = request.cookies.get("session_id")
    if sid:
        # remove server-side session mapping
        try:
            s = get_session(sid)
            if s:
                await event_logger.log_action(s.get("user_id"), "AUTH_LOGOUT", {"ip": request.client.host if request.client else None})
        except Exception:
            # continue even if logger fails
            pass
        delete_session(sid)

    # delete cookie client-side
    resp.delete_cookie("session_id")
    return {"ok": True}
    
@router.post("/register")
async def register(req: RegisterRequest):
    """
    Simple registration endpoint for dev/testing. In production you may want admin-only creation.
    """
    existing = await user_db.get_user_by_username(req.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    # create user_id here
    user_id = str(uuid.uuid4())
    await user_db.create_user(user_id, req.username, req.password, role="user")
    await event_logger.log_action(user_id, "AUTH_REGISTER", {"username": req.username})
    return {"ok": True, "user_id": user_id}

@router.get("/whoami")
async def whoami(user = Depends(require_user)):
    """
    Returns info about the currently authenticated user.
    """
    return {"user_id": user["user_id"], "username": user["username"], "role": user["role"]}