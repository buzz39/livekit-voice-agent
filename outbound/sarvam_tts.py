"""Sarvam AI TTS plugin for LiveKit agents SDK (>=1.2).

Implements the ``tts.TTS`` / ``tts.ChunkedStream`` abstract interface so
that Sarvam can be passed directly as the *tts* argument to ``AgentSession``
without needing any private-API monkey-patching.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Optional

import httpx
from livekit.agents.tts import ChunkedStream, SynthesizedAudio, TTS, TTSCapabilities
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions
from livekit import rtc

logger = logging.getLogger("outbound.sarvam_tts")

SARVAM_API_URL = os.getenv("SARVAM_API_URL", "https://api.sarvam.ai/text-to-speech")
SARVAM_DEFAULT_VOICE = os.getenv("SARVAM_VOICE_ID", "meera")
SARVAM_DEFAULT_LANGUAGE = os.getenv("SARVAM_LANGUAGE", "hi-IN")
SARVAM_DEFAULT_MODEL = os.getenv("SARVAM_MODEL", "bulbul:v1")
SARVAM_SAMPLE_RATE = 8000  # 8 kHz for telephony
SARVAM_NUM_CHANNELS = 1
VALID_SARVAM_SPEAKERS = {"meera", "pavithra", "maitreyi", "arvind", "amol", "amartya"}


def normalize_sarvam_speaker(voice: Optional[str]) -> str:
    if voice in VALID_SARVAM_SPEAKERS:
        return voice
    return SARVAM_DEFAULT_VOICE


def normalize_sarvam_model(model: Optional[str]) -> str:
    if model and model != "sarvam":
        return model
    return SARVAM_DEFAULT_MODEL


class SarvamTTS(TTS):
    """LiveKit-compatible TTS backed by the Sarvam AI REST API."""

    def __init__(
        self,
        *,
        voice: str | None = None,
        language: str | None = None,
        model: str | None = None,
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
        self._voice = normalize_sarvam_speaker(voice or SARVAM_DEFAULT_VOICE)
        self._language = language or SARVAM_DEFAULT_LANGUAGE
        self._model = normalize_sarvam_model(model or SARVAM_DEFAULT_MODEL)
        self._api_key = api_key or os.getenv("SARVAM_API_KEY", "")
        self._api_url = api_url or SARVAM_API_URL

    @property
    def model(self) -> str:
        return "sarvam"

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
            api_key=self._api_key,
            api_url=self._api_url,
        )

    async def aclose(self) -> None:
        pass


class _SarvamChunkedStream(ChunkedStream):
    """Fetches audio from Sarvam REST API and pushes PCM frames."""

    def __init__(
        self,
        *,
        tts: SarvamTTS,
        input_text: str,
        conn_options: APIConnectOptions,
        voice: str,
        language: str,
        model: str,
        api_key: str,
        api_url: str,
    ) -> None:
        super().__init__(tts=tts, input_text=input_text, conn_options=conn_options)
        self._voice = voice
        self._language = language
        self._model = model
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

        speaker = normalize_sarvam_speaker(self._voice)
        model = normalize_sarvam_model(self._model)
        if speaker != self._voice:
            logger.warning("Unsupported Sarvam speaker '%s' - falling back to '%s'", self._voice, speaker)
        if model != self._model:
            logger.warning("Unsupported Sarvam model '%s' - falling back to '%s'", self._model, model)

        payload = {
            "inputs": [self._input_text],
            "target_language_code": self._language,
            "speaker": speaker,
            "model": model,
            "pitch": 0,
            "pace": 1.0,
            "loudness": 1.5,
            "speech_sample_rate": self._tts.sample_rate,
            "enable_preprocessing": True,
            "override_triplets": {},
        }
        headers = {
            "api-subscription-key": self._api_key,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._api_url,
                json=payload,
                headers=headers,
                timeout=self._conn_options.timeout,
            )
            if response.is_error:
                logger.error("Sarvam TTS request failed with status %s: %s", response.status_code, response.text)
            response.raise_for_status()

        # Sarvam returns JSON with base64-encoded audio
        data = response.json()
        audio_b64 = data.get("audios", [None])[0]
        if audio_b64:
            import base64
            audio_bytes = base64.b64decode(audio_b64)
            output_emitter.push(audio_bytes)
        else:
            logger.error("Sarvam TTS returned no audio data")
