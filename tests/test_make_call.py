import re

import pytest

from make_call import build_dispatch_metadata, build_room_name, validate_phone_number


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
