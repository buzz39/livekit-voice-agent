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
from neon_db import get_db


load_dotenv()
logger = logging.getLogger("telephony-agent")

# Agent instructions will be loaded from Neon database
AGENT_INSTRUCTIONS = None  # Will be fetched from database

# Global variables to track call metadata
call_metadata = {
    "email_captured": False,
    "interest_level": None,
    "objection": None,
    "notes": []
}

# Function tools to enhance your agent's capabilities
@function_tool
async def get_current_time() -> str:
    """Get the current time."""
    return f"The current time is {datetime.datetime.now().strftime('%I:%M %p')}"

@function_tool
async def capture_email(email: str) -> str:
    """Capture the customer's email address. This is an internal function - do not mention calling it to the user."""
    global call_metadata
    call_metadata["email_captured"] = True
    call_metadata["notes"].append(f"Email captured: {email}")
    logger.info(f"Email captured: {email}")
    return ""  # Return empty string so nothing is spoken

@function_tool
async def set_interest_level(level: str) -> str:
    """Set the customer's interest level. Options: Hot, Warm, Cold, No Interest. This is an internal function - do not mention calling it to the user."""
    global call_metadata
    valid_levels = ["Hot", "Warm", "Cold", "No Interest"]
    if level in valid_levels:
        call_metadata["interest_level"] = level
        logger.info(f"Interest level set to: {level}")
    return ""  # Return empty string so nothing is spoken

@function_tool
async def record_objection(objection: str) -> str:
    """Record a customer objection or concern. This is an internal function - do not mention calling it to the user."""
    global call_metadata
    call_metadata["objection"] = objection
    call_metadata["notes"].append(f"Objection: {objection}")
    logger.info(f"Objection recorded: {objection}")
    return ""  # Return empty string so nothing is spoken

@function_tool
async def add_note(note: str) -> str:
    """Add a note about the call. This is an internal function - do not mention calling it to the user."""
    global call_metadata
    call_metadata["notes"].append(note)
    logger.info(f"Note added: {note}")
    return ""  # Return empty string so nothing is spoken

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

@function_tool
async def end_call() -> str:
    """End the call. Use this SILENTLY after saying goodbye - do not announce that you're ending the call."""
    logger.info("Agent ending call...")
    await hangup_call()
    return ""  # Return empty string so nothing is spoken

async def entrypoint(ctx: JobContext):
    """Main entry point for the telephony voice agent."""
    
    await ctx.connect()
    
    # Wait for participant (caller) to join
    participant = await ctx.wait_for_participant()
    logger.info(f"Phone call connected from participant: {participant.identity}")
    
    # Connect to Neon database
    db = await get_db()
    
    # Fetch agent instructions from database
    logger.info("Fetching agent instructions from Neon database...")
    agent_instructions = await db.get_active_prompt("default_roofing_agent")
    if not agent_instructions:
        logger.error("No active prompt found in database, using fallback")
        agent_instructions = "You are Sam, a professional caller for Sambhav Tech AI."
    
    # Extract metadata from room
    import json
    business_name = "there"  # Default fallback
    phone_number = participant.identity
    contact_name = None
    email = None

    if ctx.room.metadata:
        try:
            metadata = json.loads(ctx.room.metadata)
            business_name = metadata.get("business_name", "there")
            phone_number = metadata.get("phone_number", participant.identity)
            logger.info(f"Business name from metadata: {business_name}")
        except json.JSONDecodeError:
            logger.warning("Could not parse room metadata")
    
    # Create or update contact in database
    contact_id = await db.upsert_contact(
        phone_number=phone_number,
        business_name=business_name
    )
    logger.info(f"Contact ID: {contact_id}")
    
    # Get prompt ID for logging
    prompt_id = await db.get_prompt_id("default_roofing_agent")
    
    # Fetch AI configuration from database
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
    mcp_tools = await load_mcp_tools()
    logger.info(f"Loaded {len(mcp_tools)} MCP tools")
    
    # Prepare all tools including call tracking tools
    all_tools = [
        get_current_time,
        capture_email,
        set_interest_level,
        record_objection,
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
    
    # Configure TTS based on database config
    if ai_config["tts_provider"] == "cartesia":
        tts = cartesia.TTS(
            model=ai_config["tts_model"],
            voice=ai_config["tts_voice"],
            language=ai_config["tts_language"],
            speed=float(ai_config["tts_speed"]),
            sample_rate=24000
        )
    else:
        logger.warning(f"Unsupported TTS provider: {ai_config['tts_provider']}, using Cartesia")
        tts = cartesia.TTS(model="sonic-2", voice="a0e99841-438c-4a64-b679-ae501e7d6091")
    
    # Configure the voice processing pipeline optimized for telephony
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=stt,
        llm=llm,
        tts=tts
    )
    
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
    await session.generate_reply(
        instructions="Start the call with your outbound opening line immediately. Speak confidently and naturally."
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
                logger.info(f"Captured transcript with {len(transcript_lines)} turns")
        except Exception as e:
            logger.error(f"Failed to capture transcript: {e}")
        
        # Log the call to database with captured metadata
        try:
            logger.info("Logging call to database...")
            
            # Combine notes into a single string
            notes_text = " | ".join(call_metadata["notes"]) if call_metadata["notes"] else None
            
            # Log call with transcript
            async with db.pool.acquire() as conn:
                call_id = await conn.fetchval("""
                    INSERT INTO calls (
                        contact_id, room_id, prompt_id, duration_seconds,
                        interest_level, objection, notes, email_captured, 
                        call_status, transcript
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    RETURNING id
                """, contact_id, ctx.room.name, prompt_id, duration_seconds,
                    call_metadata["interest_level"], call_metadata["objection"], 
                    notes_text, call_metadata["email_captured"], "completed", transcript_text)
            
            logger.info(f"Call logged successfully with ID: {call_id}")
            logger.info(f"Call summary - Duration: {duration_seconds}s, Interest: {call_metadata['interest_level']}, Email: {call_metadata['email_captured']}")
            if transcript_text:
                logger.info(f"Transcript saved ({len(transcript_text)} characters)")
            
            # Track objection in database if one was recorded
            if call_metadata["objection"]:
                await db.track_objection(call_metadata["objection"])
                logger.info(f"Objection tracked: {call_metadata['objection']}")
            
        except Exception as e:
            logger.error(f"Failed to log call to database: {e}")
        
        # Reset call metadata for next call
        call_metadata.update({
            "email_captured": False,
            "interest_level": None,
            "objection": None,
            "notes": []
        })

if __name__ == "__main__":
    # Configure logging for better debugging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the agent with the name that matches your dispatch rule
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        agent_name="telephony_agent"  # This must match your dispatch rule
    ))
