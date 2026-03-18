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

SARVAM_API_URL = os.getenv("SARVAM_API_URL", "https://api.sarvam.ai/v1/tts")
SARVAM_DEFAULT_VOICE = os.getenv("SARVAM_VOICE_ID", "saarika:v2.5")
SARVAM_SAMPLE_RATE = 16_000
SARVAM_NUM_CHANNELS = 1


class SarvamTTS(TTS):
    """LiveKit-compatible TTS backed by the Sarvam AI REST API."""

    def __init__(
        self,
        *,
        voice: str | None = None,
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
        self._voice = voice or SARVAM_DEFAULT_VOICE
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
        api_key: str,
        api_url: str,
    ) -> None:
        super().__init__(tts=tts, input_text=input_text, conn_options=conn_options)
        self._voice = voice
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

        payload = {
            "text": self._input_text,
            "voice": self._voice,
            "response_format": "pcm",
            "sample_rate": self._tts.sample_rate,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._api_url,
                json=payload,
                headers=headers,
                timeout=self._conn_options.timeout,
            )
            response.raise_for_status()

        output_emitter.push(response.content)
