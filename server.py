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
from neon_db import get_db, NeonDB

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("outbound-server")

app = FastAPI(title="LiveKit Voice Agent Outbound API")

# Global database instance
db_instance: Optional[NeonDB] = None

@app.on_event("startup")
async def startup():
    global db_instance
    db_instance = await get_db()
    logger.info("Database connection established")

@app.on_event("shutdown")
async def shutdown():
    global db_instance
    if db_instance:
        await db_instance.close()
        logger.info("Database connection closed")

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

        # Explicitly dispatch outbound_agent to the room
        try:
            from livekit import api as livekit_api
            dispatch_metadata = json.dumps({
                "phone_number": request.phone_number,
                "business_name": request.business_name,
                "agent_slug": request.agent_slug
            })
            
            await lk.agent_dispatch.create_dispatch(
                livekit_api.CreateAgentDispatchRequest(
                    agent_name="telephony_agent",  # Must match agent_name in outbound_agent.py line 339
                    room=room_name,
                    metadata=dispatch_metadata
                )
            )
            logger.info(f"Agent dispatch created for {room_name}")
        except Exception as e:
            logger.error(f"Failed to dispatch agent: {e}")
            return


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

@app.get("/dashboard/stats")
async def get_dashboard_stats():
    """Get dashboard statistics."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        stats = await db_instance.get_call_stats(days=7)
        return stats
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/dashboard/calls")
async def get_dashboard_calls(limit: int = 10):
    """Get recent calls."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        calls = await db_instance.get_recent_calls(limit=limit)
        return calls
    except Exception as e:
        logger.error(f"Error fetching calls: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
