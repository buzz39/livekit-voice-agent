import os
import re
import asyncio
import logging
import time
from datetime import timedelta
from livekit.protocol.sip import CreateSIPParticipantRequest, SIPMediaEncryption
from typing import Optional, Any, Dict, List

from livekit.agents.utils.participant import wait_for_participant

logger = logging.getLogger("outbound.sip")

RETRYABLE_SIP_CODES = {408, 429, 500, 502, 503, 504}
COOLDOWN_ELIGIBLE_SIP_CODES = {500, 502, 503, 504}

_TRUNK_COOLDOWNS: Dict[str, float] = {}


def _parse_trunk_candidates(preferred_trunks: Optional[List[str]] = None) -> List[str]:
    primary = os.getenv("LIVEKIT_OUTBOUND_TRUNK_ID") or os.getenv("SIP_TRUNK_ID") or ""
    raw_candidates = os.getenv("LIVEKIT_OUTBOUND_TRUNK_IDS", "")
    extra = [item.strip() for item in raw_candidates.split(",") if item.strip()]

    ordered = [primary, *extra]
    unique: List[str] = []
    for trunk in ordered:
        if trunk and trunk not in unique:
            unique.append(trunk)
    if preferred_trunks:
        normalized_preferred = [item.strip() for item in preferred_trunks if isinstance(item, str) and item.strip()]
        preferred_existing = [item for item in normalized_preferred if item in unique]
        remaining = [item for item in unique if item not in preferred_existing]
        unique = preferred_existing + remaining

    return unique


def _extract_sip_status_code(error: Exception) -> Optional[int]:
    status = None
    if hasattr(error, "metadata") and isinstance(error.metadata, dict):
        status = error.metadata.get("sip_status_code")
    if status is None:
        err_str = str(error)
        match = re.search(r"sip_status_code['\"]?\s*[:=]\s*['\"]?(\d+)", err_str)
        if match:
            status = match.group(1)
    if status is None:
        err_str = str(error)
        match = re.search(r"status\s*=\s*(\d{3})", err_str)
        if match:
            status = match.group(1)
    try:
        return int(status) if status is not None else None
    except (TypeError, ValueError):
        return None


def _get_active_trunk_candidates(trunks: List[str]) -> List[str]:
    now = time.time()
    active = [trunk for trunk in trunks if _TRUNK_COOLDOWNS.get(trunk, 0.0) <= now]
    if active:
        return active
    # If all trunks are in cooldown, keep original order to avoid total deadlock.
    return trunks


def _mark_trunk_cooldown(trunk_id: str, cooldown_seconds: float) -> None:
    if cooldown_seconds <= 0:
        return
    _TRUNK_COOLDOWNS[trunk_id] = time.time() + cooldown_seconds


def get_sip_identity(phone_number: str) -> str:
    """Return the participant identity that ``dial_participant`` will assign.

    For regular phone numbers the identity is digits-only; for SIP URIs it
    is the raw URI string.
    """
    if "sip:" in phone_number:
        return phone_number
    return re.sub(r"\D", "", phone_number)


