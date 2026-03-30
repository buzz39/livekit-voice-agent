import pytest
from unittest.mock import AsyncMock

from outbound.tenant_profile import get_tenant_profile, refresh_tenant_config_cache


@pytest.mark.asyncio
async def test_get_tenant_profile_returns_empty_without_tenant_id():
    profile = await get_tenant_profile(None)
    assert profile == {}


@pytest.mark.asyncio
async def test_get_tenant_profile_uses_db_first(monkeypatch):
    monkeypatch.setenv(
        "TENANT_CONFIGS_JSON",
        '{"acme":{"agent_slug":"env-agent","workflow_policy":"env"}}',
    )
    refresh_tenant_config_cache()

    mock_db = AsyncMock()
    mock_db.get_tenant_config = AsyncMock(
        return_value={
            "tenant_id": "acme",
            "agent_slug": "db-agent",
            "workflow_policy": "db-policy",
            "routing_policy": {"preferred_trunks": ["VOBIZ_PRIMARY"]},
            "ai_overrides": {"tts_language": "hi-IN"},
            "opening_line": "Namaste from DB",
            "is_active": True,
        }
    )
    mock_db.close = AsyncMock()

    async def fake_get_db():
        return mock_db

    monkeypatch.setattr("outbound.tenant_profile.get_db", fake_get_db)

    profile = await get_tenant_profile("acme")

    assert profile["agent_slug"] == "db-agent"
    assert profile["workflow_policy"] == "db-policy"
    assert profile["routing_policy"]["preferred_trunks"][0] == "VOBIZ_PRIMARY"
    mock_db.get_tenant_config.assert_awaited_once_with("acme")
    mock_db.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_tenant_profile_falls_back_to_env_when_db_fails(monkeypatch):
    monkeypatch.setenv(
        "TENANT_CONFIGS_JSON",
        '{"acme":{"agent_slug":"env-agent","workflow_policy":"standard","opening_line":"Hello"}}',
    )
    refresh_tenant_config_cache()

    async def failing_get_db():
        raise RuntimeError("db unavailable")

    monkeypatch.setattr("outbound.tenant_profile.get_db", failing_get_db)

    profile = await get_tenant_profile("acme")

    assert profile["agent_slug"] == "env-agent"
    assert profile["workflow_policy"] == "standard"
    assert profile["opening_line"] == "Hello"
