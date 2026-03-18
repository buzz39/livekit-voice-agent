import argparse
import asyncio
import json
import os
import random
import re

from dotenv import load_dotenv
from livekit import api

import config as app_config

load_dotenv()

_E164_RE = re.compile(r"^\+[1-9]\d{1,14}$")


def validate_phone_number(phone_number: str) -> str:
    phone_number = phone_number.strip()
    if not _E164_RE.match(phone_number):
        raise ValueError("Phone number must be in E.164 format (e.g. +14155552671).")
    return phone_number


def build_room_name(phone_number: str) -> str:
    return f"call-{phone_number.replace('+', '')}-{random.randint(1000, 9999)}"


def build_dispatch_metadata(phone_number: str, business_name: str, agent_slug: str) -> dict:
    return {
        "phone_number": phone_number,
        "business_name": business_name,
        "agent_slug": agent_slug,
    }


async def dispatch_call(phone_number: str, business_name: str, agent_slug: str, agent_name: str) -> str:
    url = os.getenv("LIVEKIT_URL")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")

    if not (url and api_key and api_secret):
        raise RuntimeError("LiveKit credentials missing in the environment.")

    room_name = build_room_name(phone_number)
    metadata = build_dispatch_metadata(phone_number, business_name, agent_slug)

    async with api.LiveKitAPI(url=url, api_key=api_key, api_secret=api_secret) as lk:
        await lk.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=agent_name,
                room=room_name,
                metadata=json.dumps(metadata),
            )
        )

    return room_name


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dispatch an outbound call via the LiveKit voice agent.")
    parser.add_argument("--to", required=True, help="E.164 phone number to call (for example +14155552671)")
    parser.add_argument("--business-name", default="there", help="Business name injected into call metadata")
    parser.add_argument("--agent-slug", default="default_roofing_agent", help="Agent slug for DB-driven prompts/config")
    parser.add_argument("--agent-name", default=app_config.OUTBOUND_AGENT_NAME, help="LiveKit agent worker name to dispatch")
    return parser


async def main() -> int:
    args = create_parser().parse_args()

    try:
        phone_number = validate_phone_number(args.to)
        room_name = await dispatch_call(
            phone_number=phone_number,
            business_name=args.business_name,
            agent_slug=args.agent_slug,
            agent_name=args.agent_name,
        )
    except Exception as exc:
        print(f"Error: {exc}")
        return 1

    print(f"Call dispatched successfully to {phone_number}")
    print(f"Room: {room_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
