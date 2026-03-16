"""
LiveKit AI Telephony Agent with n8n MCP Integration

A production-ready voice AI agent for handling phone calls with:
- Natural language conversations powered by GPT-4o-mini
- High-quality speech recognition (Deepgram Nova-3)
- Natural text-to-speech (Cartesia Sonic-2)
- Integration with n8n workflows via Model Context Protocol (MCP)
- Extensible function tools for custom capabilities

Author: Your Name/Company
License: MIT
"""

import datetime
import logging
import json
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
from livekit.plugins import deepgram, openai, cartesia, silero
from livekit import api
from mcp_integration import load_mcp_tools
import os
import httpx
from neon_db import get_db

load_dotenv()
logger = logging.getLogger("telephony-agent")

SARVAM_API_URL = os.environ.get("SARVAM_API_URL", "https://api.sarvam.ai/v1/tts")
SARVAM_VOICE_ID = os.environ.get("SARVAM_VOICE_ID", "saarika:v2.5") # Example: saarika:v2.5 (Hindi female)

async def sarvam_tts(text: str, voice_id: str = SARVAM_VOICE_ID) -> bytes:
    sarvam_api_key = os.environ.get("SARVAM_API_KEY")
    if not sarvam_api_key:
        logger.error("SARVAM_API_KEY not set")
        raise ValueError("Sarvam AI API key not found.")
    
    headers = {
        "Authorization": f"Bearer {sarvam_api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "voice": voice_id,
        "response_format": "pcm", # LiveKit expects raw audio
        "sample_rate": 16000 # LiveKit expects 16kHz
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(SARVAM_API_URL, json=payload, headers=headers, timeout=10.0)
            response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
            return response.content
        except httpx.RequestError as exc:
            logger.error(f"An error occurred while requesting Sarvam TTS: {exc}")
            raise
        except httpx.HTTPStatusError as exc:
            logger.error(f"Sarvam TTS HTTP error for {exc.request.url}: {exc.response.status_code} - {exc.response.text}")
            raise


# Agent instructions will be loaded from Neon database
AGENT_INSTRUCTIONS = None  # Will be fetched from database


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


from webhook_dispatcher import WebhookDispatcher

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
        """End the call. Use this SILENTLY after saying goodbye - do not announce that you're ending the call."""
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
            
    # Fetch agent configuration (greeting, MCP URL) - EARLY CHECK
    logger.info(f"Fetching configuration for agent: {agent_slug}")
    agent_config = await db.get_agent_config(agent_slug)
    
    # If explicit agent slug failed (not active or not found), try default
    if not agent_config and agent_slug != "default_roofing_agent":
        logger.warning(f"Agent {agent_slug} not found or inactive, falling back to default")
        agent_slug = "default_roofing_agent"
        agent_config = await db.get_agent_config(agent_slug)

    # If still no config (even default is broken/inactive), use hardcoded fallback or exit
    if not agent_config:
        logger.error(f"CRITICAL: Active configuration for {agent_slug} not found. Using bare defaults.")
        agent_config = {}
    
    # Fetch schema fields and Webhooks using the RESOLVED slug
    logger.info(f"Fetching data schema and webhooks for {agent_slug}...")
    schema_fields = await db.get_data_schema(agent_slug)
    webhooks = await db.get_webhooks(agent_slug)
    
    # Initialize Webhook Dispatcher
    dispatcher = WebhookDispatcher(webhooks, agent_slug)
    
    # Fire call.started event
    await dispatcher.dispatch("call.started", {
        "phone_number": phone_number,
        "business_name": business_name,
        "room_name": ctx.room.name,
        "agent_slug": agent_slug
    })

    # Fetch agent instructions from database
    logger.info(f"Fetching agent instructions for {agent_slug}...")
    # Update get_active_prompt to take the slug (it was defaulting implicitly before)
    # Warning: neon_db.get_active_prompt signature might need check if it takes slug param correctly
    # Checking neon_db.py content from previous views... yes, it takes `name`.
    agent_instructions = await db.get_active_prompt(agent_slug) 
    if not agent_instructions:
        logger.error("No active prompt found in database, using fallback")
        agent_instructions = "You are a professional caller."
    
    # Inject schema into instructions
    if schema_fields:
        schema_prompt = "\n\nYou are authorized to collect the following information:\n"
        for field in schema_fields:
            field_name = field['field_name']
            desc = field.get('description', 'No description found')
            rules = field.get('validation_rules')
            
            schema_prompt += f"- {field_name}: {desc}"
            if rules:
                schema_prompt += f" (Allowed values: {rules})"
            schema_prompt += "\n"
            
        schema_prompt += "\nUse the `update_call_data` tool to save these values."
        
        # Append to existing instructions
        agent_instructions += schema_prompt
        logger.info(f"Injected {len(schema_fields)} fields into prompt")

    # Create or update contact in database
    contact_id = await db.upsert_contact(
        phone_number=phone_number,
        business_name=business_name
    )
    logger.info(f"Contact ID: {contact_id}")
    
    # Get prompt ID for logging implementation
    # Note: get_prompt_id likely needs the slug too if it's agent specific, 
    # but based on previous code it seemed to take a name.
    prompt_id = await db.get_prompt_id(agent_slug)
    
    # Fetch AI configuration from database
    # This remains shared for now unless we want per-agent AI configs (e.g. different voices)
    # For now, keeping it global or we could fetch it FROM agent_config later if we linked them.
    logger.info("Fetching AI configuration from Neon database...")
    ai_config = await db.get_ai_config("default_telephony_config")
    
    if not ai_config:
        logger.warning("No AI config found in database, using defaults")
        ai_config = {
            "llm_provider": "openai",
            "llm_model": "gpt-4o-mini",
            "llm_temperature": 0.7,
            "stt_provider": "deepgram",
            "stt_model": "nova-3",
            "stt_language": "en-US",
            "tts_provider": "cartesia",
            "tts_model": "sonic-2",
            "tts_voice": "a0e99841-438c-4a64-b679-ae501e7d6091",
            "tts_language": "en",
            "tts_speed": 1.0
        }
    
    logger.info(f"Using LLM: {ai_config['llm_provider']}/{ai_config['llm_model']}")
    logger.info(f"Using STT: {ai_config['stt_provider']}/{ai_config['stt_model']}")
    logger.info(f"Using TTS: {ai_config['tts_provider']}/{ai_config['tts_model']}")
    
    # Load MCP tools from n8n server
    logger.info("Loading MCP tools...")
    # Use dynamic URL if present, otherwise fallback to env
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
    
    # Configure LLM based on database config
    if ai_config["llm_provider"] == "openai":
        llm = openai.LLM(
            model=ai_config["llm_model"],
            temperature=float(ai_config["llm_temperature"])
        )
    else:
        logger.warning(f"Unsupported LLM provider: {ai_config['llm_provider']}, using OpenAI")
        llm = openai.LLM(model="gpt-4o-mini", temperature=0.7)
    
    # Configure STT based on database config
    if ai_config["stt_provider"] == "deepgram":
        stt = deepgram.STT(
            model=ai_config["stt_model"],
            language=ai_config["stt_language"],
            interim_results=True,
            punctuate=True,
            smart_format=True,
            filler_words=True,
            endpointing_ms=25,
            sample_rate=16000
        )
    else:
        logger.warning(f"Unsupported STT provider: {ai_config['stt_provider']}, using Deepgram")
        stt = deepgram.STT(model="nova-3", language="en-US")
    
    # Configure TTS based on database config, with environment variable override
    tts_provider_env = os.environ.get("TTS_PROVIDER", "").lower()
    
    # Prioritize environment variable if set and valid
    if tts_provider_env == "sarvam":
        logger.info(f"Using Sarvam TTS based on TTS_PROVIDER environment variable")
        # For Sarvam, we'll use a custom function later in session.generate_reply
        # For now, we'll set a placeholder or use openai for structure
        tts = openai.TTS(model="tts-1", voice="alloy") # Placeholder, actual call will be custom
        
    elif tts_provider_env == "cartesia":
        logger.info(f"Using Cartesia TTS based on TTS_PROVIDER environment variable")
        tts = cartesia.TTS(
            model=ai_config["tts_model"],
            voice=ai_config["tts_voice"],
            language=ai_config["tts_language"],
            speed=float(ai_config["tts_speed"]),
            sample_rate=16000
        )
    elif tts_provider_env == "openai":
        logger.info(f"Using OpenAI TTS based on TTS_PROVIDER environment variable")
        tts = openai.TTS(
            model=ai_config.get("tts_model", "tts-1"),
            voice=ai_config.get("tts_voice", "alloy"),
        )
    # Fallback to database config if no valid env var is set
    elif ai_config["tts_provider"] == "cartesia":
        logger.info(f"Using Cartesia TTS based on database config")
        tts = cartesia.TTS(
            model=ai_config["tts_model"],
            voice=ai_config["tts_voice"],
            language=ai_config["tts_language"],
            speed=float(ai_config["tts_speed"]),
            sample_rate=16000
        )
    elif ai_config["tts_provider"] == "openai":
        logger.info(f"Using OpenAI TTS based on database config")
        tts = openai.TTS(
            model=ai_config.get("tts_model", "tts-1"),
            voice=ai_config.get("tts_voice", "alloy"),
        )
    elif ai_config["tts_provider"] == "sarvam":
        logger.info(f"Using Sarvam TTS based on database config")
        # Placeholder, actual call will be custom
        tts = openai.TTS(model="tts-1", voice="alloy")
    else:
        logger.warning(f"Unsupported TTS provider: {ai_config['tts_provider']} or {tts_provider_env}, using OpenAI TTS as fallback")
        tts = openai.TTS(model="tts-1", voice="alloy")
    
    # Configure the voice processing pipeline optimized for telephony
    # Use VAD settings from DB if available
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=stt,
        llm=llm,
        tts=tts
    )
    
    # Override TTS generation for Sarvam if selected
    if tts_provider_env == "sarvam" or ai_config["tts_provider"] == "sarvam":
        async def sarvam_generate_speech(text: str) -> bytes:
            return await sarvam_tts(text)
        session._generate_speech = sarvam_generate_speech
        logger.info("Overridden session._generate_speech for Sarvam TTS")

    # Track if call was ended by agent
    call_ended_by_agent = False
    
    # Listen for participant disconnect
    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(participant):
        nonlocal call_ended_by_agent
        if participant.identity == phone_number:
            logger.info(f"Participant {participant.identity} disconnected")
            # If user hung up, we should end the session
            if not call_ended_by_agent:
                logger.info("User hung up, ending session")
    
    # Start the agent session
    call_start_time = datetime.datetime.now()
    await session.start(agent=agent, room=ctx.room)
    
    # Trigger outbound opener immediately
    opening_line = agent_config.get("opening_line") or "Start the call with your outbound opening line immediately. Speak confidently and naturally."
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
        agent_name="inbound_agent"  # Updated for separate dispatch rule
    ))
