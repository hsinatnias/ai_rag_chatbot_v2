# db/modules.py
from db.engine import get_conn

async def init_modules_table():
    conn = await get_conn()
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS modules (
        module_name TEXT PRIMARY KEY,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    await conn.commit()
    await conn.close()

async def get_module_by_name(name: str):
    conn = await get_conn()
    cur = await conn.execute("SELECT module_name FROM modules WHERE module_name = ?", (name,))
    row = await cur.fetchone()
    await cur.close()
    await conn.close()
    if not row:
        return None
    return {"module_name": row[0]}

async def create_module(name: str):
    conn = await get_conn()
    await conn.execute("INSERT INTO modules (module_name) VALUES (?)", (name,))
    await conn.commit()
    await conn.close()

async def delete_module(name: str):
    conn = await get_conn()
    await conn.execute("DELETE FROM modules WHERE module_name = ?", (name,))
    await conn.commit()
    await conn.close()