async def dial_participant(
    ctx,
    phone_number: str,
    business_name: str,
    dispatcher=None,
    from_number: Optional[str] = None,
    call_metadata: Optional[Dict[str, Any]] = None,
) -> bool:
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
    preferred_trunks: Optional[List[str]] = None
    if call_metadata and isinstance(call_metadata.get("routing_policy"), dict):
        candidate_pref = call_metadata["routing_policy"].get("preferred_trunks")
        if isinstance(candidate_pref, list):
            preferred_trunks = candidate_pref

    sip_trunk_candidates = _parse_trunk_candidates(preferred_trunks=preferred_trunks)
    sip_from_number = from_number or os.getenv("SIP_FROM_NUMBER")
    ringing_timeout = timedelta(seconds=int(os.getenv("SIP_RINGING_TIMEOUT", "30")))
    max_call_duration = timedelta(seconds=int(os.getenv("SIP_MAX_CALL_DURATION", "600")))
    dial_max_rounds = max(1, int(os.getenv("SIP_DIAL_MAX_ROUNDS", "2")))
    dial_retry_delay = max(0.0, float(os.getenv("SIP_DIAL_RETRY_DELAY_SECONDS", "1.5")))
    trunk_failure_threshold = max(1, int(os.getenv("SIP_TRUNK_FAILURE_THRESHOLD", "2")))
    trunk_cooldown_seconds = max(0.0, float(os.getenv("SIP_TRUNK_COOLDOWN_SECONDS", "90")))

    if not sip_trunk_candidates:
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

    logger.info("Dialing %s (identity=%s) using trunks=%s", actual_sip_target, final_identity, sip_trunk_candidates)

    attempts: List[Dict[str, Any]] = []
    hard_failure_error: Optional[Exception] = None
    per_trunk_failures: Dict[str, int] = {}

    stop_due_to_trunk_failure = False

    for round_idx in range(dial_max_rounds):
        active_trunks = _get_active_trunk_candidates(sip_trunk_candidates)
        for trunk_id in active_trunks:
            attempt_number = len(attempts) + 1
            dial_error: Optional[Exception] = None
            sip_status_code: Optional[int] = None

            try:
                await ctx.api.sip.create_sip_participant(
                    CreateSIPParticipantRequest(
                        room_name=ctx.room.name,
                        sip_trunk_id=trunk_id,
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
                logger.info("Dial attempt #%d accepted on trunk %s", attempt_number, trunk_id)
            except Exception as e:
                dial_error = e
                sip_status_code = _extract_sip_status_code(e)
                logger.error(
                    "Dial attempt #%d failed on trunk %s (sip_status=%s): %s",
                    attempt_number,
                    trunk_id,
                    sip_status_code,
                    e,
                )

            attempt_record = {
                "attempt": attempt_number,
                "round": round_idx + 1,
                "trunk_id": trunk_id,
                "sip_status_code": sip_status_code,
                "error": str(dial_error) if dial_error else None,
            }
            attempts.append(attempt_record)

            if dispatcher:
                try:
                    await dispatcher.dispatch("call.dial.attempt", attempt_record)
                except Exception:
                    pass

            # If create_sip_participant succeeded, wait for participant join.
            if dial_error is None:
                per_trunk_failures[trunk_id] = 0
                try:
                    participant = await asyncio.wait_for(
                        wait_for_participant(ctx.room, identity=final_identity),
                        timeout=30.0,
                    )
                    logger.info("SIP participant connected: %s (trunk=%s)", participant.identity, trunk_id)
                    if call_metadata is not None:
                        call_metadata["dial_attempts"] = attempts
                        call_metadata["successful_trunk_id"] = trunk_id
                    return True
                except asyncio.TimeoutError:
                    logger.error("Participant join timeout on trunk %s", trunk_id)
                    attempts[-1]["error"] = "participant join timeout"
                    attempts[-1]["sip_status_code"] = attempts[-1]["sip_status_code"] or 408

            if dial_error is not None:
                per_trunk_failures[trunk_id] = per_trunk_failures.get(trunk_id, 0) + 1
                if sip_status_code in COOLDOWN_ELIGIBLE_SIP_CODES:
                    _mark_trunk_cooldown(trunk_id, trunk_cooldown_seconds)
                if per_trunk_failures[trunk_id] >= trunk_failure_threshold:
                    logger.warning(
                        "Trunk %s reached failure threshold (%s) in this call",
                        trunk_id,
                        trunk_failure_threshold,
                    )
                    # If there is no alternative trunk, stop early instead of hammering the same route.
                    if len(sip_trunk_candidates) == 1:
                        stop_due_to_trunk_failure = True
                        break

            # Hard failures should stop immediately (except retryable SIP codes).
            if sip_status_code is not None and sip_status_code >= 400 and sip_status_code not in RETRYABLE_SIP_CODES:
                hard_failure_error = dial_error
                if call_metadata is not None:
                    call_metadata["dial_attempts"] = attempts
                logger.error("SIP hard failure %s on trunk %s, stopping dial workflow", sip_status_code, trunk_id)
                if dispatcher:
                    try:
                        await dispatcher.dispatch(
                            "call.failed",
                            {
                                "error": str(dial_error),
                                "sip_status_code": sip_status_code,
                                "phone_number": phone_number,
                                "trunk_id": trunk_id,
                                "attempt": attempt_number,
                            },
                        )
                    except Exception:
                        pass
                return False

            # If we still have candidates in this round or another round, delay before retry.
            has_more_candidates = trunk_id != active_trunks[-1] or round_idx < dial_max_rounds - 1
            if has_more_candidates and dial_retry_delay > 0:
                await asyncio.sleep(dial_retry_delay)

        if stop_due_to_trunk_failure:
            break

    if call_metadata is not None:
        call_metadata["dial_attempts"] = attempts

    logger.error("All SIP dial attempts failed for %s", phone_number)
    if dispatcher:
        try:
            await dispatcher.dispatch(
                "call.failed",
                {
                    "error": str(hard_failure_error) if hard_failure_error else "all dial attempts failed",
                    "phone_number": phone_number,
                    "dial_attempts": attempts,
                },
            )
        except Exception:
            pass
    return False
