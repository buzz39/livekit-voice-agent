import logging
import os
from typing import Any, Dict, Optional

from livekit.plugins import cartesia, deepgram, inworld, openai

import config as default_config

logger = logging.getLogger("outbound.providers")

_REQUIRED_ENV_VARS = {
    "openai": ("OPENAI_API_KEY",),
    "groq": ("GROQ_API_KEY",),
    "deepgram": ("DEEPGRAM_API_KEY",),
    "cartesia": ("CARTESIA_API_KEY",),
    "inworld": ("INWORLD_API_KEY",),
}


def _override(metadata_overrides: Optional[Dict[str, Any]], *keys: str) -> Optional[Any]:
    """Return the first non-empty override value from metadata for the provided keys."""
    if not metadata_overrides:
        return None
    for key in keys:
        value = metadata_overrides.get(key)
        if value not in (None, ""):
            return value
    return None


def resolve_ai_configuration(ai_config: Dict[str, Any], metadata_overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    llm_provider = (
        os.getenv("LLM_PROVIDER")
        or _override(metadata_overrides, "llm_provider", "model_provider")
        or ai_config.get("llm_provider")
        or default_config.DEFAULT_LLM_PROVIDER
    ).lower()
    llm_model = (
        _override(metadata_overrides, "llm_model")
        or ai_config.get("llm_model")
        or (default_config.GROQ_MODEL if llm_provider == "groq" else default_config.DEFAULT_LLM_MODEL)
    )
    llm_temperature = float(
        _override(metadata_overrides, "llm_temperature")
        or ai_config.get("llm_temperature")
        or (default_config.GROQ_TEMPERATURE if llm_provider == "groq" else default_config.DEFAULT_LLM_TEMPERATURE)
    )

    stt_provider = default_config.DEFAULT_STT_PROVIDER.lower()
    stt_model = (
        _override(metadata_overrides, "stt_model")
        or ai_config.get("stt_model")
        or default_config.DEFAULT_STT_MODEL
    )
    stt_language = (
        _override(metadata_overrides, "stt_language")
        or ai_config.get("stt_language")
        or default_config.DEFAULT_STT_LANGUAGE
    )

    tts_provider = (
        os.getenv("TTS_PROVIDER")
        or _override(metadata_overrides, "tts_provider")
        or ai_config.get("tts_provider")
        or default_config.DEFAULT_TTS_PROVIDER
    ).lower()
    tts_voice = _override(metadata_overrides, "voice_id", "tts_voice") or ai_config.get("tts_voice")
    tts_model = _override(metadata_overrides, "tts_model") or ai_config.get("tts_model")

    if tts_provider == "cartesia":
        tts_model = tts_model or default_config.CARTESIA_TTS_MODEL
        tts_voice = tts_voice or default_config.CARTESIA_TTS_VOICE
    elif tts_provider == "deepgram":
        tts_model = tts_model or default_config.DEEPGRAM_TTS_MODEL
    elif tts_provider == "inworld":
        tts_voice = tts_voice or default_config.INWORLD_TTS_VOICE
    else:
        tts_provider = "openai"
        tts_model = tts_model or default_config.OPENAI_TTS_MODEL
        tts_voice = tts_voice or default_config.OPENAI_TTS_VOICE

    return {
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "llm_temperature": llm_temperature,
        "stt_provider": stt_provider,
        "stt_model": stt_model,
        "stt_language": stt_language,
        "tts_provider": tts_provider,
        "tts_model": tts_model,
        "tts_voice": tts_voice,
    }


def get_missing_provider_env_vars(ai_config: Dict[str, Any], metadata_overrides: Optional[Dict[str, Any]] = None) -> list[str]:
    resolved = resolve_ai_configuration(ai_config=ai_config, metadata_overrides=metadata_overrides)
    required = (
        _REQUIRED_ENV_VARS.get(resolved["llm_provider"], ())
        + _REQUIRED_ENV_VARS.get(resolved["stt_provider"], ())
        + _REQUIRED_ENV_VARS.get(resolved["tts_provider"], ())
    )
    return sorted({env_var for env_var in required if not os.getenv(env_var)})


def build_llm(ai_config: Dict[str, Any], metadata_overrides: Optional[Dict[str, Any]] = None):
    resolved = resolve_ai_configuration(ai_config=ai_config, metadata_overrides=metadata_overrides)
    provider = resolved["llm_provider"]

    if provider == "groq":
        model = resolved["llm_model"]
        temperature = resolved["llm_temperature"]
        logger.info(f"Using Groq LLM: {model}")
        return openai.LLM(
            model=model,
            temperature=temperature,
            base_url=os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1"),
            api_key=os.getenv("GROQ_API_KEY"),
        )

    model = resolved["llm_model"]
    temperature = resolved["llm_temperature"]
    logger.info(f"Using OpenAI LLM: {model}")
    return openai.LLM(model=model, temperature=temperature)


def build_stt(ai_config: Dict[str, Any], metadata_overrides: Optional[Dict[str, Any]] = None):
    resolved = resolve_ai_configuration(ai_config=ai_config, metadata_overrides=metadata_overrides)
    model = resolved["stt_model"]
    language = resolved["stt_language"]
    logger.info(f"Using Deepgram STT: {model}/{language}")
    return deepgram.STT(model=model, language=language)


def build_tts(ai_config: Dict[str, Any], metadata_overrides: Optional[Dict[str, Any]] = None):
    resolved = resolve_ai_configuration(ai_config=ai_config, metadata_overrides=metadata_overrides)
    provider = resolved["tts_provider"]
    voice = resolved["tts_voice"]
    model = resolved["tts_model"]

    if provider == "cartesia":
        logger.info(f"Using Cartesia TTS: {model}/{voice}")
        return cartesia.TTS(model=model, voice=voice)

    if provider == "deepgram":
        logger.info(f"Using Deepgram TTS: {model}")
        return deepgram.TTS(model=model)

    if provider == "inworld":
        logger.info(f"Using Inworld TTS: {voice}")
        return inworld.TTS(voice=voice)

    logger.info(f"Using OpenAI TTS: {model}/{voice}")
    return openai.TTS(model=model, voice=voice)
