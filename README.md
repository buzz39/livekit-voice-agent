# 📞 LiveKit Voice Agent Platform

**Production AI voice agents for real phone calls — inbound and outbound.**

A dual-agent telephony platform that handles live phone conversations using LiveKit, SIP integration, and database-driven agent configuration. Extensible with n8n workflows via Model Context Protocol (MCP).

---

## 🔌 LiveKit + Vobiz SIP Setup

This deployment is wired to the following infrastructure:

| Setting | Value |
|---|---|
| **LiveKit Cloud URL** | `wss://sambhavtech-tv4l8lub.livekit.cloud` |
| **Outbound SIP Trunk** | `ST_nVvG7n8BpJd3` |
| **Inbound Dispatch Rule** | Routes to agent named `voice-assistant` |
| **Vobiz SIP Domain** | `f292f0f3.sip.vobiz.ai` |
| **Phone Number** | `+911171366938` |

### Agent Name
Both `outbound_agent.py` and `telephony_agent.py` register with LiveKit as `voice-assistant`. This matches the inbound dispatch rule configured in LiveKit Cloud.

### Outbound Trunk
The outbound SIP dialer (`outbound/sip.py`) reads the trunk ID from `LIVEKIT_OUTBOUND_TRUNK_ID` env var (falls back to legacy `SIP_TRUNK_ID`). Set it to `ST_nVvG7n8BpJd3`.

### Quick Start
Copy `.env.example` to `.env` — it already contains the Vobiz + LiveKit credentials.

![Python](https://img.shields.io/badge/Python-LiveKit-3776AB?logo=python&logoColor=white)
![LiveKit](https://img.shields.io/badge/LiveKit-SIP-FF6B35)
![PostgreSQL](https://img.shields.io/badge/Neon-PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)
![Stars](https://img.shields.io/github/stars/gaganthakur04/livekit-voice-agent?style=social)

---

## ✨ Features

- 🖥️ **Configurable UI** — Manage LLM and TTS providers directly from the React dashboard.
- 📞 **Dual Voice Agents** — Separate inbound and outbound call handling
- 📡 **SIP Telephony Integration** — Connect to real phone networks
- 🗄️ **Database-Driven Config** — Agent behavior configured via Neon PostgreSQL, no redeployment needed
- 🔗 **MCP Integration** — Extend agents with n8n workflows via Model Context Protocol
- 🔧 **Extensible Function Tools** — Plug in custom capabilities per agent
- 👁️ **Whispey Observability** — Monitor and debug agent conversations
- 🖥️ **React Dashboard** — Frontend for agent management and monitoring
- 🐳 **Docker & Cloud Ready** — Dockerfile included, deploy anywhere

## 🇮🇳 Production-readiness design for India

If you are evaluating how this system should evolve from a strong pilot into a production-ready platform for the Indian market, see:

- [`PRODUCTION_READY_INDIA.md`](./PRODUCTION_READY_INDIA.md)

That note captures the most important design changes and the reason behind each one, including:

- service separation for reliability and scale
- compliance-first controls such as consent, suppression, and IST calling windows
- carrier-aware outbound dialing and fallback
- multilingual routing beyond Hinglish
- security, auditability, and cost-aware orchestration

## 🏗️ Architecture

```
                    ┌──────────────┐
  PSTN / SIP ──────►│  LiveKit SIP  │
                    │  Gateway      │
                    └──────┬───────┘
                           │
              ┌────────────┴────────────┐
              │                         │
     ┌────────▼────────┐   ┌───────────▼──────────┐
     │  Inbound Agent  │   │   Outbound Agent     │
     └────────┬────────┘   └───────────┬──────────┘
              │                         │
     ┌────────▼─────────────────────────▼──────────┐
     │           Neon PostgreSQL                    │
     │        (Agent Config & State)                │
     └────────────────────┬────────────────────────┘
                          │
                  ┌───────▼───────┐
                  │  n8n via MCP  │
                  │  (Workflows)  │
                  └───────────────┘
```

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Voice Engine | LiveKit Agents SDK |
| Language | Python |
| Telephony | SIP (LiveKit SIP) |
| Database | Neon PostgreSQL |
| Workflows | n8n + MCP |
| Observability | Whispey |
| Frontend | React |
| Deployment | Docker |

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/gaganthakur04/livekit-voice-agent.git
cd livekit-voice-agent

# Docker
docker build -t voice-agent .
docker run --env-file .env voice-agent

# Or run directly
pip install -r requirements.txt
python main.py
```

### Environment Variables

```env
LIVEKIT_URL=<your-livekit-server>
LIVEKIT_API_KEY=<key>
LIVEKIT_API_SECRET=<secret>
DATABASE_URL=<neon-postgres-connection-string>
N8N_WEBHOOK_URL=<n8n-endpoint>

# LLM Configuration
OPENAI_API_KEY=sk-proj-your-openai-api-key
GROQ_API_KEY=your_groq_api_key
LLM_PROVIDER=openai # or groq (defaults to openai, configurable in UI)
GROQ_MODEL=llama-3.3-70b-versatile # or llama-3.1-8b-instant (only for Groq)

# TTS Configuration
DEEPGRAM_API_KEY=your-deepgram-api-key # Deepgram API Key (also used for STT)
SARVAM_API_KEY=your_sarvam_api_key # Get from Sarvam AI dashboard
CARTESIA_API_KEY=sk_car_your-cartesia-api-key # Get from Cartesia
TTS_PROVIDER=cartesia # or sarvam or deepgram (defaults to cartesia, configurable in UI)
```

## 📸 Screenshots

> *Screenshots coming soon*

## 📁 Project Structure

```
livekit-voice-agent/
├── agents/           # Inbound & outbound agent logic
├── tools/            # Extensible function tools
├── dashboard/        # React frontend
├── Dockerfile
└── 64 files
```

## 👤 Author

**Gagan Thakur** — 15 years in enterprise AI, ex-Microsoft, ex-Nuance. Building production voice systems since before LLMs existed.

## 📄 License

MIT
