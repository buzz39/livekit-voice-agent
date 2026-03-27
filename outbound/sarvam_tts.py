"""Sarvam TTS plugin for LiveKit Agents using Bulbul v3 HTTP streaming synthesis."""

from __future__ import annotations

import base64
import io
import logging
import os
import struct
import uuid
import wave
from typing import Optional

import httpx
from livekit.agents.tts import ChunkedStream, TTS, TTSCapabilities
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions

logger = logging.getLogger("outbound.sarvam_tts")

SARVAM_API_URL = os.getenv("SARVAM_API_URL", "https://api.sarvam.ai/text-to-speech")
SARVAM_STREAM_URL = os.getenv("SARVAM_STREAM_URL", "https://api.sarvam.ai/text-to-speech/stream")
SARVAM_DEFAULT_VOICE = os.getenv("SARVAM_VOICE_ID", "shubh")
SARVAM_DEFAULT_LANGUAGE = os.getenv("SARVAM_LANGUAGE", "en-IN")
SARVAM_DEFAULT_MODEL = os.getenv("SARVAM_MODEL", "bulbul:v3")
SARVAM_SAMPLE_RATE = int(os.getenv("SARVAM_SAMPLE_RATE", "24000"))
SARVAM_NUM_CHANNELS = 1
VALID_MODELS = {"bulbul:v2", "bulbul:v3-beta", "bulbul:v3"}
VALID_SARVAM_LANGUAGES = {
    "bn-IN",
    "en-IN",
    "gu-IN",
    "hi-IN",
    "kn-IN",
    "ml-IN",
    "mr-IN",
    "od-IN",
    "pa-IN",
    "ta-IN",
    "te-IN",
}
SARVAM_LANGUAGE_ALIASES = {
    "bn": "bn-IN",
    "bengali": "bn-IN",
    "en": "en-IN",
    "en-gb": "en-IN",
    "en-us": "en-IN",
    "english": "en-IN",
    "gu": "gu-IN",
    "gujarati": "gu-IN",
    "hi": "hi-IN",
    "hindi": "hi-IN",
    "hinglish": "en-IN",
    "kn": "kn-IN",
    "kannada": "kn-IN",
    "ml": "ml-IN",
    "malayalam": "ml-IN",
    "mr": "mr-IN",
    "marathi": "mr-IN",
    "od": "od-IN",
    "odia": "od-IN",
    "oriya": "od-IN",
    "pa": "pa-IN",
    "punjabi": "pa-IN",
    "ta": "ta-IN",
    "tamil": "ta-IN",
    "te": "te-IN",
    "telugu": "te-IN",
}
VALID_SARVAM_SPEAKERS_V3 = {
    "aayan",
    "aditya",
    "advait",
    "amelia",
    "amit",
    "anand",
    "ashutosh",
    "dev",
    "gokul",
    "ishita",
    "kabir",
    "kavitha",
    "kavya",
    "manan",
    "mani",
    "mohit",
    "neha",
    "pooja",
    "priya",
    "rahul",
    "ratan",
    "rehan",
    "rohan",
    "roopa",
    "ritu",
    "rupali",
    "shreya",
    "shubh",
    "shruti",
    "simran",
    "soham",
    "sophia",
    "suhani",
    "sumit",
    "sunny",
    "tanya",
    "tarun",
    "varun",
    "vijay",
}
VALID_SARVAM_SPEAKERS_V2 = {
    "abhilash",
    "anushka",
    "arya",
    "hitesh",
    "karun",
    "manisha",
    "vidya",
}
# Combined set kept for backward compatibility with imports
VALID_SARVAM_SPEAKERS = VALID_SARVAM_SPEAKERS_V3 | VALID_SARVAM_SPEAKERS_V2

_MODEL_SPEAKER_MAP = {
    "bulbul:v3": VALID_SARVAM_SPEAKERS_V3,
    "bulbul:v3-beta": VALID_SARVAM_SPEAKERS_V3,
    "bulbul:v2": VALID_SARVAM_SPEAKERS_V2,
}
_MODEL_DEFAULT_VOICE = {
    "bulbul:v3": "shubh",
    "bulbul:v3-beta": "shubh",
    "bulbul:v2": "anushka",
}


