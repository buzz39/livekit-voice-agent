import base64
import io
import json
import wave
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from outbound.sarvam_tts import SarvamTTS, _extract_pcm, normalize_sarvam_language


class _FakeEmitter:
    def __init__(self):
        self.initialized = None
        self.chunks = []

    def initialize(self, **kwargs):
        self.initialized = kwargs

    def push(self, chunk):
        self.chunks.append(chunk)


def _wav_bytes(frames: bytes, sample_rate: int = 22050, channels: int = 1, sample_width: int = 2) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(frames)
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_sarvam_chunked_stream_posts_rest_payload_and_pushes_pcm():
    pcm_bytes = b"\x01\x02\x03\x04"
    wav_bytes = _wav_bytes(pcm_bytes)
    response = httpx.Response(
        200,
        request=httpx.Request("POST", "https://api.sarvam.ai/text-to-speech"),
        json={"audios": [base64.b64encode(wav_bytes).decode("ascii")]},
    )

    tts = SarvamTTS(api_key="test-key", voice="simran", model="bulbul:v3", language="en-IN")
    stream = tts.synthesize("hello world", conn_options=SimpleNamespace(timeout=5))
    emitter = _FakeEmitter()

    post = AsyncMock(return_value=response)
    with patch("outbound.sarvam_tts.httpx.AsyncClient") as client_cls:
        client_cls.return_value.__aenter__.return_value.post = post
        await stream._run(emitter)

    _, kwargs = post.call_args
    assert kwargs["json"] == {
        "text": "hello world",
        "target_language_code": "en-IN",
        "speaker": "simran",
        "model": "bulbul:v3",
        "speech_sample_rate": 22050,
        "pace": 1.0,
    }
    assert emitter.initialized["mime_type"] == "audio/pcm"
    assert emitter.chunks == [pcm_bytes]


@pytest.mark.asyncio
async def test_sarvam_chunked_stream_normalizes_language_aliases():
    pcm_bytes = b"\x01\x02\x03\x04"
    wav_bytes = _wav_bytes(pcm_bytes)
    response = httpx.Response(
        200,
        request=httpx.Request("POST", "https://api.sarvam.ai/text-to-speech"),
        json={"audios": [base64.b64encode(wav_bytes).decode("ascii")]},
    )

    tts = SarvamTTS(api_key="test-key", voice="simran", model="bulbul:v3", language="english")
    stream = tts.synthesize("hello world", conn_options=SimpleNamespace(timeout=5))
    emitter = _FakeEmitter()

    post = AsyncMock(return_value=response)
    with patch("outbound.sarvam_tts.httpx.AsyncClient") as client_cls:
        client_cls.return_value.__aenter__.return_value.post = post
        await stream._run(emitter)

    _, kwargs = post.call_args
    assert kwargs["json"]["target_language_code"] == "en-IN"


@pytest.mark.asyncio
async def test_sarvam_chunked_stream_logs_response_body_before_raise(caplog):
    response = httpx.Response(
        400,
        request=httpx.Request("POST", "https://api.sarvam.ai/text-to-speech"),
        text=json.dumps({"error": {"message": "bad payload"}}),
    )

    tts = SarvamTTS(api_key="test-key")
    stream = tts.synthesize("hello world", conn_options=SimpleNamespace(timeout=5))
    emitter = _FakeEmitter()

    post = AsyncMock(return_value=response)
    with patch("outbound.sarvam_tts.httpx.AsyncClient") as client_cls:
        client_cls.return_value.__aenter__.return_value.post = post
        with pytest.raises(httpx.HTTPStatusError):
            await stream._run(emitter)

    assert "bad payload" in caplog.text


def test_extract_pcm_returns_raw_frames_for_wav_bytes():
    pcm_bytes = b"\x10\x20\x30\x40"
    assert _extract_pcm(_wav_bytes(pcm_bytes)) == pcm_bytes


def test_extract_pcm_leaves_non_wav_bytes_unchanged():
    pcm_bytes = b"\x10\x20\x30\x40"
    assert _extract_pcm(pcm_bytes) == pcm_bytes


def test_normalize_sarvam_language_maps_aliases_to_supported_codes():
    assert normalize_sarvam_language("english") == "en-IN"
    assert normalize_sarvam_language("hinglish") == "en-IN"
    assert normalize_sarvam_language("hi") == "hi-IN"
    assert normalize_sarvam_language("en-US") == "en-IN"
    assert normalize_sarvam_language("invalid-language") == "en-IN"