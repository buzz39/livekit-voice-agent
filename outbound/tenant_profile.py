import json
import logging
import os
from functools import lru_cache
from typing import Any, Dict, Optional

from neon_db import get_db

logger = logging.getLogger("outbound.tenant")


@lru_cache(maxsize=1)
def _load_tenant_config_map() -> Dict[str, Dict[str, Any]]:
    """Load tenant configuration map from TENANT_CONFIGS_JSON.

    Expected shape:
    {
      "tenant-id": {
        "agent_slug": "default_roofing_agent",
        "workflow_policy": "standard",
        "routing_policy": {"preferred_trunks": ["TRUNK_A", "TRUNK_B"]},
        "ai_overrides": {"tts_voice": "simran", "tts_language": "hi-IN"},
        "opening_line": "..."
      }
    }
    """
    raw = os.getenv("TENANT_CONFIGS_JSON", "").strip()
    if not raw:
        return {}

    try:
        parsed = json.loads(raw)
    except Exception as exc:
        logger.error("Invalid TENANT_CONFIGS_JSON: %s", exc)
        return {}

    if not isinstance(parsed, dict):
        logger.error("TENANT_CONFIGS_JSON must be a JSON object mapping tenant_id to profile")
        return {}

    out: Dict[str, Dict[str, Any]] = {}
    for tenant_id, profile in parsed.items():
        if not isinstance(tenant_id, str) or not tenant_id.strip():
            continue
        if isinstance(profile, dict):
            out[tenant_id.strip()] = profile
    return out


def refresh_tenant_config_cache() -> None:
    _load_tenant_config_map.cache_clear()


def _extract_runtime_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Return only runtime-relevant tenant fields consumed by the outbound agent."""
    out: Dict[str, Any] = {}
    for key in ("agent_slug", "workflow_policy", "routing_policy", "ai_overrides", "opening_line"):
        value = profile.get(key)
        if value is not None:
            out[key] = value
    return out


async def get_tenant_profile(tenant_id: Optional[str]) -> Dict[str, Any]:
    if not tenant_id:
        return {}

    # Primary source: tenant_configs table
    try:
        db = await get_db()
        try:
            profile = await db.get_tenant_config(tenant_id)
            if isinstance(profile, dict) and profile.get("is_active", True):
                return _extract_runtime_profile(profile)
        finally:
            await db.close()
    except Exception as exc:
        logger.debug("Tenant profile DB lookup failed for %s: %s", tenant_id, exc)

    # Fallback source: environment JSON map
    profile = _load_tenant_config_map().get(tenant_id)
    if isinstance(profile, dict):
        return _extract_runtime_profile(profile)
    return {}
