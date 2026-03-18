# System Architecture Audit Report

**Date:** 2026-03-18  
**Auditor Role:** Senior Solution Architect  
**Repository:** `buzz39/livekit-voice-agent`  
**Scope:** Full-stack security, architecture, code quality, and production-readiness review

---

## Executive Summary

This is a **LiveKit-based AI voice agent platform** that handles both inbound and outbound phone calls via SIP, with an AI conversation engine (OpenAI/Groq LLM, Deepgram STT, Cartesia TTS), a React dashboard, PostgreSQL persistence, and n8n workflow integration via MCP.

The system demonstrates solid **proof-of-concept** engineering but has several issues that must be addressed before production deployment. This audit identified **4 critical**, **4 high**, and **8 medium** findings. The most urgent fixes have been applied in this PR.

---

## Fixes Applied in This PR

### 🔴 CRITICAL — Fixed

| # | Issue | File | Fix |
|---|-------|------|-----|
| 1 | **Hardcoded production credentials** in `.env.example` (LiveKit API keys, Vobiz SIP password) | `.env.example` | Replaced all real credentials with placeholder values. **Original credentials should be rotated immediately.** |
| 2 | **Code injection via `exec()`** — MCP tool names/parameters from untrusted n8n endpoint were injected into dynamically generated Python code | `mcp_integration.py` | Replaced `exec()` with a closure-based factory pattern. Added `_validate_identifier()` that rejects names not matching `^[A-Za-z_][A-Za-z0-9_]*$`. |
| 3 | **No input validation** on outbound call phone numbers — any string accepted, could trigger expensive SIP calls | `server.py` | Added E.164 format validation (`^\+[1-9]\d{1,14}$`) via Pydantic `field_validator`. |
| 4 | **Hardcoded production URL** (`https://livekit-outbound-api.tinysaas.fun`) in recording URL rewriting | `server.py` | Replaced with configurable `API_BASE_URL` environment variable; falls back to relative path. |

### 🟡 MEDIUM — Fixed

| # | Issue | File | Fix |
|---|-------|------|-----|
| 5 | **Unused dependency** `aiosqlite` in `pyproject.toml` (project only uses `asyncpg` for PostgreSQL) | `pyproject.toml` | Removed `aiosqlite>=0.22.0`. |
| 6 | **Health check returning static `{"status": "ok"}`** without verifying database connectivity | `server.py` | Enhanced `/health` to probe DB with `SELECT 1`; returns `"degraded"` status when DB is unavailable. |

---

## Remaining Findings (Not Fixed — Require Broader Changes)

### 🔴 CRITICAL — Needs Attention

| # | Issue | Location | Recommendation |
|---|-------|----------|----------------|
| C1 | **CORS wildcard `allow_origins=["*"]`** allows any website to call the API | `server.py:51` | Set to specific frontend origin(s) via `ALLOWED_ORIGINS` env var. |
| C2 | **No authentication on `/dashboard/*` endpoints** — call recordings, transcripts, and PII accessible without auth | `server.py`, `audio_router.py` | Add auth middleware (Stack Auth JWT validation) to all `/dashboard/*` and `/api/*` routes. |

### 🟠 HIGH — Recommended Before Rollout

| # | Issue | Location | Recommendation |
|---|-------|----------|----------------|
| H1 | **In-memory `_active_agent_config`** not persisted — lost on restart, race conditions with multiple workers | `server.py:80` | Persist to database; load on startup. |
| H2 | **Webhook URLs not validated** — could target internal/private IPs (SSRF risk) | `webhook_dispatcher.py` | Validate URLs: enforce HTTPS, block private IP ranges. |
| H3 | **Phone numbers stored in plain text** — PII exposure risk if DB is compromised | `neon_db.py` | Consider encryption at rest for PII fields. |
| H4 | **No rate limiting** on `/outbound-call` — could be flooded to incur telephony costs | `server.py` | Add per-IP or per-user rate limiting. |

### 🟡 MEDIUM — Short-Term Improvements

