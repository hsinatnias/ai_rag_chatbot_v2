# db/users.py
from typing import Optional
from db.engine import get_conn
from auth.password import hash_password, verify_password

CREATE_USERS_SQL = """
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

async def init_users_table():
    conn = await get_conn()
    try:
        await conn.execute(CREATE_USERS_SQL)
        await conn.commit()
    finally:
        await conn.close()

async def create_user(user_id: str, username: str, password: str, role: str = "user"):
    pwd = hash_password(password)
    conn = await get_conn()
    try:
        await conn.execute(
            "INSERT INTO users (user_id, username, password_hash, role) VALUES (?, ?, ?, ?)",
            (user_id, username, pwd, role)
        )
        await conn.commit()
    finally:
        await conn.close()

async def get_user_by_username(username: str) -> Optional[dict]:
    conn = await get_conn()
    try:
        cur = await conn.execute(
            "SELECT user_id, username, password_hash, role FROM users WHERE username = ?",
            (username,)
        )
        row = await cur.fetchone()
        await cur.close()
    finally:
        await conn.close()
    if not row:
        return None
    return {"user_id": row[0], "username": row[1], "password_hash": row[2], "role": row[3]}

async def get_user_by_id(user_id: str) -> Optional[dict]:
    conn = await get_conn()
    try:
        cur = await conn.execute(
            "SELECT user_id, username, password_hash, role FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = await cur.fetchone()
        await cur.close()
    finally:
        await conn.close()
    if not row:
        return None
    return {"user_id": row[0], "username": row[1], "password_hash": row[2], "role": row[3]}

async def authenticate(username: str, password: str) -> Optional[dict]:
    user = await get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    # Return user excluding password hash
    return {"user_id": user["user_id"], "username": user["username"], "role": user["role"]}

async def update_password(user_id: str, new_password: str):
    new_hash = hash_password(new_password)
    conn = await get_conn()
    try:
        await conn.execute(
            "UPDATE users SET password_hash = ? WHERE user_id = ?",
            (new_hash, user_id)
        )
        await conn.commit()
    finally:
        await conn.close()
