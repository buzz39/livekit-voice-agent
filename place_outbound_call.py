from dotenv import load_dotenv
import os
import asyncio
from pathlib import Path

from livekit import api
from livekit.protocol.sip import CreateSIPParticipantRequest

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path.as_posix(), override=True)

ROOM_NAME = "outbound-call-room"

async def place_call():
    lk_url = os.getenv("LIVEKIT_URL")
    lk_key = os.getenv("LIVEKIT_API_KEY")
    lk_secret = os.getenv("LIVEKIT_API_SECRET")

    print(f"LiveKit URL: {lk_url}")
    print(f"API Key: {lk_key[:10] if lk_key else 'NOT SET'}...")
    print(f"API Secret: {lk_secret[:10] if lk_secret else 'NOT SET'}...")

    if not all([lk_url, lk_key, lk_secret]):
        raise ValueError("Missing LIVEKIT_URL / LIVEKIT_API_KEY / LIVEKIT_API_SECRET")

    async with api.LiveKitAPI(
        url=lk_url,
        api_key=lk_key,
        api_secret=lk_secret,
    ) as lk:
        request = CreateSIPParticipantRequest(
            sip_trunk_id="ST_WBf7rtea4MQt",
            sip_call_to="+919096132265",
            sip_number="+12029787305",
            room_name=ROOM_NAME,
            participant_identity="outbound-caller",
            participant_name="AI Assistant",
            krisp_enabled=True,
            wait_until_answered=False,  # Don't wait for answer to avoid timeout
        )

        try:
            print(f"\nInitiating call to +919096132265...")
            print(f"From number: +12029787305")
            print(f"Room: {ROOM_NAME}")

            participant = await lk.sip.create_sip_participant(request)

            print("\n✓ Call initiated successfully!")
            print(f"Participant ID: {participant.participant_id}")
            print(f"SIP Call ID: {participant.sip_call_id}")

        except Exception as e:
            print(f"\n✗ Error placing call: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(place_call())
