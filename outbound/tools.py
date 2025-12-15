import datetime
import logging
import asyncio
from livekit.agents.llm import function_tool
from typing import Callable, List, Dict, Any

logger = logging.getLogger("outbound.tools")

def create_tools(
    call_metadata: Dict[str, Any],
    db: Any,
    dispatcher: Any,
    contact_id: str,
    phone_number: str,
    hangup_callback: Callable[[], Any]
) -> List[Callable]:
    """
    Creates and returns a list of function tools for the agent.

    Args:
        call_metadata: Mutable dictionary to store call metadata.
        db: Database interface.
        dispatcher: WebhookDispatcher instance.
        contact_id: The database ID of the contact.
        phone_number: The phone number of the contact.
        hangup_callback: Async function to trigger hangup/finalization.
    """

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
        """End the call safely and immediately."""
        logger.info("Agent requested end_call")
        # Immediate hangup to prevent dead air.
        # The 'disconnected' event will trigger finalize_call() for data persistence.
        asyncio.create_task(hangup_callback())
        return ""

    return [get_current_time, update_call_data, add_note, end_call]
