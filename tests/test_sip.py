import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from outbound.sip import (
    _extract_sip_status_code,
    _parse_trunk_candidates,
    dial_participant,
    get_sip_identity,
)

# Ensure trunk ID is set so dial_participant doesn't early-return
_SIP_ENV = {"LIVEKIT_OUTBOUND_TRUNK_ID": "trunk-test-123"}


def _make_ctx():
    ctx = SimpleNamespace()
    ctx.room = MagicMock()
    ctx.room.name = "room-123"
    ctx.api = SimpleNamespace()
    ctx.api.sip = SimpleNamespace()
    ctx.api.sip.create_sip_participant = AsyncMock()
    return ctx


@pytest.mark.asyncio
async def test_dial_participant_stops_on_hard_sip_failure():
    ctx = _make_ctx()
    dispatcher = AsyncMock()

    class _HardSipError(Exception):
        def __init__(self):
            super().__init__("sip hard failure")
            self.metadata = {"sip_status_code": "486"}

    ctx.api.sip.create_sip_participant.side_effect = _HardSipError()

    with patch.dict(os.environ, _SIP_ENV), \
         patch("outbound.sip.wait_for_participant", new=AsyncMock()):
        success = await dial_participant(ctx, "+15550000000", "Test Biz", dispatcher)

    assert success is False
    dispatch_calls = [args.args for args in dispatcher.dispatch.await_args_list]
    assert any(call[0] == "call.failed" for call in dispatch_calls)


@pytest.mark.asyncio
async def test_dial_participant_retries_with_secondary_trunk_on_retryable_failure():
    ctx = _make_ctx()
    dispatcher = AsyncMock()
    participant = SimpleNamespace(identity="15550000000")
    call_metadata = {}

    class _RetryableSipError(Exception):
        def __init__(self):
            super().__init__("sip temporary failure")
            self.metadata = {"sip_status_code": "500"}

    ctx.api.sip.create_sip_participant.side_effect = [_RetryableSipError(), None]

    env = {
        **_SIP_ENV,
        "LIVEKIT_OUTBOUND_TRUNK_IDS": "trunk-test-456",
        "SIP_DIAL_RETRY_DELAY_SECONDS": "0",
        "SIP_DIAL_MAX_ROUNDS": "1",
    }

    with patch.dict(os.environ, env), \
         patch("outbound.sip.wait_for_participant", new=AsyncMock(return_value=participant)):
        success = await dial_participant(
            ctx,
            "+15550000000",
            "Test Biz",
            dispatcher,
            call_metadata=call_metadata,
        )

    assert success is True
    assert ctx.api.sip.create_sip_participant.await_count == 2
    assert call_metadata["successful_trunk_id"] == "trunk-test-456"
    assert len(call_metadata["dial_attempts"]) == 2


@pytest.mark.asyncio
async def test_dial_participant_stops_early_on_single_trunk_repeated_failures():
    ctx = _make_ctx()
    dispatcher = AsyncMock()

    class _RetryableSipError(Exception):
        def __init__(self):
            super().__init__("sip temporary failure")
            self.metadata = {"sip_status_code": "500"}

    ctx.api.sip.create_sip_participant.side_effect = _RetryableSipError()

    env = {
        **_SIP_ENV,
        "SIP_DIAL_RETRY_DELAY_SECONDS": "0",
        "SIP_DIAL_MAX_ROUNDS": "5",
        "SIP_TRUNK_FAILURE_THRESHOLD": "2",
        "SIP_TRUNK_COOLDOWN_SECONDS": "30",
    }

    with patch.dict(os.environ, env), \
         patch("outbound.sip.wait_for_participant", new=AsyncMock()):
        success = await dial_participant(ctx, "+15550000000", "Test Biz", dispatcher)

    assert success is False
    # Should fail fast after threshold instead of consuming all 5 rounds.
    assert ctx.api.sip.create_sip_participant.await_count == 2


@pytest.mark.asyncio
async def test_dial_participant_waits_for_join_after_successful_dial():
    ctx = _make_ctx()
    dispatcher = AsyncMock()
    participant = SimpleNamespace(identity="sip:agent@test.local")

    with patch.dict(os.environ, _SIP_ENV), \
         patch("outbound.sip.wait_for_participant", new=AsyncMock(return_value=participant)):
        success = await dial_participant(ctx, "sip:agent@test.local", "Test Biz", dispatcher)

    assert success is True
    dispatch_events = [args.args[0] for args in dispatcher.dispatch.await_args_list]
    assert dispatch_events == ["call.dial.attempt"]
    request = ctx.api.sip.create_sip_participant.await_args.args[0]
    assert request.participant_identity == "sip:agent@test.local"
    assert request.sip_call_to == "agent"


@pytest.mark.asyncio
async def test_dial_participant_uses_from_number_override():
    """When from_number is passed, it should be used as sip_number instead of env var."""
    ctx = _make_ctx()
    participant = SimpleNamespace(identity="15550000000")

    env = {**_SIP_ENV, "SIP_FROM_NUMBER": "+12029787305"}
    with patch.dict(os.environ, env, clear=False), \
         patch("outbound.sip.wait_for_participant", new=AsyncMock(return_value=participant)):
        success = await dial_participant(ctx, "+15550000000", "Test Biz", from_number="+911171366938")

    assert success is True
    request = ctx.api.sip.create_sip_participant.await_args.args[0]
    assert request.sip_number == "+911171366938"


@pytest.mark.asyncio
async def test_dial_participant_falls_back_to_env_when_no_from_number():
    """When from_number is None, it should fall back to SIP_FROM_NUMBER env var."""
    ctx = _make_ctx()
    participant = SimpleNamespace(identity="15550000000")

    env = {**_SIP_ENV, "SIP_FROM_NUMBER": "+12029787305"}
    with patch.dict(os.environ, env, clear=False), \
         patch("outbound.sip.wait_for_participant", new=AsyncMock(return_value=participant)):
        success = await dial_participant(ctx, "+15550000000", "Test Biz")

    assert success is True
    request = ctx.api.sip.create_sip_participant.await_args.args[0]
    assert request.sip_number == "+12029787305"


# ---------------------------------------------------------------------------
# get_sip_identity tests
# ---------------------------------------------------------------------------

def test_get_sip_identity_strips_non_digits():
    assert get_sip_identity("+15550000000") == "15550000000"


def test_get_sip_identity_returns_raw_sip_uri():
    assert get_sip_identity("sip:hello@example.com") == "sip:hello@example.com"


def test_get_sip_identity_digits_only_input():
    assert get_sip_identity("919096132265") == "919096132265"


def test_parse_trunk_candidates_deduplicates_and_preserves_order():
    with patch.dict(
        os.environ,
        {
            "LIVEKIT_OUTBOUND_TRUNK_ID": "primary",
            "LIVEKIT_OUTBOUND_TRUNK_IDS": "secondary,primary, tertiary ",
        },
        clear=False,
    ):
        assert _parse_trunk_candidates() == ["primary", "secondary", "tertiary"]


def test_extract_sip_status_code_from_metadata():
    class _Error(Exception):
        def __init__(self):
            super().__init__("err")
            self.metadata = {"sip_status_code": "503"}

    assert _extract_sip_status_code(_Error()) == 503