# Product Requirements Document (PRD)
## LiveKit Voice Agent Platform

- Document owner: Product and Engineering
- Status: Draft for execution
- Version: 1.0
- Date: 2026-03-29

---

## 1. Executive Summary

This product is a production-grade AI telephony platform for inbound and outbound business calls over SIP and PSTN, powered by LiveKit, configurable AI providers, and database-driven runtime behavior. The platform must deliver high call quality, low latency, compliance-ready operations, and strong reliability under carrier variability.

Primary business objective:
- Convert voice calls into measurable outcomes (qualified leads, bookings, follow-ups) with lower operational cost and faster response times than human-only workflows.

Primary technical objective:
- Provide resilient, observable, and configurable real-time voice interactions that can scale to multi-tenant, multilingual, compliance-sensitive production environments.

---

## 2. Problem Statement

Current pain points in real-world operation:
- Voice quality instability during telephony calls (breaking/choppy output under some conditions).
- Carrier-side SIP variability (timeouts, busy/reject, intermittent failures).
- Hard-to-debug failures due to insufficient surfaced diagnostics in normal dashboard views.
- Latency spikes from LLM/STT/TTS providers causing dead air.
- Need for robust fallback behavior when one provider or route degrades.

Desired outcome:
- Calls should remain intelligible and controlled even during partial failures.
- Teams should quickly identify where a call degraded and why.
- The system should maintain business continuity through retries/fallbacks, not fail silently.

---

## 3. Product Vision

Build the most reliable AI voice operations platform for SMB and mid-market teams that need:
- Always-on outbound and inbound voice automation
- Human-like interactions with strict operational controls
- Configurable AI stack by campaign, language, and cost profile
- Compliance-first call orchestration

---

## 4. Goals and Non-Goals

### 4.1 Goals
- G1: Deliver stable telephony audio quality with telephony-safe defaults.
- G2: Increase successful call completion rate through SIP failover/retry controls.
- G3: Eliminate dead-air experiences via timeout watchdogs and spoken fallbacks.
- G4: Make call execution diagnosable through state timelines and attempt history.
- G5: Enable no-code operator control for prompts, AI configuration, and call monitoring.
- G6: Maintain secure, auditable, tenant-safe operations.

### 4.2 Non-Goals (Current PRD Scope)
- N1: Building a full consumer calling app.
- N2: Replacing external CRMs.
- N3: Training custom foundation models.
- N4: Full omnichannel orchestration beyond initial webhook and API integrations.

---

## 5. Target Users and Personas

### 5.1 Operations Manager
- Owns daily outbound performance.
- Needs campaign controls, call outcomes, failure reasons, retry behavior.

### 5.2 Sales / Support Team Lead
- Needs reliable call handoff and lead context.
- Needs transcript and recording visibility for QA.

### 5.3 Admin / Developer
- Manages provider keys, telephony settings, routing, compliance controls.
- Needs deep diagnostics and rollback-safe changes.

### 5.4 Compliance and Risk Stakeholder
- Needs auditability, consent signals, call windows, and access control guarantees.

---

## 6. User Jobs To Be Done

- As an operator, I want calls to continue gracefully when AI response is slow, so customers do not hang up due to silence.
- As an operator, I want automatic dial retries and route fallback when carrier errors occur, so campaigns maintain throughput.
- As an admin, I want to inspect call state transitions and dial attempts, so root-cause analysis takes minutes, not days.
- As a manager, I want consistent call quality across telephony routes, so user trust and conversion improve.

---

## 7. Scope

### 7.1 In Scope
- Outbound and inbound telephony workflows over LiveKit SIP.
- Dynamic AI stack selection for LLM/STT/TTS.
- State-machine-driven call lifecycle tracking.
- Carrier retry/failover logic with attempt telemetry.
- LLM latency watchdog and spoken fallback behavior.
- Dashboard and API visibility for reliability metadata.
- Synthetic probe-based runtime verification.

### 7.2 Out of Scope
- Billing and invoicing subsystem.
- Workforce management / full agent scheduling.
- Native mobile applications.

---

## 8. Functional Requirements

### FR-1: Call Lifecycle State Machine
The system shall maintain explicit call states and transitions from room connection to finalization.

Acceptance:
- Every call stores current_state and transition history.
- Each transition includes timestamp and optional reason/details.
- Transition data is persisted in call metadata.

### FR-2: SIP Dial Retry and Trunk Failover
The system shall support multiple outbound trunks with retry rounds and delay controls.

