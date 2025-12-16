import os
import json
import logging
from typing import Optional
from urllib.parse import urlparse
from contextlib import asynccontextmanager
import boto3
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

# Global database instance
db_instance: Optional[NeonDB] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_instance
    try:
        db_instance = await get_db()
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        logger.warning("Server starting without database connection. Some endpoints may fail.")
        db_instance = None

    yield

    if db_instance:
        await db_instance.close()
        logger.info("Database connection closed")

app = FastAPI(title="LiveKit Voice Agent Outbound API", lifespan=lifespan)

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

def generate_presigned_url(recording_url: str, expiration=3600) -> Optional[str]:
    """
    Generates a presigned URL for an S3 object.
    """
    if not recording_url:
        return None

    # Check if we have S3 credentials
    access_key = os.getenv("S3_ACCESS_KEY") or os.getenv("AWS_ACCESS_KEY")
    secret_key = os.getenv("S3_SECRET_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY")
    endpoint_url = os.getenv("S3_ENDPOINT")
    region_name = os.getenv("S3_REGION") or os.getenv("AWS_REGION")
    bucket_name = os.getenv("S3_BUCKET") or os.getenv("S3_BUCKET_NAME")

    if not (access_key and secret_key and bucket_name):
        return recording_url # Return original if no credentials

    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            endpoint_url=endpoint_url,
            region_name=region_name,
        )

        key = None
        # Strategy 1: standard path style (endpoint/bucket/key)
        path_style_prefix = f"/{bucket_name}/"
        if path_style_prefix in recording_url:
            key = recording_url.split(path_style_prefix, 1)[1]

        # Strategy 2: virtual hosted style (bucket.s3.../key) or just parsing path if we trust the URL structure
        if not key:
            parsed = urlparse(recording_url)
            # If path starts with /bucket_name/, we already caught it in strategy 1 (usually).
            # If host contains bucket name (virtual hosted), path is the key.
            if bucket_name in parsed.netloc:
                 key = parsed.path.lstrip("/")
            # If we simply can't find it, we might just assume it's the filename if it looks like one
            elif recording_url.endswith(".mp4"):
                 key = recording_url.split("/")[-1]

        if not key:
            return recording_url

        response = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': key},
            ExpiresIn=expiration
        )
        return response

    except Exception as e:
        logger.error(f"Error generating presigned URL: {e}")
        return recording_url

@app.get("/dashboard/calls")
async def get_dashboard_calls(limit: int = 10):
    """Get recent calls."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        calls = await db_instance.get_recent_calls(limit=limit)
        # Sign recording URLs
        for call in calls:
            if call.get("recording_url"):
                call["recording_url"] = generate_presigned_url(call["recording_url"])
        return calls
    except Exception as e:
        logger.error(f"Error fetching calls: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/dashboard/call/{call_id}")
async def get_call_details(call_id: int):
    """Get details for a specific call, including transcript."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")

    # Since get_recent_calls returns a list, and we don't have get_call_by_id yet,
    # we can re-use get_recent_calls filtered or implement a new method.
    # For now, let's implement a simple fetch from DB directly if possible or add method to NeonDB
    # But since I can't modify NeonDB interface easily without touching both implementations,
    # I'll rely on a new method I should add to NeonDB/SQLiteDB.

    # Wait, I already added methods to NeonDB class in the previous step?
    # No, I only added `get_recent_calls`.
    # Let's add a `get_call` method to the DB classes.

    try:
        call = await db_instance.get_call(call_id)
        if not call:
             raise HTTPException(status_code=404, detail="Call not found")

        if call.get("recording_url"):
            call["recording_url"] = generate_presigned_url(call["recording_url"])

        return call
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching call {call_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
