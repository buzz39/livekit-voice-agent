import asyncio
from dotenv import load_dotenv
load_dotenv()
from neon_db import get_db

async def check():
    db = await get_db()
    rows = await db.pool.fetch(
        "SELECT id, call_status, transcript FROM calls WHERE id IN (222, 223, 224) ORDER BY id"
    )
    for r in rows:
        tid = r["id"]
        status = r["call_status"]
        transcript = r["transcript"] or "(empty)"
        print(f"--- Call {tid} [{status}] ---")
        print(transcript)
        print()
    await db.close()

asyncio.run(check())
