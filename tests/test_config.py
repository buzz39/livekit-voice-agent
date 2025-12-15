import pytest
from unittest.mock import AsyncMock, MagicMock
from outbound.config import prepare_instructions, load_agent_config

@pytest.mark.asyncio
async def test_prepare_instructions_defaults():
    # Mock DB
    mock_db = AsyncMock()
    # Mock get_active_prompt to return None (trigger default)
    mock_db.get_active_prompt.return_value = None

    instructions = await prepare_instructions(mock_db, "test_agent", [])

    assert "You are a professional caller." in instructions
    assert "IMPORTANT BEHAVIORAL INSTRUCTIONS" in instructions

@pytest.mark.asyncio
async def test_prepare_instructions_with_schema():
    mock_db = AsyncMock()
    mock_db.get_active_prompt.return_value = "Custom prompt."

    schema_fields = [
        {"field_name": "email", "description": "User email address"}
    ]

    instructions = await prepare_instructions(mock_db, "test_agent", schema_fields)

    assert "Custom prompt." in instructions
    assert "email: User email address" in instructions
    assert "update_call_data" in instructions
    assert "IMPORTANT BEHAVIORAL INSTRUCTIONS" in instructions

@pytest.mark.asyncio
async def test_load_agent_config_fallback():
    mock_db = AsyncMock()
    mock_db.get_agent_config.side_effect = [None, {"name": "Default Agent"}]
    mock_db.get_data_schema.return_value = []
    mock_db.get_webhooks.return_value = []

    config, schema, dispatcher, slug = await load_agent_config(mock_db, "unknown_agent")

    assert slug == "default_roofing_agent"
    assert config["name"] == "Default Agent"
