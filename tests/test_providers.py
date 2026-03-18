from unittest.mock import patch

from outbound.providers import build_llm, build_stt, build_tts


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
