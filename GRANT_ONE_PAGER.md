# Sarvam Grant One-Pager: India-First AI Voice IVR SaaS

## 1) Project Snapshot
- Project name: VoiceStack India (working title)
- Objective: Build a multilingual AI IVR and voice automation SaaS for Indian businesses using Sarvam as the primary AI layer.
- Target users: SMB and mid-market teams in healthcare, finance, logistics, and customer support.
- Core promise: Human-like multilingual voice support on Indian phone numbers with fast deployment, high reliability, and full developer control.

## 2) Problem Statement
Indian businesses need scalable voice automation, but face:
- Limited quality for code-mixed and regional language calls.
- High dependence on black-box platforms with low product control.
- Weak observability and difficult production debugging.
- Slow customization for business-specific workflows.

This project addresses the gap by combining telecom-grade call connectivity with India-optimized speech and language models.

## 3) Why This Matters for India
- India-first language reality: callers frequently switch between English and Indian languages.
- Real business workflows are voice-heavy for collections, appointment handling, support triage, and follow-ups.
- Businesses need compliant, auditable, and customizable systems rather than closed templates.

## 4) Solution Architecture (Sarvam-Centered)
- Telephony layer: Vobiz SIP trunks and Indian DIDs for inbound/outbound calling.
- Realtime orchestration: LiveKit rooms, SIP participants, dispatch rules, and call lifecycle handling.
- AI layer (default):
  - STT: Sarvam Saaras v3 (multilingual, code-mix tolerant).
  - TTS: Sarvam Bulbul v3 (telephony-compatible output).
  - LLM: Sarvam 30B/105B for reasoning and response generation.
- Application layer: Multi-tenant SaaS backend, workflow engine, tool calling, audit logs.
- Data layer: Call metadata, transcripts, outcomes, and analytics in Postgres.
- Observability: Turn-level latency, fallback events, SIP outcomes, QA flags, and cost per call.

## 5) Sarvam Grant Alignment
This project is strongly aligned with Sarvam goals:
- Uses Sarvam APIs as the default core intelligence stack for speech and language.
- Demonstrates India-language practical impact in production phone workflows.
- Creates reusable architecture patterns and benchmarks for Indian voice AI deployments.
- Can produce measurable outcomes (accuracy, containment, latency, CSAT) for ecosystem validation.

## 6) Product Differentiation
Compared with no-code or template-heavy solutions:
- Full control over prompts, tool logic, retries, guardrails, and call routing.
- Open architecture with clear provider boundaries and portability.
- Deep reliability engineering (timeouts, failover, watchdogs, diagnostics).
- Tenant-safe SaaS model with role-based controls and configurable workflows.

## 7) Initial Use Cases
- AI receptionist and smart routing.
- Appointment booking and reminder calls.
- Payment follow-ups and collections.
- Customer support triage with escalation.
- Post-call summaries and structured CRM updates.

## 8) Success Metrics (First 90 Days)
- Voice automation containment rate >= 45% (without human transfer).
- Median end-of-user-turn to first audio response <= 1.2s.
- Call setup success rate >= 95%.
- Average STT language detection confidence trend up month-over-month.
- At least 3 paid pilot customers and >= 2 production workflows each.

## 9) Risks and Mitigations
- Telecom variability: mitigate with SIP trunk failover and retry classification.
- Latency spikes: enforce turn watchdogs, endpointing tuning, and fallback prompts.
- Prompt drift/hallucination: use strict tool schemas and response guardrails.
- Operational complexity: ship with synthetic probes, health checks, and runbooks.

## 10) Support Requested From Sarvam
- Grant credits for STT/TTS/LLM production pilots.
- Technical collaboration on multilingual optimization and benchmarking.
- Access path for higher throughput and enterprise-grade limits as pilots scale.

## 11) Expected Outcome for Grant Program
- A production-grade, India-first AI IVR SaaS reference implementation.
- Real-world benchmarks and deployment learnings across language-mixed call traffic.
- Demonstrated ecosystem value by driving adoption of Sarvam APIs in high-volume voice workflows.
