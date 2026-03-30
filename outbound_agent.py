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
    metrics,
)
from livekit.agents.voice.room_io import RoomInputOptions, RoomOutputOptions
from livekit.agents.voice.events import ErrorEvent
from livekit.agents.llm import LLMError
from livekit.plugins import noise_cancellation
from livekit import api
from livekit import rtc
from livekit.agents.llm import ChatMessage

from egress_manager import EgressManager
from neon_db import get_db

# Import new modules
from outbound.metadata import extract_metadata, get_required_fields
from outbound.config import load_agent_config, prepare_instructions, load_ai_config
from outbound.sip import dial_participant, get_sip_identity
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
from outbound.state_machine import CallState, CallStateMachine
from outbound.tenant_profile import get_tenant_profile

# Whispey Observability Integration
try:
    from whispey import LivekitObserve
    WHISPEY_ENABLED = True
except ImportError:
    WHISPEY_ENABLED = False

load_dotenv()
logger = logging.getLogger("outbound-agent")

LLM_ERROR_FALLBACK_MESSAGE = "Give me just a moment, I need to gather my thoughts."

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
    state_machine = CallStateMachine()
    session_start_timeout_seconds = float(os.getenv("OUTBOUND_SESSION_START_TIMEOUT_SECONDS", "20"))
    opening_playout_timeout_seconds = float(os.getenv("OUTBOUND_OPENING_PLAYOUT_TIMEOUT_SECONDS", "25"))
    llm_response_timeout_seconds = float(os.getenv("OUTBOUND_LLM_RESPONSE_TIMEOUT_SECONDS", "8"))
    llm_slow_fallback_message = os.getenv(
        "OUTBOUND_LLM_SLOW_FALLBACK_MESSAGE",
        "Thanks for your patience, give me a quick moment while I pull that up.",
    )
    output_sample_rate = int(os.getenv("OUTBOUND_OUTPUT_SAMPLE_RATE", "8000"))
    enable_output_dtx = os.getenv("OUTBOUND_ENABLE_DTX", "false").lower() in {"1", "true", "yes", "on"}
    enable_output_red = os.getenv("OUTBOUND_ENABLE_RED", "false").lower() in {"1", "true", "yes", "on"}

    # Connect to room
    await ctx.connect()
    state_machine.transition(CallState.ROOM_CONNECTED)
    call_metadata["state_machine"] = state_machine.export()
    logger.info(f"Connected to room {ctx.room.name}")

    # 2. Extract outbound metadata (robust)
    initial_metadata = extract_metadata(ctx)
    phone_number, business_name, agent_slug = get_required_fields(initial_metadata)
    tenant_id = initial_metadata.get("tenant_id")
    tenant_profile = await get_tenant_profile(tenant_id)

    if tenant_profile:
        tenant_agent_slug = tenant_profile.get("agent_slug")
        if isinstance(tenant_agent_slug, str) and tenant_agent_slug.strip():
            agent_slug = tenant_agent_slug.strip()
        ai_overrides = tenant_profile.get("ai_overrides")
        if isinstance(ai_overrides, dict):
            # Reuse existing metadata override resolution path in outbound.providers.
            initial_metadata.update(ai_overrides)
    from_number = initial_metadata.get("from_number")
    call_metadata["business_name"] = business_name
    if tenant_id:
        call_metadata["tenant_id"] = tenant_id
    if tenant_profile:
        call_metadata["workflow_policy"] = tenant_profile.get("workflow_policy")
        routing_policy = tenant_profile.get("routing_policy")
        if isinstance(routing_policy, dict):
            call_metadata["routing_policy"] = routing_policy

    logger.info(f"Parsed metadata → phone: {phone_number}, business: {business_name}, slug: {agent_slug}")
    if from_number:
        logger.info(f"Using caller ID (from_number): {from_number}")

    if not phone_number:
        logger.error("No phone number found in metadata. Cannot place outbound call.")
        return

    logger.info(f"Preparing outbound call to {phone_number} using agent {agent_slug}")
    logger.info(
        "Telephony output config: sample_rate=%s, dtx=%s, red=%s",
        output_sample_rate,
        enable_output_dtx,
        enable_output_red,
    )

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
    agent_instructions = await prepare_instructions(db, agent_slug, schema_fields, agent_config=agent_config)
    state_machine.transition(CallState.CONFIG_LOADED)
    call_metadata["state_machine"] = state_machine.export()

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
        state_machine.transition(CallState.CALL_LOGGED, details={"call_id": call_id})
        call_metadata["state_machine"] = state_machine.export()
        logger.info(f"Call initiated in DB with ID: {call_id}")
    except Exception as e:
        logger.error(f"Failed to log initial call record: {e}")

    # Initialize EgressManager early
    egress_manager = EgressManager(ctx.api)

    # AI Config
    ai_config = await load_ai_config(db, agent_slug, agent_config=agent_config)
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

    # Inject caller context directly into prompt (avoids Groq null-argument bug with lookup tools)
    caller_context = (
        f"\n\nCALLER CONTEXT (already known — do NOT ask for this or call any lookup tool):\n"
        f"- Phone: {phone_number}\n"
        f"- Business: {business_name}\n"
        f"- Contact ID: {contact_id}\n"
    )
    agent_instructions += caller_context

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

    # STT-based turn detection via Deepgram handles endpointing.
    # Silero VAD removed — the container CPU cannot sustain real-time
    # ONNX inference, causing delays that grow to 8+ seconds and
    # break interrupt handling.  STT alone is sufficient.
    session = AgentSession(
        turn_detection="stt",
        stt=stt,
        llm=llm,
        tts=tts,
        min_endpointing_delay=0.5,
        max_endpointing_delay=6.0,
        min_interruption_words=1,
        preemptive_generation=os.getenv("OUTBOUND_PREEMPTIVE_GENERATION", "false").lower() in {"1", "true", "yes", "on"},
    )

    # --- Agent Observability: collect & log STT/LLM/TTS latency metrics ---
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics(mets: metrics.AgentMetrics):
        try:
            metrics.log_metrics(mets)
        except AttributeError:
            pass  # SDK 1.2.18 bug: MetricsCollectedEvent missing .metadata
        usage_collector.collect(mets)

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

    # Guard against long LLM delays after a committed user utterance.
    pending_turn_watchdog: asyncio.Task | None = None
    user_turn_counter = 0
    assistant_turn_counter = 0

    def _cancel_watchdog() -> None:
        nonlocal pending_turn_watchdog
        if pending_turn_watchdog and not pending_turn_watchdog.done():
            pending_turn_watchdog.cancel()
        pending_turn_watchdog = None

    async def _turn_watchdog(turn_number: int) -> None:
        try:
            await asyncio.sleep(llm_response_timeout_seconds)
            if assistant_turn_counter < turn_number:
                note = (
                    f"LLM response timeout ({llm_response_timeout_seconds}s) after user turn #{turn_number}; "
                    "speaking fallback"
                )
                call_metadata["notes"].append(note)
                state_machine.transition(
                    CallState.LLM_TIMEOUT_FALLBACK,
                    reason="assistant_turn_timeout",
                    details={"turn_number": turn_number, "timeout_seconds": llm_response_timeout_seconds},
                )
                call_metadata["state_machine"] = state_machine.export()
                logger.warning(note)
                handle = session.say(llm_slow_fallback_message, allow_interruptions=True)
                await handle
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.warning("LLM watchdog fallback failed: %s", e)

    @session.on("user_input_transcribed")
    def _on_user_input_transcribed(ev):
        nonlocal user_turn_counter, pending_turn_watchdog
        transcript = (getattr(ev, "transcript", "") or "").strip()
        if not getattr(ev, "is_final", False) or not transcript:
            return
        user_turn_counter += 1
        _cancel_watchdog()
        pending_turn_watchdog = asyncio.create_task(_turn_watchdog(user_turn_counter))

    @session.on("conversation_item_added")
    def _on_conversation_item_added(ev):
        nonlocal assistant_turn_counter
        item = getattr(ev, "item", None)
        if isinstance(item, ChatMessage) and getattr(item, "role", None) == "assistant":
            assistant_turn_counter += 1
            _cancel_watchdog()

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
    state_machine.transition(CallState.SESSION_STARTING)
    call_metadata["state_machine"] = state_machine.export()

    async def start_agent_session():
        try:
            await session.start(
                agent=agent,
                room=ctx.room,
                room_input_options=RoomInputOptions(
                    noise_cancellation=noise_cancellation.BVCTelephony(),
                    close_on_disconnect=False,
                ),
                room_output_options=RoomOutputOptions(
                    audio_sample_rate=output_sample_rate,
                    audio_publish_options=rtc.TrackPublishOptions(
                        dtx=enable_output_dtx,
                        red=enable_output_red,
                        source=rtc.TrackSource.SOURCE_MICROPHONE,
                    ),
                ),
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
    state_machine.transition(CallState.DIALING, details={"phone_number": phone_number})
    call_metadata["state_machine"] = state_machine.export()
    dial_success = await dial_participant(
        ctx,
        phone_number,
        business_name,
        dispatcher,
        from_number=from_number,
        call_metadata=call_metadata,
    )
    if not dial_success:
        state_machine.transition(CallState.DIAL_FAILED, reason="sip_dial_failed")
        call_metadata["state_machine"] = state_machine.export()
        logger.warning("SIP dial failed for %s — marking call %s as failed", phone_number, call_metadata.get("call_id"))
        call_id = call_metadata.get("call_id")
        if call_id and db:
            try:
                await db.update_call(
                    call_id=call_id,
                    call_status="failed",
                    notes="SIP dial failed — carrier returned error",
                    captured_data=call_metadata,
                )
            except Exception as e:
                logger.error("Failed to update call %s as failed: %s", call_id, e)
        # Cancel the pending session start task
        session_start_task.cancel()
        try:
            await session_start_task
        except (asyncio.CancelledError, Exception):
            pass
        return

    state_machine.transition(CallState.DIALED)
    call_metadata["state_machine"] = state_machine.export()

    # ===================== RECORDING =====================
    # Start recording only after the call is answered
    await start_recording(ctx, egress_manager, call_metadata, dispatcher, contact_id, phone_number)
    state_machine.transition(CallState.RECORDING_STARTED)
    call_metadata["state_machine"] = state_machine.export()
    # =====================================================

    # 8. Fire Opener using session.say()
    opening_line = agent_config.get("opening_line") or "Hello? Am I speaking with the business owner?"
    tenant_opening_line = tenant_profile.get("opening_line") if tenant_profile else None
    if isinstance(tenant_opening_line, str) and tenant_opening_line.strip():
        opening_line = tenant_opening_line

    if business_name:
        if "{business_name}" in opening_line:
            opening_line = opening_line.format(business_name=business_name)
        elif "Am I speaking with the owner?" in opening_line and business_name != "Local Tester":
            opening_line = opening_line.replace("Am I speaking with the owner?", f"Am I speaking with the owner of {business_name}?")

    logger.info(f"Final Opening Line: '{opening_line}'")
    
    # Ensure session is started before speaking
    logger.info("Waiting for LiveKit agent session to finish startup before sending opening line")
    try:
        await asyncio.wait_for(session_start_task, timeout=session_start_timeout_seconds)
        state_machine.transition(CallState.SESSION_READY)
        call_metadata["state_machine"] = state_machine.export()
    except Exception:
        state_machine.transition(CallState.FAILED, reason="session_start_timeout_or_error")
        call_metadata["state_machine"] = state_machine.export()
        call_metadata["notes"].append(
            f"Session start failed or timed out after {session_start_timeout_seconds}s"
        )
        try:
            await hangup_call()
        except Exception as hangup_error:
            logger.warning("Failed to clean up after session startup error: %s", hangup_error)
        return
    logger.info("LiveKit agent session is ready; sending opening line")
    
    try:
        state_machine.transition(CallState.OPENING_PLAYING)
        call_metadata["state_machine"] = state_machine.export()
        handle = session.say(opening_line, allow_interruptions=False)
        logger.info("Opening line queued: handle=%s", handle.id)
        await asyncio.wait_for(handle, timeout=opening_playout_timeout_seconds)
        state_machine.transition(CallState.OPENING_PLAYED)
        call_metadata["state_machine"] = state_machine.export()
        logger.info("Opening line playout completed")
        state_machine.transition(CallState.IN_CONVERSATION)
        call_metadata["state_machine"] = state_machine.export()
    except asyncio.TimeoutError:
        state_machine.transition(CallState.OPENING_FAILED, reason="opening_playout_timeout")
        call_metadata["state_machine"] = state_machine.export()
        call_metadata["notes"].append(
            f"Opening line playout timed out after {opening_playout_timeout_seconds}s"
        )
        logger.warning("Opening line playout timed out; continuing call flow")
    except Exception as e:
        state_machine.transition(CallState.OPENING_FAILED, reason="opening_playout_error")
        call_metadata["state_machine"] = state_machine.export()
        logger.warning(f"Failed to play opening line: {e}", exc_info=True)

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
        _cancel_watchdog()
        state_machine.transition(CallState.FINALIZING)
        call_metadata["state_machine"] = state_machine.export()

        # Log usage summary before finalizing
        try:
            summary = usage_collector.get_summary()
            logger.info(
                "Usage summary: llm_prompt_tokens=%d, llm_completion_tokens=%d, "
                "tts_characters=%d, stt_audio_duration=%.1fs",
                summary.llm_prompt_tokens,
                summary.llm_completion_tokens,
                summary.tts_characters_count,
                summary.stt_audio_duration,
            )
        except Exception as e:
            logger.debug("Could not log usage summary: %s", e)
        
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
        state_machine.transition(CallState.FINALIZED)
        call_metadata["state_machine"] = state_machine.export()

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
    # Only react to the SIP participant we actually dialled to avoid double-finalize
    # when unexpected participants (e.g. from a duplicate SIP creation) disconnect.
    expected_sip_identity = get_sip_identity(phone_number)

    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(participant: rtc.RemoteParticipant):
        if participant.identity != expected_sip_identity:
            logger.debug(
                "Ignoring disconnect from unexpected participant %s (expected %s)",
                participant.identity,
                expected_sip_identity,
            )
            return
        state_machine.transition(
            CallState.PARTICIPANT_DISCONNECTED,
            details={"participant_identity": participant.identity},
        )
        call_metadata["state_machine"] = state_machine.export()
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

    # === Startup diagnostics: log provider env vars so we can debug 403s ===
    _startup_logger = logging.getLogger("outbound-agent.startup")
    _groq_key = os.getenv("GROQ_API_KEY", "")
    _openai_key = os.getenv("OPENAI_API_KEY", "")
    _llm_provider_env = os.getenv("LLM_PROVIDER", "(not set)")
    _tts_provider_env = os.getenv("TTS_PROVIDER", "(not set)")
    _startup_logger.info(
        "ENV CHECK → LLM_PROVIDER=%s, TTS_PROVIDER=%s, GROQ_API_KEY=%s, OPENAI_API_KEY=%s",
        _llm_provider_env,
        _tts_provider_env,
        f"set ({_groq_key[:8]}...)" if _groq_key else "NOT SET",
        f"set ({_openai_key[:8]}...)" if _openai_key else "NOT SET",
    )
    # ======================================================================

    # Set default load threshold to 0.9 to avoid flapping in dev/high-load envs
    os.environ.setdefault("LIVEKIT_WORKER_LOAD_THRESHOLD", "0.9")
    _agent_name = os.getenv("OUTBOUND_AGENT_NAME", "voice-assistant")
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name=_agent_name,
        )
    )
