"""Sarvam TTS plugin for LiveKit Agents using Bulbul v3 HTTP streaming."""

from __future__ import annotations

import logging
import os
import uuid
from typing import Optional

import httpx
from livekit.agents.tts import ChunkedStream, TTS, TTSCapabilities
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions

logger = logging.getLogger("outbound.sarvam_tts")

SARVAM_API_URL = os.getenv("SARVAM_API_URL", "https://api.sarvam.ai/text-to-speech/stream")
SARVAM_DEFAULT_VOICE = os.getenv("SARVAM_VOICE_ID", "simran")
SARVAM_DEFAULT_LANGUAGE = os.getenv("SARVAM_LANGUAGE", "en-IN")
SARVAM_DEFAULT_MODEL = os.getenv("SARVAM_MODEL", "bulbul:v3")
SARVAM_SAMPLE_RATE = 22050
SARVAM_NUM_CHANNELS = 1
VALID_MODELS = {"bulbul:v2", "bulbul:v3-beta", "bulbul:v3"}
VALID_SARVAM_SPEAKERS = {
    "aditya",
    "anand",
    "amit",
    "aayan",
    "advait",
    "amelia",
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
    "sumit",
    "suhani",
    "sunny",
    "tanya",
    "tarun",
    "varun",
    "vijay",
}


def normalize_sarvam_speaker(voice: Optional[str]) -> str:
    if voice:
        normalized = voice.strip().lower()
        if normalized in VALID_SARVAM_SPEAKERS:
            return normalized
    return SARVAM_DEFAULT_VOICE


def normalize_sarvam_model(model: Optional[str]) -> str:
    if model:
        normalized = model.strip().lower()
        if normalized in VALID_MODELS:
            return normalized
    return SARVAM_DEFAULT_MODEL


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
        self._voice = normalize_sarvam_speaker(voice or SARVAM_DEFAULT_VOICE)
        self._language = language or SARVAM_DEFAULT_LANGUAGE
        self._model = normalize_sarvam_model(model or SARVAM_DEFAULT_MODEL)
        self._pace = pace
        self._api_key = api_key or os.getenv("SARVAM_API_KEY", "")
        self._api_url = api_url or SARVAM_API_URL

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

        speaker = normalize_sarvam_speaker(self._voice)
        model = normalize_sarvam_model(self._model)
        if speaker != self._voice:
            logger.warning("Unsupported Sarvam speaker '%s' - falling back to '%s'", self._voice, speaker)
        if model != self._model:
            logger.warning("Unsupported Sarvam model '%s' - falling back to '%s'", self._model, model)

        payload = {
            "text": self._input_text,
            "target_language_code": self._language,
            "speaker": speaker,
            "model": model,
            "output_audio_codec": "linear16",
            "speech_sample_rate": self._tts.sample_rate,
            "pace": self._pace,
            "enable_preprocessing": True,
        }
        headers = {
            "api-subscription-key": self._api_key,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
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
                        "Sarvam TTS request failed with status %s: %s",
                        response.status_code,
                        body.decode("utf-8", errors="replace"),
                    )
                    response.raise_for_status()

                async for chunk in response.aiter_bytes(chunk_size=4096):
                    if chunk:
                        output_emitter.push(chunk)
