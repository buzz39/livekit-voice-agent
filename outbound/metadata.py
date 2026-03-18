import json
import logging
from typing import Dict, Any

logger = logging.getLogger("outbound.metadata")

def _parse_metadata(raw_metadata: Any) -> Dict[str, Any]:
    """
    Parse JSON metadata from bytes or strings, unwrap nested ``metadata`` payloads, and return a dict.

    When both outer and nested metadata contain the same key, the nested value wins.
    Invalid or non-dict payloads are treated as empty metadata, and nested parse failures are logged at debug level.
    """
    if not raw_metadata:
        return {}

    meta = raw_metadata
    if isinstance(meta, (bytes, bytearray)):
        meta = meta.decode("utf-8")

    parsed = json.loads(meta)
    if not isinstance(parsed, dict):
        return {}

    nested = parsed.get("metadata")
    if nested:
        try:
            if isinstance(nested, (bytes, bytearray)):
                nested = nested.decode("utf-8")
            nested_metadata = json.loads(nested)
            if isinstance(nested_metadata, dict):
                parsed = {**parsed, **nested_metadata}
                parsed.pop("metadata", None)
        except Exception as e:
            logger.debug(f"[metadata] Failed to parse nested metadata: {e}")

    return parsed


def extract_metadata(ctx: Any) -> Dict[str, Any]:
    """
    Extracts and normalizes metadata from ctx.job.metadata or ctx.room.metadata.
    """
    initial_metadata: Dict[str, Any] = {}

    if getattr(ctx, "job", None) and getattr(ctx.job, "metadata", None):
        try:
            job_metadata = _parse_metadata(ctx.job.metadata)
            initial_metadata.update(job_metadata)
            logger.info(f"[metadata] Loaded from ctx.job.metadata: {job_metadata}")
        except Exception as e:
            logger.warning(f"[metadata] Failed to parse ctx.job.metadata: {e}")

    if getattr(ctx, "room", None) and getattr(ctx.room, "metadata", None):
        try:
            room_metadata = _parse_metadata(ctx.room.metadata)
            initial_metadata.update(room_metadata)
            logger.info(f"[metadata] Loaded from ctx.room.metadata: {room_metadata}")
        except Exception as e:
            logger.warning(f"[metadata] Failed to parse ctx.room.metadata: {e}")

    return initial_metadata

def get_required_fields(metadata: Dict[str, Any]):
    """
    Extracts phone_number, business_name, and agent_slug from normalized metadata.
    """
    phone_number = metadata.get("phone_number", "LOCAL_TEST_NUMBER")
    business_name = metadata.get("business_name", "there")
    agent_slug = metadata.get("agent_slug", "default_roofing_agent")

    return phone_number, business_name, agent_slug
