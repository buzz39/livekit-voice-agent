import logging
import os
from typing import Any, Dict, Optional

from livekit.plugins import cartesia, deepgram, inworld, openai

import config as default_config

logger = logging.getLogger("outbound.providers")


def _override(metadata_overrides: Optional[Dict[str, Any]], *keys: str) -> Optional[Any]:
    """Return the first non-empty override value from metadata for the provided keys."""
    if not metadata_overrides:
        return None
    for key in keys:
        value = metadata_overrides.get(key)
        if value not in (None, ""):
            return value
    return None


def build_llm(ai_config: Dict[str, Any], metadata_overrides: Optional[Dict[str, Any]] = None):
    provider = (
        os.getenv("LLM_PROVIDER")
        or _override(metadata_overrides, "llm_provider", "model_provider")
        or ai_config.get("llm_provider")
        or default_config.DEFAULT_LLM_PROVIDER
    ).lower()

    if provider == "groq":
        model = (
            _override(metadata_overrides, "llm_model")
            or ai_config.get("llm_model")
            or default_config.GROQ_MODEL
        )
        temperature = float(
            _override(metadata_overrides, "llm_temperature")
            or ai_config.get("llm_temperature")
            or default_config.GROQ_TEMPERATURE
        )
        logger.info(f"Using Groq LLM: {model}")
        return openai.LLM(
            model=model,
            temperature=temperature,
            base_url=os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1"),
            api_key=os.getenv("GROQ_API_KEY"),
        )

    model = (
        _override(metadata_overrides, "llm_model")
        or ai_config.get("llm_model")
        or default_config.DEFAULT_LLM_MODEL
    )
    temperature = float(
        _override(metadata_overrides, "llm_temperature")
        or ai_config.get("llm_temperature")
        or default_config.DEFAULT_LLM_TEMPERATURE
    )
    logger.info(f"Using OpenAI LLM: {model}")
    return openai.LLM(model=model, temperature=temperature)


def build_stt(ai_config: Dict[str, Any], metadata_overrides: Optional[Dict[str, Any]] = None):
    model = (
        _override(metadata_overrides, "stt_model")
        or ai_config.get("stt_model")
        or default_config.DEFAULT_STT_MODEL
    )
    language = (
        _override(metadata_overrides, "stt_language")
        or ai_config.get("stt_language")
        or default_config.DEFAULT_STT_LANGUAGE
    )
    logger.info(f"Using Deepgram STT: {model}/{language}")
    return deepgram.STT(model=model, language=language)


def build_tts(ai_config: Dict[str, Any], metadata_overrides: Optional[Dict[str, Any]] = None):
    provider = (
        os.getenv("TTS_PROVIDER")
        or _override(metadata_overrides, "tts_provider")
        or ai_config.get("tts_provider")
        or default_config.DEFAULT_TTS_PROVIDER
    ).lower()
    voice = _override(metadata_overrides, "voice_id", "tts_voice") or ai_config.get("tts_voice")
    model = _override(metadata_overrides, "tts_model") or ai_config.get("tts_model")

    if provider == "cartesia":
        model = model or default_config.CARTESIA_TTS_MODEL
        voice = voice or default_config.CARTESIA_TTS_VOICE
        logger.info(f"Using Cartesia TTS: {model}/{voice}")
        return cartesia.TTS(model=model, voice=voice)

    if provider == "deepgram":
        model = model or default_config.DEEPGRAM_TTS_MODEL
        logger.info(f"Using Deepgram TTS: {model}")
        return deepgram.TTS(model=model)

    if provider == "inworld":
        voice = voice or default_config.INWORLD_TTS_VOICE
        logger.info(f"Using Inworld TTS: {voice}")
        return inworld.TTS(voice=voice)

    model = model or default_config.OPENAI_TTS_MODEL
    voice = voice or default_config.OPENAI_TTS_VOICE
    logger.info(f"Using OpenAI TTS: {model}/{voice}")
    return openai.TTS(model=model, voice=voice)
