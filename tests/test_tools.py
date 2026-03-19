import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from outbound.tools import create_tools

@pytest.mark.asyncio
async def test_tools_update_call_data():
    call_metadata = {"notes": []}
    mock_db = AsyncMock()
    mock_dispatcher = AsyncMock()
    mock_hangup = AsyncMock()
    contact_id = "contact_123"
    phone_number = "+15550000000"

    tools = create_tools(
        call_metadata,
        mock_db,
        mock_dispatcher,
        contact_id,
        phone_number,
        mock_hangup
    )

    # Find update_call_data tool
    update_tool = next(t for t in tools if t.__name__ == "update_call_data")

    # Test updating generic field
    await update_tool(field="name", value="John Doe")
    assert call_metadata["name"] == "John Doe"
    mock_dispatcher.dispatch.assert_called_with(
        "data.captured",
        {"field": "name", "value": "John Doe", "contact_id": contact_id}
    )

@pytest.mark.asyncio
async def test_tools_update_email():
    call_metadata = {"notes": []}
    mock_db = AsyncMock()
    mock_dispatcher = AsyncMock()
    mock_hangup = AsyncMock()
    contact_id = "contact_123"
    phone_number = "+15550000000"

    tools = create_tools(
        call_metadata,
        mock_db,
        mock_dispatcher,
        contact_id,
        phone_number,
        mock_hangup
    )

    update_tool = next(t for t in tools if t.__name__ == "update_call_data")

    # Test updating email (should trigger specific logic)
    await update_tool(field="email", value="test@example.com")

    assert call_metadata["email"] == "test@example.com"
    mock_db.update_contact_email.assert_called_with(contact_id, "test@example.com")

    # Verify both webhooks were called
    calls = mock_dispatcher.dispatch.call_args_list
    assert any(c[0][0] == "contact.email.captured" for c in calls)
    assert any(c[0][0] == "data.captured" for c in calls)

@pytest.mark.asyncio
async def test_tools_end_call():
    call_metadata = {"notes": []}
    mock_db = AsyncMock()
    mock_dispatcher = AsyncMock()
    mock_hangup = AsyncMock()
    contact_id = "contact_123"
    phone_number = "+15550000000"

    tools = create_tools(
        call_metadata,
        mock_db,
        mock_dispatcher,
        contact_id,
        phone_number,
        mock_hangup
    )

    end_call_tool = next(t for t in tools if t.__name__ == "end_call")

    await end_call_tool()

    # Verify hangup callback was scheduled/called
    # Since it uses asyncio.create_task, we might need to yield to let it run
    # But checking if called is tricky if it is just a task creation.
    # However, create_tools just calls asyncio.create_task(hangup_callback())
    # mocking hangup_callback to be an async func should work.

    # In the code: asyncio.create_task(hangup_callback())
    # Since we can't easily await the task created inside the function without returning it,
    # we might just verify that the function didn't crash.
    # But usually creating a task on a mock might not register as 'awaited'.
    # We can check if the mock was called if it was passed directly.

    # Wait a bit for the task to start
    import asyncio
    await asyncio.sleep(0.01)

    mock_hangup.assert_called_once()

@pytest.mark.asyncio
async def test_transfer_call_formats_plain_number_with_sip_domain():
    call_metadata = {"notes": []}
    mock_db = AsyncMock()
    mock_dispatcher = AsyncMock()
    mock_hangup = AsyncMock()
    mock_ctx = MagicMock()
    mock_ctx.room.name = "room-123"
    mock_ctx.room.remote_participants = {}
    mock_ctx.api.sip.transfer_sip_participant = AsyncMock()

    tools = create_tools(
        call_metadata,
        mock_db,
        mock_dispatcher,
        "contact_123",
        "+15550000000",
        mock_hangup,
        ctx=mock_ctx,
        sip_domain="demo.sip.test",
    )

    transfer_call_tool = next((t for t in tools if t.__name__ == "transfer_call"), None)
    assert transfer_call_tool is not None

    result = await transfer_call_tool(destination="+15551112222")

    assert result == "Transfer initiated successfully."
    request = mock_ctx.api.sip.transfer_sip_participant.await_args.args[0]
    assert request.room_name == "room-123"
    assert request.participant_identity == "15550000000"
    assert request.transfer_to == "sip:+15551112222@demo.sip.test"

@pytest.mark.asyncio
async def test_transfer_call_uses_default_tel_destination_without_sip_domain():
    call_metadata = {"notes": []}
    mock_db = AsyncMock()
    mock_dispatcher = AsyncMock()
    mock_hangup = AsyncMock()
    mock_ctx = MagicMock()
    mock_ctx.room.name = "room-456"
    mock_ctx.room.remote_participants = {}
    mock_ctx.api.sip.transfer_sip_participant = AsyncMock()

    tools = create_tools(
        call_metadata,
        mock_db,
        mock_dispatcher,
        "contact_123",
        "+15550000000",
        mock_hangup,
        ctx=mock_ctx,
        default_transfer_destination="+15553334444",
    )

    transfer_call_tool = next((t for t in tools if t.__name__ == "transfer_call"), None)
    assert transfer_call_tool is not None

    result = await transfer_call_tool()

    assert result == "Transfer initiated successfully."
    request = mock_ctx.api.sip.transfer_sip_participant.await_args.args[0]
    sip_domain = os.getenv("SIP_DOMAIN") or os.getenv("VOBIZ_SIP_DOMAIN")
    if sip_domain:
        assert request.transfer_to == f"sip:+15553334444@{sip_domain}"
    else:
        assert request.transfer_to == "tel:+15553334444"
