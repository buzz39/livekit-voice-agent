import datetime
import logging
import asyncio
from livekit import api
from typing import Dict, Any

logger = logging.getLogger("outbound.lifecycle")

async def finalize_call(
    ctx: Any,
    db: Any,
    dispatcher: Any,
    egress_manager: Any,
    session: Any,
    call_start_time: datetime.datetime,
    call_metadata: Dict[str, Any],
    contact_id: str,
    prompt_id: str,
    is_finalized: bool
):
    """
    Handles call finalization: stopping recording, capturing transcript, persisting data.
    """
    if is_finalized:
        return True

    logger.info("⚡ Starting finalize_call...")

    # Calculate duration
    call_end_time = datetime.datetime.now()
    duration_seconds = int((call_end_time - call_start_time).total_seconds())

    recording_id = call_metadata.get("recording_id")

    # Stop Egress immediately
    if recording_id:
        logger.info(f"Stopping Egress {recording_id}")
        try:
            await egress_manager.stop_egress(recording_id)
            logger.info(f"Egress {recording_id} stop requested")
        except Exception:
            pass

    # Capture transcript
    transcript_text = None
    transcript_json = []
    try:
        if getattr(session, "history", None):
            transcript_lines = []
            items = getattr(session.history, "items", None) or getattr(session.history, "messages", None) or []
            for item in items:
                role = getattr(item, "role", None)
                content = getattr(item, "content", None) or getattr(item, "text", None) or ""

                # Build JSON entry
                if role and content:
                    transcript_json.append({"role": role, "content": content})

                # Build Text entry
                display_role = "Agent" if role == "assistant" else "User"
                if content:
                    transcript_lines.append(f"{display_role}: {content}")

            transcript_text = "\n".join(transcript_lines)

            # Add structured transcript to call_metadata for Observability
            call_metadata["transcript_json"] = transcript_json

            logger.info(f"Transcript captured ({len(transcript_lines)} lines)")
    except Exception as e:
        logger.warning(f"Failed to capture transcript: {e}")

    # Persist to DB immediately
    try:
        email_flag = bool(call_metadata.get("email"))
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
        logger.info("✅ Final call data persisted to DB")
    except Exception as e:
        logger.error(f"Failed to persist final call data: {e}")

    # Try to get recording URL (with brief poll)
    try:
        # We try a few times to get the recording URL
        # NOTE: In the original code there were two versions of this logic.
        # One with a loop and sleep (asyncio.sleep(0.5)), and one without sleep.
        # Since this is running in background/async, a small wait loop is acceptable.
        for _ in range(3):
            resp = await ctx.api.recording.list_recordings(api.ListRecordingsRequest(room_name=ctx.room.name))
            recordings = getattr(resp, "recordings", None) or getattr(resp, "content", None) or []
            if recordings:
                first = recordings[0]
                rec_url = getattr(first, "url", None) or getattr(first, "download_url", None) or (first.get("url") if isinstance(first, dict) else None)
                if rec_url:
                    await db.update_call_recording(ctx.room.name, rec_url)
                    logger.info(f"Recording URL captured: {rec_url}")
                    await dispatcher.dispatch("call.recording.ready", {"room_id": ctx.room.name, "recording_url": rec_url, "contact_id": contact_id})
                    break
            await asyncio.sleep(0.5)
    except Exception:
        pass

    # Cleanup
    try:
        await dispatcher.close()
    except Exception:
        pass

    try:
        await db.close()
        logger.info("DB Connection closed")
    except Exception:
        pass

    return True
