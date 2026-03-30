# 6-Week Implementation Plan: Sarvam + Vobiz + LiveKit IVR SaaS

## Plan Goal
Ship a production-ready MVP for an India-first AI voice IVR SaaS with multi-tenant support, reliable telephony, and Sarvam-first AI execution.

## Scope Guardrails
- In scope: voice IVR flows, inbound/outbound call handling, workflow tools, analytics dashboard, tenant configs, pilot readiness.
- Out of scope (for 6 weeks): full enterprise SSO suite, advanced billing marketplace, omnichannel chat.

## Team Assumption
- 1 product/founder, 1 full-stack engineer, 1 voice platform engineer, 1 QA/ops contributor (part-time acceptable).

## Week-by-Week Plan

## Week 1: Platform Baseline and Environment Hardening
### Objectives
- Stabilize local and cloud dev environments.
- Lock provider contracts and env strategy.

### Deliverables
- Environment profiles: local/dev/staging/prod.
- Provider wiring documented for Vobiz trunking and Sarvam keys.
- Health endpoints and startup self-checks for missing/invalid config.
- Process manager setup for API server and agent worker.

### Exit Criteria
- Repeatable boot sequence with one command per environment.
- Basic inbound and outbound test calls complete successfully.

## Week 2: Core IVR Engine and Conversation Reliability
### Objectives
- Finalize call state machine and guardrails.
- Implement robust response timing behavior.

### Deliverables
- State transitions persisted for every call.
- LLM response watchdog with spoken fallback.
- Stage timeouts for session start and opening playout.
- DTMF + voice hybrid intent routing for first-level IVR menu.

### Exit Criteria
- No dead-air > 3 seconds in standard paths.
- All failed calls include structured reason codes.

## Week 3: Multi-Tenant SaaS Foundations
### Objectives
- Add tenant-aware configuration and isolation.
- Enable tenant-specific prompts and voice profiles.

### Deliverables
- Tenant model with scoped configs: language, speaker, routing, workflow policy.
- Tenant-level API keys/secrets handling via environment or secret manager abstraction.
- RBAC baseline (admin/operator/viewer) for dashboard.
- Tenant-aware call log views and filtering.

### Exit Criteria
- Two tenants can run independent workflows without config bleed.

## Week 4: Workflow Tools and Business Integrations
### Objectives
- Make IVR useful for real operations.
- Add deterministic tool-calling for external systems.

### Deliverables
- Tool adapters: appointment booking, lead capture, CRM note push.
- Structured function schemas and validation.
- Retry and idempotency strategy for side-effecting operations.
- Audit trail linking each tool call to call/session ids.

### Exit Criteria
- At least 3 end-to-end business workflows pass scripted tests.

## Week 5: Observability, QA, and Pilot Readiness
### Objectives
- Build confidence before pilots.
- Operationalize testing and monitoring.

### Deliverables
- Synthetic call probe suite for inbound/outbound smoke checks.
- Dashboards: call setup success, turn latency, fallback rate, transfer rate.
- Call quality checklist and weekly regression script.
- Incident runbook for common failures (401/408/429/no-media/timeouts).

### Exit Criteria
- 7-day stability burn-in completed in staging.
- Alerting thresholds defined and tested.

## Week 6: Pilot Launch and Feedback Loop
### Objectives
- Launch controlled pilots.
- Establish product learning loop.

### Deliverables
- Pilot onboarding kit (number setup, prompts, webhook mapping, QA checklist).
- SLA/SLO baseline and support workflow.
- Customer success playbook for tuning scripts and prompts.
- Post-launch review template for each tenant.

### Exit Criteria
- 2-3 pilots live with weekly KPI review.
- Clear backlog for v2 based on pilot findings.

## Technical Backlog by Priority
### P0 (must-have)
- Reliable SIP failover and retry rules.
- Turn-level timeout/fallback protection.
- Tenant isolation for configuration and data.
- Structured call diagnostics in API responses.

### P1 (should-have)
- Cost per call analytics.
- Prompt/version management with rollback.
- Per-tenant throttling and abuse controls.

### P2 (nice-to-have)
- Visual flow builder for non-technical users.
- Advanced QA simulation with synthetic persona packs.

## KPI Targets for MVP
- Call setup success rate >= 95%.
- Median first-response latency <= 1.2s.
- Fallback trigger rate <= 8% of turns.
- Automated containment >= 45% for selected workflows.
- Error budget: critical failure rate <= 2% calls/day.

## Risk Register
- Carrier/network instability: multi-trunk strategy + retryable code handling.
- Provider throttling: queueing, adaptive concurrency, and backoff.
- Voice quality drift: enforce telephony sample rate profiles and periodic MOS-style review.
- Prompt regressions: versioned prompt releases with canary rollout.

## Launch Checklist
- Security: secrets rotation, least-privilege access, audit logs.
- Reliability: chaos-style call failure drills completed.
- Compliance: consent prompts and recording disclosures configured.
- Operations: on-call schedule and incident severity matrix set.
- Product: pilot goals and acceptance KPIs signed off.

## Post-6-Week Immediate Next Step
- Move from MVP to scale track:
  - Enterprise auth and tenant provisioning automation.
  - Billing metering and invoice-ready usage exports.
  - Expanded language persona packs and domain-specific prompt bundles.
