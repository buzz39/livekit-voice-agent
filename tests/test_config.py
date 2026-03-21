import pytest
from unittest.mock import AsyncMock, MagicMock
from outbound.config import prepare_instructions, load_agent_config, load_ai_config

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


@pytest.mark.asyncio
async def test_load_ai_config_uses_agent_slug_then_default():
    """load_ai_config should try the agent-specific config first, then default."""
    mock_db = AsyncMock()
    mock_db.get_ai_config.side_effect = [None, {"llm_provider": "openai"}]

    ai_config = await load_ai_config(mock_db, "my_agent")

    # First call with agent slug, second call with default
    assert mock_db.get_ai_config.call_count == 2
    calls = mock_db.get_ai_config.call_args_list
    assert calls[0].args[0] == "my_agent"
    assert calls[1].args[0] == "default_telephony_config"
    assert ai_config["llm_provider"] == "openai"


@pytest.mark.asyncio
async def test_load_ai_config_hardcoded_fallback():
    """When DB returns no config at all, hardcoded defaults are used."""
    mock_db = AsyncMock()
    mock_db.get_ai_config.return_value = None

    ai_config = await load_ai_config(mock_db, "missing_agent")

    assert ai_config["llm_provider"] == "openai"
    assert ai_config["stt_provider"] == "deepgram"
    assert ai_config["tts_provider"] == "openai"


class TestSingleSourceOfTruth:
    """Verify that both agents use the shared config module (no UI override)."""

    def _telephony_source(self) -> str:
        import pathlib
        return (
            pathlib.Path(__file__).resolve().parent.parent / "telephony_agent.py"
        ).read_text()

    def _outbound_source(self) -> str:
        import pathlib
        return (
            pathlib.Path(__file__).resolve().parent.parent / "outbound_agent.py"
        ).read_text()

    def test_telephony_imports_shared_load_agent_config(self):
        src = self._telephony_source()
        assert "from outbound.config import load_agent_config" in src

    def test_telephony_imports_shared_prepare_instructions(self):
        src = self._telephony_source()
        assert "prepare_instructions" in src

    def test_telephony_imports_shared_load_ai_config(self):
        src = self._telephony_source()
        assert "load_ai_config" in src

    def test_telephony_no_ui_config_override(self):
        """telephony_agent must NOT fetch config from the in-memory server."""
        src = self._telephony_source()
        assert "ui_config" not in src

    def test_telephony_no_httpx_fetch(self):
        """telephony_agent must NOT make HTTP calls for config."""
        src = self._telephony_source()
        assert "httpx" not in src
        assert "/api/config" not in src

    def test_telephony_no_system_prompt_override(self):
        """telephony_agent must NOT override the DB prompt with a runtime one."""
        src = self._telephony_source()
        # The specific pattern we eliminated: fetching system_prompt from an
        # external config and overriding the DB-provided instructions.
        assert 'ui_config["system_prompt"]' not in src
        assert "system_prompt" not in src

    def test_outbound_uses_same_shared_config(self):
        src = self._outbound_source()
        assert "from outbound.config import" in src
        assert "load_agent_config" in src
        assert "prepare_instructions" in src
        assert "load_ai_config" in src

    def test_server_no_in_memory_config(self):
        """server.py must NOT have an in-memory _active_agent_config."""
        import pathlib
        src = (
            pathlib.Path(__file__).resolve().parent.parent / "server.py"
        ).read_text()
        assert "_active_agent_config" not in src
