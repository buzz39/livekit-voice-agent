import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock


@pytest.fixture
def client_with_db(monkeypatch):
    import server

    mock_db = AsyncMock()
    mock_db.get_all_tenant_configs = AsyncMock(
        return_value=[
            {
                'tenant_id': 'acme',
                'display_name': 'Acme Roofing',
                'agent_slug': 'default_roofing_agent',
                'workflow_policy': 'standard',
                'routing_policy': {'preferred_trunks': ['TRUNK_A']},
                'ai_overrides': {'tts_language': 'hi-IN'},
                'opening_line': 'Namaste',
                'is_active': True,
            }
        ]
    )
    mock_db.get_tenant_config = AsyncMock(
        return_value={
            'tenant_id': 'acme',
            'display_name': 'Acme Roofing',
            'agent_slug': 'default_roofing_agent',
            'workflow_policy': 'standard',
            'routing_policy': {'preferred_trunks': ['TRUNK_A']},
            'ai_overrides': {'tts_language': 'hi-IN'},
            'opening_line': 'Namaste',
            'is_active': True,
        }
    )
    mock_db.upsert_tenant_config = AsyncMock(return_value='acme')
    mock_db.delete_tenant_config = AsyncMock(return_value=None)
    mock_db.get_tenant_api_key = AsyncMock(return_value='tenant-key')
    mock_db.get_call_stats = AsyncMock(return_value={'total_calls': 1, 'avg_duration': 10})
    mock_db.get_daily_call_volume = AsyncMock(return_value=[{'date': '2026-03-29', 'count': 1, 'avg_duration': 10, 'completed': 1, 'failed': 0}])

    async def fake_get_db():
        return mock_db

    monkeypatch.setattr(server, 'get_db', fake_get_db)
    monkeypatch.setattr(server, 'API_SECRET_KEY', '')
    monkeypatch.setattr(server, '_TENANT_API_KEYS', {})
    monkeypatch.setenv('RBAC_ENFORCED', 'false')

    with TestClient(server.app, raise_server_exceptions=False) as c:
        server.db_instance = mock_db
        yield c, mock_db


def test_get_tenants_returns_list(client_with_db):
    client, mock_db = client_with_db
    resp = client.get('/dashboard/tenants')
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert body[0]['tenant_id'] == 'acme'
    mock_db.get_all_tenant_configs.assert_awaited_once()


def test_get_single_tenant(client_with_db):
    client, mock_db = client_with_db
    resp = client.get('/dashboard/tenant/acme')
    assert resp.status_code == 200
    assert resp.json()['tenant_id'] == 'acme'
    mock_db.get_tenant_config.assert_awaited_once_with('acme')


def test_upsert_tenant(client_with_db):
    client, mock_db = client_with_db
    payload = {
        'tenant_id': 'acme',
        'display_name': 'Acme Roofing',
        'agent_slug': 'default_roofing_agent',
        'workflow_policy': 'standard',
        'routing_policy': {'preferred_trunks': ['TRUNK_A']},
        'ai_overrides': {'tts_language': 'hi-IN'},
        'opening_line': 'Namaste',
        'api_key': 'tenant-key',
        'is_active': True,
    }
    resp = client.post('/dashboard/tenants', json=payload)
    assert resp.status_code == 200
    assert resp.json()['tenant_id'] == 'acme'
    mock_db.upsert_tenant_config.assert_awaited_once()


def test_delete_tenant(client_with_db):
    client, mock_db = client_with_db
    resp = client.delete('/dashboard/tenant/acme')
    assert resp.status_code == 200
    assert resp.json()['status'] == 'deleted'
    mock_db.delete_tenant_config.assert_awaited_once_with('acme')


def test_tenant_api_key_checked_from_db(client_with_db):
    client, _ = client_with_db
    resp = client.get(
        '/dashboard/tenants',
        headers={
            'x-tenant-id': 'acme',
            'x-tenant-api-key': 'tenant-key',
        },
    )
    assert resp.status_code == 200


def test_tenant_api_key_rejects_invalid_key(client_with_db):
    client, _ = client_with_db
    resp = client.get(
        '/dashboard/tenants',
        headers={
            'x-tenant-id': 'acme',
            'x-tenant-api-key': 'wrong-key',
        },
    )
    assert resp.status_code == 401


def test_stats_scoped_by_tenant(client_with_db):
    client, mock_db = client_with_db
    resp = client.get('/dashboard/stats?days=14&tenant_id=acme')
    assert resp.status_code == 200
    mock_db.get_call_stats.assert_awaited_with(days=14, tenant_id='acme')


def test_analytics_volume_scoped_by_tenant(client_with_db):
    client, mock_db = client_with_db
    resp = client.get('/dashboard/analytics/volume?days=21&tenant_id=acme')
    assert resp.status_code == 200
    mock_db.get_daily_call_volume.assert_awaited_with(days=21, tenant_id='acme')
