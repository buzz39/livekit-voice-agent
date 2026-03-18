import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from outbound.sip import dial_participant


def _make_ctx():
    ctx = SimpleNamespace()
    ctx.room = MagicMock()
    ctx.room.name = "room-123"
    ctx.api = SimpleNamespace()
    ctx.api.sip = SimpleNamespace()
    ctx.api.sip.create_sip_participant = AsyncMock()
    return ctx


@pytest.mark.asyncio
async def test_dial_participant_recovers_when_participant_joins_after_exception():
    ctx = _make_ctx()
    dispatcher = AsyncMock()
    participant = SimpleNamespace(identity="15550000000")
    ctx.api.sip.create_sip_participant.side_effect = RuntimeError("sip status 500")

    with patch("outbound.sip.wait_for_participant", new=AsyncMock(return_value=participant)):
        success = await dial_participant(ctx, "+15550000000", "Test Biz", dispatcher)

    assert success is True
    dispatcher.dispatch.assert_called_once_with(
        "call.dial_recovered",
        {"error": "sip status 500", "participant_identity": "15550000000"},
    )


@pytest.mark.asyncio
async def test_dial_participant_fails_when_participant_never_joins():
    ctx = _make_ctx()
    dispatcher = AsyncMock()
    ctx.api.sip.create_sip_participant.side_effect = RuntimeError("sip status 500")

    async def _timeout(*args, **kwargs):
        raise asyncio.TimeoutError()

    with patch("outbound.sip.wait_for_participant", new=AsyncMock(side_effect=_timeout)):
        success = await dial_participant(ctx, "+15550000000", "Test Biz", dispatcher)

    assert success is False
    dispatcher.dispatch.assert_called_once_with("call.failed", {"error": "sip status 500"})


@pytest.mark.asyncio
async def test_dial_participant_waits_for_join_after_successful_dial():
    ctx = _make_ctx()
    dispatcher = AsyncMock()
    participant = SimpleNamespace(identity="sip:agent@test.local")

    with patch("outbound.sip.wait_for_participant", new=AsyncMock(return_value=participant)):
        success = await dial_participant(ctx, "sip:agent@test.local", "Test Biz", dispatcher)

    assert success is True
    dispatcher.dispatch.assert_not_called()
    request = ctx.api.sip.create_sip_participant.await_args.args[0]
    assert request.participant_identity == "sip:agent@test.local"
    assert request.sip_call_to == "agent"