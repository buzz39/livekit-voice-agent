"""
Tests for security-critical fixes discovered during the architecture audit.

Covers:
- MCP tool name/param sanitization (no exec() code injection)
- Phone number E.164 validation on the outbound-call endpoint
- Health check endpoint returns DB status
"""

import re
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# MCP Integration – identifier validation
# ---------------------------------------------------------------------------

class TestMCPIdentifierValidation:
    """Verify that create_livekit_tool rejects unsafe identifiers."""

    def _make_integration(self):
        from mcp_integration import MCPToolsIntegration
        return MCPToolsIntegration(mcp_url="https://example.com/mcp/test")

    def test_valid_tool_name_accepted(self):
        integration = self._make_integration()
        assert integration._validate_identifier("book_appointment") == "book_appointment"

    def test_tool_name_with_injection_rejected(self):
        integration = self._make_integration()
        with pytest.raises(ValueError, match="Unsafe identifier"):
            integration._validate_identifier("__import__('os').system('rm -rf /')")

    def test_tool_name_with_quotes_rejected(self):
        integration = self._make_integration()
        with pytest.raises(ValueError, match="Unsafe identifier"):
            integration._validate_identifier("tool'; DROP TABLE users;--")

    def test_param_name_with_spaces_rejected(self):
        integration = self._make_integration()
        with pytest.raises(ValueError, match="Unsafe identifier"):
            integration._validate_identifier("param name")

    def test_empty_identifier_rejected(self):
        integration = self._make_integration()
        with pytest.raises(ValueError, match="Unsafe identifier"):
            integration._validate_identifier("")

    def test_numeric_start_rejected(self):
        integration = self._make_integration()
        with pytest.raises(ValueError, match="Unsafe identifier"):
            integration._validate_identifier("123abc")

    def test_create_tool_rejects_bad_tool_name(self):
        integration = self._make_integration()
        bad_def = {
            "name": "bad-name!",
            "description": "A malicious tool",
            "inputSchema": {"properties": {}, "required": []},
        }
        with pytest.raises(ValueError, match="Unsafe identifier"):
            integration.create_livekit_tool(bad_def)

    def test_create_tool_rejects_bad_param_name(self):
        integration = self._make_integration()
        bad_def = {
            "name": "good_name",
            "description": "Tool with bad param",
            "inputSchema": {
                "properties": {
                    "ok_param": {"type": "string"},
                    "bad param!": {"type": "string"},
                },
                "required": [],
            },
        }
        with pytest.raises(ValueError, match="Unsafe identifier"):
            integration.create_livekit_tool(bad_def)


# ---------------------------------------------------------------------------
# Phone number E.164 validation
# ---------------------------------------------------------------------------

class TestPhoneNumberValidation:
    """Verify that OutboundCallRequest validates phone numbers."""

    def test_valid_e164_accepted(self):
        from server import OutboundCallRequest
        req = OutboundCallRequest(
            phone_number="+14155552671",
            business_name="Acme Corp",
        )
        assert req.phone_number == "+14155552671"

    def test_valid_indian_number_accepted(self):
        from server import OutboundCallRequest
        req = OutboundCallRequest(
            phone_number="+911234567890",
            business_name="Acme Corp",
        )
        assert req.phone_number == "+911234567890"

    def test_missing_plus_rejected(self):
        from server import OutboundCallRequest
        with pytest.raises(ValidationError, match="E.164"):
            OutboundCallRequest(
                phone_number="14155552671",
                business_name="Acme Corp",
            )

    def test_alphabetic_rejected(self):
        from server import OutboundCallRequest
        with pytest.raises(ValidationError, match="E.164"):
            OutboundCallRequest(
                phone_number="+1415ABCDEFG",
                business_name="Acme Corp",
            )

    def test_empty_string_rejected(self):
        from server import OutboundCallRequest
        with pytest.raises(ValidationError, match="E.164"):
            OutboundCallRequest(
                phone_number="",
                business_name="Acme Corp",
            )

    def test_too_long_rejected(self):
        from server import OutboundCallRequest
        with pytest.raises(ValidationError, match="E.164"):
            OutboundCallRequest(
                phone_number="+12345678901234567890",
                business_name="Acme Corp",
            )


# ---------------------------------------------------------------------------
# Health check endpoint
# ---------------------------------------------------------------------------

class TestHealthCheck:
    """Verify health check returns database connectivity status."""

    @pytest.mark.asyncio
    async def test_health_ok_with_db(self):
        from server import app, health_check
        import server

        mock_db = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(return_value=AsyncContextManager(mock_conn))
        mock_db.pool = mock_pool

        original = server.db_instance
        server.db_instance = mock_db
        try:
            result = await health_check()
            assert result["status"] == "ok"
            assert result["database"] == "connected"
        finally:
            server.db_instance = original

    @pytest.mark.asyncio
    async def test_health_degraded_without_db(self):
        from server import health_check
        import server

        original = server.db_instance
        server.db_instance = None
        try:
            result = await health_check()
            assert result["status"] == "degraded"
            assert result["database"] == "not_configured"
        finally:
            server.db_instance = original


# Minimal async context manager helper for mocking pool.acquire()
class AsyncContextManager:
    def __init__(self, value):
        self._value = value

    async def __aenter__(self):
        return self._value

    async def __aexit__(self, *args):
        pass
