import pytest
from unittest.mock import AsyncMock, MagicMock
from livekit.agents import Agent, AgentSession
from outbound.tools import create_tools

@pytest.mark.asyncio
async def test_agent_instantiation():
    """
    Test that we can instantiate an Agent and AgentSession with our tools and instructions.
    This doesn't run the full conversation loop (which requires LLM keys),
    but verifies the wiring.
    """
    # Setup mocks
    mock_db = AsyncMock()
    mock_dispatcher = AsyncMock()
    mock_hangup = AsyncMock()

    call_metadata = {"notes": []}
    contact_id = "test_contact"
    phone_number = "+15551234567"

    tools = create_tools(
        call_metadata,
        mock_db,
        mock_dispatcher,
        contact_id,
        phone_number,
        mock_hangup
    )

    instructions = "You are a test agent."

    agent = Agent(instructions=instructions, tools=tools)

    # Mock LLM and other components for Session
    mock_llm = MagicMock()
    mock_stt = MagicMock()
    mock_vad = MagicMock()
    mock_tts = MagicMock()

    session = AgentSession(
        vad=mock_vad,
        stt=mock_stt,
        llm=mock_llm,
        tts=mock_tts
    )

    # Just verify we can start the session (even if we don't await run)
    # Note: session.start is an async method

    # We can't easily assert on internal state of C++ wrapped objects often found in livekit,
    # but ensuring no exception is raised during instantiation is a good start.
    assert agent.instructions == instructions
    assert len(agent.tools) == 4
    assert session is not None

# If we had a mock LLM that followed the protocol, we could do:
# @pytest.mark.asyncio
# async def test_agent_conversation():
#     ...