Acceptance:
- On retryable failures, the next trunk/attempt is used.
- On non-retryable hard failures, call fails fast with reason.
- dial_attempts array is persisted for each call.

### FR-3: Telephony-Safe Audio Defaults
The system shall use telephony-safe defaults for outbound audio.

Acceptance:
- Default output sample rate is 8000 Hz for telephony path.
- DTX and RED are disabled by default unless explicitly enabled.
- Runtime logs include active telephony output config.

### FR-4: LLM Delay Watchdog
The system shall detect delayed assistant turns and speak a fallback phrase.

Acceptance:
- Trigger after configurable timeout post-final user transcript.
- Add note and state transition indicating timeout fallback.
- Fallback phrase configurable via environment variable.

### FR-5: Dashboard Reliability Metadata
The API shall expose parsed reliability metadata for recent calls and call detail endpoints.

Acceptance:
- captured_data returned as parsed JSON object.
- state_machine and dial_attempts visible in API response.

### FR-6: Synthetic Probe
The system shall provide a probe utility to trigger and monitor test calls.

Acceptance:
- Probe triggers outbound call and polls terminal status.
- Probe reports call id, status, duration, and diagnostics.
- Probe avoids stale-match errors through new-call selection logic.

### FR-7: Safe Finalization
The system shall always finalize call state and persistence even after partial failures.

Acceptance:
- Finalization runs once per call.
- DB update and transcript capture errors are logged, not silent.
- Final state reflected in metadata.

### FR-8: Transfer Tool Availability
The system shall support live call transfer where context permits.

Acceptance:
- Transfer destination supports number or SIP URI.
- Tool returns explicit error messages on invalid target or API failure.

---

## 9. Non-Functional Requirements

### NFR-1: Reliability
- No silent failure path for session start, opening playout, or LLM response timeout.
- Recoverable errors should degrade behavior, not terminate call immediately.

### NFR-2: Latency
- Opening line should begin quickly after answer with bounded startup timeout.
- LLM response delay beyond threshold must be user-handled by fallback prompt.

### NFR-3: Audio Quality
- Telephony output must prioritize intelligibility over wideband richness.
- Avoid unnecessary transcoding pressure in SIP/PSTN path.

### NFR-4: Observability
- State transitions and dial attempts available in API and logs.
- Error events include provider and stage context.

### NFR-5: Security
- API key auth and rate limits on public API surface.
- Sensitive configuration and provider keys managed via environment/secure deployment configs.

### NFR-6: Maintainability
- Reliability logic isolated in dedicated modules with test coverage.
- Configurable behavior via env vars with sane defaults.

---

## 10. Solution Design Summary

### 10.1 Core Runtime Components
- API Server: request intake, call dispatch, dashboard APIs.
- Agent Worker: SIP dial, conversation runtime, fallback behavior.
- DB Layer: persistent prompts, configs, contacts, call logs, metadata.

### 10.2 Reliability Mechanisms
- State machine transitions embedded in call metadata.
- SIP trunk candidates and retry policy.
- Explicit startup and opening deadlines.
- LLM watchdog fallback for user-facing continuity.

### 10.3 Diagnostics Surface
- Dashboard calls endpoint with parsed captured_data.
- Call detail endpoint exposing full state timeline and dial attempts.
- Probe script for repeatable black-box tests.

---

## 11. API Requirements

### 11.1 Existing Endpoints (Operational)
- POST /outbound-call
- GET /dashboard/calls
- GET /dashboard/call/{call_id}
- GET /health

### 11.2 Response Requirements
For call list/detail responses:
- Include captured_data as JSON object when present.
- Include nested state_machine transitions and current_state.
- Include dial_attempts and successful_trunk_id if available.

---

## 12. Data Model Requirements

Calls must retain:
- call_status
- duration_seconds
- transcript
- recording_url
- captured_data

captured_data must support:
- notes
- dial_attempts
- state_machine
- transcript_json
- business_name
- call_id
- successful_trunk_id

---

## 13. Configuration Requirements

Mandatory runtime settings:
- LIVEKIT_URL
- LIVEKIT_API_KEY
- LIVEKIT_API_SECRET
- NEON_DATABASE_URL
- LIVEKIT_OUTBOUND_TRUNK_ID or LIVEKIT_OUTBOUND_TRUNK_IDS
- SIP_FROM_NUMBER
- Provider keys for selected LLM/STT/TTS