def normalize_sarvam_speaker(voice: Optional[str], model: Optional[str] = None) -> str:
    resolved_model = normalize_sarvam_model(model) if model else SARVAM_DEFAULT_MODEL
    valid_speakers = _MODEL_SPEAKER_MAP.get(resolved_model, VALID_SARVAM_SPEAKERS_V3)
    default_voice = _MODEL_DEFAULT_VOICE.get(resolved_model, SARVAM_DEFAULT_VOICE)
    if voice:
        normalized = voice.strip().lower()
        if normalized in valid_speakers:
            return normalized
    return default_voice


def normalize_sarvam_model(model: Optional[str]) -> str:
    if model:
        normalized = model.strip().lower()
        if normalized in VALID_MODELS:
            return normalized
    return SARVAM_DEFAULT_MODEL


def normalize_sarvam_language(language: Optional[str]) -> str:
    if language:
        candidate = language.strip()
        if candidate in VALID_SARVAM_LANGUAGES:
            return candidate

        normalized = candidate.lower()
        if normalized in SARVAM_LANGUAGE_ALIASES:
            return SARVAM_LANGUAGE_ALIASES[normalized]

        title_cased = normalized.split("-")[0] + "-IN" if "-" not in normalized else normalized.split("-")[0] + "-IN"
        if title_cased in VALID_SARVAM_LANGUAGES:
            return title_cased

    return SARVAM_DEFAULT_LANGUAGE


