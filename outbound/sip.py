import os
import re
import asyncio
import logging
from datetime import timedelta
from livekit.protocol.sip import CreateSIPParticipantRequest, SIPMediaEncryption
from typing import Optional

from livekit.agents.utils.participant import wait_for_participant

logger = logging.getLogger("outbound.sip")


def get_sip_identity(phone_number: str) -> str:
    """Return the participant identity that ``dial_participant`` will assign.

    For regular phone numbers the identity is digits-only; for SIP URIs it
    is the raw URI string.
    """
    if "sip:" in phone_number:
        return phone_number
    return re.sub(r"\D", "", phone_number)


async def dial_participant(ctx, phone_number: str, business_name: str, dispatcher=None, from_number: Optional[str] = None) -> bool:
    """
    Dials a SIP participant.

    Args:
        ctx: The JobContext (must have .api and .room).
        phone_number: The target phone number or SIP URI.
        business_name: The name to display for the caller.
        dispatcher: Optional WebhookDispatcher to report failures.
        from_number: Optional caller ID / FROM number override. When provided,
                     takes precedence over the SIP_FROM_NUMBER environment variable.

    Returns:
        True if the call was answered (or at least dialed successfully without immediate exception),
        False otherwise.
    """
    sip_trunk_id = os.getenv("LIVEKIT_OUTBOUND_TRUNK_ID") or os.getenv("SIP_TRUNK_ID")
    sip_from_number = from_number or os.getenv("SIP_FROM_NUMBER")
    ringing_timeout = timedelta(seconds=int(os.getenv("SIP_RINGING_TIMEOUT", "30")))
    max_call_duration = timedelta(seconds=int(os.getenv("SIP_MAX_CALL_DURATION", "600")))

    if not sip_trunk_id:
        logger.error("LIVEKIT_OUTBOUND_TRUNK_ID (or SIP_TRUNK_ID) not set in env")
        return False

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
    dial_error: Exception | None = None
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
                krisp_enabled=True,
                ringing_timeout=ringing_timeout,
                max_call_duration=max_call_duration,
                media_encryption=SIPMediaEncryption.SIP_MEDIA_ENCRYPT_ALLOW,
            )
        )
        logger.info("Call answered or dialing request accepted")
    except Exception as e:
        dial_error = e
        logger.error(f"Failed to dial: {e}")

    try:
        participant = await asyncio.wait_for(
            wait_for_participant(ctx.room, identity=final_identity),
            timeout=30.0,
        )
        logger.info("SIP participant connected: %s", participant.identity)
        if dial_error and dispatcher:
            try:
                await dispatcher.dispatch(
                    "call.dial_recovered",
                    {"error": str(dial_error), "participant_identity": participant.identity},
                )
            except Exception:
                pass
        return True
    except asyncio.TimeoutError:
        logger.error("SIP participant never joined after dial attempt (identity=%s)", final_identity)
        if dispatcher:
            try:
                payload = {"error": str(dial_error) if dial_error else "participant join timeout"}
                await dispatcher.dispatch("call.failed", payload)
            except Exception:
                pass
        return False