Reliability and quality controls:
- OUTBOUND_SESSION_START_TIMEOUT_SECONDS
- OUTBOUND_OPENING_PLAYOUT_TIMEOUT_SECONDS
- OUTBOUND_LLM_RESPONSE_TIMEOUT_SECONDS
- OUTBOUND_LLM_SLOW_FALLBACK_MESSAGE
- OUTBOUND_OUTPUT_SAMPLE_RATE
- OUTBOUND_ENABLE_DTX
- OUTBOUND_ENABLE_RED
- OUTBOUND_PREEMPTIVE_GENERATION
- SIP_DIAL_MAX_ROUNDS
- SIP_DIAL_RETRY_DELAY_SECONDS

---

## 14. Success Metrics

### 14.1 Product Metrics
- Completed call rate
- Qualified lead rate
- Conversation continuation beyond opening turn
- Transfer success rate

### 14.2 Reliability Metrics
- SIP failure rate by status code and trunk
- Retry recovery rate
- LLM timeout fallback rate
- Dead-air incident rate
- Call finalization success rate

### 14.3 Quality Metrics
- User interruption rate
- Transcript confidence trends
- Average response latency per provider

---

## 15. SLO Targets (Initial)

- SLO-1: 99.0% of calls should finalize with terminal status and persisted metadata.
- SLO-2: 95% of answered calls should play opening line without timeout.
- SLO-3: 99% of user turns should receive either model reply or fallback speech within configured timeout bounds.
- SLO-4: 99% of call records should include parseable reliability metadata in dashboard detail response.

---

## 16. Risks and Mitigations

### Risk: Carrier instability causes high dial failure spikes
Mitigation:
- Multi-trunk retries, failure classification, attempt telemetry, route-level dashboards.

### Risk: LLM latency variability impacts user experience
Mitigation:
- Turn watchdog fallback, lower-latency model options, timeout tuning.

### Risk: Audio artifacts from transcoding mismatch
Mitigation:
- Telephony-safe output defaults (8k, DTX off, RED off), provider sample-rate alignment.

### Risk: Limited observability in list views
Mitigation:
- Expose parsed captured_data in list/detail APIs; add diagnostics endpoint (next phase).

---

## 17. Rollout Plan

### Phase 1 (Completed)
- State machine lifecycle tracking
- SIP retry/failover policy
- LLM timeout fallback
- Telephony-safe default output settings
- Dashboard metadata parsing and visibility
- Synthetic probe utility

### Phase 2 (Next)
- Diagnostics-only API endpoint per call
- Aggregated reliability dashboard cards
- Trunk-level health scoring and dynamic ordering
- Recording availability resilience and quota handling

### Phase 3 (Scale)
- Multi-tenant policy controls
- Compliance workflow hardening (consent/DND windows)
- Automated canary and replay test harness for prompt/model changes

---

## 18. QA and Test Plan

### Unit Tests
- SIP retry/failover behavior
- State machine transitions
- Metadata parsing and payload normalization

### Integration Tests
- Outbound call trigger to terminal status
- Dashboard detail includes state_machine and dial_attempts
- LLM fallback triggers under induced delay

### Synthetic Production Tests
- Scheduled probe calls at intervals
- Alert on failed terminal status, repeated timeout fallback spikes, or dial failure spikes

---

## 19. Operational Runbook (Minimum)

- Step 1: Verify health endpoint and DB connectivity.
- Step 2: Run synthetic probe call.
- Step 3: Inspect dashboard call detail for state timeline and dial attempts.
- Step 4: If call failed before answer, analyze SIP status and trunk route.
- Step 5: If call answered but quality degraded, verify telephony output config and provider latency logs.

---

## 20. Open Questions

- Should retry policy vary by campaign value and call window?
- Should fallback phrase be locale-specific by detected language?
- Should call list endpoint include summarized reliability fields without full captured_data payload for performance?
- Should recording failure (quota/exhausted) alter call status or remain a note-level degradation?

---

## 21. Definition of Done

This PRD is considered implemented when:
- Functional requirements FR-1 through FR-8 are available in production deployment.
- Reliability metadata is observable via dashboard APIs.
- Telephony quality defaults are enforced in runtime.
- Probe-based verification is executable and documented for operations.
- Core tests pass in CI and smoke tests pass in staging.

---

## 22. Appendix: Current Project Anchors

Primary repository components:
- API and dashboard routes
- Inbound and outbound agent workers
- SIP dialer and provider adapters
- Neon DB integration
- Frontend dashboard

This PRD intentionally aligns to the existing architecture and extends it with explicit reliability, quality, and operational controls rather than introducing a separate greenfield design.
