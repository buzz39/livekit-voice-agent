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
)
from livekit.agents.llm import function_tool
from livekit.plugins import deepgram, openai, cartesia, silero
from mcp_integration import load_mcp_tools
from neon_db import get_db


load_dotenv()
logger = logging.getLogger("telephony-agent")

# Agent instructions will be loaded from Neon database
AGENT_INSTRUCTIONS = None  # Will be fetched from database

# Function tools to enhance your agent's capabilities
@function_tool
async def get_current_time() -> str:
    """Get the current time."""
    return f"The current time is {datetime.datetime.now().strftime('%I:%M %p')}"

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
    
    # Load MCP tools from n8n server
    logger.info("Loading MCP tools...")
    mcp_tools = await load_mcp_tools()
    logger.info(f"Loaded {len(mcp_tools)} MCP tools")
    
    # Prepare all tools
    all_tools = [get_current_time] + mcp_tools
    
    # Initialize the conversational agent with tools
    agent = Agent(
        instructions=agent_instructions,
        tools=all_tools
    )
    
    # Configure the voice processing pipeline optimized for telephony
    session = AgentSession(
        # Voice Activity Detection
        vad=silero.VAD.load(),
        
        # Speech-to-Text - Deepgram Nova-3
        stt=deepgram.STT(
            model="nova-3",
            language="en-US",
            interim_results=True,
            punctuate=True,
            smart_format=True,
            filler_words=True,
            endpointing_ms=25,
            sample_rate=16000
        ),
        
        # Large Language Model - GPT-4o-mini
        llm=openai.LLM(
            model="gpt-4o-mini",
            temperature=0.7
        ),
        
        # Text-to-Speech - Cartesia Sonic-2
        tts=cartesia.TTS(
            model="sonic-2",
            voice="a0e99841-438c-4a64-b679-ae501e7d6091",  # Professional female voice
            language="en",
            speed=1.0,
            sample_rate=24000
        )
    )
    
    # Start the agent session
    call_start_time = datetime.datetime.now()
    await session.start(agent=agent, room=ctx.room)
    
    # Trigger outbound opener immediately
    await session.generate_reply(
        instructions="Start the call with your outbound opening line immediately. Speak confidently and naturally."
    )
    
    # Note: Call logging will happen when the session ends
    # For now, we log the call start. You can add session end hooks to log completion data

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
