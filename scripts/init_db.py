# scripts/init_db.py
import asyncio
from db.users import init_users_table, create_user
from db.modules import init_modules_table
from db.logs import init_logs_table
import uuid

async def main():
    await init_users_table()
    await init_modules_table()
    await init_logs_table()
    # create a default admin (change password)
    try:
        user_id = str(uuid.uuid4())
        await create_user(user_id, "admin", "adminpass", role="admin")
        print("Created default admin: username=admin password=adminpass")
    except Exception as e:
        print("failed to create default admin:", e)

if __name__ == "__main__":
    asyncio.run(main())
