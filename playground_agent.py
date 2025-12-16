import logging
import asyncio
import os
import datetime
from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
)
from livekit.plugins import deepgram, openai, silero, inworld
from livekit import api, rtc

from egress_manager import EgressManager
from neon_db import get_db

# Reuse outbound logic
from outbound.metadata import extract_metadata, get_required_fields
from outbound.config import load_agent_config, prepare_instructions, load_ai_config
from outbound.tools import create_tools
from outbound.lifecycle import finalize_call as finalize_call_logic

load_dotenv()
logger = logging.getLogger("playground-agent")

class PlaygroundAgent:
    def __init__(self, ctx: JobContext):
        self.ctx = ctx
        self.db = None
        self.agent_slug = "default_roofing_agent"
        self.phone_number = "PLAYGROUND_USER"
        self.business_name = "Playground User"
        self.call_metadata = {"notes": []}
        self.contact_id = None
        self.prompt_id = None
        self.call_start_time = None
        self.is_finalized = False
        self.session = None

    async def start(self):
        logger.info(f"Connected to room {self.ctx.room.name}")
        await self.ctx.connect()

        # Extract metadata or use defaults
        initial_metadata = extract_metadata(self.ctx)
        self.phone_number, self.business_name, self.agent_slug = get_required_fields(initial_metadata)

        # Override phone number for playground to avoid confusion/lookup issues if not provided or default
        if self.phone_number == "LOCAL_TEST_NUMBER":
             self.phone_number = "PLAYGROUND_USER"

        logger.info(f"Playground Agent starting for agent: {self.agent_slug}")

        # Setup DB and Config
        self.db = await get_db()
        agent_config, schema_fields, dispatcher, self.agent_slug = await load_agent_config(self.db, self.agent_slug)

        # Skip call.initiated webhook dispatch for playground if desired, or keep it to test full flow.
        # Keeping it as it mimics outbound behavior.

        # Fetch instructions
        agent_instructions = await prepare_instructions(self.db, self.agent_slug, schema_fields)

        # Upsert contact (Playground User)
        self.contact_id = await self.db.upsert_contact(self.phone_number, self.business_name)
        self.prompt_id = await self.db.get_prompt_id(self.agent_slug)

        # Log call initiation
        try:
            call_id = await self.db.log_call(
                contact_id=self.contact_id,
                room_id=self.ctx.room.name,
                prompt_id=self.prompt_id,
                call_status="initiated",
                captured_data=self.call_metadata
            )
            self.call_metadata["call_id"] = call_id
            logger.info(f"Call initiated in DB with ID: {call_id}")
        except Exception as e:
            logger.error(f"Failed to log initial call record: {e}")

        # Egress Manager (needed for finalize_call even if we don't record)
        egress_manager = EgressManager(self.ctx.api)

        # Tools
        async def hangup_callback():
             await self.finalize_call(dispatcher, egress_manager)
             await self.ctx.room.disconnect()

        all_tools = create_tools(
            call_metadata=self.call_metadata,
            db=self.db,
            dispatcher=dispatcher,
            contact_id=self.contact_id,
            phone_number=self.phone_number,
            hangup_callback=hangup_callback
        )

        # AI Config
        ai_config = await load_ai_config(self.db, self.agent_slug)

        # Construct Agent
        agent = Agent(instructions=agent_instructions, tools=all_tools)

        llm = openai.LLM(model=ai_config.get("llm_model", "gpt-4o-mini"))
        stt = deepgram.STT(model=ai_config.get("stt_model", "nova-3"), language=ai_config.get("stt_language", "en-US"))

        if ai_config["tts_provider"] == "openai":
            tts = openai.TTS(model=ai_config.get("tts_model", "tts-1"), voice=ai_config.get("tts_voice", "alloy"))
        elif ai_config["tts_provider"] == "inworld":
            tts = inworld.TTS(voice=ai_config.get("tts_voice", "Sarah"))
        else:
             tts = openai.TTS(model="tts-1", voice="alloy")

        self.session = AgentSession(vad=silero.VAD.load(), stt=stt, llm=llm, tts=tts)

        # Start Session
        # In playground, we often wait for user to say something, or we can say greeting.
        # Outbound calls say greeting.
        self.session.start(agent=agent, room=self.ctx.room)

        # Wait for participant to join (if not already there)
        participant = await self.ctx.wait_for_participant()
        logger.info(f"Participant joined: {participant.identity}")

        # Say opening line
        opening_line = agent_config.get("opening_line")
        if opening_line:
             # Basic formatting if needed, though usually template vars are for outbound specific data
             if "{business_name}" in opening_line:
                 opening_line = opening_line.format(business_name=self.business_name)
             await self.session.say(opening_line, allow_interruptions=True)

        self.call_start_time = datetime.datetime.now()

        # Handle disconnects
        @self.ctx.room.on("participant_disconnected")
        def on_participant_disconnected(p: rtc.RemoteParticipant):
             if p.identity == participant.identity:
                 asyncio.create_task(self.finalize_call(dispatcher, egress_manager))

        @self.ctx.room.on("disconnected")
        def on_room_disconnected():
             asyncio.create_task(self.finalize_call(dispatcher, egress_manager))

        # Keep alive
        self.shutdown_event = asyncio.Event()
        await self.shutdown_event.wait()


    async def finalize_call(self, dispatcher, egress_manager):
        if self.is_finalized:
            return
        self.is_finalized = True

        await finalize_call_logic(
            ctx=self.ctx,
            db=self.db,
            dispatcher=dispatcher,
            egress_manager=egress_manager,
            session=self.session,
            call_start_time=self.call_start_time or datetime.datetime.now(),
            call_metadata=self.call_metadata,
            contact_id=self.contact_id,
            prompt_id=self.prompt_id,
            is_finalized=False
        )
        self.shutdown_event.set()

async def entrypoint(ctx: JobContext):
    agent = PlaygroundAgent(ctx)
    await agent.start()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, agent_name="playground_agent"))
