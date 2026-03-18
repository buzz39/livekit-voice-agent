import json
from types import SimpleNamespace

from outbound.metadata import extract_metadata


def test_extract_metadata_merges_job_and_room_metadata():
    ctx = SimpleNamespace(
        job=SimpleNamespace(
            metadata=json.dumps(
                {
                    "phone_number": "+14155550100",
                    "agent_slug": "job-agent",
                    "llm_provider": "openai",
                }
            )
        ),
        room=SimpleNamespace(
            metadata=json.dumps(
                {
                    "agent_slug": "room-agent",
                    "business_name": "Room Co",
                    "tts_provider": "cartesia",
                }
            )
        ),
    )

    metadata = extract_metadata(ctx)

    assert metadata == {
        "phone_number": "+14155550100",
        "agent_slug": "room-agent",
        "llm_provider": "openai",
        "business_name": "Room Co",
        "tts_provider": "cartesia",
    }


def test_extract_metadata_parses_nested_metadata_payload():
    ctx = SimpleNamespace(
        job=SimpleNamespace(
            metadata=json.dumps(
                {
                    "metadata": json.dumps(
                        {
                            "phone_number": "+14155550101",
                            "business_name": "Nested Co",
                        }
                    )
                }
            )
        ),
        room=SimpleNamespace(metadata=None),
    )

    metadata = extract_metadata(ctx)

    assert metadata == {
        "phone_number": "+14155550101",
        "business_name": "Nested Co",
    }
