import os
from dotenv import load_dotenv

load_dotenv()

_llm_provider_default = os.getenv("LLM_PROVIDER", "groq")
DEFAULT_LLM_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", _llm_provider_default)
DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "llama-3.3-70b-versatile")
DEFAULT_LLM_TEMPERATURE = float(os.getenv("DEFAULT_LLM_TEMPERATURE", "0.7"))
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_TEMPERATURE = float(os.getenv("GROQ_TEMPERATURE", "0.7"))

DEFAULT_STT_PROVIDER = os.getenv("DEFAULT_STT_PROVIDER", "deepgram")
DEFAULT_STT_MODEL = os.getenv("DEFAULT_STT_MODEL", "nova-3")
DEFAULT_STT_LANGUAGE = os.getenv("DEFAULT_STT_LANGUAGE", "en-US")

_tts_provider_default = os.getenv("TTS_PROVIDER", "sarvam")
DEFAULT_TTS_PROVIDER = os.getenv("DEFAULT_TTS_PROVIDER", _tts_provider_default)
OPENAI_TTS_MODEL = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
OPENAI_TTS_VOICE = os.getenv("OPENAI_TTS_VOICE", "alloy")
DEEPGRAM_TTS_MODEL = os.getenv("DEEPGRAM_TTS_MODEL", "aura-asteria-en")
CARTESIA_TTS_MODEL = os.getenv("CARTESIA_TTS_MODEL", "sonic-2")
CARTESIA_TTS_VOICE = os.getenv("CARTESIA_TTS_VOICE", "f786b574-daa5-4673-aa0c-cbe3e8534c02")
INWORLD_TTS_VOICE = os.getenv("INWORLD_TTS_VOICE", "Sarah")

OUTBOUND_AGENT_NAME = os.getenv("OUTBOUND_AGENT_NAME", "voice-assistant")
DEFAULT_TRANSFER_NUMBER = os.getenv("DEFAULT_TRANSFER_NUMBER")
SIP_DOMAIN = os.getenv("SIP_DOMAIN") or os.getenv("VOBIZ_SIP_DOMAIN")
