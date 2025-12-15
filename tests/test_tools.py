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
