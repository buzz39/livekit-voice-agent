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

    @function_tool
    async def get_current_time() -> str:
        """Get the current time."""
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

        return ""

    @function_tool
    async def add_note(note: str) -> str:
        """Add a general note about the call."""
        call_metadata["notes"].append(note)
        logger.info(f"Note added: {note}")
        return ""

    @function_tool
    async def end_call() -> str:
        """Terminates the call. Call this IMMEDIATELY after saying goodbye. Do not wait for the user to hang up."""
        logger.info("Agent requested end_call")
        # Immediate hangup to prevent dead air.
        # The 'disconnected' event will trigger finalize_call() for data persistence.
        asyncio.create_task(hangup_callback())
        return ""

    tools = [get_current_time, update_call_data, add_note, end_call]

    if ctx:
        @function_tool
        async def lookup_user(phone: str) -> str:
            """
            Return current-call business details when the provided phone matches the active caller.

            If the phone does not match the current call, returns a simple "not found" message.
            """
            if _normalize_phone_number(phone) == normalized_phone_number:
                business_name = call_metadata.get("business_name") or "Unknown business"
                return f"User found for {phone}: business={business_name}, contact_id={contact_id}."
            return f"No stored details found for {phone}."

        @function_tool
        async def transfer_call(destination: Optional[str] = None) -> str:
            """
            Transfer the live call to a phone number or SIP URI.

            If destination is omitted, the configured default transfer destination is used.
            Returns an error message if no destination is configured, the caller cannot be identified,
            or the LiveKit SIP transfer request fails.
            """
            transfer_target = destination or default_transfer_destination
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

        tools.extend([lookup_user, transfer_call])

    return tools
