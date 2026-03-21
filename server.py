import os
import json
import re
import logging
from typing import Optional
from urllib.parse import urlparse
from contextlib import asynccontextmanager
import boto3
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from livekit import api
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
SIP_TRUNK_ID = os.getenv("SIP_TRUNK_ID", "ST_nVvG7n8BpJd3") # Default from existing code
SIP_FROM_NUMBER = os.getenv("SIP_FROM_NUMBER", "+12029787305") # Default from existing code
API_BASE_URL = os.getenv("API_BASE_URL", "").rstrip("/")  # e.g. https://livekit-outbound-api.tinysaas.fun

# E.164 pattern: starts with + and a non-zero country code digit, followed by 1–14 more
# digits (ITU-T E.164 allows up to 15 digits total including country code).
_E164_RE = re.compile(r"^\+[1-9]\d{1,14}$")


def _rewrite_recording_url(call: dict) -> None:
    """Replace the raw S3 recording URL with a proxied dashboard audio URL."""
    if call.get("recording_url"):
        call_id = call["id"]
        call["recording_url"] = (
            f"{API_BASE_URL}/dashboard/audio/{call_id}"
            if API_BASE_URL
            else f"/dashboard/audio/{call_id}"
        )

class OutboundCallRequest(BaseModel):
    phone_number: str
    business_name: str
    agent_slug: str = "roofing_agent"
    provider: Optional[str] = None # 'twilio' or 'telnyx' or default/sip
    from_number: Optional[str] = None  # Caller ID / FROM number in E.164 format

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        if not _E164_RE.match(v):
            raise ValueError(
                "phone_number must be in E.164 format (e.g. +14155552671)"
            )
        return v

    @field_validator("from_number")
    @classmethod
    def validate_from_number(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not _E164_RE.match(v):
            raise ValueError(
                "from_number must be in E.164 format (e.g. +14155552671)"
            )
        return v

class PromptUpdateRequest(BaseModel):
    name: str = "roofing_agent"
    content: str

class AgentConfigRequest(BaseModel):
    company_name: str = ""
    agent_name: str = "Aisha"
    system_prompt: str = ""
    tts_provider: str = "cartesia"  # "cartesia" | "sarvam"
    language: str = "hinglish"     # "hinglish" | "english" | "hindi"
    llm_provider: str = ""
    agent_slug: str = "default_roofing_agent"

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
        # Build metadata dict shared by room and dispatch
        call_metadata = {
            "phone_number": request.phone_number,
            "business_name": request.business_name,
            "agent_slug": request.agent_slug,
        }
        if request.from_number:
            call_metadata["from_number"] = request.from_number

        # Create room with metadata
        room_metadata = json.dumps(call_metadata)

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

        # Explicitly dispatch outbound_agent to the room.
        # The agent itself handles SIP dialing via outbound/sip.py so we
        # must NOT create a SIP participant here — doing so would place a
        # duplicate phone call and leave the agent unresponsive after its
        # opening line.
        try:
            from livekit import api as livekit_api
            dispatch_metadata = json.dumps(call_metadata)
            
            await lk.agent_dispatch.create_dispatch(
                livekit_api.CreateAgentDispatchRequest(
                    agent_name="voice-assistant",  # Must match agent_name in outbound_agent.py WorkerOptions
                    room=room_name,
                    metadata=dispatch_metadata
                )
            )
            logger.info(f"Agent dispatch created for {room_name}")
        except Exception as e:
            logger.error(f"Failed to dispatch agent: {e}")
            return


@app.post("/api/config")
async def save_agent_config(request: AgentConfigRequest):
    """
    Save agent configuration to the database (single source of truth).
    The system_prompt is saved to the ``prompts`` table (with placeholder
    substitution applied) and AI provider settings are saved to the
    ``ai_configs`` table.
    """
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")

    agent_slug = request.agent_slug

    # Persist system prompt to the prompts table
    if request.system_prompt.strip():
        # Apply placeholder substitution so the DB always stores the
        # final prompt text — no runtime guessing required.
        final_prompt = request.system_prompt
        if request.company_name:
            final_prompt = final_prompt.replace("{company_name}", request.company_name)
        if request.agent_name:
            final_prompt = final_prompt.replace("{agent_name}", request.agent_name)
        await db_instance.update_active_prompt(agent_slug, final_prompt)

    # Persist AI provider settings to the ai_configs table.
    # AI provider settings (LLM, TTS, STT) are infrastructure-level and shared
    # across agents via the "default_telephony_config" row.  Agent-specific
    # behaviour differences are captured in the *prompts* table instead.
    await db_instance.update_ai_config(
        name="default_telephony_config",
        llm_provider=request.llm_provider or None,
        tts_provider=request.tts_provider or None,
        tts_language=request.language or None,
    )

    logger.info(
        "Agent config saved to DB: slug=%s, tts=%s, lang=%s",
        agent_slug, request.tts_provider, request.language,
    )
    return {"status": "ok", "message": "Configuration saved to database"}


@app.get("/api/config")
async def get_agent_config():
    """Return the current active agent configuration from the database."""
    if not db_instance:
        return {}

    agent_slug = "default_roofing_agent"
    prompt_content = await db_instance.get_active_prompt(agent_slug)
    ai_config = await db_instance.get_ai_config("default_telephony_config")

    return {
        "system_prompt": prompt_content or "",
        "tts_provider": (ai_config.get("tts_provider") or "openai") if ai_config else "openai",
        "llm_provider": (ai_config.get("llm_provider") or "openai") if ai_config else "openai",
        "language": (ai_config.get("tts_language") or "") if ai_config else "",
        "company_name": "",
        "agent_name": "",
    }


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

@app.get("/dashboard/analytics/volume")
async def get_analytics_volume(days: int = 30):
    """Get daily call volume for analytics."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        data = await db_instance.get_daily_call_volume(days=days)
        return data
    except Exception as e:
        logger.error(f"Error fetching analytics volume: {e}")
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
            _rewrite_recording_url(call)
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

        _rewrite_recording_url(call)

        return call
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching call {call_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/dashboard/appointments")
async def get_appointments():
    """
    Get scheduled appointments/callbacks booked during AI calls.
    Returns mock data for now — replace with real DB query when appointments table exists.
    """
    from datetime import date, timedelta
    today = date.today()
    mock_appointments = [
        {
            "id": 1,
            "lead_name": "Rajesh Sharma",
            "phone": "+91-98201-12345",
            "date": str(today),
            "time": "10:00 AM",
            "status": "confirmed"
        },
        {
            "id": 2,
            "lead_name": "Priya Mehta",
            "phone": "+91-98765-43210",
            "date": str(today),
            "time": "2:30 PM",
            "status": "pending"
        },
        {
            "id": 3,
            "lead_name": "Anil Kapoor",
            "phone": "+91-90001-11111",
            "date": str(today + timedelta(days=1)),
            "time": "11:00 AM",
            "status": "pending"
        },
        {
            "id": 4,
            "lead_name": "Sunita Verma",
            "phone": "+91-77777-88888",
            "date": str(today + timedelta(days=2)),
            "time": "4:00 PM",
            "status": "confirmed"
        },
        {
            "id": 5,
            "lead_name": "Deepak Joshi",
            "phone": "+91-99999-00000",
            "date": str(today - timedelta(days=1)),
            "time": "9:00 AM",
            "status": "done"
        },
        {
            "id": 6,
            "lead_name": "Kavita Singh",
            "phone": "+91-88888-55555",
            "date": str(today + timedelta(days=3)),
            "time": "3:00 PM",
            "status": "pending"
        },
    ]
    return mock_appointments


@app.get("/health")
async def health_check():
    health = {"status": "ok", "database": "unknown"}
    if db_instance and db_instance.pool:
        try:
            async with db_instance.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            health["database"] = "connected"
        except Exception:
            health["database"] = "disconnected"
            health["status"] = "degraded"
    else:
        health["database"] = "not_configured"
        health["status"] = "degraded"
    return health

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
