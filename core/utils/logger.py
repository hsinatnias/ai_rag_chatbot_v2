# core/utils/logger.py
import json, traceback
from db.engine import get_conn
from db.logs import init_logs_table

# Ensure logs table exists (call once before writing)
async def ensure_logs_table():
    # init_logs_table handles connection and IF NOT EXISTS
    await init_logs_table()

async def log_action(admin_id: str, action_type: str, details: dict):
    """
    Write an audit/log row. Defensive:
      - ensures logs table exists
      - serializes details to JSON
      - catches DB errors and prints them (so logging won't crash requests)
    """
    try:
        await ensure_logs_table()
        conn = await get_conn()
        try:
            await conn.execute(
                "INSERT INTO logs (admin_id, action_type, details) VALUES (?, ?, ?)",
                (admin_id, action_type, json.dumps(details))
            )
            await conn.commit()
        finally:
            await conn.close()
    except Exception as exc:
        # Don't raise — log to stdout so server keeps running
        print("logger.log_action error:", exc)
        print(traceback.format_exc())
