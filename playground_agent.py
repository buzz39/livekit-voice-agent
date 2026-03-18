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
        logger.info(f"Connecting to room {self.ctx.room.name}...")
        await self.ctx.connect()
        logger.info(f"Connected to room {self.ctx.room.name}")

        # Extract metadata or use defaults
        initial_metadata = extract_metadata(self.ctx)
        self.phone_number, self.business_name, self.agent_slug = get_required_fields(initial_metadata)
        
        # Override phone number for playground
        if self.phone_number == "LOCAL_TEST_NUMBER":
             self.phone_number = "PLAYGROUND_USER"

        logger.info(f"Playground Agent starting for agent: {self.agent_slug}")

        try:
            # Setup DB and Config
            logger.info("Connecting to database...")
            self.db = await get_db()
            
            logger.info(f"Loading config for {self.agent_slug}...")
            agent_config, schema_fields, dispatcher, self.agent_slug = await load_agent_config(self.db, self.agent_slug)

            # Fetch instructions
            logger.info("Preparing instructions...")
            agent_instructions = await prepare_instructions(self.db, self.agent_slug, schema_fields)

            # Upsert contact
            logger.info("Upserting contact...")
            self.contact_id = await self.db.upsert_contact(self.phone_number, self.business_name)
            self.prompt_id = await self.db.get_prompt_id(self.agent_slug)

            # Log call initiation
            logger.info("Logging call initiation...")
            call_id = await self.db.log_call(
                contact_id=self.contact_id,
                room_id=self.ctx.room.name,
                prompt_id=self.prompt_id,
                call_status="initiated",
                captured_data=self.call_metadata
            )
            self.call_metadata["call_id"] = call_id
            logger.info(f"Call initiated in DB with ID: {call_id}")

            # Egress Manager
            egress_manager = EgressManager(self.ctx.api)
            
            # Tools
            async def hangup_callback():
                logger.info("Hangup callback triggered")
                await self.finalize_call(dispatcher, egress_manager)
                # In playground, deleting the room kicks everyone out. 
                # Disconnect is softer if we want to stay in room, but for "end call" simulation, delete/disconnect is fine.
                await self.ctx.room.disconnect() 

            all_tools = create_tools(
                call_metadata=self.call_metadata,
                db=self.db,
                dispatcher=dispatcher,
                contact_id=self.contact_id,
                phone_number=self.phone_number,
                hangup_callback=hangup_callback,
                ctx=self.ctx,
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

            self.session = AgentSession(
                vad=silero.VAD.load(
                    min_speech_duration=0.2,
                    min_silence_duration=0.2,
                    activation_threshold=0.6,
                ),
                stt=stt,
                llm=llm,
                tts=tts
            )

            # Wait for participant to join (CRITICAL: Wait BEFORE speaking)
            logger.info("Waiting for participant...")
            participant = await self.ctx.wait_for_participant()
            logger.info(f"Participant joined: {participant.identity}")

            # Start Session (CRITICAL: AWAIT THIS)
            logger.info("Starting Agent Session...")
            session_task = asyncio.create_task(self.session.start(agent=agent, room=self.ctx.room))
            
            # Give session a moment to initialize
            await asyncio.sleep(0.5)

            # Say opening line
            opening_line = agent_config.get("opening_line")
            if opening_line:
                if "{business_name}" in opening_line:
                    opening_line = opening_line.format(business_name=self.business_name)
                
                logger.info(f"Saying opening line: {opening_line}")
                await self.session.say(opening_line, allow_interruptions=True)

            self.call_start_time = datetime.datetime.now()

            # Handle disconnects
            @self.ctx.room.on("participant_disconnected")
            def on_participant_disconnected(p: rtc.RemoteParticipant):
                if p.identity == participant.identity:
                    logger.info("Participant disconnected")
                    asyncio.create_task(self.finalize_call(dispatcher, egress_manager))

            @self.ctx.room.on("disconnected")
            def on_room_disconnected():
                logger.info("Room disconnected")
                asyncio.create_task(self.finalize_call(dispatcher, egress_manager))

            # Keep alive
            logger.info("Agent loop running...")
            self.shutdown_event = asyncio.Event()
            
            # Wait for the session task or shutdown
            done, pending = await asyncio.wait(
                [session_task, asyncio.create_task(self.shutdown_event.wait())],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # If session task finished (e.g. error or close), verify
            for task in done:
                if task == session_task:
                    try:
                        task.result() # check for exceptions
                    except Exception as e:
                        logger.error(f"Session task failed: {e}")

        except Exception as e:
            logger.error(f"Playground Agent Error: {e}", exc_info=True)
            # Try to disconnect if we can
            try:
                await self.ctx.disconnect()
            except:
                pass


    async def finalize_call(self, dispatcher, egress_manager):
        if self.is_finalized:
            return
        self.is_finalized = True
        logger.info("Finalizing call...")
        
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
        if hasattr(self, 'shutdown_event'):
            self.shutdown_event.set()

async def entrypoint(ctx: JobContext):
    agent = PlaygroundAgent(ctx)
    await agent.start()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, agent_name="playground_agent"))
