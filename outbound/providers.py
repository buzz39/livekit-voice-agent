import logging
import os
from typing import Any, Dict, Optional

import httpx
from livekit.plugins import cartesia, deepgram, inworld, openai

import config as default_config
from outbound.sarvam_tts import (
    SARVAM_DEFAULT_MODEL,
    SARVAM_DEFAULT_VOICE,
    VALID_SARVAM_SPEAKERS,
    SarvamTTS,
)

logger = logging.getLogger("outbound.providers")

SARVAM_TTS_VOICE = os.getenv("SARVAM_VOICE_ID", SARVAM_DEFAULT_VOICE)
SARVAM_PLACEHOLDER_MODEL = SARVAM_DEFAULT_MODEL

_REQUIRED_ENV_VARS = {
    "openai": ("OPENAI_API_KEY",),
    "groq": ("GROQ_API_KEY",),
    "deepgram": ("DEEPGRAM_API_KEY",),
    "cartesia": ("CARTESIA_API_KEY",),
    "inworld": ("INWORLD_API_KEY",),
    "sarvam": ("SARVAM_API_KEY",),
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


def _has_credentials(provider: str) -> bool:
    """Return True if all required env vars for *provider* are set."""
    return all(os.getenv(v) for v in _REQUIRED_ENV_VARS.get(provider, ()))


def resolve_ai_configuration(ai_config: Dict[str, Any], metadata_overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    llm_provider = (
        os.getenv("LLM_PROVIDER")
        or _override(metadata_overrides, "llm_provider", "model_provider")
        or ai_config.get("llm_provider")
        or default_config.DEFAULT_LLM_PROVIDER
    ).lower()

    # Auto-fallback: if the chosen LLM provider's credentials are missing, degrade
    # to a provider that IS configured rather than aborting the call entirely.
    if not _has_credentials(llm_provider):
        fallback = "openai" if llm_provider != "openai" else "groq"
        if _has_credentials(fallback):
            logger.warning(
                "LLM provider '%s' credentials missing — falling back to '%s'",
                llm_provider, fallback,
            )
            llm_provider = fallback
        # If neither has credentials the downstream validation will still catch it.

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

    # Auto-fallback for TTS provider as well
    if not _has_credentials(tts_provider):
        fallback = "openai" if tts_provider != "openai" else "cartesia"
        if _has_credentials(fallback):
            logger.warning(
                "TTS provider '%s' credentials missing — falling back to '%s'",
                tts_provider, fallback,
            )
            tts_provider = fallback

    tts_voice = _override(metadata_overrides, "voice_id", "tts_voice") or ai_config.get("tts_voice")
    tts_model = _override(metadata_overrides, "tts_model") or ai_config.get("tts_model")

    if tts_provider == "cartesia":
        tts_model = tts_model or default_config.CARTESIA_TTS_MODEL
        tts_voice = tts_voice or default_config.CARTESIA_TTS_VOICE
    elif tts_provider == "deepgram":
        tts_model = tts_model or default_config.DEEPGRAM_TTS_MODEL
    elif tts_provider == "inworld":
        tts_voice = tts_voice or default_config.INWORLD_TTS_VOICE
    elif tts_provider == "sarvam":
        tts_model = tts_model or SARVAM_PLACEHOLDER_MODEL
        tts_voice = tts_voice or SARVAM_TTS_VOICE
        if tts_model == "sarvam":
            tts_model = SARVAM_PLACEHOLDER_MODEL
        if tts_voice not in VALID_SARVAM_SPEAKERS:
            tts_voice = SARVAM_TTS_VOICE
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
    model = resolved["llm_model"]
    temperature = resolved["llm_temperature"]

    if provider == "groq":
        # Groq only supports its own model catalogue; catch obvious misconfigurations
        # (e.g. an OpenAI model name stored in the DB) early with a clear message.
        if model and model.startswith(("gpt-", "o1-", "o3-", "chatgpt-")):
            logger.warning(
                "Groq provider configured with non-Groq model '%s' — "
                "falling back to default '%s'. Update the ai_config in the database.",
                model,
                default_config.GROQ_MODEL,
            )
            model = default_config.GROQ_MODEL
        logger.info(f"Using Groq LLM: {model}")
        return openai.LLM(
            model=model,
            temperature=temperature,
            base_url=os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1"),
            api_key=os.getenv("GROQ_API_KEY"),
            _strict_tool_schema=False,  # Groq rejects OpenAI strict-mode schemas for zero-param tools
        )

    # OpenAI (default) — fix model if it's a leftover Groq model name after fallback
    if model and not model.startswith(("gpt-", "o1-", "o3-", "chatgpt-")):
        logger.warning(
            "OpenAI provider configured with non-OpenAI model '%s' — "
            "falling back to default '%s'.",
            model,
            default_config.DEFAULT_LLM_MODEL,
        )
        model = default_config.DEFAULT_LLM_MODEL
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

    if provider == "sarvam":
        logger.info(f"Using Sarvam TTS: {model}/{voice}")
        return SarvamTTS(voice=voice, model=model)

    logger.info(f"Using OpenAI TTS: {model}/{voice}")
    return openai.TTS(model=model, voice=voice)