| # | Issue | Location | Recommendation |
|---|-------|----------|----------------|
| M1 | **Broad exception handling** (`except Exception` with logging only) in 24+ places | Multiple files | Catch specific exceptions; add structured error responses. |
| M2 | **No database transactions** across multi-step operations (e.g., contact upsert + call log) | `neon_db.py`, agent files | Wrap related operations in transactions. |
| M3 | **No graceful shutdown** — container killed immediately; active calls not drained | `start.sh` | Add SIGTERM handlers; drain active sessions before exit. |
| M4 | **Server and agent worker in single container** — can't scale independently | `start.sh`, `Dockerfile` | Separate into two services with individual Dockerfiles. |
| M5 | **No caching** — agent config and prompts fetched from DB on every call | Agent files | Add in-memory cache with TTL (or Redis). |
| M6 | **`/dashboard/appointments` returns mock data** | `server.py:363-421` | Implement with real database table or remove endpoint. |
| M7 | **Inconsistent logging** — mix of `logger.*` and `print()`, some logs expose PII | Multiple files | Standardize with structured JSON logging; redact PII. |
| M8 | **Test coverage ~15%** — no integration tests, no API endpoint tests, no DB tests | `tests/` | Target 70%+ coverage; add integration and API tests. |

---

## Architecture Observations

### What's Done Well ✅

- **Parameterized SQL queries** throughout `neon_db.py` — no SQL injection risk
- **Connection pooling** via `asyncpg` with configurable pool size
- **Modular outbound call logic** in `outbound/` package with clear separation
- **Webhook system** with retry logic and exponential backoff
- **Non-privileged Docker user** for container security
- **UV-based dependency management** with lockfile for reproducible builds
- **Pydantic models** for API request validation

### Architecture Gaps

1. **No service boundaries** — `server.py` mixes API routing, business logic, and S3 operations
2. **No observability foundation** — Whispey is optional with no fallback; no Prometheus metrics
3. **No audit logging** — no record of who accessed recordings or changed configuration
4. **No circuit breakers** for external API calls (LiveKit, n8n, S3)
5. **Multi-tenancy partially implemented** — `owner_id` columns added but not enforced

---

## Production Readiness Scorecard

| Category | Score | Notes |
|----------|-------|-------|
| **Security** | 5/10 → **7/10** | Credential leak and code injection fixed; auth + CORS still needed |
| **Architecture** | 5/10 | Good patterns exist; needs service boundaries and state management |
| **Code Quality** | 6/10 | Clean code; needs error handling and validation improvements |
| **Testing** | 3/10 | Basic unit tests exist; needs integration and API tests |
| **Observability** | 4/10 | Optional Whispey only; needs metrics and structured logging |
| **Scalability** | 3/10 | In-memory state and single-container design limit scaling |
| **DevOps** | 5/10 | Docker-ready; needs health checks (fixed), graceful shutdown |

---

## Recommended Priority Roadmap

### Phase 1 — Security Hardening (1–2 days)
- [ ] Rotate all exposed credentials (LiveKit, Vobiz, S3)
- [ ] Configure `ALLOWED_ORIGINS` for CORS
- [ ] Add auth middleware to `/dashboard/*` routes
- [ ] Validate webhook URLs (block private IPs)
- [ ] Add rate limiting on `/outbound-call`

### Phase 2 — Reliability (1 week)
- [ ] Persist `_active_agent_config` to database
- [ ] Add graceful shutdown handlers (SIGTERM)
- [ ] Separate server and agent into individual containers
- [ ] Add database transactions for multi-step operations
- [ ] Improve error handling (specific exceptions, error codes)

### Phase 3 — Observability & Testing (2 weeks)
- [ ] Add structured JSON logging with PII redaction
- [ ] Export Prometheus metrics (call count, duration, error rate)
- [ ] Add OpenTelemetry distributed tracing
- [ ] Increase test coverage to 70%+ (integration + API tests)
- [ ] Add database migration tool (Alembic)

### Phase 4 — Scale & Performance (2–4 weeks)
- [ ] Add Redis caching for config and prompts
- [ ] Implement connection pool health monitoring
- [ ] Add circuit breakers for external services
- [ ] Complete multi-tenancy enforcement (row-level security)
- [ ] Replace mock appointments endpoint with real implementation
