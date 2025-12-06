import os
import json
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from livekit import api
from livekit.protocol.sip import CreateSIPParticipantRequest
from livekit.protocol.room import CreateRoomRequest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("outbound-server")

app = FastAPI(title="LiveKit Voice Agent Outbound API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, set this to the specific frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
ROOM_NAME_PREFIX = "outbound-call-"
SIP_TRUNK_ID = os.getenv("SIP_TRUNK_ID", "ST_WBf7rtea4MQt") # Default from existing code
SIP_FROM_NUMBER = os.getenv("SIP_FROM_NUMBER", "+12029787305") # Default from existing code

class OutboundCallRequest(BaseModel):
    phone_number: str
    business_name: str
    agent_slug: str = "default_roofing_agent"
    provider: Optional[str] = None # 'twilio' or 'telnyx' or default/sip

async def initiate_outbound_call(request: OutboundCallRequest):
    """
    Background task to create room and initiate SIP call.
    """
    lk_url = os.getenv("LIVEKIT_URL")
    lk_key = os.getenv("LIVEKIT_API_KEY")
    lk_secret = os.getenv("LIVEKIT_API_SECRET")

    if not all([lk_url, lk_key, lk_secret]):
        logger.error("Missing LiveKit credentials")
        return

    room_name = f"{ROOM_NAME_PREFIX}{request.phone_number.replace('+', '')}"

    async with api.LiveKitAPI(url=lk_url, api_key=lk_key, api_secret=lk_secret) as lk:
        # Create room with metadata
        room_metadata = json.dumps({
            "business_name": request.business_name,
            "phone_number": request.phone_number,
            "agent_slug": request.agent_slug
        })

        try:
            await lk.room.create_room(
                CreateRoomRequest(
                    name=room_name,
                    metadata=room_metadata,
                    empty_timeout=300, # 5 minutes
                    max_participants=2,
                )
            )
            logger.info(f"Room created: {room_name}")
        except Exception as e:
            logger.warning(f"Room creation ignored (likely exists): {e}")

        # NOTE: SIP Participant creation is now handled by the outbound_agent
        # independently to ensure the agent is ready before dialing.
        # We only create the room here. The outbound_agent must be dispatched 
        # to this room (via Dispatch Rule matching 'outbound-call-*').
        logger.info(f"Room created. Waiting for outbound_agent to join and dial...")


@app.post("/outbound-call")
async def trigger_outbound_call(request: OutboundCallRequest, background_tasks: BackgroundTasks):
    """
    Endpoint to trigger an outbound call.
    Returns immediately and processes call in background.
    """
    # Basic validation
    if not request.phone_number:
        raise HTTPException(status_code=400, detail="Phone number is required")

    logger.info(f"Received outbound call request for {request.phone_number} ({request.business_name})")
    
    background_tasks.add_task(initiate_outbound_call, request)
    
    return {
        "status": "queued",
        "message": f"Calling {request.phone_number} with agent {request.agent_slug}",
        "data": request.model_dump()
    }

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
