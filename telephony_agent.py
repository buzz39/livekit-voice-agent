"""
LiveKit AI Telephony Agent with n8n MCP Integration

A production-ready voice AI agent for handling inbound phone calls with:
- Natural language conversations powered by configurable LLM (OpenAI / Groq)
- High-quality speech recognition (Deepgram Nova-3)
- Flexible text-to-speech (Cartesia, OpenAI, Sarvam, Inworld, Deepgram)
- Telephony-optimized noise cancellation (BVCTelephony)
- STT-based turn detection for natural conversation flow
- Integration with n8n workflows via Model Context Protocol (MCP)
- Extensible function tools for custom capabilities

License: MIT
"""

import datetime
import logging
import json
from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    get_job_context,
)
from livekit.agents.llm import function_tool, LLMError
from livekit.agents.voice.room_io import RoomInputOptions, RoomOutputOptions
from livekit.agents.voice.events import ErrorEvent
from livekit.plugins import noise_cancellation
from livekit import rtc
from mcp_integration import load_mcp_tools
from neon_db import get_db
from outbound.providers import (
    build_llm,
    build_stt,
    build_tts,
    resolve_ai_configuration,
)
from outbound.config import load_agent_config, prepare_instructions, load_ai_config
    

load_dotenv()
logger = logging.getLogger("telephony-agent")

LLM_ERROR_FALLBACK_MESSAGE = "Give me just a moment, I need to gather my thoughts."


async def hangup_call():
    """End the call for all participants."""
    ctx = get_job_context()
    if ctx is None:
        logger.warning("Not running in a job context, cannot hang up")
        return
    
    try:
        await ctx.room.disconnect()
        logger.info(f"Disconnected from room {ctx.room.name}")
    except Exception as e:
        logger.error(f"Failed to disconnect room: {e}")



