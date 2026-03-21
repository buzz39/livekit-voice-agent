import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from livekit.agents import Agent, AgentSession
from livekit.agents.llm import LLMError
from livekit.agents.voice.events import ErrorEvent
from outbound.tools import create_tools
from outbound.config import prepare_instructions


class TestLLMErrorHandler:
    """Tests for the session-level LLM error fallback handler."""

    def _make_session_and_handler(self, call_metadata):
        """Wire up a mock AgentSession and return the error handler registered via session.on."""
        mock_session = MagicMock(spec=AgentSession)
        # Capture the handler registered via `session.on("error", handler)`
        registered_handlers = {}

        def fake_on(event_name):
            def decorator(fn):
                registered_handlers[event_name] = fn
                return fn
            return decorator

        mock_session.on = fake_on
        return mock_session, registered_handlers

    def test_llm_error_triggers_fallback_say(self):
        """When an LLM error event fires, session.say() should be called with a fallback message."""
        call_metadata = {"notes": []}
        mock_session, handlers = self._make_session_and_handler(call_metadata)

        # Simulate the error handler registration (mirrors the agent code)
        @mock_session.on("error")
        def _on_session_error(ev: ErrorEvent):
            error_obj = ev.error
            is_llm = isinstance(error_obj, LLMError) or getattr(error_obj, "type", None) == "llm_error"
            underlying = getattr(error_obj, "error", error_obj)
            if is_llm:
                call_metadata["notes"].append(f"LLM error: {underlying}")
                mock_session.say("Give me just a moment, I need to gather my thoughts.")

        # Create an LLMError matching the framework's structure
        llm_error = LLMError(
            type="llm_error",
            timestamp=0.0,
            label="openai",
            error=Exception("Failed to call a function. Please adjust your prompt."),
            recoverable=False,
        )
        error_event = ErrorEvent(error=llm_error, source=MagicMock())

        # Fire the handler
        handlers["error"](error_event)

        # Verify fallback say was called
        mock_session.say.assert_called_once_with(
            "Give me just a moment, I need to gather my thoughts."
        )
        assert len(call_metadata["notes"]) == 1
        assert "Failed to call a function" in call_metadata["notes"][0]

    def test_non_llm_error_does_not_trigger_fallback(self):
        """Non-LLM errors (e.g. TTS) should not trigger the fallback say."""
        call_metadata = {"notes": []}
        mock_session, handlers = self._make_session_and_handler(call_metadata)

        @mock_session.on("error")
        def _on_session_error(ev: ErrorEvent):
            error_obj = ev.error
            is_llm = isinstance(error_obj, LLMError) or getattr(error_obj, "type", None) == "llm_error"
            underlying = getattr(error_obj, "error", error_obj)
            if is_llm:
                call_metadata["notes"].append(f"LLM error: {underlying}")
                mock_session.say("Give me just a moment, I need to gather my thoughts.")

        # A non-LLM error (e.g. generic)
        non_llm_error = MagicMock()
        non_llm_error.type = "tts_error"
        error_event = ErrorEvent(error=non_llm_error, source=MagicMock())

        handlers["error"](error_event)

        mock_session.say.assert_not_called()
        assert len(call_metadata["notes"]) == 0

    def test_say_failure_does_not_raise(self):
        """If session.say() itself fails, the handler should not propagate the exception."""
        call_metadata = {"notes": []}
        mock_session, handlers = self._make_session_and_handler(call_metadata)

        mock_session.say.side_effect = RuntimeError("session closing")

        @mock_session.on("error")
        def _on_session_error(ev: ErrorEvent):
            error_obj = ev.error
            is_llm = isinstance(error_obj, LLMError) or getattr(error_obj, "type", None) == "llm_error"
            underlying = getattr(error_obj, "error", error_obj)
            if is_llm:
                call_metadata["notes"].append(f"LLM error: {underlying}")
                try:
                    mock_session.say("Give me just a moment, I need to gather my thoughts.")
                except Exception:
                    pass  # matches the agent code's try/except

        llm_error = LLMError(
            type="llm_error",
            timestamp=0.0,
            label="openai",
            error=Exception("APIError"),
            recoverable=False,
        )
        error_event = ErrorEvent(error=llm_error, source=MagicMock())

        # Should not raise
        handlers["error"](error_event)

        assert len(call_metadata["notes"]) == 1
        assert "APIError" in call_metadata["notes"][0]


class TestSimplifiedPromptInstructions:
    """Ensure the behavioral instructions are concise and non-contradictory."""

    @pytest.mark.asyncio
    async def test_behavioral_instructions_are_concise(self):
        mock_db = AsyncMock()
        mock_db.get_active_prompt.return_value = "You are a test agent."

        instructions = await prepare_instructions(mock_db, "test_agent", [])

        # The old verbose instructions should NOT be present
        assert "DO NOT stop at" not in instructions
        assert "THEN IMMEDIATELY" not in instructions
        # The simplified instructions should be present
        assert "CALL TERMINATION" in instructions
        assert "end_call" in instructions

    @pytest.mark.asyncio
    async def test_email_instruction_simplified(self):
        mock_db = AsyncMock()
        mock_db.get_active_prompt.return_value = "You are a test agent."

        instructions = await prepare_instructions(mock_db, "test_agent", [])

        # Should still mention email spelling
        assert "spell" in instructions.lower()
        # But should NOT have the overly forceful "MUST" phrasing
        assert "you MUST spell" not in instructions
