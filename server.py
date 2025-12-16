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
from audio_router import audio_router

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

app.include_router(audio_router)

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

class PromptUpdateRequest(BaseModel):
    name: str = "default_roofing_agent"
    content: str

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

@app.get("/dashboard/prompts")
async def get_all_prompts():
    """Get all available prompts."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        prompts = await db_instance.get_all_prompts()
        return prompts
    except Exception as e:
        logger.error(f"Error fetching prompts: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/dashboard/prompt")
async def get_active_prompt(name: str = "default_roofing_agent"):
    """Get active prompt."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        content = await db_instance.get_active_prompt(name)
        if not content:
             raise HTTPException(status_code=404, detail="Prompt not found")
        return {"name": name, "content": content}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching prompt: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/dashboard/prompt")
async def update_active_prompt(request: PromptUpdateRequest):
    """Update active prompt."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        await db_instance.update_active_prompt(request.name, request.content)
        return {"status": "success", "message": "Prompt updated"}
    except Exception as e:
        logger.error(f"Error updating prompt: {e}")
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
        logger.warning(f"Missing S3 credentials. Access Key: {bool(access_key)}, Secret: {bool(secret_key)}, Bucket: {bool(bucket_name)}. Returning original URL.")
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
        parsed = urlparse(recording_url)
        path = parsed.path

        # Strategy 1: standard path style (endpoint/bucket/key)
        path_style_prefix = f"/{bucket_name}/"
        if path_style_prefix in path:
            key = path.split(path_style_prefix, 1)[1]

        # Strategy 2: virtual hosted style (bucket.s3.../key) or just parsing path if we trust the URL structure
        elif bucket_name in parsed.netloc:
             key = path.lstrip("/")

        # Strategy 3: Filename fallback (check parsed path, not full URL, to ignore query params)
        elif path.endswith(".mp4"):
             key = path.split("/")[-1]

        if not key:
            logger.warning(f"Could not extract S3 key from recording URL: {recording_url}")
            return recording_url

        response = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': key},
            ExpiresIn=expiration
        )
        return response

    except Exception as e:
        logger.error(f"Error generating presigned URL for {recording_url}: {e}")
        return recording_url

@app.get("/dashboard/calls")
async def get_dashboard_calls(limit: int = 10):
    """Get recent calls."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        calls = await db_instance.get_recent_calls(limit=limit)
        # Rewrite recording URLs to point to our proxy
        # This fixes issues where the frontend (local) cannot access the S3/MinIO endpoint (internal docker)
        # or avoids CORS/Presigning issues entirely.
        for call in calls:
            if call.get("recording_url"):
                # Use the audio proxy endpoint
                call["recording_url"] = f"https://livekit-outbound-api.tinysaas.fun/dashboard/audio/{call['id']}"
        return calls
    except Exception as e:
        logger.error(f"Error fetching calls: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/dashboard/call/{call_id}")
async def get_call_details(call_id: int):
    """Get details for a specific call, including transcript."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        call = await db_instance.get_call(call_id)
        if not call:
             raise HTTPException(status_code=404, detail="Call not found")

        if call.get("recording_url"):
            call["recording_url"] = f"https://livekit-outbound-api.tinysaas.fun/dashboard/audio/{call['id']}"

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
