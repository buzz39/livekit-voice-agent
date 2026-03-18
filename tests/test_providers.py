from unittest.mock import patch

import pytest

from outbound.providers import (
    build_custom_tts_generator,
    build_llm,
    build_stt,
    build_tts,
    get_missing_provider_env_vars,
    resolve_ai_configuration,
)


def test_build_llm_uses_metadata_override_for_groq():
    ai_config = {"llm_provider": "openai", "llm_model": "gpt-4o-mini", "llm_temperature": 0.4}
    metadata = {"llm_provider": "groq", "llm_model": "llama-3.3-70b-versatile", "llm_temperature": 0.9}
    llm_instance = object()

    with patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}, clear=False):
        with patch("outbound.providers.openai.LLM", return_value=llm_instance) as mock_llm:
            llm = build_llm(ai_config=ai_config, metadata_overrides=metadata)

    assert llm is llm_instance
    mock_llm.assert_called_once()
    kwargs = mock_llm.call_args.kwargs
    assert kwargs["model"] == "llama-3.3-70b-versatile"
    assert kwargs["temperature"] == 0.9
    assert kwargs["base_url"] == "https://api.groq.com/openai/v1"
    assert kwargs["api_key"] == "test-key"


def test_build_stt_uses_metadata_override_values():
    ai_config = {"stt_model": "nova-3", "stt_language": "en-US"}
    metadata = {"stt_model": "nova-2", "stt_language": "hi"}
    stt_instance = object()

    with patch("outbound.providers.deepgram.STT", return_value=stt_instance) as mock_stt:
        stt = build_stt(ai_config=ai_config, metadata_overrides=metadata)

    assert stt is stt_instance
    mock_stt.assert_called_once_with(model="nova-2", language="hi")


def test_build_tts_supports_cartesia_with_voice_override():
    ai_config = {"tts_provider": "cartesia", "tts_model": "sonic-2", "tts_voice": "db-voice"}
    metadata = {"voice_id": "room-voice"}
    tts_instance = object()

    with patch("outbound.providers.cartesia.TTS", return_value=tts_instance) as mock_tts:
        tts = build_tts(ai_config=ai_config, metadata_overrides=metadata)

    assert tts is tts_instance
    mock_tts.assert_called_once_with(model="sonic-2", voice="room-voice")


def test_resolve_ai_configuration_reports_effective_pipeline():
    ai_config = {
        "llm_provider": "openai",
        "llm_model": "gpt-4o-mini",
        "llm_temperature": 0.4,
        "stt_model": "nova-3",
        "stt_language": "en-US",
        "tts_provider": "cartesia",
        "tts_model": "sonic-2",
        "tts_voice": "db-voice",
    }
    metadata = {"llm_provider": "groq", "llm_model": "llama-3.3-70b-versatile", "voice_id": "room-voice"}

    with patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}, clear=False):
        resolved = resolve_ai_configuration(ai_config=ai_config, metadata_overrides=metadata)

    assert resolved == {
        "llm_provider": "groq",
        "llm_model": "llama-3.3-70b-versatile",
        "llm_temperature": 0.4,
        "stt_provider": "deepgram",
        "stt_model": "nova-3",
        "stt_language": "en-US",
        "tts_provider": "cartesia",
        "tts_model": "sonic-2",
        "tts_voice": "room-voice",
    }


def test_get_missing_provider_env_vars_lists_selected_provider_keys():
    ai_config = {
        "llm_provider": "groq",
        "stt_model": "nova-3",
        "stt_language": "en-US",
        "tts_provider": "cartesia",
    }

    with patch.dict("os.environ", {}, clear=True):
        missing = get_missing_provider_env_vars(ai_config=ai_config)

    assert missing == ["CARTESIA_API_KEY", "DEEPGRAM_API_KEY", "GROQ_API_KEY"]


def test_get_missing_provider_env_vars_uses_available_credentials():
    ai_config = {"llm_provider": "openai", "tts_provider": "deepgram"}

    with patch.dict(
        "os.environ",
        {"OPENAI_API_KEY": "test-openai", "DEEPGRAM_API_KEY": "test-deepgram"},
        clear=True,
    ):
        missing = get_missing_provider_env_vars(ai_config=ai_config)

    assert missing == []


def test_resolve_ai_configuration_preserves_sarvam_provider():
    ai_config = {"tts_provider": "sarvam"}

    resolved = resolve_ai_configuration(ai_config=ai_config)

    assert resolved["tts_provider"] == "sarvam"
    assert resolved["tts_model"] == "sarvam"
    assert resolved["tts_voice"] == "saarika:v2.5"


def test_get_missing_provider_env_vars_includes_sarvam_key():
    ai_config = {"tts_provider": "sarvam"}

    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-openai", "DEEPGRAM_API_KEY": "test-deepgram"}, clear=True):
        missing = get_missing_provider_env_vars(ai_config=ai_config)

    assert missing == ["SARVAM_API_KEY"]


def test_build_tts_uses_placeholder_for_sarvam():
    ai_config = {"tts_provider": "sarvam", "tts_voice": "meera"}
    tts_instance = object()

    with patch("outbound.providers.openai.TTS", return_value=tts_instance) as mock_tts:
        tts = build_tts(ai_config=ai_config)

    assert tts is tts_instance
    mock_tts.assert_called_once_with(model="tts-1", voice="alloy")


@pytest.mark.asyncio
async def test_build_custom_tts_generator_uses_sarvam_voice():
    ai_config = {"tts_provider": "sarvam", "tts_voice": "meera"}
    audio = b"pcm"

    with patch("outbound.providers.sarvam_tts", return_value=audio) as mock_sarvam:
        generator = build_custom_tts_generator(ai_config=ai_config)
        result = await generator("hello")

    assert result == audio
    mock_sarvam.assert_called_once_with(text="hello", voice_id="meera")
