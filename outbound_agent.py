import datetime
import logging
import asyncio
import os
from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    get_job_context,
)
from livekit.agents.voice.room_io import RoomInputOptions
import groq # Import Groq library
from livekit import api
from livekit import rtc

from egress_manager import EgressManager
from neon_db import get_db

# Import new modules
from outbound.metadata import extract_metadata, get_required_fields
from outbound.config import load_agent_config, prepare_instructions, load_ai_config
from outbound.sip import dial_participant
from outbound.tools import create_tools
from outbound.recording import start_recording
from outbound.lifecycle import finalize_call as finalize_call_logic
from outbound.providers import (
    build_llm,
    build_stt,
    build_tts,
    get_missing_provider_env_vars,
    resolve_ai_configuration,
)

# Whispey Observability Integration
try:
    from whispey import LivekitObserve
    WHISPEY_ENABLED = True
except ImportError:
    WHISPEY_ENABLED = False

load_dotenv()
logger = logging.getLogger("outbound-agent")

if not WHISPEY_ENABLED:
    logger.warning("Whispey not installed. Install with: pip install whispey")

async def entrypoint(ctx: JobContext):
    try:
        await _run_entrypoint(ctx)
    except Exception:
        room_name = getattr(getattr(ctx, "room", None), "name", "unknown_room")
        logger.exception("Agent crashed while handling room %s", room_name)
        raise


