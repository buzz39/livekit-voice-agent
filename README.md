# LiveKit Voice Agent Platform

A production-ready AI voice agent platform for inbound and outbound phone calls, powered by LiveKit with Neon PostgreSQL configuration and Whispey observability.

## Features

- 🎙️ **Dual Agents** - Separate inbound/outbound call handling
- 📞 **Telephony Ready** - SIP integration for phone calls  
- 🗄️ **Database-Driven** - Dynamic agent configuration via Neon PostgreSQL
- 📊 **Observability** - Integrated with Whispey for call analytics and transcripts
- 🔧 **n8n Integration** - Execute workflows via Model Context Protocol (MCP)
- 🎯 **Function Tools** - Extensible tool system for custom capabilities
- 🚀 **Production Ready** - Cloud deployment ready, proper error handling

## Quick Start

### 1. Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Setup Whispey Observability

See [WHISPEY_SETUP.md](WHISPEY_SETUP.md) for detailed instructions.

```bash
uv pip install whispey
# Add WHISPEY_API_KEY and WHISPEY_AGENT_ID to .env
```

### 4. Run the Agents

```bash
# Inbound agent (terminal 1)
python inbound_agent.py dev

# Outbound agent (terminal 2)  
python outbound_agent.py dev

# API server (terminal 3)
python server.py
```

## Project Structure

```
.
├── inbound_agent.py          # Handles incoming calls
├── outbound_agent.py         # Makes outbound calls
├── server.py                 # FastAPI server for triggering calls
├── neon_db.py               # Database integration layer
├── mcp_integration.py       # n8n MCP client
├── webhook_dispatcher.py    # Webhook event dispatcher
├── pyproject.toml           # Python dependencies
├── .env.example             # Environment template
├── WHISPEY_SETUP.md        # Observability setup guide
└── INTEGRATION_COMPLETE.md # Implementation summary
```

## Architecture

```
┌─────────────────┐
│   n8n/Excel     │  
│   (Triggers)    │
└────────┬────────┘
         │
         v
┌─────────────────┐     ┌──────────────┐
│  server.py API  │────>│ LiveKit Room │
└─────────────────┘     └──────┬───────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
         ┌──────────v──────┐   ┌─────────v────────┐
         │ inbound_agent   │   │ outbound_agent   │
         │     .py         │   │      .py         │
         └────────┬────────┘   └────────┬─────────┘
                  │                     │
                  └──────────┬──────────┘
                             │
                    ┌────────v─────────┐
                    │  Whispey SDK     │
                    │  (Observability) │
                    └────────┬─────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
         ┌──────v──────┐         ┌───────v────────┐
         │ Neon DB     │         │ Whispey Cloud  │
         │ (Config)    │         │ (Analytics)    │
         └─────────────┘         └────────────────┘
```

## Configuration

### Environment Variables

```env
# LiveKit
LIVEKIT_URL=wss://your-instance.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret

# AI Services
OPENAI_API_KEY=sk-...
DEEPGRAM_API_KEY=...
CARTESIA_API_KEY=sk_car_...

# Database
NEON_DATABASE_URL=postgresql://...

# Observability
WHISPEY_API_KEY=wsp_...
WHISPEY_AGENT_ID=your-agent-id

# Optional: n8n Integration
N8N_MCP_URL=https://your-n8n.com/mcp/endpoint

# Optional: SIP Configuration  
SIP_TRUNK_ID=ST_...
SIP_FROM_NUMBER=+1...
```

### Agent Configuration

Agents are configured dynamically via the Neon database:
- **Prompts** - Agent instructions and personality
- **AI Models** - LLM, STT, TTS provider settings
- **Data Schema** - Fields to collect during calls
- **Webhooks** - Event notifications to external systems

Update configurations in the database to change agent behavior without redeploying code.

## Database Schema

Key tables in Neon PostgreSQL:

- `prompts` - Agent instructions (by agent slug)
- `ai_configs` - AI provider configurations
- `agent_configs` - Agent-specific settings (greeting, MCP URL)
- `data_schemas` - Custom fields to collect per agent
- `webhook_configs` - Event webhook endpoints
- `contacts` - Customer/lead database
- `calls` - Call logs with transcripts and metadata

Run `db_schema_update.sql` to create/update tables.

## Usage Examples

### Triggering Outbound Calls via n8n

Use the `n8n_outbound_flow.json` workflow:

1. Import workflow into n8n
2. Configure Google Sheets with leads (Phone, Business Name)
3. Set schedule trigger
4. Update HTTP Request node with your server URL
5. Activate workflow

n8n will:
- Read leads from Excel/Google Sheets
- Call `server.py` API for each lead
- `outbound_agent.py` makes the call
- Results logged to Neon DB and Whispey

### API Endpoint for Outbound Calls

```bash
curl -X POST http://localhost:8000/outbound-call \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+15551234567",
    "business_name": "Acme Corp",
    "agent_slug": "sales_agent"
  }'
```

## Deployment

### Deploy to LiveKit Cloud

```bash
# Install LiveKit CLI
brew install livekit

# Deploy agents
lk deploy create --name inbound-agent inbound_agent.py
lk deploy create --name outbound-agent outbound_agent.py
```

### Deploy API Server

Deploy `server.py` to:
- Railway: `railway up`
- Render: Connect GitHub repo
- Docker: Use provided `Dockerfile`

## Documentation

- **[WHISPEY_SETUP.md](WHISPEY_SETUP.md)** - Observability integration guide
- **[INTEGRATION_COMPLETE.md](INTEGRATION_COMPLETE.md)** - What's been implemented
- **[n8n_outbound_flow.json](n8n_outbound_flow.json)** - Example n8n workflow

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Agents | Python 3.12 + LiveKit Agents SDK |
| LLM | OpenAI GPT-4o-mini |
| STT | Deepgram Nova-3 |
| TTS | Cartesia Sonic-2 |
| VAD | Silero |
| Database | Neon PostgreSQL |
| Observability | Whispey |
| Automation | n8n (MCP integration) |
| API Server | FastAPI + Uvicorn |
| Telephony | LiveKit SIP |

## Best Practices Implemented

✅ Separate inbound/outbound agents  
✅ Using `AgentSession` (not deprecated `VoicePipelineAgent`)  
✅ Function tools for call metadata capture  
✅ Database-driven configuration  
✅ Proper error handling and logging  
✅ Webhook system for extensibility  
✅ No global state (per-call closures)  
✅ Graceful degradation (Whispey optional)  

## Cost Estimate

For ~100 calls/month (personal use):
- **LiveKit Cloud**: ~$10-20/month
- **Neon Database**: Free tier
- **Whispey**: Check pricing (likely free tier)
- **n8n**: Self-hosted free or $20/month cloud
- **Total**: ~$10-40/month

## Troubleshooting

### Agents not starting
- Check `.env` file has all required variables
- Run `uv sync` to install dependencies
- Verify LiveKit credentials are correct

### No data in Whispey
- Check `WHISPEY_API_KEY` is set
- Look for "Whispey observability enabled" in logs
- Make a test call and wait 1-2 minutes

### Database connection errors
- Verify `NEON_DATABASE_URL` is correct
- Check database tables exist (run `db_schema_update.sql`)
- Ensure Neon project is not paused

## Support

- **LiveKit Docs**: https://docs.livekit.io/agents
- **Whispey**: https://github.com/PYPE-AI-MAIN/whispey
- **Neon**: https://neon.tech/docs

## License

MIT
