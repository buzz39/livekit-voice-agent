import re
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
    WHISPEY_AVAILABLE = True
except ImportError:
    WHISPEY_AVAILABLE = False
    logger.warning("Whispey not installed. Install with: pip install whispey")

# Check if Whispey is enabled via environment variable (default: False)
WHISPEY_ENABLED = os.getenv("ENABLE_WHISPEY", "false").lower() in ("true", "1", "yes")


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
    call_metadata = {"notes": []}

    # Connect to room
    await ctx.connect()
    logger.info(f"Connected to room {ctx.room.name}")

    # Initialize Whispey observability if enabled
    whispey = None
    if WHISPEY_ENABLED and WHISPEY_AVAILABLE:
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
    elif WHISPEY_ENABLED and not WHISPEY_AVAILABLE:
        logger.warning("ENABLE_WHISPEY is set but Whispey package is not installed")

    # 2. Extract outbound metadata (robust)
    initial_metadata = {}

    # --- 1. Try ctx.job.metadata ---
    if ctx.job and getattr(ctx.job, "metadata", None):
        try:
            meta = ctx.job.metadata
            if isinstance(meta, (bytes, bytearray)):
                meta = meta.decode("utf-8")
            initial_metadata = json.loads(meta)
            logger.info(f"[metadata] Loaded from ctx.job.metadata: {initial_metadata}")
        except Exception as e:
            logger.warning(f"[metadata] Failed to parse ctx.job.metadata: {e}")

    # --- 2. If empty, try ctx.room.metadata ---
    if not initial_metadata and ctx.room and getattr(ctx.room, "metadata", None):
        try:
            meta = ctx.room.metadata
            if isinstance(meta, (bytes, bytearray)):
                meta = meta.decode("utf-8")
            initial_metadata = json.loads(meta)
            logger.info(f"[metadata] Loaded from ctx.room.metadata: {initial_metadata}")
        except Exception as e:
            logger.warning(f"[metadata] Failed to parse ctx.room.metadata: {e}")

    # --- 3. Normalize nested metadata: sometimes stored as {"metadata": "{...json...}"} ---
    if isinstance(initial_metadata, dict) and "metadata" in initial_metadata:
        try:
            nested = initial_metadata["metadata"]
            if isinstance(nested, (bytes, bytearray)):
                nested = nested.decode("utf-8")
            initial_metadata = json.loads(nested)
            logger.info(f"[metadata] Loaded nested metadata: {initial_metadata}")
        except Exception:
            pass

    # Extract fields safely
    phone_number = initial_metadata.get("phone_number")
    business_name = initial_metadata.get("business_name", "there")
    agent_slug = initial_metadata.get("agent_slug", "default_roofing_agent")

    logger.info(f"Parsed metadata → phone: {phone_number}, business: {business_name}, slug: {agent_slug}")

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
    try:
        await dispatcher.dispatch(
            "call.initiated",
            {"phone_number": phone_number, "business_name": business_name, "agent_slug": agent_slug},
        )
    except Exception as e:
        logger.debug(f"call.initiated webhook error: {e}")

    # Fetch instructions
    agent_instructions = await db.get_active_prompt(agent_slug)
    if not agent_instructions:
        agent_instructions = "You are a professional caller."

    # Inject schema into instructions
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
            "llm_provider": "openai",
            "llm_model": "gpt-4o-mini",
            "llm_temperature": 0.7,
            "stt_provider": "deepgram",
            "stt_model": "nova-3",
            "stt_language": "en-US",
            "tts_provider": "openai",
            "tts_model": "tts-1",
            "tts_voice": "alloy",
        }

    # Load MCP Tools
    mcp_tools = await load_mcp_tools(mcp_url=agent_config.get("mcp_endpoint_url"))

    # ---- Define function tools AFTER db/dispatcher/contact_id are available ----
    @function_tool
    async def get_current_time() -> str:
        """Get the current time."""
        return f"The current time is {datetime.datetime.now().strftime('%I:%M %p')}"

    @function_tool
    async def update_call_data(field: str, value: str) -> str:
        """Record a piece of data collected from the user and persist important fields."""
        call_metadata[field] = value
        logger.info(f"Captured data: {field} = {value}")

        # If email, persist immediately and fire webhook
        if field.lower() == "email":
            try:
                await db.update_contact_email(contact_id, value)
                await dispatcher.dispatch(
                    "contact.email.captured", {"contact_id": contact_id, "phone_number": phone_number, "email": value}
                )
            except Exception as e:
                logger.exception(f"Failed to persist or dispatch email: {e}")

        # Always dispatch a generic data.captured event
        try:
            await dispatcher.dispatch("data.captured", {"field": field, "value": value, "contact_id": contact_id})
        except Exception as e:
            logger.debug(f"data.captured webhook error: {e}")

        return ""

    @function_tool
    async def add_note(note: str) -> str:
        """Add a general note about the call."""
        call_metadata["notes"].append(note)
        logger.info(f"Note added: {note}")
        return ""

    # IMPORTANT: end_call now logs call BEFORE issuing hangup to avoid losing call_metadata
    @function_tool
    async def end_call() -> str:
        """End the call safely - persist call then hangup."""
        logger.info("Agent requested end_call — persisting data before hangup")

        # Persist call immediately (best-effort)
        try:
            email_flag = bool(call_metadata.get("email"))
            # Attempt to write an entry (this will create a call record so you have captured data even if teardown crashes)
            await db.log_call(
                contact_id=contact_id,
                room_id=ctx.room.name,
                prompt_id=prompt_id,
                duration_seconds=None,  # final duration will be updated later if needed
                call_status="ending",
                transcript=None,
                captured_data=call_metadata,
                email_captured=email_flag,
            )
            await dispatcher.dispatch(
                "call.ending", {"room_id": ctx.room.name, "contact_id": contact_id, "email_captured": email_flag}
            )
            logger.info("Early call log persisted before hangup")
        except Exception as e:
            logger.exception(f"Failed early log_call in end_call: {e}")

        # Now attempt hangup
        try:
            await hangup_call()
        except Exception as e:
            logger.error(f"hangup_call during end_call failed: {e}")

        return ""

    all_tools = [get_current_time, update_call_data, add_note, end_call] + mcp_tools

    # 4. Initialize Agent Components
    agent = Agent(instructions=agent_instructions, tools=all_tools)

    llm = openai.LLM(model=ai_config.get("llm_model", "gpt-4o-mini"))
    stt = deepgram.STT(model=ai_config.get("stt_model", "nova-3"), language=ai_config.get("stt_language", "en-US"))

    # Configure TTS based on provider
    if ai_config["tts_provider"] == "openai":
        tts = openai.TTS(model=ai_config.get("tts_model", "tts-1"), voice=ai_config.get("tts_voice", "alloy"))
    else:
        logger.warning(f"Unsupported TTS provider: {ai_config['tts_provider']}, using OpenAI")
        tts = openai.TTS(model="tts-1", voice="alloy")

    session = AgentSession(vad=silero.VAD.load(), stt=stt, llm=llm, tts=tts)

    # Start Whispey session tracking with metadata
    session_id = None
    if whispey:
        try:
            session_id = whispey.start_session(session, room=ctx.room, phone_number=phone_number, customer_name=business_name)
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
    session_start_task = asyncio.create_task(session.start(agent=agent, room=ctx.room))

    # 6. Dial the user (SIP)
    sip_trunk_id = os.getenv("SIP_TRUNK_ID")
    sip_from_number = os.getenv("SIP_FROM_NUMBER")

    if not sip_trunk_id:
        logger.error("SIP_TRUNK_ID not set in env")
        return

    # Sanitize participant_identity to avoid Rust parsing errors (remove non-digit chars)
    clean_identity = re.sub(r"\D", "", phone_number)

    logger.info(f"Dialing {phone_number} (identity={clean_identity})...")
    try:
        await ctx.api.sip.create_sip_participant(
            CreateSIPParticipantRequest(
                room_name=ctx.room.name,
                sip_trunk_id=sip_trunk_id,
                sip_call_to=phone_number,
                sip_number=sip_from_number,
                participant_identity=clean_identity,
                participant_name=business_name,
                wait_until_answered=True,  # Wait here so we know they picked up
            )
        )
        logger.info("Call answered!")
    except Exception as e:
        logger.error(f"Failed to dial: {e}")
        try:
            await dispatcher.dispatch("call.failed", {"error": str(e)})
        except Exception:
            pass
        return

    # 7. Wait for session to be fully started (should be quick now)
    await session_start_task

    # 8. Fire Opener using session.say() for immediate audio output
    opening_line = agent_config.get("opening_line") or "Hello? Am I speaking with the business owner?"

    # Dynamic Business Name Injection
    if business_name:
        if "{business_name}" in opening_line:
            opening_line = opening_line.format(business_name=business_name)
        elif "Am I speaking with the owner?" in opening_line and business_name != "Local Tester":
            opening_line = opening_line.replace("Am I speaking with the owner?", f"Am I speaking with the owner of {business_name}?")

    logger.info(f"Final Opening Line: '{opening_line}'")
    try:
        await session.say(opening_line, allow_interruptions=True)
    except Exception as e:
        logger.warning(f"Failed to play opening line: {e}")

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
            if getattr(session, "history", None):
                transcript_lines = []
                items = getattr(session.history, "items", None) or getattr(session.history, "messages", None) or []
                for item in items:
                    role = "Agent" if getattr(item, "role", None) == "assistant" else "User"
                    text = getattr(item, "content", None) or getattr(item, "text", None) or ""
                    if text:
                        transcript_lines.append(f"{role}: {text}")
                transcript_text = "\n".join(transcript_lines)
        except Exception as e:
            logger.error(f"Failed to capture transcript: {e}")

        # Fetch recordings from LiveKit (if any) and try to persist
        recording_url = None
        try:
            resp = await ctx.api.recording.list_recordings(api.ListRecordingsRequest(room_name=ctx.room.name))
            recordings = getattr(resp, "recordings", None) or getattr(resp, "content", None) or []
            if recordings:
                first = recordings[0]
                recording_url = getattr(first, "url", None) or getattr(first, "download_url", None) or (first.get("url") if isinstance(first, dict) else None)
                if recording_url:
                    try:
                        await db.update_call_recording(ctx.room.name, recording_url)
                        await dispatcher.dispatch("call.recording.ready", {"room_id": ctx.room.name, "recording_url": recording_url, "contact_id": contact_id})
                    except Exception as e:
                        logger.debug(f"Failed to persist/dispatch recording url: {e}")
        except Exception as e:
            logger.debug(f"Failed to fetch recordings: {e}")

        # Final attempt to persist the call (robust)
        try:
            email_value = call_metadata.get("email")
            email_flag = bool(email_value)
            # Update the final call row (duration, transcript, call_status). Note: if an early record exists (from end_call), this inserts a new row; you may want to update instead depending on schema.
            await db.log_call(
                contact_id=contact_id,
                room_id=ctx.room.name,
                prompt_id=prompt_id,
                duration_seconds=duration_seconds,
                call_status="completed",
                transcript=transcript_text,
                captured_data=call_metadata,
                email_captured=email_flag,
            )
            await dispatcher.dispatch(
                "call.completed",
                {"room_id": ctx.room.name, "contact_id": contact_id, "duration_seconds": duration_seconds, "email_captured": email_flag},
            )
            logger.info(f"Call logged successfully. Duration: {duration_seconds}s")
        except Exception as e:
            logger.exception(f"Failed to log call in finalizer: {e}")

        # Clean up
        try:
            await dispatcher.close()
        except Exception:
            pass

        try:
            await session.aclose()
        except Exception:
            pass

        try:
            await db.close()
        except Exception:
            pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="telephony_agent",  # Distinct name
        )
    )
