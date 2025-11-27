# db/logs.py
from db.engine import get_conn
from typing import Optional

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id TEXT,
    action_type TEXT,
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

async def init_logs_table():
    conn = await get_conn()
    try:
        await conn.execute(CREATE_SQL)
        await conn.commit()
    finally:
        await conn.close()

async def insert_log(admin_id: Optional[str], action_type: str, details: str):
    conn = await get_conn()
    try:
        await conn.execute(
            "INSERT INTO logs (admin_id, action_type, details) VALUES (?, ?, ?)",
            (admin_id, action_type, details)
        )
        await conn.commit()
    finally:
        await conn.close()

async def get_recent_logs(limit: int = 100):
    conn = await get_conn()
    try:
        cur = await conn.execute(
            "SELECT log_id, admin_id, action_type, details, timestamp FROM logs ORDER BY log_id DESC LIMIT ?",
            (limit,)
        )
        rows = await cur.fetchall()
    finally:
        await conn.close()
    return rows


