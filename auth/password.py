# auth/password.py
from passlib.context import CryptContext

pwd_ctx = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

def hash_password(plain: str) -> str:
    """Return bcrypt hash of plain password."""
    return pwd_ctx.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches hashed password."""
    return pwd_ctx.verify(plain, hashed)