async def _run_entrypoint(ctx: JobContext):
    """Main entry point for the outbound voice agent."""

    # 1. Initialize per-call state
    call_metadata = {"notes": []}

    # Connect to room
    await ctx.connect()
    logger.info(f"Connected to room {ctx.room.name}")

    # 2. Extract outbound metadata (robust)
    initial_metadata = extract_metadata(ctx)
    phone_number, business_name, agent_slug = get_required_fields(initial_metadata)
    call_metadata["business_name"] = business_name

    logger.info(f"Parsed metadata → phone: {phone_number}, business: {business_name}, slug: {agent_slug}")

    if not phone_number:
        logger.error("No phone number found in metadata. Cannot place outbound call.")
        return

    logger.info(f"Preparing outbound call to {phone_number} using agent {agent_slug}")

    # 3. Setup Database & Config
    db = await get_db()

    # Fetch agent configuration, schema, webhooks
    agent_config, schema_fields, dispatcher, agent_slug = await load_agent_config(db, agent_slug)

    # Fire call.initiated event
    try:
        await dispatcher.dispatch(
            "call.initiated",
            {"phone_number": phone_number, "business_name": business_name, "agent_slug": agent_slug},
        )
    except Exception as e:
        logger.debug(f"call.initiated webhook error: {e}")

    # Fetch instructions (with schema injection)
    agent_instructions = await prepare_instructions(db, agent_slug, schema_fields)

    # Create contact
    contact_id = await db.upsert_contact(phone_number, business_name)
    prompt_id = await db.get_prompt_id(agent_slug)

    # 4. Log Call Initiation
    # Log the call immediately so it shows up in DB even if it crashes later
    try:
        call_id = await db.log_call(
            contact_id=contact_id,
            room_id=ctx.room.name,
            prompt_id=prompt_id,
            call_status="initiated",
            captured_data=call_metadata
        )
        call_metadata["call_id"] = call_id
        logger.info(f"Call initiated in DB with ID: {call_id}")
    except Exception as e:
        logger.error(f"Failed to log initial call record: {e}")

    # Initialize EgressManager early
    egress_manager = EgressManager(ctx.api)

    # AI Config
    ai_config = await load_ai_config(db, agent_slug)
    resolved_ai_config = resolve_ai_configuration(ai_config=ai_config, metadata_overrides=initial_metadata)
    logger.info(
        "Resolved outbound AI pipeline: llm=%s/%s temp=%s, stt=%s/%s, tts=%s/%s voice=%s",
        resolved_ai_config["llm_provider"],
        resolved_ai_config["llm_model"],
        resolved_ai_config["llm_temperature"],
        resolved_ai_config["stt_provider"],
        f'{resolved_ai_config["stt_model"]}/{resolved_ai_config["stt_language"]}',
        resolved_ai_config["tts_provider"],
        resolved_ai_config["tts_model"],
        resolved_ai_config["tts_voice"],
    )
    missing_provider_env_vars = get_missing_provider_env_vars(ai_config=ai_config, metadata_overrides=initial_metadata)
    if missing_provider_env_vars:
        error_message = (
            "Cannot start outbound audio pipeline because required provider credentials are missing: "
            + ", ".join(missing_provider_env_vars)
        )
        call_metadata["notes"].append(error_message)
        logger.error(error_message)
        try:
            await dispatcher.dispatch(
                "call.failed",
                {
                    "phone_number": phone_number,
                    "business_name": business_name,
                    "agent_slug": agent_slug,
                    "stage": "provider_validation",
                    "error": error_message,
                },
            )
        except Exception as e:
            logger.debug(f"call.failed webhook error during provider validation: {e}")
        return

    # Initialize Whispey observability if enabled
    whispey = None
    if WHISPEY_ENABLED:
        whispey_api_key = os.getenv("WHISPEY_API_KEY")
        whispey_agent_id = os.getenv("WHISPEY_OUTBOUND_AGENT_ID", os.getenv("WHISPEY_AGENT_ID", "outbound-agent"))
        whispey_base_url = os.getenv("WHISPEY_BASE_URL")  # Optional self-hosted URL

        if whispey_api_key:
            try:
                # Add base_url if present
                if whispey_base_url:
                    whispey = LivekitObserve(
                        agent_id=whispey_agent_id,
                        apikey=whispey_api_key,
                        base_url=whispey_base_url)
                else:
                    whispey = LivekitObserve(agent_id=whispey_agent_id,
                        apikey=whispey_api_key)

                logger.info(f"Whispey observability enabled for agent: {whispey_agent_id}")
            except Exception as e:
                logger.error(f"Failed to initialize Whispey: {e}")
        else:
            logger.warning("WHISPEY_API_KEY not set, observability disabled")

    # 4. Initialize Agent Components

    # We need a forward declaration or a wrapper for finalize_call because it's used in event listeners
    # and potentially by tools (via hangup -> disconnect -> finalize).
    is_finalized = False

    # We will define the finalize_call wrapper later when we have 'session' and 'call_start_time'.

    async def hangup_call():
        """End the call for all participants by deleting the room."""
        # Trigger finalize manually just in case event didn't fire (robustness)
        # We await it to ensure data is persisted before the process potentially exits or context is lost.
        if 'finalize_call' in locals():
            await finalize_call()

        # Disconnect agent first to avoid race conditions/panics during room deletion
        try:
            await ctx.room.disconnect()
            logger.info("Agent disconnected from room")
        except Exception as e:
            logger.warning(f"Failed to disconnect agent: {e}")

        # Explicitly delete the room to ensure SIP call ends
        try:
            # Short delay to allow disconnect to propagate
            await asyncio.sleep(0.5)
            await ctx.api.room.delete_room(api.DeleteRoomRequest(room=ctx.room.name))
            logger.info(f"Deleted room {ctx.room.name}")
        except Exception as e:
            logger.error(f"Failed to delete room: {e}")

    # Define tools
    all_tools = create_tools(
        call_metadata=call_metadata,
        db=db,
        dispatcher=dispatcher,
        contact_id=contact_id,
        phone_number=phone_number,
        hangup_callback=hangup_call,
        ctx=ctx,
    )

    agent = Agent(instructions=agent_instructions, tools=all_tools)

    try:
        llm = build_llm(ai_config=ai_config, metadata_overrides=initial_metadata)
        stt = build_stt(ai_config=ai_config, metadata_overrides=initial_metadata)
        tts = build_tts(ai_config=ai_config, metadata_overrides=initial_metadata)
    except Exception as e:
        error_message = (
            "Failed to initialize outbound AI providers "
            f"(llm={resolved_ai_config['llm_provider']}, stt={resolved_ai_config['stt_provider']}, "
            f"tts={resolved_ai_config['tts_provider']}): {e}"
        )
        call_metadata["notes"].append(error_message)
        logger.error(error_message, exc_info=True)
        try:
            await dispatcher.dispatch(
                "call.failed",
                {
                    "phone_number": phone_number,
                    "business_name": business_name,
                    "agent_slug": agent_slug,
                    "stage": "provider_initialization",
                    "error": error_message,
                },
            )
        except Exception as dispatch_error:
            logger.warning("call.failed webhook error during provider initialization: %s", dispatch_error)
        return

    # Use STT-based turn detection instead of Silero VAD to avoid the
    # 0.6–1s inference delay that was making the agent feel sluggish on
    # the container's CPU budget.  Deepgram's endpointing handles
    # silence/speech gating natively.
    session = AgentSession(
        turn_detection="stt",
        stt=stt,
        llm=llm,
        tts=tts,
        min_endpointing_delay=0.07,
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


    # 5. Start Session ASYNCHRONOUSLY (Critical for latency)
    logger.info("Starting LiveKit agent session")

    async def start_agent_session():
        try:
            await session.start(
                agent=agent,
                room=ctx.room,
                room_input_options=RoomInputOptions(close_on_disconnect=False),
            )
        except Exception as e:
            error_message = (
                f"LiveKit agent session failed to start for room {ctx.room.name} "
                f"(agent={agent_slug}): {e}"
            )
            call_metadata["notes"].append(error_message)
            logger.error(error_message, exc_info=True)
            try:
                await dispatcher.dispatch(
                    "call.failed",
                    {
                        "phone_number": phone_number,
                        "business_name": business_name,
                        "agent_slug": agent_slug,
                        "stage": "session_start",
                        "error": error_message,
                    },
                )
            except Exception as dispatch_error:
                logger.warning("call.failed webhook error during session start: %s", dispatch_error)
            raise

    session_start_task = asyncio.create_task(start_agent_session())

    # 6. Dial the user (SIP)
    # This function handles the dialing and basic error reporting
    dial_success = await dial_participant(ctx, phone_number, business_name, dispatcher)
    if not dial_success:
        return

    # ===================== RECORDING =====================
    # Start recording only after the call is answered
    await start_recording(ctx, egress_manager, call_metadata, dispatcher, contact_id, phone_number)
    # =====================================================

    # 8. Fire Opener using session.say()
    opening_line = agent_config.get("opening_line") or "Hello? Am I speaking with the business owner?"

    if business_name:
        if "{business_name}" in opening_line:
            opening_line = opening_line.format(business_name=business_name)
        elif "Am I speaking with the owner?" in opening_line and business_name != "Local Tester":
            opening_line = opening_line.replace("Am I speaking with the owner?", f"Am I speaking with the owner of {business_name}?")

    logger.info(f"Final Opening Line: '{opening_line}'")
    
    # Ensure session is started before speaking
    logger.info("Waiting for LiveKit agent session to finish startup before sending opening line")
    try:
        await session_start_task
    except Exception:
        try:
            await hangup_call()
        except Exception as hangup_error:
            logger.warning("Failed to clean up after session startup error: %s", hangup_error)
        return
    logger.info("LiveKit agent session is ready; sending opening line")
    
    try:
        await session.say(opening_line, allow_interruptions=True)
    except Exception as e:
        logger.warning(f"Failed to play opening line: {e}")

    # 9. Handle Disconnect & Cleanup Robustly

    call_start_time = datetime.datetime.now()

    async def finalize_call():
        nonlocal is_finalized
        # We delegate to the logic in outbound/lifecycle.py
        # We need to capture the return value to update is_finalized if we wanted,
        # but here we just check is_finalized first.

        # Note: logic inside finalize_call_logic checks if is_finalized is true.
        # But we need to update the local variable 'is_finalized' to prevent re-entry
        # if the logic module doesn't handle the state persistence across calls (which it doesn't, it just takes the bool).

        if is_finalized:
            return

        is_finalized = True
        
        await finalize_call_logic(
            ctx=ctx,
            db=db,
            dispatcher=dispatcher,
            egress_manager=egress_manager,
            session=session,
            call_start_time=call_start_time,
            call_metadata=call_metadata,
            contact_id=contact_id,
            prompt_id=prompt_id,
            is_finalized=False # We already checked above, but passing False lets it run.
        )

    # Register Whispey shutdown callback
    if whispey and session_id:
        async def whispey_shutdown():
            try:
                await whispey.export(session_id)
                logger.info(f"Whispey data exported for session: {session_id}")
            except Exception as e:
                logger.error(f"Failed to export Whispey data: {e}")

        # ctx.add_shutdown_callback is available in LiveKit agents
        ctx.add_shutdown_callback(whispey_shutdown)

    # Create a shutdown event to keep the process alive
    shutdown_event = asyncio.Event()

    # Listen for disconnect explicitly to run finalize BEFORE the main wait finishes/crashes
    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(participant: rtc.RemoteParticipant):
        logger.info(f"Participant {participant.identity} disconnected - triggering finalize")
        asyncio.create_task(finalize_call())

    @ctx.room.on("disconnected")
    def on_room_disconnected():
        logger.info("Room disconnected - triggering finalize")
        asyncio.create_task(finalize_call())

    # Ensure finalize_call sets the event to unblock the main loop
    original_finalize = finalize_call
    async def finalize_wrapper():
        try:
            await original_finalize()
        except Exception as e:
            logger.error(f"Error in finalize_call: {e}")
        finally:
            if not shutdown_event.is_set():
                shutdown_event.set()
    
    finalize_call = finalize_wrapper
    
    # Wait until we explicitly decide to shut down (via end_call or disconnect events)
    await shutdown_event.wait()
    
    # Final cleanup
    try:
        await session.aclose()
    except Exception:
        pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Set default load threshold to 0.9 to avoid flapping in dev/high-load envs
    # Note: Ensure this is a valid float string.
    # os.environ.setdefault("LIVEKIT_WORKER_LOAD_THRESHOLD", "0.9")
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="voice-assistant",
        )
    )
