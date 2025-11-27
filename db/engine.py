# db/engine.py
import aiosqlite
from pathlib import Path

DB_PATH = Path("data/app.db")

async def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return await aiosqlite.connect(DB_PATH)