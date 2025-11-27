# db/modules.py
from db.engine import get_conn
from typing import List, Optional

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS modules (
    module_name TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

async def init_modules_table():
    conn = await get_conn()
    try:
        await conn.execute(CREATE_SQL)
        await conn.commit()
    finally:
        await conn.close()

async def get_module_by_name(name: str) -> Optional[dict]:
    conn = await get_conn()
    try:
        cur = await conn.execute("SELECT module_name, created_at FROM modules WHERE module_name = ?", (name,))
        row = await cur.fetchone()
        await cur.close()
    finally:
        await conn.close()
    if not row:
        return None
    return {"module_name": row[0], "created_at": row[1]}

async def list_modules() -> List[dict]:
    """
    Return list of modules as dicts: {"module_name":..., "created_at": ...}
    """
    conn = await get_conn()
    try:
        cur = await conn.execute("SELECT module_name, created_at FROM modules ORDER BY created_at DESC")
        rows = await cur.fetchall()
        await cur.close()
    finally:
        await conn.close()
    return [{"module_name": r[0], "created_at": r[1]} for r in rows]

async def create_module(name: str):
    conn = await get_conn()
    try:
        await conn.execute("INSERT INTO modules (module_name) VALUES (?)", (name,))
        await conn.commit()
    finally:
        await conn.close()

async def delete_module(name: str):
    conn = await get_conn()
    try:
        await conn.execute("DELETE FROM modules WHERE module_name = ?", (name,))
        await conn.commit()
    finally:
        await conn.close()
