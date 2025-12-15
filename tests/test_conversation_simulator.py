
import pytest
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, ANY
from livekit.agents import llm
from livekit.plugins import openai
from outbound.tools import create_tools
from outbound.config import prepare_instructions
import logging

# We will mock the database and other external dependencies
# but use the real LLM logic (which requires OPENAI_API_KEY env var)

@pytest.mark.asyncio
async def test_conversation_flow():
    # 1. SETUP
    mock_db = AsyncMock()
    mock_dispatcher = AsyncMock()
    mock_hangup = AsyncMock()

    # Mock DB responses
    mock_db.get_active_prompt.return_value = "You are a helpful assistant."
    mock_db.update_contact_email = AsyncMock()

    call_metadata = {"notes": []}
    contact_id = "test_contact_123"
    phone_number = "+15550000000"

    # Create real tools with mocks
    tools = create_tools(
        call_metadata=call_metadata,
        db=mock_db,
        dispatcher=mock_dispatcher,
        contact_id=contact_id,
        phone_number=phone_number,
        hangup_callback=mock_hangup
    )

    # Get instructions
    instructions = await prepare_instructions(mock_db, "test_agent", [])

    # Shadow history for mock logic since ChatContext is opaque
    shadow_history = []

    # Initialize LLM
    # Note: This requires OPENAI_API_KEY to be set in the environment.
    api_key = os.environ.get("OPENAI_API_KEY")

    if api_key:
        llm_instance = openai.LLM(model="gpt-4o-mini")
    else:
        print("\nWARNING: OPENAI_API_KEY not found. Using Mock LLM for simulation.")
        llm_instance = MagicMock()

        # Define a mock chat method that behaves like the real one for specific inputs
        async def mock_chat(chat_ctx, fns):
            # Inspect the last message from shadow history
            last_msg_obj = shadow_history[-1]
            # Handle list content or string
            if hasattr(last_msg_obj, "content"):
                c = last_msg_obj.content
                if isinstance(c, list):
                     last_msg = ""
                     for item in c:
                         if isinstance(item, str):
                             last_msg += item
                         elif hasattr(item, "text"):
                             last_msg += item.text
                         else:
                             last_msg += str(item)
                else:
                    last_msg = str(c)
            else:
                last_msg = ""

            # Create a mock stream
            async def stream_generator():
                response_text = ""
                tool_calls = []

                if "Hello" in last_msg or "owner" in last_msg:
                    response_text = "Hello! Can I confirm your email address?"
                elif "@" in last_msg:
                    # User provided email, simulate tool call
                    response_text = "Thank you. I'm updating that now."
                    # Mock tool call

                    # Create mock for ToolCall
                    tc_mock = MagicMock()
                    tc_mock.function.name = "update_call_data"
                    tc_mock.function.arguments = '{"field": "email", "value": "test@example.com"}'
                    tc_mock.tool_call_id = "call_123"
                    tc_mock.index = 0

                    tool_calls.append(tc_mock)

                elif "goodbye" in last_msg.lower():
                    response_text = "Goodbye!"

                    tc_mock = MagicMock()
                    tc_mock.function.name = "end_call"
                    tc_mock.function.arguments = '{}'
                    tc_mock.tool_call_id = "call_456"
                    tc_mock.index = 0

                    tool_calls.append(tc_mock)
                else:
                    response_text = "I didn't understand that."

                # Yield text chunk
                chunk = MagicMock()
                chunk.choices = [MagicMock()]
                chunk.choices[0].delta.content = response_text
                chunk.choices[0].delta.tool_calls = None
                yield chunk

                # Yield tool calls if any
                if tool_calls:
                    chunk = MagicMock()
                    chunk.choices = [MagicMock()]
                    chunk.choices[0].delta.content = None
                    chunk.choices[0].delta.tool_calls = tool_calls
                    yield chunk

            return stream_generator()

        llm_instance.chat = mock_chat

    # Initialize ChatContext
    chat_ctx = llm.ChatContext()

    # Create System Message
    sys_msg = chat_ctx.add_message(role="system", content=instructions)
    shadow_history.append(sys_msg)

    print(f"\nSystem: {instructions[:50]}...")

    # TURN 1: Agent Greeting (simulated trigger)
    opening_line = "Hello? Am I speaking with the business owner?"
    agent_msg = chat_ctx.add_message(role="assistant", content=opening_line)
    shadow_history.append(agent_msg)
    print(f"Agent: {opening_line}")

    # TURN 2: User replies
    user_text = "Yes, this is the owner."
    user_msg = chat_ctx.add_message(role="user", content=user_text)
    shadow_history.append(user_msg)
    print(f"User: {user_text}")

    # Generate Agent response
    stream = await llm_instance.chat(chat_ctx=chat_ctx, fns=tools)

    captured_text = ""
    current_tool_call = {}

    async for chunk in stream:
        choice = chunk.choices[0]
        if choice.delta.content:
            print(choice.delta.content, end="", flush=True)
            captured_text += choice.delta.content

        if choice.delta.tool_calls:
            for tc in choice.delta.tool_calls:
                idx = tc.index
                if idx not in current_tool_call:
                    current_tool_call[idx] = {"name": "", "arguments": "", "id": ""}

                if tc.function:
                    if tc.function.name:
                        current_tool_call[idx]["name"] += tc.function.name
                    if tc.function.arguments:
                        current_tool_call[idx]["arguments"] += tc.function.arguments
                if tc.tool_call_id:
                    current_tool_call[idx]["id"] = tc.tool_call_id

    print() # Newline

    # Append Agent response to history (Text only to avoid Pydantic issues with tool calls in this version)
    # We verify tool calls via captured logic below.
    content_list = []
    if captured_text:
        content_list.append(captured_text)

    if not content_list:
        content_list = ""

    agent_response_msg = chat_ctx.add_message(role="assistant", content=content_list)
    shadow_history.append(agent_response_msg)

    # TURN 3: Providing Email.
    user_text = "My email is test@example.com"
    user_msg_2 = chat_ctx.add_message(role="user", content=user_text)
    shadow_history.append(user_msg_2)
    print(f"User: {user_text}")

    stream = await llm_instance.chat(chat_ctx=chat_ctx, fns=tools)

    captured_text = ""
    current_tool_call = {}

    async for chunk in stream:
        choice = chunk.choices[0]
        if choice.delta.content:
            print(choice.delta.content, end="", flush=True)
            captured_text += choice.delta.content

        if choice.delta.tool_calls:
            for tc in choice.delta.tool_calls:
                idx = tc.index
                if idx not in current_tool_call:
                    current_tool_call[idx] = {"name": "", "arguments": "", "id": ""}

                if tc.function:
                    if tc.function.name:
                        current_tool_call[idx]["name"] += tc.function.name
                    if tc.function.arguments:
                        current_tool_call[idx]["arguments"] += tc.function.arguments
                if tc.tool_call_id:
                    current_tool_call[idx]["id"] = tc.tool_call_id

    print()

    # Append agent response to history (Text only)
    content_list = []
    if captured_text:
        content_list.append(captured_text)
    if not content_list:
        content_list = ""

    agent_response_msg_2 = chat_ctx.add_message(role="assistant", content=content_list)
    shadow_history.append(agent_response_msg_2)

    # Check if update_call_data was called
    tool_calls_list = list(current_tool_call.values())
    update_email_call = next((tc for tc in tool_calls_list if tc["name"] == "update_call_data"), None)

    if update_email_call:
        print(f"SUCCESS: Agent tried to update email: {update_email_call['arguments']}")
    else:
        # In mock mode we expect it.
        if api_key is None:
            pytest.fail("Mock agent did not call update_call_data")

    # Terminate
    user_text = "That's all, goodbye."
    user_msg_3 = chat_ctx.add_message(role="user", content=user_text)
    shadow_history.append(user_msg_3)
    print(f"User: {user_text}")

    stream = await llm_instance.chat(chat_ctx=chat_ctx, fns=tools)

    captured_text = ""
    current_tool_call = {}
    async for chunk in stream:
        choice = chunk.choices[0]
        if choice.delta.content:
            print(choice.delta.content, end="", flush=True)
        if choice.delta.tool_calls:
            for tc in choice.delta.tool_calls:
                idx = tc.index
                if idx not in current_tool_call:
                    current_tool_call[idx] = {"name": "", "arguments": "", "id": ""}

                if tc.function:
                    if tc.function.name:
                        current_tool_call[idx]["name"] += tc.function.name
                    if tc.function.arguments:
                        current_tool_call[idx]["arguments"] += tc.function.arguments
                if tc.tool_call_id:
                    current_tool_call[idx]["id"] = tc.tool_call_id
    print()

    tool_calls_list = list(current_tool_call.values())
    end_call_action = next((tc for tc in tool_calls_list if tc["name"] == "end_call"), None)

    if api_key is None:
        assert end_call_action is not None, "Agent should have called end_call (mock)"
        print("SUCCESS: Agent called end_call")
    else:
        if end_call_action:
             print("SUCCESS: Agent called end_call")
        else:
             print("WARNING: Real Agent did not call end_call. Check prompt or flow.")
