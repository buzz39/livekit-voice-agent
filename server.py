import os
import json
import re
import logging
import time
from collections import defaultdict
from typing import Optional
from urllib.parse import urlparse
from contextlib import asynccontextmanager
import boto3
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from livekit import api
from livekit.protocol.room import CreateRoomRequest
from dotenv import load_dotenv
from neon_db import get_db, NeonDB
from audio_router import audio_router
from config import OUTBOUND_AGENT_NAME

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

# CORS: restrict to configured frontend origins (comma-separated) or allow all in dev
_cors_origins_raw = os.getenv("CORS_ALLOWED_ORIGINS", "")
_cors_origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()] if _cors_origins_raw else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Key Authentication ---
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "")

_ROLE_LEVELS = {"viewer": 1, "operator": 2, "admin": 3}


def _parse_tenant_api_key_map() -> dict[str, str]:
    raw = os.getenv("TENANT_API_KEYS_JSON", "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception as exc:
        logger.error("Invalid TENANT_API_KEYS_JSON: %s", exc)
        return {}
    if not isinstance(parsed, dict):
        logger.error("TENANT_API_KEYS_JSON must be an object of tenant_id to api_key")
        return {}
    out: dict[str, str] = {}
    for tenant_id, tenant_key in parsed.items():
        if isinstance(tenant_id, str) and tenant_id.strip() and isinstance(tenant_key, str) and tenant_key.strip():
            out[tenant_id.strip()] = tenant_key.strip()
    return out


_TENANT_API_KEYS = _parse_tenant_api_key_map()


def _extract_request_api_key(request: Request) -> str:
    key = request.headers.get("x-api-key") or ""
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        key = key or auth_header[7:]
    return key


def _check_dashboard_rbac(request: Request) -> None:
    if not os.getenv("RBAC_ENFORCED", "false").lower() in {"1", "true", "yes", "on"}:
        return
    path = request.url.path
    if not path.startswith("/dashboard"):
        return

    role = (request.headers.get("x-role") or "viewer").strip().lower()
    role_level = _ROLE_LEVELS.get(role)
    if role_level is None:
        raise HTTPException(status_code=403, detail="Invalid role")

    required_level = 1
    if request.method in {"POST", "PATCH", "DELETE", "PUT"}:
        required_level = 2

    admin_only_prefixes = (
        "/dashboard/agent",
        "/dashboard/ai-config",
        "/dashboard/agents",
        "/dashboard/ai-configs",
    )
    if request.method in {"DELETE", "PUT"} and path.startswith(admin_only_prefixes):
        required_level = 3

    if role_level < required_level:
        raise HTTPException(status_code=403, detail="Insufficient role permissions")


async def _check_tenant_api_key(request: Request) -> None:
    tenant_id = (request.headers.get("x-tenant-id") or "").strip()
    if not tenant_id:
        return

    expected = _TENANT_API_KEYS.get(tenant_id)
    if expected is None and db_instance:
        try:
            expected = await db_instance.get_tenant_api_key(tenant_id)
        except Exception as exc:
            logger.warning("Failed to load tenant API key for %s: %s", tenant_id, exc)

    if expected is None:
        # No tenant key configured in env or DB.
        return

    if not expected:
        raise HTTPException(status_code=401, detail="Unknown tenant")

    presented = (request.headers.get("x-tenant-api-key") or "").strip() or _extract_request_api_key(request)
    if presented != expected:
        raise HTTPException(status_code=401, detail="Invalid tenant API key")

async def verify_api_key(request: Request):
    """Verify API key from Authorization header or x-api-key header.
    Skips auth if API_SECRET_KEY is not configured (dev mode)."""
    if not API_SECRET_KEY:
        await _check_tenant_api_key(request)
        _check_dashboard_rbac(request)
        return  # No global key configured — dev mode, still enforce optional tenant/RBAC rules
    # Allow health endpoint without auth
    if request.url.path == "/health":
        return
    key = _extract_request_api_key(request)
    if key != API_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    await _check_tenant_api_key(request)
    _check_dashboard_rbac(request)

# --- Simple Rate Limiter ---
_RATE_LIMIT_WINDOW = 60  # seconds
_RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX_CALLS_PER_MIN", "10"))
_RATE_LIMIT_TENANT_MAX = int(os.getenv("RATE_LIMIT_MAX_CALLS_PER_MIN_PER_TENANT", "60"))
_call_timestamps: dict[str, list[float]] = defaultdict(list)
_tenant_call_timestamps: dict[str, list[float]] = defaultdict(list)

def _check_rate_limit(client_ip: str, tenant_id: Optional[str] = None):
    """Raise 429 if the client exceeds the outbound call rate limit."""
    now = time.time()
    timestamps = _call_timestamps[client_ip]
    # Purge old entries
    _call_timestamps[client_ip] = [t for t in timestamps if now - t < _RATE_LIMIT_WINDOW]
    if len(_call_timestamps[client_ip]) >= _RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again shortly.")
    _call_timestamps[client_ip].append(now)

    if tenant_id:
        tenant_timestamps = _tenant_call_timestamps[tenant_id]
        _tenant_call_timestamps[tenant_id] = [t for t in tenant_timestamps if now - t < _RATE_LIMIT_WINDOW]
        if len(_tenant_call_timestamps[tenant_id]) >= _RATE_LIMIT_TENANT_MAX:
            raise HTTPException(status_code=429, detail="Tenant rate limit exceeded. Try again shortly.")
        _tenant_call_timestamps[tenant_id].append(now)

# Configuration
ROOM_NAME_PREFIX = "outbound-call-"
SIP_TRUNK_ID = os.getenv("SIP_TRUNK_ID", "")
SIP_FROM_NUMBER = os.getenv("SIP_FROM_NUMBER", "")
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


def _normalize_call_payload(call: dict) -> None:
    """Normalize API payload fields for dashboard consumers."""
    captured_data = call.get("captured_data")
    if isinstance(captured_data, str):
        try:
            call["captured_data"] = json.loads(captured_data)
        except json.JSONDecodeError:
            pass

class OutboundCallRequest(BaseModel):
    phone_number: str
    business_name: str
    agent_slug: str = "roofing_agent"
    provider: Optional[str] = None # 'twilio' or 'telnyx' or default/sip
    from_number: Optional[str] = None  # Caller ID / FROM number in E.164 format
    tenant_id: Optional[str] = None

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

    @field_validator("tenant_id")
    @classmethod
    def validate_tenant_id(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        tenant = v.strip()
        if not tenant:
            return None
        if len(tenant) > 64:
            raise ValueError("tenant_id must be <= 64 characters")
        return tenant


def _resolve_tenant_id(request: Request, body_tenant_id: Optional[str]) -> Optional[str]:
    """Resolve tenant ID from request body or X-Tenant-Id header.

    If both are present and differ, reject the request to avoid cross-tenant confusion.
    """
    header_tenant_id = (request.headers.get("x-tenant-id") or "").strip() or None
    if body_tenant_id and header_tenant_id and body_tenant_id != header_tenant_id:
        raise HTTPException(
            status_code=400,
            detail="tenant_id in request body does not match X-Tenant-Id header",
        )
    return body_tenant_id or header_tenant_id


def _matches_tenant(call: dict, tenant_id: Optional[str]) -> bool:
    """Return True when the call belongs to the requested tenant.

    Calls without captured tenant metadata are only visible when tenant_id is omitted.
    """
    if not tenant_id:
        return True
    captured_data = call.get("captured_data")
    if not isinstance(captured_data, dict):
        return False
    return captured_data.get("tenant_id") == tenant_id


def _extract_call_diagnostics(call: dict) -> dict:
    """Return compact reliability diagnostics from call payload."""
    captured_data = call.get("captured_data")
    captured = captured_data if isinstance(captured_data, dict) else {}
    state_machine = captured.get("state_machine") if isinstance(captured.get("state_machine"), dict) else {}
    diagnostics = {
        "call_id": call.get("id"),
        "call_status": call.get("call_status"),
        "duration_seconds": call.get("duration_seconds"),
        "created_at": call.get("created_at"),
        "tenant_id": captured.get("tenant_id"),
        "state_machine": {
            "current_state": state_machine.get("current_state"),
            "transitions": state_machine.get("transitions", []),
        },
        "dial_attempts": captured.get("dial_attempts", []),
        "successful_trunk_id": captured.get("successful_trunk_id"),
        "notes": captured.get("notes", []),
    }
    return diagnostics

class PromptUpdateRequest(BaseModel):
    name: str = "roofing_agent"
    content: str

class PromptCreateRequest(BaseModel):
    name: str
    content: str
    industry: str = "general"
    description: str = ""
    is_active: bool = True

class PromptPatchRequest(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class PromptCloneRequest(BaseModel):
    new_name: str
    new_industry: str

class AgentConfigUpsertRequest(BaseModel):
    slug: str
    owner_id: str = ""
    opening_line: str = ""
    mcp_endpoint_url: str = ""
    is_active: bool = True
    prompt_id: Optional[int] = None
    ai_config_name: Optional[str] = None


class TenantConfigUpsertRequest(BaseModel):
    tenant_id: str
    display_name: str = ""
    agent_slug: str = ""
    workflow_policy: str = ""
    routing_policy: dict = Field(default_factory=dict)
    ai_overrides: dict = Field(default_factory=dict)
    opening_line: str = ""
    api_key: Optional[str] = None
    is_active: bool = True

    @field_validator("tenant_id")
    @classmethod
    def validate_tenant_id(cls, v: str) -> str:
        tenant = v.strip()
        if not tenant:
            raise ValueError("tenant_id is required")
        if len(tenant) > 64:
            raise ValueError("tenant_id must be <= 64 characters")
        return tenant

class DataSchemaFieldRequest(BaseModel):
    slug: str
    field_name: str
    field_type: str = "string"
    description: str = ""

class TestCallRequest(BaseModel):
    phone_number: str
    business_name: str = ""
    prompt_id: int
    agent_slug: str = "default_roofing_agent"
    from_number: Optional[str] = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        if not _E164_RE.match(v):
            raise ValueError("phone_number must be in E.164 format")
        return v

    @field_validator("from_number")
    @classmethod
    def validate_from_number(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not _E164_RE.match(v):
            raise ValueError("from_number must be in E.164 format")
        return v

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

    phone_suffix = re.sub(r"\D", "", request.phone_number) or "unknown"
    unique_suffix = int(time.time() * 1000)
    room_name = f"{ROOM_NAME_PREFIX}{phone_suffix}-{unique_suffix}"

    async with api.LiveKitAPI(url=lk_url, api_key=lk_key, api_secret=lk_secret) as lk:
        # Build metadata dict shared by room and dispatch
        call_metadata = {
            "phone_number": request.phone_number,
            "business_name": request.business_name,
            "agent_slug": request.agent_slug,
        }
        if request.tenant_id:
            call_metadata["tenant_id"] = request.tenant_id
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
                    agent_name=OUTBOUND_AGENT_NAME,
                    room=room_name,
                    metadata=dispatch_metadata
                )
            )
            logger.info(f"Agent dispatch created for {room_name}")
        except Exception as e:
            logger.error(f"Failed to dispatch agent: {e}")
            return


@app.post("/api/config", dependencies=[Depends(verify_api_key)])
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


@app.post("/outbound-call", dependencies=[Depends(verify_api_key)])
async def trigger_outbound_call(request: OutboundCallRequest, background_tasks: BackgroundTasks, req: Request):
    """
    Endpoint to trigger an outbound call.
    Returns immediately and processes call in background.
    """
    # Basic validation
    if not request.phone_number:
        raise HTTPException(status_code=400, detail="Phone number is required")

    tenant_id = _resolve_tenant_id(req, request.tenant_id)

    # Rate limit by client IP and optional tenant
    client_ip = req.client.host if req.client else "unknown"
    _check_rate_limit(client_ip, tenant_id=tenant_id)
    effective_request = request.model_copy(update={"tenant_id": tenant_id})

    logger.info(f"Received outbound call request for {request.phone_number} ({request.business_name})")
    
    background_tasks.add_task(initiate_outbound_call, effective_request)
    
    return {
        "status": "queued",
        "message": f"Calling {request.phone_number} with agent {request.agent_slug}",
        "data": request.model_dump()
    }

@app.get("/dashboard/stats", dependencies=[Depends(verify_api_key)])
async def get_dashboard_stats(request: Request, days: int = 7, tenant_id: Optional[str] = None):
    """Get dashboard statistics."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
        stats = await db_instance.get_call_stats(days=days, tenant_id=resolved_tenant_id)
        return stats
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/dashboard/analytics/volume", dependencies=[Depends(verify_api_key)])
async def get_analytics_volume(request: Request, days: int = 30, tenant_id: Optional[str] = None):
    """Get daily call volume for analytics."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
        data = await db_instance.get_daily_call_volume(days=days, tenant_id=resolved_tenant_id)
        return data
    except Exception as e:
        logger.error(f"Error fetching analytics volume: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/dashboard/prompts", dependencies=[Depends(verify_api_key)])
async def get_all_prompts(industry: Optional[str] = None):
    """Get all available prompts, optionally filtered by industry."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        prompts = await db_instance.get_all_prompts(industry=industry)
        return prompts
    except Exception as e:
        logger.error(f"Error fetching prompts: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/dashboard/industries", dependencies=[Depends(verify_api_key)])
async def get_industries():
    """Get all distinct industry values."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        return await db_instance.get_industries()
    except Exception as e:
        logger.error(f"Error fetching industries: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/dashboard/prompts", dependencies=[Depends(verify_api_key)])
async def create_prompt(request: PromptCreateRequest):
    """Create a new prompt."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        prompt_id = await db_instance.create_prompt(
            name=request.name,
            content=request.content,
            industry=request.industry,
            description=request.description,
            is_active=request.is_active,
        )
        return {"status": "created", "id": prompt_id}
    except Exception as e:
        logger.error(f"Error creating prompt: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/dashboard/prompt/{prompt_id}", dependencies=[Depends(verify_api_key)])
async def get_prompt_by_id(prompt_id: int):
    """Get a single prompt by ID with full content."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        prompt = await db_instance.get_prompt_by_id(prompt_id)
        if not prompt:
            raise HTTPException(status_code=404, detail="Prompt not found")
        return prompt
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching prompt {prompt_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.patch("/dashboard/prompt/{prompt_id}", dependencies=[Depends(verify_api_key)])
async def patch_prompt(prompt_id: int, request: PromptPatchRequest):
    """Update fields on an existing prompt."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        await db_instance.update_prompt(
            prompt_id,
            name=request.name,
            content=request.content,
            industry=request.industry,
            description=request.description,
            is_active=request.is_active,
        )
        return {"status": "updated"}
    except Exception as e:
        logger.error(f"Error updating prompt {prompt_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/dashboard/prompt/{prompt_id}", dependencies=[Depends(verify_api_key)])
async def delete_prompt(prompt_id: int):
    """Delete a prompt by ID."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        await db_instance.delete_prompt(prompt_id)
        return {"status": "deleted"}
    except Exception as e:
        logger.error(f"Error deleting prompt {prompt_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/dashboard/prompt/{prompt_id}/clone", dependencies=[Depends(verify_api_key)])
async def clone_prompt(prompt_id: int, request: PromptCloneRequest):
    """Clone an existing prompt to a new name/industry."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        new_id = await db_instance.clone_prompt(prompt_id, request.new_name, request.new_industry)
        return {"status": "cloned", "id": new_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error cloning prompt {prompt_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# --- Agent Config endpoints ---

@app.get("/dashboard/agents", dependencies=[Depends(verify_api_key)])
async def get_all_agents():
    """List all agent configurations."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        return await db_instance.get_all_agent_configs()
    except Exception as e:
        logger.error(f"Error fetching agents: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/dashboard/agents", dependencies=[Depends(verify_api_key)])
async def upsert_agent(request: AgentConfigUpsertRequest):
    """Create or update an agent configuration."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        slug = await db_instance.upsert_agent_config(
            slug=request.slug,
            owner_id=request.owner_id,
            opening_line=request.opening_line,
            mcp_endpoint_url=request.mcp_endpoint_url,
            is_active=request.is_active,
            prompt_id=request.prompt_id,
            ai_config_name=request.ai_config_name,
        )
        return {"status": "ok", "slug": slug}
    except Exception as e:
        logger.error(f"Error upserting agent: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/dashboard/agent/{slug}", dependencies=[Depends(verify_api_key)])
async def delete_agent(slug: str):
    """Delete an agent configuration."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        await db_instance.delete_agent_config(slug)
        return {"status": "deleted"}
    except Exception as e:
        logger.error(f"Error deleting agent {slug}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# --- Tenant Config endpoints ---

@app.get("/dashboard/tenants", dependencies=[Depends(verify_api_key)])
async def get_all_tenants(active_only: bool = False, limit: int = 200):
    """List tenant configurations."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        return await db_instance.get_all_tenant_configs(active_only=active_only, limit=limit)
    except Exception as e:
        logger.error(f"Error fetching tenants: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/dashboard/tenant/{tenant_id}", dependencies=[Depends(verify_api_key)])
async def get_tenant(tenant_id: str):
    """Get a single tenant configuration by tenant_id."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        tenant = await db_instance.get_tenant_config(tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        return tenant
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/dashboard/tenants", dependencies=[Depends(verify_api_key)])
async def upsert_tenant(request: TenantConfigUpsertRequest):
    """Create or update tenant configuration."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        tenant_id = await db_instance.upsert_tenant_config(
            tenant_id=request.tenant_id,
            display_name=request.display_name,
            agent_slug=request.agent_slug,
            workflow_policy=request.workflow_policy,
            routing_policy=request.routing_policy,
            ai_overrides=request.ai_overrides,
            opening_line=request.opening_line,
            api_key=request.api_key,
            is_active=request.is_active,
        )
        return {"status": "ok", "tenant_id": tenant_id}
    except Exception as e:
        logger.error(f"Error upserting tenant {request.tenant_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/dashboard/tenant/{tenant_id}", dependencies=[Depends(verify_api_key)])
async def delete_tenant(tenant_id: str):
    """Delete tenant configuration."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        await db_instance.delete_tenant_config(tenant_id)
        return {"status": "deleted"}
    except Exception as e:
        logger.error(f"Error deleting tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# --- Data Schema endpoints ---

@app.get("/dashboard/data-schemas", dependencies=[Depends(verify_api_key)])
async def get_data_schemas(slug: Optional[str] = None):
    """List data schema fields, optionally filtered by agent slug."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        return await db_instance.get_all_data_schemas(slug=slug)
    except Exception as e:
        logger.error(f"Error fetching data schemas: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/dashboard/data-schemas", dependencies=[Depends(verify_api_key)])
async def create_data_schema_field(request: DataSchemaFieldRequest):
    """Add a data collection field to an agent's schema."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        field_id = await db_instance.create_data_schema_field(
            slug=request.slug,
            field_name=request.field_name,
            field_type=request.field_type,
            description=request.description,
        )
        return {"status": "created", "id": field_id}
    except Exception as e:
        logger.error(f"Error creating schema field: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/dashboard/data-schema/{field_id}", dependencies=[Depends(verify_api_key)])
async def delete_data_schema_field(field_id: int):
    """Delete a data schema field."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        await db_instance.delete_data_schema_field(field_id)
        return {"status": "deleted"}
    except Exception as e:
        logger.error(f"Error deleting schema field {field_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# --- AI Config endpoints ---

class AIConfigUpsertRequest(BaseModel):
    name: str
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.7
    stt_provider: str = "deepgram"
    stt_model: str = "nova-3"
    stt_language: str = "en-US"
    tts_provider: str = "openai"
    tts_model: str = "tts-1"
    tts_voice: str = "alloy"
    tts_language: str = ""
    tts_speed: float = 1.0
    vad_silence_threshold: float = 0.5
    vad_sensitivity: float = 0.5
    vad_interruption_threshold: float = 0.5
    is_active: bool = True

@app.get("/dashboard/ai-configs", dependencies=[Depends(verify_api_key)])
async def get_all_ai_configs():
    """List all AI configurations."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        return await db_instance.get_all_ai_configs()
    except Exception as e:
        logger.error(f"Error fetching AI configs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/dashboard/ai-config", dependencies=[Depends(verify_api_key)])
async def get_ai_config_by_name(name: str = "default_telephony_config"):
    """Get a single AI config by name."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        config = await db_instance.get_ai_config(name)
        if not config:
            raise HTTPException(status_code=404, detail="AI config not found")
        return config
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching AI config {name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/dashboard/ai-configs", dependencies=[Depends(verify_api_key)])
async def upsert_ai_config_endpoint(request: AIConfigUpsertRequest):
    """Create or update an AI configuration."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        name = await db_instance.upsert_ai_config_full(
            name=request.name,
            llm_provider=request.llm_provider,
            llm_model=request.llm_model,
            llm_temperature=request.llm_temperature,
            stt_provider=request.stt_provider,
            stt_model=request.stt_model,
            stt_language=request.stt_language,
            tts_provider=request.tts_provider,
            tts_model=request.tts_model,
            tts_voice=request.tts_voice,
            tts_language=request.tts_language,
            tts_speed=request.tts_speed,
            vad_silence_threshold=request.vad_silence_threshold,
            vad_sensitivity=request.vad_sensitivity,
            vad_interruption_threshold=request.vad_interruption_threshold,
            is_active=request.is_active,
        )
        return {"status": "ok", "name": name}
    except Exception as e:
        logger.error(f"Error upserting AI config: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/dashboard/ai-config/{name}", dependencies=[Depends(verify_api_key)])
async def delete_ai_config(name: str):
    """Delete an AI configuration by name."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        async with db_instance.pool.acquire() as conn:
            await conn.execute("DELETE FROM ai_configs WHERE name = $1", name)
        return {"status": "deleted"}
    except Exception as e:
        logger.error(f"Error deleting AI config {name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# --- Objection endpoints ---

class ObjectionUpsertRequest(BaseModel):
    objection_text: str
    response_text: str = ""
    agent_slug: Optional[str] = None

@app.get("/dashboard/objections", dependencies=[Depends(verify_api_key)])
async def get_objections(agent_slug: Optional[str] = None):
    """List objections, optionally filtered by agent_slug."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        return await db_instance.get_all_objections(agent_slug=agent_slug)
    except Exception as e:
        logger.error(f"Error fetching objections: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/dashboard/objections", dependencies=[Depends(verify_api_key)])
async def upsert_objection(request: ObjectionUpsertRequest):
    """Create or update an objection handler."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        await db_instance.upsert_objection(
            objection_text=request.objection_text,
            response_text=request.response_text,
            agent_slug=request.agent_slug,
        )
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error upserting objection: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/dashboard/objection/{objection_id}", dependencies=[Depends(verify_api_key)])
async def delete_objection(objection_id: int):
    """Delete an objection handler."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        await db_instance.delete_objection(objection_id)
        return {"status": "deleted"}
    except Exception as e:
        logger.error(f"Error deleting objection {objection_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# --- Test call with specific prompt ---

@app.post("/dashboard/test-call", dependencies=[Depends(verify_api_key)])
async def trigger_test_call(request: TestCallRequest, background_tasks: BackgroundTasks, req: Request):
    """Trigger a test call using a specific prompt from the DB.

    This temporarily activates the chosen prompt for the agent_slug,
    then dispatches a call.  The prompt is set as active so the agent
    picks it up on join.
    """
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")

    client_ip = req.client.host if req.client else "unknown"
    _check_rate_limit(client_ip)

    # Load the chosen prompt and make it active for the agent
    prompt = await db_instance.get_prompt_by_id(request.prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    # Activate this prompt under the agent slug name
    await db_instance.update_active_prompt(request.agent_slug, prompt["content"])

    # Dispatch normal outbound call
    call_request = OutboundCallRequest(
        phone_number=request.phone_number,
        business_name=request.business_name or f"Test ({prompt.get('industry', 'general')})",
        agent_slug=request.agent_slug,
        from_number=request.from_number,
    )
    background_tasks.add_task(initiate_outbound_call, call_request)

    return {
        "status": "queued",
        "message": f"Test call to {request.phone_number} using prompt '{prompt['name']}' ({prompt.get('industry', '')})",
        "prompt_name": prompt["name"],
        "industry": prompt.get("industry", ""),
    }

@app.get("/dashboard/prompt", dependencies=[Depends(verify_api_key)])
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

@app.post("/dashboard/prompt", dependencies=[Depends(verify_api_key)])
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

@app.get("/dashboard/calls", dependencies=[Depends(verify_api_key)])
async def get_dashboard_calls(request: Request, limit: int = 10, tenant_id: Optional[str] = None):
    """Get recent calls."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        calls = await db_instance.get_recent_calls(limit=limit)
        resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
        # Rewrite recording URLs to point to our proxy
        # This fixes issues where the frontend (local) cannot access the S3/MinIO endpoint (internal docker)
        # or avoids CORS/Presigning issues entirely.
        filtered_calls = []
        for call in calls:
            _normalize_call_payload(call)
            if _matches_tenant(call, resolved_tenant_id):
                _rewrite_recording_url(call)
                filtered_calls.append(call)
        return filtered_calls
    except Exception as e:
        logger.error(f"Error fetching calls: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/dashboard/calls/by-tenant", dependencies=[Depends(verify_api_key)])
async def get_dashboard_calls_by_tenant(
    request: Request,
    limit: int = 100,
    tenant_id: Optional[str] = None,
):
    """Get recent calls filtered by tenant.

    tenant_id can be supplied via query param or X-Tenant-Id header.
    """
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")

    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
    if not resolved_tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")

    try:
        calls = await db_instance.get_recent_calls(limit=limit)
        filtered_calls = []
        for call in calls:
            _normalize_call_payload(call)
            if _matches_tenant(call, resolved_tenant_id):
                _rewrite_recording_url(call)
                filtered_calls.append(call)
        return filtered_calls
    except Exception as e:
        logger.error(f"Error fetching tenant calls: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/dashboard/call/{call_id}/diagnostics", dependencies=[Depends(verify_api_key)])
async def get_call_diagnostics(call_id: int, request: Request, tenant_id: Optional[str] = None):
    """Return compact reliability diagnostics for a specific call."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")

    resolved_tenant_id = _resolve_tenant_id(request, tenant_id)

    try:
        call = await db_instance.get_call(call_id)
        if not call:
            raise HTTPException(status_code=404, detail="Call not found")

        _normalize_call_payload(call)
        if resolved_tenant_id and not _matches_tenant(call, resolved_tenant_id):
            raise HTTPException(status_code=404, detail="Call not found")

        return _extract_call_diagnostics(call)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching call diagnostics for {call_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/dashboard/call/{call_id}", dependencies=[Depends(verify_api_key)])
async def get_call_details(call_id: int, request: Request, tenant_id: Optional[str] = None):
    """Get details for a specific call, including transcript."""
    if not db_instance:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        call = await db_instance.get_call(call_id)
        if not call:
             raise HTTPException(status_code=404, detail="Call not found")

        _normalize_call_payload(call)
        resolved_tenant_id = _resolve_tenant_id(request, tenant_id)
        if resolved_tenant_id and not _matches_tenant(call, resolved_tenant_id):
            raise HTTPException(status_code=404, detail="Call not found")
        _rewrite_recording_url(call)

        return call
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching call {call_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/dashboard/appointments", dependencies=[Depends(verify_api_key)])
async def get_appointments():
    """
    Get scheduled appointments/callbacks booked during AI calls.
    Returns empty list — appointments feature coming soon.
    """
    return []


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


@app.get("/health/startup")
async def startup_health_check():
    """Report startup-critical configuration checks for API and telephony path."""
    required = ["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "NEON_DATABASE_URL"]
    optional_recommended = ["SIP_TRUNK_ID", "LIVEKIT_OUTBOUND_TRUNK_ID", "SARVAM_API_KEY", "GROQ_API_KEY"]

    missing_required = [name for name in required if not os.getenv(name)]
    missing_recommended = [name for name in optional_recommended if not os.getenv(name)]

    return {
        "status": "ok" if not missing_required else "degraded",
        "missing_required": missing_required,
        "missing_recommended": missing_recommended,
        "cors_allowed_origins": _cors_origins,
        "rate_limit_per_min": _RATE_LIMIT_MAX,
        "tenant_rate_limit_per_min": _RATE_LIMIT_TENANT_MAX,
        "rbac_enforced": os.getenv("RBAC_ENFORCED", "false").lower() in {"1", "true", "yes", "on"},
        "tenant_api_keys_loaded": len(_TENANT_API_KEYS),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
