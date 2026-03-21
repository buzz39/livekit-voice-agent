"""
Smoke tests for CI/CD pre-deployment gate.

These tests verify that the FastAPI server responds on critical
endpoints, config defaults are sane, and security invariants hold.
They run WITHOUT external services (LiveKit, Neon DB, S3) by relying
on the "degraded" fallback paths already in the codebase.

Heavy module import tests are skipped – the livekit-agents SDK is
large and import-time checks are covered by the Docker build step.
"""

import importlib

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# 1. Lightweight module imports (fast, no heavy SDK deps)
# ---------------------------------------------------------------------------

class TestModuleImports:
    """Verify light modules import cleanly."""

    @pytest.mark.parametrize(
        "module",
        [
            "config",
            "outbound.config",
            "outbound.metadata",
            "mcp_integration",
            "webhook_dispatcher",
        ],
    )
    def test_module_imports(self, module):
        mod = importlib.import_module(module)
        assert mod is not None


# ---------------------------------------------------------------------------
# 2. FastAPI app smoke – health & key routes
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    """TestClient against the FastAPI app (no real DB / LiveKit)."""
    from server import app

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


class TestHealthEndpoint:
    """Health check must always respond, even without a database."""

    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_body_has_required_keys(self, client):
        body = client.get("/health").json()
        assert "status" in body
        assert "database" in body

    def test_health_status_value(self, client):
        body = client.get("/health").json()
        assert body["status"] in ("ok", "degraded")


class TestOutboundCallValidation:
    """POST /outbound-call must reject bad input before touching LiveKit."""

    def test_missing_body_returns_422(self, client):
        resp = client.post("/outbound-call")
        assert resp.status_code == 422

    def test_invalid_phone_returns_422(self, client):
        resp = client.post(
            "/outbound-call",
            json={
                "phone_number": "not-a-number",
                "business_name": "Acme",
                "agent_slug": "roofing_agent",
            },
        )
        assert resp.status_code == 422

    def test_valid_phone_accepted(self, client):
        """A well-formed request should be accepted (200) even without
        LiveKit credentials – the actual call is a background task."""
        resp = client.post(
            "/outbound-call",
            json={
                "phone_number": "+14155552671",
                "business_name": "Acme Roofing",
                "agent_slug": "roofing_agent",
            },
        )
        assert resp.status_code == 200

    def test_valid_from_number_accepted(self, client):
        """A request with a valid from_number should be accepted."""
        resp = client.post(
            "/outbound-call",
            json={
                "phone_number": "+14155552671",
                "business_name": "Acme Roofing",
                "agent_slug": "roofing_agent",
                "from_number": "+911171366938",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["from_number"] == "+911171366938"

    def test_invalid_from_number_returns_422(self, client):
        """An invalid from_number should be rejected."""
        resp = client.post(
            "/outbound-call",
            json={
                "phone_number": "+14155552671",
                "business_name": "Acme Roofing",
                "agent_slug": "roofing_agent",
                "from_number": "not-a-number",
            },
        )
        assert resp.status_code == 422

    def test_null_from_number_accepted(self, client):
        """Omitting from_number should be fine (backward compatible)."""
        resp = client.post(
            "/outbound-call",
            json={
                "phone_number": "+14155552671",
                "business_name": "Acme Roofing",
                "agent_slug": "roofing_agent",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["from_number"] is None


class TestServerNoSIPParticipantCreation:
    """server.py must NOT create SIP participants — only the agent does."""

    def test_no_create_sip_participant_import(self):
        """CreateSIPParticipantRequest should not be imported in server.py."""
        import server as srv
        import inspect

        source = inspect.getsource(srv)
        assert "CreateSIPParticipantRequest" not in source

    def test_no_sip_caller_identity(self):
        """The 'sip-caller-' identity prefix should not appear in server.py."""
        import server as srv
        import inspect

        source = inspect.getsource(srv)
        assert "sip-caller-" not in source


class TestDashboardEndpoints:
    """Dashboard read endpoints must be routed (not 404)."""

    def test_dashboard_stats(self, client):
        resp = client.get("/dashboard/stats")
        assert resp.status_code != 404

    def test_dashboard_calls(self, client):
        resp = client.get("/dashboard/calls")
        assert resp.status_code != 404

    def test_dashboard_prompts(self, client):
        resp = client.get("/dashboard/prompts")
        assert resp.status_code != 404


class TestAgentConfigEndpoint:
    """GET /api/config must return a JSON object."""

    def test_get_config_returns_200(self, client):
        resp = client.get("/api/config")
        assert resp.status_code == 200
        assert isinstance(resp.json(), dict)


# ---------------------------------------------------------------------------
# 3. Config sanity
# ---------------------------------------------------------------------------

class TestConfigDefaults:
    """Ensure config.py provides sane defaults without env vars."""

    def test_default_llm_provider(self):
        from config import DEFAULT_LLM_PROVIDER
        assert DEFAULT_LLM_PROVIDER

    def test_default_stt_model(self):
        from config import DEFAULT_STT_MODEL
        assert DEFAULT_STT_MODEL

    def test_default_tts_provider(self):
        from config import DEFAULT_TTS_PROVIDER
        assert DEFAULT_TTS_PROVIDER


# ---------------------------------------------------------------------------
# 4. Security invariants
# ---------------------------------------------------------------------------

class TestSecurityInvariants:
    """Quick re-check of security-critical validation that must never regress."""

    def test_e164_regex_rejects_plain_digits(self):
        from server import _E164_RE
        assert not _E164_RE.match("4155552671")

    def test_e164_regex_accepts_valid(self):
        from server import _E164_RE
        assert _E164_RE.match("+14155552671")

    def test_mcp_identifier_rejects_injection(self):
        from mcp_integration import MCPToolsIntegration
        mcp = MCPToolsIntegration(mcp_url="https://example.com/mcp/test")
        with pytest.raises(ValueError):
            mcp._validate_identifier("__import__('os').system('rm -rf /')")