class SarvamTTS(TTS):
    """LiveKit-compatible TTS backed by the Sarvam AI HTTP streaming API."""

    def __init__(
        self,
        *,
        voice: str | None = None,
        language: str | None = None,
        model: str | None = None,
        pace: float = 1.0,
        api_key: str | None = None,
        api_url: str | None = None,
        sample_rate: int = SARVAM_SAMPLE_RATE,
        num_channels: int = SARVAM_NUM_CHANNELS,
    ) -> None:
        super().__init__(
            capabilities=TTSCapabilities(streaming=False),
            sample_rate=sample_rate,
            num_channels=num_channels,
        )
        self._model = normalize_sarvam_model(model or SARVAM_DEFAULT_MODEL)
        self._voice = normalize_sarvam_speaker(voice or SARVAM_DEFAULT_VOICE, self._model)
        self._language = normalize_sarvam_language(language or SARVAM_DEFAULT_LANGUAGE)
        self._pace = pace
        self._api_key = api_key or os.getenv("SARVAM_API_KEY", "")
        self._api_url = api_url or SARVAM_STREAM_URL

        if not self._api_key:
            raise ValueError("Sarvam API key not provided. Set SARVAM_API_KEY or pass api_key=")

    @property
    def model(self) -> str:
        return self._model

    @property
    def provider(self) -> str:
        return "sarvam"

    def synthesize(
        self,
        text: str,
        *,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> ChunkedStream:
        return _SarvamChunkedStream(
            tts=self,
            input_text=text,
            conn_options=conn_options,
            voice=self._voice,
            language=self._language,
            model=self._model,
            pace=self._pace,
            api_key=self._api_key,
            api_url=self._api_url,
        )

    async def aclose(self) -> None:
        pass


class _SarvamChunkedStream(ChunkedStream):
    """Streams audio from Sarvam HTTP streaming API and pushes PCM frames."""

    def __init__(
        self,
        *,
        tts: SarvamTTS,
        input_text: str,
        conn_options: APIConnectOptions,
        voice: str,
        language: str,
        model: str,
        pace: float,
        api_key: str,
        api_url: str,
    ) -> None:
        super().__init__(tts=tts, input_text=input_text, conn_options=conn_options)
        self._voice = voice
        self._language = language
        self._model = model
        self._pace = pace
        self._api_key = api_key
        self._api_url = api_url

    async def _run(self, output_emitter) -> None:  # type: ignore[override]
        """Called by the SDK's retry loop inside ``ChunkedStream._main_task``."""
        request_id = str(uuid.uuid4())

        output_emitter.initialize(
            request_id=request_id,
            sample_rate=self._tts.sample_rate,
            num_channels=self._tts.num_channels,
            mime_type="audio/pcm",
        )

        model = normalize_sarvam_model(self._model)
        speaker = normalize_sarvam_speaker(self._voice, model)
        language = normalize_sarvam_language(self._language)
        if speaker != self._voice:
            logger.warning("Unsupported Sarvam speaker '%s' - falling back to '%s'", self._voice, speaker)
        if model != self._model:
            logger.warning("Unsupported Sarvam model '%s' - falling back to '%s'", self._model, model)
        if language != self._language:
            logger.warning("Unsupported Sarvam language '%s' - falling back to '%s'", self._language, language)

        payload = {
            "text": self._input_text,
            "target_language_code": language,
            "speaker": speaker,
            "model": model,
            "speech_sample_rate": self._tts.sample_rate,
            "pace": self._pace,
        }
        headers = {
            "api-subscription-key": self._api_key,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            # Use the streaming endpoint for lower time-to-first-byte
            if "/stream" in self._api_url:
                payload["output_audio_codec"] = "mulaw"
                async with client.stream(
                    "POST",
                    self._api_url,
                    json=payload,
                    headers=headers,
                    timeout=self._conn_options.timeout,
                ) as response:
                    if response.status_code != 200:
                        body = await response.aread()
                        logger.error(
                            "Sarvam TTS stream failed with status %s for model=%s speaker=%s language=%s: %s",
                            response.status_code,
                            model,
                            speaker,
                            language,
                            body.decode("utf-8", errors="replace"),
                        )
                        response.raise_for_status()

                    async for chunk in response.aiter_bytes(chunk_size=4096):
                        if chunk:
                            output_emitter.push(_mulaw_to_pcm(chunk))
            else:
                # Fallback: REST endpoint returns base64-encoded WAV
                response = await client.post(
                    self._api_url,
                    json=payload,
                    headers=headers,
                    timeout=self._conn_options.timeout,
                )
                if response.status_code != 200:
                    logger.error(
                        "Sarvam TTS request failed with status %s for model=%s speaker=%s language=%s: %s",
                        response.status_code,
                        model,
                        speaker,
                        language,
                        response.text,
                    )
                    response.raise_for_status()

                data = response.json()
                audios = data.get("audios") or []
                if not audios:
                    logger.error("Sarvam TTS response missing audio payload: %s", data)
                    raise ValueError("Sarvam TTS response did not include any audio data")

                audio_bytes = base64.b64decode(audios[0])
                output_emitter.push(_extract_pcm(audio_bytes))


def _extract_pcm(audio_bytes: bytes) -> bytes:
    if not audio_bytes.startswith(b"RIFF"):
        return audio_bytes

    with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
        return wav_file.readframes(wav_file.getnframes())


# --- G.711 µ-law to 16-bit linear PCM conversion ---
# Precomputed lookup table (ITU-T G.711 standard) avoids per-sample math at
# runtime.  Each µ-law byte maps to a signed 16-bit linear PCM value.

def _build_mulaw_decode_table() -> list[int]:
    table = [0] * 256
    for i in range(256):
        v = ~i & 0xFF
        t = ((v & 0x0F) << 3) + 0x84
        t <<= (v & 0x70) >> 4
        table[i] = (0x84 - t) if (v & 0x80) else (t - 0x84)
    return table


_MULAW_DECODE = _build_mulaw_decode_table()


def _mulaw_to_pcm(data: bytes) -> bytes:
    """Convert G.711 µ-law encoded bytes to 16-bit signed little-endian PCM."""
    return struct.pack(f"<{len(data)}h", *(_MULAW_DECODE[b] for b in data))
