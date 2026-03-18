import os
import re
import asyncio
import logging
from livekit.protocol.sip import CreateSIPParticipantRequest
from typing import Optional

logger = logging.getLogger("outbound.sip")

DEFAULT_SIP_TRUNK_ID = "ST_nVvG7n8BpJd3"
DEFAULT_SIP_FROM_NUMBER = "+12029787305"


def get_sip_trunk_id() -> str:
    """Resolve the outbound SIP trunk ID using supported environment variable names."""
    configured_trunk_id = (
        os.getenv("LIVEKIT_SIP_TRUNK_ID")
        or os.getenv("LIVEKIT_OUTBOUND_TRUNK_ID")
        or os.getenv("SIP_TRUNK_ID")
    )
    trunk_id = configured_trunk_id or DEFAULT_SIP_TRUNK_ID
    if not configured_trunk_id:
        logger.info(
            f"No explicit SIP trunk ID configured; defaulting to Vobiz outbound trunk {DEFAULT_SIP_TRUNK_ID}"
        )
    return trunk_id

async def dial_participant(ctx, phone_number: str, business_name: str, dispatcher=None) -> bool:
    """
    Dials a SIP participant.

    Args:
        ctx: The JobContext (must have .api and .room).
        phone_number: The target phone number or SIP URI.
        business_name: The name to display for the caller.
        dispatcher: Optional WebhookDispatcher to report failures.

    Returns:
        True if the call was answered (or at least dialed successfully without immediate exception),
        False otherwise.
    """
    sip_trunk_id = get_sip_trunk_id()
    sip_from_number = os.getenv("SIP_FROM_NUMBER", DEFAULT_SIP_FROM_NUMBER)

    # Logic for target and identity
    actual_sip_target = phone_number
    final_identity = phone_number

    if "sip:" in phone_number:
        # SIP URI Case
        # Target: User part only (e.g. "hello" from "sip:hello@domain")
        clean = phone_number.replace("sip:", "")
        if "@" in clean:
            actual_sip_target = clean.split("@")[0]
        else:
            actual_sip_target = clean
        # Identity: Full URI (safe for strings)
        final_identity = phone_number
    else:
        # Phone Number Case
        # Target: Raw intput
        actual_sip_target = phone_number
        # Identity: Digits only (Crucial for LiveKit backend compatibility)
        final_identity = re.sub(r"\D", "", phone_number)

    logger.info(f"Dialing {actual_sip_target} (identity={final_identity})...")
    try:
        await ctx.api.sip.create_sip_participant(
            CreateSIPParticipantRequest(
                room_name=ctx.room.name,
                sip_trunk_id=sip_trunk_id,
                sip_call_to=actual_sip_target,
                sip_number=sip_from_number,
                participant_identity=final_identity,
                participant_name=business_name,
                wait_until_answered=True,
            )
        )
        logger.info("Call answered!")
        return True
    except Exception as e:
        logger.error(f"Failed to dial: {e}")
        # Add a small delay to allow potential extensive cleanup or event processing
        # to settle before ensuring the agent doesn't crash on race conditions
        await asyncio.sleep(1)
        if dispatcher:
            try:
                await dispatcher.dispatch("call.failed", {"error": str(e)})
            except Exception:
                pass
        return False
