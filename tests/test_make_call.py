import re
from unittest.mock import AsyncMock, patch

import pytest

from make_call import build_dispatch_metadata, build_room_name, dispatch_call, validate_phone_number


def test_validate_phone_number_accepts_e164():
    assert validate_phone_number("+14155552671") == "+14155552671"


def test_validate_phone_number_rejects_invalid_number():
    with pytest.raises(ValueError, match="E.164"):
        validate_phone_number("4155552671")


def test_build_room_name_contains_sanitized_phone_number():
    room_name = build_room_name("+14155552671")

    assert room_name.startswith("call-14155552671-")
    assert re.match(r"^call-14155552671-\d{4}$", room_name)


def test_build_dispatch_metadata_matches_expected_shape():
    metadata = build_dispatch_metadata("+14155552671", "Acme Roofing", "default_roofing_agent")

    assert metadata == {
        "phone_number": "+14155552671",
        "business_name": "Acme Roofing",
        "agent_slug": "default_roofing_agent",
    }


@pytest.mark.asyncio
async def test_dispatch_call_raises_when_credentials_missing():
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(RuntimeError, match="LiveKit credentials missing"):
            await dispatch_call(
                phone_number="+14155552671",
                business_name="Acme Roofing",
                agent_slug="default_roofing_agent",
                agent_name="voice-assistant",
            )


@pytest.mark.asyncio
async def test_dispatch_call_creates_expected_dispatch_request():
    mock_dispatch = AsyncMock()
    mock_lk = AsyncMock()
    mock_lk.agent_dispatch.create_dispatch = mock_dispatch
    mock_api = AsyncMock()
    mock_api.__aenter__.return_value = mock_lk
    mock_api.__aexit__.return_value = None

    with patch.dict(
        "os.environ",
        {
            "LIVEKIT_URL": "wss://example.livekit.cloud",
            "LIVEKIT_API_KEY": "key",
            "LIVEKIT_API_SECRET": "secret",
        },
        clear=True,
    ):
        with patch("make_call.api.LiveKitAPI", return_value=mock_api):
            with patch("make_call.random.randint", return_value=1234):
                room_name = await dispatch_call(
                    phone_number="+14155552671",
                    business_name="Acme Roofing",
                    agent_slug="default_roofing_agent",
                    agent_name="voice-assistant",
                )

    assert room_name == "call-14155552671-1234"
    mock_dispatch.assert_awaited_once()
    request = mock_dispatch.await_args.args[0]
    assert request.agent_name == "voice-assistant"
    assert request.room == "call-14155552671-1234"
    assert request.metadata == (
        '{"phone_number": "+14155552671", "business_name": "Acme Roofing", "agent_slug": "default_roofing_agent"}'
    )
