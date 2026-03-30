import datetime
import logging
import asyncio
import os
import re
from livekit.agents.llm import function_tool
from livekit import api
from typing import Callable, List, Dict, Any, Optional

logger = logging.getLogger("outbound.tools")

def create_tools(
    call_metadata: Dict[str, Any],
    db: Any,
    dispatcher: Any,
    contact_id: str,
    phone_number: Optional[str],
    hangup_callback: Callable[[], Any],
    ctx: Optional[Any] = None,
    sip_domain: Optional[str] = None,
    default_transfer_destination: Optional[str] = None,
) -> List[Callable]:
    """
    Creates and returns a list of function tools for the agent.

    Args:
        call_metadata: Mutable dictionary to store call metadata.
        db: Database interface.
        dispatcher: WebhookDispatcher instance.
        contact_id: The database ID of the contact.
        phone_number: The phone number of the contact, if known.
        hangup_callback: Async function to trigger hangup/finalization.
    """

    sip_domain = sip_domain or os.getenv("SIP_DOMAIN") or os.getenv("VOBIZ_SIP_DOMAIN")
    default_transfer_destination = default_transfer_destination or os.getenv("DEFAULT_TRANSFER_NUMBER")

    def _normalize_phone_number(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if value.startswith("sip:"):
            return value
        return re.sub(r"\D", "", value)

    normalized_phone_number = _normalize_phone_number(phone_number)

    if not isinstance(call_metadata.get("tool_events"), list):
        call_metadata["tool_events"] = []
    if not isinstance(call_metadata.get("idempotency_keys"), dict):
        call_metadata["idempotency_keys"] = {}

    def _format_transfer_destination(destination: str) -> str:
        clean_destination = destination.strip()
        if "@" in clean_destination:
            if clean_destination.startswith("sip:"):
                return clean_destination
            return f"sip:{clean_destination.removeprefix('tel:')}"

        clean_destination = clean_destination.removeprefix("tel:").removeprefix("sip:")
        if sip_domain:
            return f"sip:{clean_destination}@{sip_domain}"
        return f"tel:{clean_destination}"

    def _participant_identity() -> Optional[str]:
        if phone_number:
            # Keep transfer identity aligned with outbound.sip.dial_participant(), which uses
            # full SIP URIs for SIP targets and digits-only identities for PSTN numbers.
            return _normalize_phone_number(phone_number)
        if ctx:
            for participant in ctx.room.remote_participants.values():
                if (
                    participant.identity.startswith("sip_")
                    or participant.identity.startswith("sip:")
                    or participant.identity.isdigit()
                ):
                    return participant.identity
        return None

    async def _record_tool_event(tool_name: str, payload: Dict[str, Any], idempotency_key: str = "") -> None:
        event = {
            "tool": tool_name,
            "at": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "payload": payload,
            "contact_id": contact_id,
            "phone_number": phone_number,
            "idempotency_key": idempotency_key or None,
        }
        call_metadata["tool_events"].append(event)
        try:
            await dispatcher.dispatch("tool.called", event)
        except Exception as exc:
            logger.debug("tool.called webhook dispatch failed: %s", exc)

    def _check_idempotency(tool_name: str, idempotency_key: str) -> bool:
        if not idempotency_key:
            return False
        idempotency_index: Dict[str, List[str]] = call_metadata.get("idempotency_keys", {})
        seen_keys = idempotency_index.setdefault(tool_name, [])
        if idempotency_key in seen_keys:
            return True
        seen_keys.append(idempotency_key)
        return False

    @function_tool
    async def get_current_time(timezone: str = "local") -> str:
        """Get the current time. Pass timezone='local' or leave empty for local time."""
        return f"The current time is {datetime.datetime.now().strftime('%I:%M %p')}"

    @function_tool
    async def update_call_data(field: str, value: str) -> str:
        """Record a piece of data collected from the user and persist important fields."""
        call_metadata[field] = value
        logger.info(f"Captured data: {field} = {value}")

        # If email, persist immediately and fire webhook
        if field.lower() == "email":
            try:
                await db.update_contact_email(contact_id, value)
                await dispatcher.dispatch(
                    "contact.email.captured", {"contact_id": contact_id, "phone_number": phone_number, "email": value}
                )
            except Exception as e:
                logger.exception(f"Failed to persist or dispatch email: {e}")

        # Always dispatch a generic data.captured event
        try:
            await dispatcher.dispatch("data.captured", {"field": field, "value": value, "contact_id": contact_id})
        except Exception as e:
            logger.debug(f"data.captured webhook error: {e}")

        return f"Saved {field}."

    @function_tool
    async def add_note(note: str) -> str:
        """Add a general note about the call."""
        call_metadata["notes"].append(note)
        logger.info(f"Note added: {note}")
        await _record_tool_event("add_note", {"note": note})
        return "Noted."

    @function_tool
    async def create_appointment(
        customer_name: str,
        appointment_time: str,
        purpose: str = "",
        idempotency_key: str = "",
    ) -> str:
        """Create an appointment record with validation and audit trail.

        appointment_time must be an ISO datetime string.
        """
        if not customer_name.strip():
            return "customer_name is required."
        try:
            datetime.datetime.fromisoformat(appointment_time.replace("Z", "+00:00"))
        except ValueError:
            return "appointment_time must be ISO format, for example 2026-03-30T10:30:00+05:30"

        if _check_idempotency("create_appointment", idempotency_key):
            return "Appointment request already processed."

        payload = {
            "customer_name": customer_name.strip(),
            "appointment_time": appointment_time,
            "purpose": purpose.strip(),
        }
        appointments = call_metadata.setdefault("appointments", [])
        appointments.append(payload)
        await _record_tool_event("create_appointment", payload, idempotency_key=idempotency_key)
        try:
            await dispatcher.dispatch("appointment.created", {**payload, "contact_id": contact_id, "phone_number": phone_number})
        except Exception as exc:
            logger.debug("appointment.created webhook dispatch failed: %s", exc)
        return "Appointment created."

    @function_tool
    async def capture_lead(
        lead_name: str,
        email: str = "",
        intent: str = "",
        budget: str = "",
        idempotency_key: str = "",
    ) -> str:
        """Capture lead details for CRM or downstream qualification workflows."""
        if not lead_name.strip():
            return "lead_name is required."
        if email and "@" not in email:
            return "email must be valid."

        if _check_idempotency("capture_lead", idempotency_key):
            return "Lead capture request already processed."

        payload = {
            "lead_name": lead_name.strip(),
            "email": email.strip(),
            "intent": intent.strip(),
            "budget": budget.strip(),
        }
        call_metadata["lead"] = payload
        await _record_tool_event("capture_lead", payload, idempotency_key=idempotency_key)
        try:
            await dispatcher.dispatch("lead.captured", {**payload, "contact_id": contact_id, "phone_number": phone_number})
        except Exception as exc:
            logger.debug("lead.captured webhook dispatch failed: %s", exc)
        return "Lead captured."

    @function_tool
    async def push_crm_note(note: str, system: str = "generic-crm", idempotency_key: str = "") -> str:
        """Push a structured note to CRM-integrated webhook workflow."""
        if not note.strip():
            return "note is required."

        if _check_idempotency("push_crm_note", idempotency_key):
            return "CRM note already pushed."

        payload = {
            "note": note.strip(),
            "system": system.strip() or "generic-crm",
        }
        await _record_tool_event("push_crm_note", payload, idempotency_key=idempotency_key)
        try:
            await dispatcher.dispatch("crm.note", {**payload, "contact_id": contact_id, "phone_number": phone_number})
        except Exception as exc:
            logger.debug("crm.note webhook dispatch failed: %s", exc)
        return "CRM note pushed."

    @function_tool
    async def end_call(reason: str = "conversation_complete") -> str:
        """Terminates the call. Call this IMMEDIATELY after saying goodbye. Do not wait for the user to hang up."""
        logger.info(f"Agent requested end_call (reason={reason})")
        # Immediate hangup to prevent dead air.
        # The 'disconnected' event will trigger finalize_call() for data persistence.
        asyncio.create_task(hangup_callback())
        return ""

    tools = [
        get_current_time,
        update_call_data,
        add_note,
        create_appointment,
        capture_lead,
        push_crm_note,
        end_call,
    ]

    if ctx:
        @function_tool
        async def transfer_call(destination: str = "") -> str:
            """
            Transfer the live call to a phone number or SIP URI.

            Pass the destination phone number or SIP URI as a string.
            If destination is empty, the configured default transfer destination is used.
            Returns an error message if no destination is configured, the caller cannot be identified,
            or the LiveKit SIP transfer request fails.
            """
            transfer_target = (destination.strip() if destination else "") or default_transfer_destination
            if not transfer_target:
                return "No transfer destination is configured."

            participant_identity = _participant_identity()
            if not participant_identity:
                return "Failed to transfer: could not identify the caller."

            formatted_destination = _format_transfer_destination(transfer_target)
            logger.info(f"Transferring participant {participant_identity} to {formatted_destination}")

            try:
                await ctx.api.sip.transfer_sip_participant(
                    api.TransferSIPParticipantRequest(
                        room_name=ctx.room.name,
                        participant_identity=participant_identity,
                        transfer_to=formatted_destination,
                        play_dialtone=False,
                    )
                )
                return "Transfer initiated successfully."
            except Exception as e:
                logger.exception(f"Transfer failed: {e}")
                return f"Error executing transfer: {e}"

        tools.append(transfer_call)

    return tools
