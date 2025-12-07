#!/usr/bin/env python3
"""Test script to debug outbound call flow"""

import asyncio
import os
import json
from dotenv import load_dotenv
from livekit import api
from livekit.protocol.room import ListRoomsRequest
from livekit.protocol.sip import CreateSIPParticipantRequest

load_dotenv()

async def main():
    lk_url = os.getenv("LIVEKIT_URL")
    lk_key = os.getenv("LIVEKIT_API_KEY")
    lk_secret = os.getenv("LIVEKIT_API_SECRET")
    sip_trunk_id = os.getenv("SIP_TRUNK_ID")
    sip_from_number = os.getenv("SIP_FROM_NUMBER")
    
    print(f"🔧 Testing with:")
    print(f"   LiveKit URL: {lk_url}")
    print(f"   API Key: {lk_key[:10]}...")
    print(f"   SIP Trunk: {sip_trunk_id}")
    print(f"   From Number: {sip_from_number}")
    print()
    
    async with api.LiveKitAPI(url=lk_url, api_key=lk_key, api_secret=lk_secret) as lk:
        # 1. List existing rooms
        print("1️⃣  Listing rooms...")
        try:
            rooms = await lk.room.list_rooms(ListRoomsRequest())
            print(f"   Found {len(rooms.rooms)} room(s):")
            for room in rooms.rooms:
                print(f"   - {room.name} ({len(room.num_participants)} participants)")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
        
        # 2. Create a test room
        print("2️⃣  Creating test room 'outbound-call-test'...")
        from livekit.protocol.room import CreateRoomRequest
        try:
            await lk.room.create_room(
                CreateRoomRequest(
                    name="outbound-call-test",
                    metadata=json.dumps({
                        "phone_number": "+91-9096132265",
                        "business_name": "Test",
                        "agent_slug": "default_roofing_agent"
                    })
                )
            )
            print(f"   ✅ Room created!")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
        
        # 3. Wait for agent to join
        print("3️⃣  Waiting 10 seconds for agent to join...")
        await asyncio.sleep(10)
        
        # 4. Check if agent joined
        print("4️⃣  Checking if agent joined...")
        try:
            rooms = await lk.room.list_rooms(ListRoomsRequest())
            for room in rooms.rooms:
                if room.name == "outbound-call-test":
                    print(f"   ✅ Room has {room.num_participants} participant(s)")
                    if room.num_participants > 0:
                        print(f"      Agent joined! Ready to dial...")
                    else:
                        print(f"      ❌ No agent joined yet. Check dispatch rules!")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
        print("Debug complete!")

if __name__ == "__main__":
    asyncio.run(main())
