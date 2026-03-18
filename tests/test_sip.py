from unittest.mock import AsyncMock, patch

import pytest

from outbound.sip import DEFAULT_SIP_TRUNK_ID, dial_participant, get_sip_trunk_id


def test_get_sip_trunk_id_prefers_livekit_sip_trunk_id():
    with patch.dict(
        "os.environ",
        {
            "LIVEKIT_SIP_TRUNK_ID": "ST_primary",
            "LIVEKIT_OUTBOUND_TRUNK_ID": "ST_secondary",
            "SIP_TRUNK_ID": "ST_legacy",
        },
        clear=True,
    ):
        assert get_sip_trunk_id() == "ST_primary"


def test_get_sip_trunk_id_falls_back_to_vobiz_default():
    with patch.dict("os.environ", {}, clear=True):
        assert get_sip_trunk_id() == DEFAULT_SIP_TRUNK_ID


@pytest.mark.asyncio
async def test_dial_participant_uses_resolved_sip_trunk_id():
    ctx = AsyncMock()
    ctx.room.name = "room-123"
    ctx.api.sip.create_sip_participant = AsyncMock()

    with patch.dict(
        "os.environ",
        {
            "LIVEKIT_SIP_TRUNK_ID": "ST_primary",
            "LIVEKIT_OUTBOUND_TRUNK_ID": "ST_secondary",
            "SIP_FROM_NUMBER": "+12025550123",
        },
        clear=True,
    ):
        dialed = await dial_participant(ctx, "+14155552671", "Acme Roofing")

    assert dialed is True
    request = ctx.api.sip.create_sip_participant.await_args.args[0]
    assert request.sip_trunk_id == "ST_primary"
    assert request.sip_call_to == "+14155552671"
    assert request.sip_number == "+12025550123"
