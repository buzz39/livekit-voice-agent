import os
import logging
import asyncio
from typing import Dict, Any, Optional
from egress_manager import EgressManager

logger = logging.getLogger("outbound.recording")

async def start_recording(
    ctx: Any,
    egress_manager: EgressManager,
    call_metadata: Dict[str, Any],
    dispatcher: Any,
    contact_id: str,
    phone_number: str
):
    """
    Starts the room composite egress (recording) in the background.
    Updates call_metadata with the recording_id and recording_url.
    """
    # Configure S3 if env vars are present
    s3_options = None
    if os.getenv("S3_ACCESS_KEY") and os.getenv("S3_SECRET_KEY") and os.getenv("S3_BUCKET"):
        s3_options = {
            "access_key": os.getenv("S3_ACCESS_KEY"),
            "secret": os.getenv("S3_SECRET_KEY"),
            "bucket": os.getenv("S3_BUCKET"),
            "region": os.getenv("S3_REGION", ""),
            "endpoint": os.getenv("S3_ENDPOINT", "")
        }
    elif os.getenv("AWS_ACCESS_KEY") and os.getenv("AWS_SECRET_ACCESS_KEY") and os.getenv("S3_BUCKET_NAME"):
         s3_options = {
            "access_key": os.getenv("AWS_ACCESS_KEY"),
            "secret": os.getenv("AWS_SECRET_ACCESS_KEY"),
            "bucket": os.getenv("S3_BUCKET_NAME"),
            "region": os.getenv("AWS_REGION", ""),
            "endpoint": os.getenv("S3_ENDPOINT", "")
        }

    # START EGRESS DIRECTLY
    # We await the API call to ensure the recording request is accepted by the server.
    # This prevents race conditions where the task might be GC'd or fail silently.
    try:
        rec_id, rec_url = await egress_manager.start_room_composite_egress(
            ctx.room.name,
            s3_options=s3_options
        )
        if rec_id:
            call_metadata["recording_id"] = rec_id
            if rec_url:
                call_metadata["recording_url"] = rec_url
            try:
                await dispatcher.dispatch("recording.started", {
                    "room_id": ctx.room.name,
                    "recording_id": rec_id,
                    "recording_url": rec_url,
                    "contact_id": contact_id,
                    "phone_number": phone_number,
                })
            except Exception as e:
                logger.debug(f"recording.started webhook error: {e}")
        else:
             logger.warning("Egress manager returned no recording ID. Recording likely failed to start.")
    except Exception as e:
        logger.error(f"Failed to start egress recording: {e}")
