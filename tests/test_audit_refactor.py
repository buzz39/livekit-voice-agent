"""
Tests for the LiveKit documentation audit refactoring.

Verifies:
- telephony_agent imports shared provider builders instead of duplicating logic
- Removed dead code (sarvam_tts, deepgram_tts, groq_llm_chat) is actually gone
- Noise cancellation (BVCTelephony) is importable and available
- STT-based turn detection is correctly configured
- Dependency bounds allow latest SDK features
"""

import ast
import importlib

import pytest


class TestDeadCodeRemoval:
    """Ensure unused functions were removed from telephony_agent."""

    def _telephony_source(self) -> str:
        import pathlib

        return (
            pathlib.Path(__file__).resolve().parent.parent / "telephony_agent.py"
        ).read_text()

    def _telephony_function_names(self) -> set:
        tree = ast.parse(self._telephony_source())
        return {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

    def test_sarvam_tts_removed(self):
        assert "sarvam_tts" not in self._telephony_function_names()

    def test_deepgram_tts_removed(self):
        assert "deepgram_tts" not in self._telephony_function_names()

    def test_groq_llm_chat_removed(self):
        assert "groq_llm_chat" not in self._telephony_function_names()

    def test_no_agent_instructions_global(self):
        src = self._telephony_source()
        assert "AGENT_INSTRUCTIONS = None" not in src

    def test_no_generate_speech_override(self):
        src = self._telephony_source()
        assert "_generate_speech" not in src

    def test_no_sarvam_api_url_constant(self):
        src = self._telephony_source()
        assert "SARVAM_API_URL" not in src

    def test_no_deepgram_tts_url_constant(self):
        src = self._telephony_source()
        assert "DEEPGRAM_TTS_URL" not in src


class TestSharedProviderReuse:
    """Telephony agent must use outbound.providers instead of inline logic."""

    def _telephony_source(self) -> str:
        import pathlib

        return (
            pathlib.Path(__file__).resolve().parent.parent / "telephony_agent.py"
        ).read_text()

    def test_imports_build_llm(self):
        src = self._telephony_source()
        assert "build_llm" in src

    def test_imports_build_stt(self):
        src = self._telephony_source()
        assert "build_stt" in src

    def test_imports_build_tts(self):
        src = self._telephony_source()
        assert "build_tts" in src

    def test_imports_resolve_ai_configuration(self):
        src = self._telephony_source()
        assert "resolve_ai_configuration" in src

    def test_no_inline_groq_api_url(self):
        """Should not hardcode GROQ_API_URL anymore."""
        src = self._telephony_source()
        assert "GROQ_API_URL" not in src

    def test_no_inline_silero_vad_load(self):
        """Should use STT-based turn detection, not Silero VAD."""
        src = self._telephony_source()
        assert "silero.VAD.load()" not in src


class TestNoiseCancellationIntegration:
    """Verify telephony-optimized noise cancellation is wired up."""

    def test_bvc_telephony_importable(self):
        from livekit.plugins import noise_cancellation

        assert hasattr(noise_cancellation, "BVCTelephony")

    def test_telephony_agent_uses_bvc_telephony(self):
        import pathlib

        src = (
            pathlib.Path(__file__).resolve().parent.parent / "telephony_agent.py"
        ).read_text()
        assert "BVCTelephony" in src

    def test_outbound_agent_uses_bvc_telephony(self):
        import pathlib

        src = (
            pathlib.Path(__file__).resolve().parent.parent / "outbound_agent.py"
        ).read_text()
        assert "BVCTelephony" in src


class TestTurnDetection:
    """Both agents should use STT-based turn detection."""

    def _source(self, filename: str) -> str:
        import pathlib

        return (
            pathlib.Path(__file__).resolve().parent.parent / filename
        ).read_text()

    def test_outbound_agent_stt_turn_detection(self):
        src = self._source("outbound_agent.py")
        assert 'turn_detection="stt"' in src

    def test_telephony_agent_stt_turn_detection(self):
        src = self._source("telephony_agent.py")
        assert 'turn_detection="stt"' in src


class TestDependencyBounds:
    """Dependency bounds in pyproject.toml should allow latest SDK features."""

    def _pyproject_source(self) -> str:
        import pathlib

        return (
            pathlib.Path(__file__).resolve().parent.parent / "pyproject.toml"
        ).read_text()

    def test_agents_upper_bound_at_least_1_6(self):
        src = self._pyproject_source()
        # Should NOT contain the old <1.3 cap
        assert "<1.3" not in src
        # Should contain a bound of <1.6 or higher
        assert "<1.6" in src

    def test_livekit_sdk_upper_bound_relaxed(self):
        src = self._pyproject_source()
        # Should NOT contain the old <1.1 cap
        assert "livekit>=1.0.20,<1.1" not in src


class TestOutboundAgentCleanup:
    """Outbound agent should not import unused groq library."""

    def _outbound_source(self) -> str:
        import pathlib

        return (
            pathlib.Path(__file__).resolve().parent.parent / "outbound_agent.py"
        ).read_text()

    def test_no_groq_import(self):
        src = self._outbound_source()
        assert "import groq" not in src
