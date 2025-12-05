"""
Test script to verify Neon database connection and data
"""

import asyncio
from dotenv import load_dotenv
from neon_db import get_db

# Load environment variables
load_dotenv()

async def test_connection():
    print("🔌 Connecting to Neon database...")
    db = await get_db()
    print("✅ Connected successfully!\n")
    
    # Test 1: Fetch active prompt
    print("📝 Fetching active prompt...")
    prompt = await db.get_active_prompt("default_roofing_agent")
    if prompt:
        print(f"✅ Found prompt (length: {len(prompt)} chars)")
        print(f"Preview: {prompt[:100]}...\n")
    else:
        print("❌ No active prompt found\n")
    
    # Test 2: Get prompt ID
    print("🔢 Getting prompt ID...")
    prompt_id = await db.get_prompt_id("default_roofing_agent")
    print(f"✅ Prompt ID: {prompt_id}\n")
    
    # Test 3: Create test contact
    print("👤 Creating test contact...")
    contact_id = await db.upsert_contact(
        phone_number="+1234567890",
        business_name="Test Roofing Co",
        contact_name="John Doe",
        email="john@testroof.com",
        interest_level="Warm"
    )
    print(f"✅ Contact created/updated. ID: {contact_id}\n")
    
    # Test 4: Log test call
    print("📞 Logging test call...")
    call_id = await db.log_call(
        contact_id=contact_id,
        room_id="test-room-123",
        prompt_id=prompt_id,
        duration_seconds=120,
        interest_level="Warm",
        email_captured=True,
        call_status="completed"
    )
    print(f"✅ Call logged. ID: {call_id}\n")
    
    # Test 5: Get call stats
    print("📊 Getting call statistics...")
    stats = await db.get_call_stats(days=30)
    print(f"✅ Stats: {stats}\n")
    
    print("🎉 All tests passed!")
    
    await db.close()

if __name__ == "__main__":
    asyncio.run(test_connection())
