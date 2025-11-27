# api/models/auth_models.py
from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    ok: bool
    user_id: str
    username: str
    role: str