async def entrypoint(ctx: JobContext):
    """Main entry point for the telephony voice agent."""
    
    # Initialize per-call state
    call_metadata = {
        "notes": []
    }

    # Define function tools within the closure to access call_metadata securely
    @function_tool
    async def get_current_time() -> str:
        """Get the current time."""
        return f"The current time is {datetime.datetime.now().strftime('%I:%M %p')}"

    @function_tool
    async def update_call_data(field: str, value: str) -> str:
        """
        Record a piece of data collected from the user.
        Args:
            field: The name of the field to update (e.g., 'email', 'interest_level', 'roof_age').
            value: The value to record.
        """
        call_metadata[field] = value
        logger.info(f"Captured data: {field} = {value}")
        
        # Fire data.captured webhook
        if 'dispatcher' in locals() and dispatcher:
            await dispatcher.dispatch("data.captured", {
                "field": field,
                "value": value
            })
            
        return ""

    @function_tool
    async def add_note(note: str) -> str:
        """Add a general note about the call that doesn't fit into a specific field."""
        call_metadata["notes"].append(note)
        logger.info(f"Note added: {note}")
        return ""

    @function_tool
    async def end_call() -> str:
        """End the current phone call. Call this after you have said goodbye to the user."""
        logger.info("Agent ending call...")
        await hangup_call()
        return ""

    await ctx.connect()
    
    # Wait for participant (caller) to join
    participant = await ctx.wait_for_participant()
    logger.info(f"Phone call connected from participant: {participant.identity}")
    
    # Connect to Neon database
    db = await get_db()
    
    # Agent instructions will be fetched after determining the agent_slug

    
    # Extract metadata from room
    business_name = "there"  # Default fallback
    phone_number = participant.identity
    agent_slug = "default_roofing_agent" # Default agent slug

    if ctx.room.metadata:
        try:
            metadata = json.loads(ctx.room.metadata)
            business_name = metadata.get("business_name", "there")
            phone_number = metadata.get("phone_number", participant.identity)
            # Extract agent slug from metadata if present
            if "agent_id" in metadata:
                agent_slug = metadata["agent_id"]
            elif "slug" in metadata:
                agent_slug = metadata["slug"]
                
            logger.info(f"Business name: {business_name}, Agent Slug: {agent_slug}")
        except json.JSONDecodeError:
            logger.warning("Could not parse room metadata")
            
    # ── Load all configuration from the database (single source of truth) ──
    # Uses the same shared helpers as outbound_agent.py so that every call
    # — inbound or outbound — resolves the identical config for a given slug.
    logger.info(f"Loading configuration for agent: {agent_slug}")
    agent_config, schema_fields, dispatcher, agent_slug = await load_agent_config(db, agent_slug)

    # Fire call.started event
    await dispatcher.dispatch("call.started", {
        "phone_number": phone_number,
        "business_name": business_name,
        "room_name": ctx.room.name,
        "agent_slug": agent_slug
    })

    # Fetch and prepare agent instructions from database (with schema injection)
    agent_instructions = await prepare_instructions(db, agent_slug, schema_fields, agent_config=agent_config)
    logger.info(f"Agent instructions ready (first 120 chars): {agent_instructions[:120]}")

    # Create or update contact in database
    contact_id = await db.upsert_contact(
        phone_number=phone_number,
        business_name=business_name
    )
    logger.info(f"Contact ID: {contact_id}")
    
    prompt_id = await db.get_prompt_id(agent_slug)
    
    # Fetch AI configuration from database (agent-specific, then default fallback)
    logger.info("Fetching AI configuration from database...")
    ai_config = await load_ai_config(db, agent_slug, agent_config=agent_config)

    resolved = resolve_ai_configuration(ai_config=ai_config)
    logger.info(
        "Resolved telephony AI pipeline: llm=%s/%s, stt=%s/%s, tts=%s/%s voice=%s",
        resolved["llm_provider"], resolved["llm_model"],
        resolved["stt_provider"], f'{resolved["stt_model"]}/{resolved["stt_language"]}',
        resolved["tts_provider"], resolved["tts_model"], resolved["tts_voice"],
    )
    
    # Load MCP tools from n8n server
    logger.info("Loading MCP tools...")
    mcp_tools = await load_mcp_tools(mcp_url=agent_config.get("mcp_endpoint_url"))
    logger.info(f"Loaded {len(mcp_tools)} MCP tools")
    
    # Prepare all tools including call tracking tools
    all_tools = [
        get_current_time,
        update_call_data,
        add_note,
        end_call
    ] + mcp_tools
    
    # Initialize the conversational agent with tools
    agent = Agent(
        instructions=agent_instructions,
        tools=all_tools
    )
    
    # Build providers via shared module (handles fallback, Groq compat, etc.)
    llm = build_llm(ai_config=ai_config)
    stt = build_stt(ai_config=ai_config)
    tts = build_tts(ai_config=ai_config)

    # Configure the voice processing pipeline optimized for telephony.
    # - STT-based turn detection avoids the Silero VAD inference delay on
    #   constrained CPU budgets and lets Deepgram's endpointing handle
    #   silence/speech gating natively.
    session = AgentSession(
        turn_detection="stt",
        stt=stt,
        llm=llm,
        tts=tts,
        min_endpointing_delay=0.5,
        max_endpointing_delay=6.0,
        min_interruption_words=1,
        preemptive_generation=True,
    )

    # Handle LLM/TTS errors gracefully: speak a fallback message instead of
    # going silent when the model fails (e.g. function-calling APIError).
    @session.on("error")
    def _on_session_error(ev: ErrorEvent):
        error_obj = ev.error
        is_llm = isinstance(error_obj, LLMError) or getattr(error_obj, "type", None) == "llm_error"
        underlying = getattr(error_obj, "error", error_obj)
        logger.error("Session error (llm=%s): %s", is_llm, underlying)

        if is_llm:
            call_metadata["notes"].append(f"LLM error: {underlying}")
            try:
                session.say(LLM_ERROR_FALLBACK_MESSAGE)
            except Exception:
                logger.warning("Failed to speak LLM error fallback message")

    # Start the agent session with telephony-optimized noise cancellation
    # and Opus-optimized audio output (DTX + RED for jitter/packet-loss resilience)
    call_start_time = datetime.datetime.now()
    await session.start(
        agent=agent,
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVCTelephony(),
        ),
        room_output_options=RoomOutputOptions(
            audio_sample_rate=48000,
            audio_publish_options=rtc.TrackPublishOptions(
                dtx=True,
                red=True,
                source=rtc.TrackSource.SOURCE_MICROPHONE,
            ),
        ),
    )
    
    # Trigger outbound opener immediately
    opening_line = agent_config.get("opening_line") or "Start the call with your outbound opening line immediately. Speak confidently and naturally."
    if business_name and "{business_name}" in opening_line:
        opening_line = opening_line.format(business_name=business_name)
    await session.generate_reply(
        instructions=opening_line
    )
    
    # Wait for the session to end (when participant disconnects or call is ended)
    try:
        # Wait for room disconnect instead of session completion
        await ctx.room.wait_for_disconnect()
    except Exception as e:
        logger.error(f"Session error: {e}")
    finally:
        # Calculate call duration
        call_end_time = datetime.datetime.now()
        duration_seconds = int((call_end_time - call_start_time).total_seconds())

        # Capture transcript from session history (Unified)
        transcript_text = None
        transcript_json = []
        try:
            if session.history:
                transcript_lines = []
                for item in session.history.items:
                    role = getattr(item, 'role', None)
                    content = getattr(item, 'content', None)

                    if role and content:
                        transcript_json.append({"role": role, "content": content})

                    display_role = "Agent" if role == "assistant" else "User"
                    if content:
                        transcript_lines.append(f"{display_role}: {content}")

                transcript_text = "\n".join(transcript_lines)

                # Add structured transcript to call_metadata
                call_metadata["transcript_json"] = transcript_json

                logger.info(f"Captured transcript with {len(transcript_lines)} turns")
        except Exception as e:
            logger.error(f"Failed to capture transcript: {e}")

        # Fire call.ended event
        if 'dispatcher' in locals() and dispatcher:
            await dispatcher.dispatch("call.ended", {
                "duration_seconds": duration_seconds,
                "call_status": "completed",
                "disconnect_reason": "unknown",
                "transcript": transcript_text,
                "captured_data": call_metadata,
                "notes": call_metadata.get("notes", [])
            })
        
        # Log the call to database with captured metadata
        try:
            logger.info("Logging call to database...")
            
            # Combine notes into a single string
            notes_text = " | ".join(call_metadata["notes"]) if call_metadata["notes"] else None
            
            # Extract standard fields for legacy columns if they exist in captured data
            legacy_email = call_metadata.get("email")
            legacy_interest = call_metadata.get("interest_level")
            legacy_objection = call_metadata.get("objection")
            
            # Log call with transcript and JSON data
            await db.log_call(
                contact_id=contact_id,
                room_id=ctx.room.name,
                prompt_id=prompt_id,
                duration_seconds=duration_seconds,
                interest_level=legacy_interest,
                objection=legacy_objection,
                notes=notes_text,
                email_captured=bool(legacy_email),
                call_status="completed",
                transcript=transcript_text,
                captured_data=call_metadata
            )
            
            logger.info(f"Call logged successfully")
            if transcript_text:
                logger.info(f"Transcript saved")
            
            # Track objection in database if one was recorded
            if legacy_objection:
                await db.track_objection(legacy_objection)
                logger.info(f"Objection tracked: {legacy_objection}")
            
        except Exception as e:
            logger.error(f"Failed to log call to database: {e}")
        
        # Metadata is local now, no need to reset global state

if __name__ == "__main__":
    # Configure logging for better debugging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the agent with the name that matches your dispatch rule
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        agent_name="voice-assistant"  # Matches LiveKit inbound dispatch rule
    ))
