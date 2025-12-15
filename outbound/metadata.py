import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("outbound.metadata")

def extract_metadata(ctx: Any) -> Dict[str, Any]:
    """
    Extracts and normalizes metadata from ctx.job.metadata or ctx.room.metadata.
    """
    initial_metadata = {}

    # --- 1. Try ctx.job.metadata ---
    if getattr(ctx, "job", None) and getattr(ctx.job, "metadata", None):
        try:
            meta = ctx.job.metadata
            if isinstance(meta, (bytes, bytearray)):
                meta = meta.decode("utf-8")
            initial_metadata = json.loads(meta)
            logger.info(f"[metadata] Loaded from ctx.job.metadata: {initial_metadata}")
        except Exception as e:
            logger.warning(f"[metadata] Failed to parse ctx.job.metadata: {e}")

    # --- 2. If empty, try ctx.room.metadata ---
    if not initial_metadata and getattr(ctx, "room", None) and getattr(ctx.room, "metadata", None):
        try:
            meta = ctx.room.metadata
            if isinstance(meta, (bytes, bytearray)):
                meta = meta.decode("utf-8")
            initial_metadata = json.loads(meta)
            logger.info(f"[metadata] Loaded from ctx.room.metadata: {initial_metadata}")
        except Exception as e:
            logger.warning(f"[metadata] Failed to parse ctx.room.metadata: {e}")

    # --- 3. Normalize nested metadata: sometimes stored as {"metadata": "{...json...}"} ---
    if isinstance(initial_metadata, dict) and "metadata" in initial_metadata:
        try:
            nested = initial_metadata["metadata"]
            if isinstance(nested, (bytes, bytearray)):
                nested = nested.decode("utf-8")
            initial_metadata = json.loads(nested)
            logger.info(f"[metadata] Loaded nested metadata: {initial_metadata}")
        except Exception:
            pass

    return initial_metadata

def get_required_fields(metadata: Dict[str, Any]):
    """
    Extracts phone_number, business_name, and agent_slug from normalized metadata.
    """
    phone_number = metadata.get("phone_number", "LOCAL_TEST_NUMBER")
    business_name = metadata.get("business_name", "there")
    agent_slug = metadata.get("agent_slug", "default_roofing_agent")

    return phone_number, business_name, agent_slug
