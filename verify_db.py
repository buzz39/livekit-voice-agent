import asyncio
import os
from dotenv import load_dotenv
from neon_db import get_db

load_dotenv()

async def test_db():
    print(f"Connecting to: {os.getenv('NEON_DATABASE_URL')}")
    try:
        db = await get_db()
        print("Connected successfully!")

        stats = await db.get_call_stats()
        print(f"Stats: {stats}")

        calls = await db.get_recent_calls(limit=1)
        print(f"Recent calls: {len(calls)}")
        if calls:
            print(f"First call: {calls[0]}")

        await db.close()
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_db())
