
import datetime
import logging
import json
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    get_job_context,
)
from livekit.agents.llm import function_tool
from livekit.plugins import deepgram, openai, silero
from livekit import api
from livekit.protocol.sip import CreateSIPParticipantRequest

from mcp_integration import load_mcp_tools
from neon_db import get_db
from webhook_dispatcher import WebhookDispatcher

load_dotenv()
logger = logging.getLogger("outbound-agent")

# Whispey Observability Integration
try:
    from whispey import LivekitObserve
    WHISPEY_ENABLED = True
except ImportError:
    WHISPEY_ENABLED = False
    logger.warning("Whispey not installed. Install with: pip install whispey")

async def hangup_call():
    """End the call for all participants by deleting the room."""
    ctx = get_job_context()
    if ctx is None:
        logger.warning("Not running in a job context, cannot hang up")
        return
    
    try:
        await ctx.api.room.delete_room(
            api.DeleteRoomRequest(
                room=ctx.room.name,
            )
        )
        logger.info(f"Call ended - room {ctx.room.name} deleted")
    except Exception as e:
        logger.error(f"Failed to delete room: {e}")

async def entrypoint(ctx: JobContext):
    """Main entry point for the outbound voice agent."""
    
    # 1. Initialize per-call state
    call_metadata = {
        "notes": []
    }

    # Define function tools
    @function_tool
    async def get_current_time() -> str:
        """Get the current time."""
        return f"The current time is {datetime.datetime.now().strftime('%I:%M %p')}"

    @function_tool
    async def update_call_data(field: str, value: str) -> str:
        """Record a piece of data collected from the user."""
        call_metadata[field] = value
        logger.info(f"Captured data: {field} = {value}")
        
        if 'dispatcher' in locals() and dispatcher:
            await dispatcher.dispatch("data.captured", {
                "field": field,
                "value": value
            })
            
        return ""

    @function_tool
    async def add_note(note: str) -> str:
        """Add a general note about the call."""
        call_metadata["notes"].append(note)
        logger.info(f"Note added: {note}")
        return ""

    @function_tool
    async def end_call() -> str:
        """End the call safely."""
        logger.info("Agent ending call...")
        await hangup_call()
        return ""

    await ctx.connect()
    logger.info(f"Connected to room {ctx.room.name}")
    
    # Initialize Whispey observability if enabled
    whispey = None
    if WHISPEY_ENABLED:
        whispey_api_key = os.getenv("WHISPEY_API_KEY")
        whispey_agent_id = os.getenv("WHISPEY_AGENT_ID", "outbound-agent")
        if whispey_api_key:
            try:
                whispey = LivekitObserve(agent_id=whispey_agent_id, apikey=whispey_api_key)
                logger.info(f"Whispey observability enabled for agent: {whispey_agent_id}")
            except Exception as e:
                logger.error(f"Failed to initialize Whispey: {e}")
        else:
            logger.warning("WHISPEY_API_KEY not set, observability disabled")

    # 2. Extract outbound details from Job Metadata
    # Note: server.py puts this in `metadata` of the room, but for pure agent dispatch
    # it's often in ctx.job.metadata. We'll check both.
    
    initial_metadata = {}
    if ctx.job.metadata:
        try:
            initial_metadata = json.loads(ctx.job.metadata)
        except:
            pass
            
    if not initial_metadata and ctx.room.metadata:
        try:
            initial_metadata = json.loads(ctx.room.metadata)
        except:
            pass

    phone_number = initial_metadata.get("phone_number")
    business_name = initial_metadata.get("business_name", "there")
    agent_slug = initial_metadata.get("agent_slug", "default_roofing_agent")
    
    if not phone_number:
        logger.error("No phone number found in metadata. Cannot place outbound call.")
        return

    logger.info(f"Preparing outbound call to {phone_number} using agent {agent_slug}")

    # 3. Setup Database & Config
    db = await get_db()
    
    # Fetch agent configuration
    agent_config = await db.get_agent_config(agent_slug)
    if not agent_config:
        logger.warning(f"Agent {agent_slug} not found, falling back to default")
        agent_slug = "default_roofing_agent"
        agent_config = await db.get_agent_config(agent_slug) or {}

    # Fetch schema & webhooks
    schema_fields = await db.get_data_schema(agent_slug)
    webhooks = await db.get_webhooks(agent_slug)
    dispatcher = WebhookDispatcher(webhooks, agent_slug)
    
    # Fire call.initiated event
    await dispatcher.dispatch("call.initiated", {
        "phone_number": phone_number,
        "business_name": business_name,
        "agent_slug": agent_slug
    })

    # Fetch instructions
    agent_instructions = await db.get_active_prompt(agent_slug) 
    if not agent_instructions:
        agent_instructions = "You are a professional caller."

    # Inject schema
    if schema_fields:
        schema_prompt = "\n\nYou are authorized to collect the following information:\n"
        for field in schema_fields:
            schema_prompt += f"- {field['field_name']}: {field.get('description', '')}\n"
        schema_prompt += "\nUse the `update_call_data` tool to save these values."
        agent_instructions += schema_prompt

    # Create contact
    contact_id = await db.upsert_contact(phone_number, business_name)
    prompt_id = await db.get_prompt_id(agent_slug)

    # AI Config
    ai_config = await db.get_ai_config("default_telephony_config")
    if not ai_config:
         ai_config = {
            "llm_provider": "openai", "llm_model": "gpt-4o-mini", "llm_temperature": 0.7,
            "stt_provider": "deepgram", "stt_model": "nova-3", "stt_language": "en-US",
            "tts_provider": "openai", "tts_model": "tts-1", "tts_voice": "alloy"
        }

    # Load MCP Tools
    mcp_tools = await load_mcp_tools(mcp_url=agent_config.get("mcp_endpoint_url"))
    
    all_tools = [get_current_time, update_call_data, add_note, end_call] + mcp_tools

    # 4. Initialize Agent Components
    agent = Agent(instructions=agent_instructions, tools=all_tools)
    
    llm = openai.LLM(model=ai_config.get("llm_model", "gpt-4o-mini"))
    stt = deepgram.STT(model=ai_config.get("stt_model", "nova-3"), language=ai_config.get("stt_language", "en-US"))
    
    # Configure TTS based on provider
    if ai_config["tts_provider"] == "openai":
        tts = openai.TTS(
            model=ai_config.get("tts_model", "tts-1"),
            voice=ai_config.get("tts_voice", "alloy")
        )
    else:
        logger.warning(f"Unsupported TTS provider: {ai_config['tts_provider']}, using OpenAI")
        tts = openai.TTS(model="tts-1", voice="alloy")
    
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=stt,
        llm=llm,
        tts=tts
    )
    
    # Start Whispey session tracking with metadata
    session_id = None
    if whispey:
        try:
            session_id = whispey.start_session(
                session=session,
                phone_number=phone_number,
                business_name=business_name
            )
            logger.info(f"Whispey session started: {session_id}")
        except Exception as e:
            logger.error(f"Failed to start Whispey session: {e}")
    
    # Register Whispey shutdown callback
    if whispey and session_id:
        async def whispey_shutdown():
            try:
                await whispey.export(session_id)
                logger.info(f"Whispey data exported for session: {session_id}")
            except Exception as e:
                logger.error(f"Failed to export Whispey data: {e}")
        ctx.add_shutdown_callback(whispey_shutdown)

    # 5. Start Session ASYNCHRONOUSLY (Critical for latency)
    # This ensures the agent is ready to listen immediately upon connection
    session_start_task = asyncio.create_task(session.start(agent=agent, room=ctx.room))

    # 6. Dial the user (SIP)
    sip_trunk_id = os.getenv("SIP_TRUNK_ID")
    sip_from_number = os.getenv("SIP_FROM_NUMBER")
    
    if not sip_trunk_id:
        logger.error("SIP_TRUNK_ID not set in env")
        return

    logger.info(f"Dialing {phone_number}...")
    try:
        await ctx.api.sip.create_sip_participant(
            CreateSIPParticipantRequest(
                room_name=ctx.room.name,
                sip_trunk_id=sip_trunk_id,
                sip_call_to=phone_number,
                sip_number=sip_from_number,
                participant_identity=phone_number,
                participant_name=business_name,
                wait_until_answered=True # Wait here so we know they picked up
            )
        )
        logger.info("Call answered!")
    except Exception as e:
        logger.error(f"Failed to dial: {e}")
        await dispatcher.dispatch("call.failed", {"error": str(e)})
        return

    # 7. Wait for session to be fully started (should be quick now)
    await session_start_task

    # 8. Fire Opener immediately without waiting for LLM
    opening_line = agent_config.get("opening_line") or "Hello? Am I speaking with the business owner?"
    asyncio.create_task(session.generate_reply(instructions=opening_line))
    
    # 9. Wait for disconnect
    call_start_time = datetime.datetime.now()
    try:
        # Wait for room disconnect - this is the proper way to wait for call to end
        await ctx.room.wait_for_disconnect()
    except AttributeError:
        # Fallback for newer versions that don't have wait_for_disconnect
        try:
            await session.aclose()
        except:
            pass
    finally:
        # Calculate call duration
        call_end_time = datetime.datetime.now()
        duration_seconds = int((call_end_time - call_start_time).total_seconds())
        
        # Capture transcript from session history
        transcript_text = None
        try:
            if session.history:
                transcript_lines = []
                for item in session.history.items:
                    role = "Agent" if item.role == "assistant" else "User"
                    if hasattr(item, 'content') and item.content:
                        transcript_lines.append(f"{role}: {item.content}")
                transcript_text = "\n".join(transcript_lines)
        except Exception as e:
            logger.error(f"Failed to capture transcript: {e}")
        
        # Log call to database
        try:
            await db.log_call(
                contact_id=contact_id,
                room_id=ctx.room.name,
                prompt_id=prompt_id,
                duration_seconds=duration_seconds,
                call_status="completed",
                transcript=transcript_text,
                captured_data=call_metadata
            )
            logger.info(f"Call logged successfully. Duration: {duration_seconds}s")
        except Exception as e:
            logger.error(f"Failed to log call: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        agent_name="outbound_agent" # Distinct name
    ))
