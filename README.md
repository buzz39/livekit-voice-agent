# LiveKit AI Telephony Agent with n8n MCP Integration

A production-ready AI voice agent for phone calls, powered by LiveKit and integrated with n8n workflows via Model Context Protocol (MCP).

## Features

- 🎙️ **Voice AI Agent** - Natural phone conversations with GPT-4o-mini
- 📞 **Telephony Ready** - Optimized for phone call quality and latency
- 🔧 **n8n Integration** - Execute n8n workflows during calls via MCP
- 🎯 **Function Tools** - Extensible tool system for custom capabilities
- 🚀 **Production Ready** - Docker support, proper error handling, logging

## Tech Stack

- **LiveKit** - Real-time voice infrastructure
- **OpenAI GPT-4o-mini** - Language model
- **Deepgram Nova-3** - Speech-to-text
- **Cartesia Sonic-2** - Text-to-speech
- **Silero VAD** - Voice activity detection
- **n8n MCP** - Workflow automation integration

## Quick Start

### Prerequisites

- Python 3.12+
- LiveKit Cloud account or self-hosted instance
- n8n instance with MCP endpoint
- API keys for OpenAI, Deepgram, Cartesia

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   uv sync
   ```

3. Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   ```

4. Edit `.env` with your credentials

### Running the Agent

```bash
python telephony_agent.py
```

The agent will:
1. Connect to LiveKit
2. Load n8n MCP tools
3. Wait for incoming calls
4. Handle conversations with AI + n8n workflows

## Configuration

### Environment Variables

```env
# LiveKit Configuration
LIVEKIT_URL=wss://your-instance.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret

# AI Service Keys
OPENAI_API_KEY=sk-...
DEEPGRAM_API_KEY=...
CARTESIA_API_KEY=sk_car_...

# n8n MCP Integration
N8N_MCP_URL=https://your-n8n.com/mcp/your-endpoint-id
```

### Agent Configuration

Edit `telephony_agent.py` to customize:
- Agent instructions and personality
- Voice settings (speed, voice ID)
- STT/TTS models
- Custom function tools

## n8n MCP Integration

The agent automatically loads tools from your n8n MCP endpoint. When a caller requests something that matches an n8n workflow, the agent will:

1. Recognize the intent
2. Call the appropriate n8n tool
3. Execute the workflow
4. Return results to the caller

### Example Use Cases

- "Create a calendar event for tomorrow at 2pm"
- "Send an email to the team"
- "Check the status of order #12345"
- "Add this to my CRM"

## Docker Deployment

Build and run with Docker:

```bash
docker build -t telephony-agent .
docker run --env-file .env telephony-agent
```

## Project Structure

```
.
├── telephony_agent.py      # Main agent application
├── mcp_integration.py      # n8n MCP client
├── place_outbound_call.py  # Utility for testing outbound calls
├── pyproject.toml          # Python dependencies
├── Dockerfile              # Container configuration
├── livekit.toml           # LiveKit agent config
└── .env                    # Environment variables (not in git)
```

## Making Outbound Calls

Use the included utility script:

```bash
python place_outbound_call.py
```

Edit the script to configure:
- Destination phone number
- Source number (from your SIP trunk)
- Room name

## Customization

### Adding Custom Tools

Add function tools in `telephony_agent.py`:

```python
@function_tool
async def my_custom_tool(param: str) -> str:
    """Tool description for the LLM."""
    # Your logic here
    return "result"

# Register the tool
agent.register_tool(my_custom_tool)
```

### Changing Voice Settings

Modify the TTS configuration:

```python
tts=cartesia.TTS(
    model="sonic-2",
    voice="your-voice-id",  # Browse voices at cartesia.ai
    speed=1.0,              # 0.5 to 2.0
    sample_rate=24000
)
```

## Troubleshooting

### Agent not connecting
- Check LiveKit credentials
- Verify network connectivity
- Check logs for error messages

### n8n tools not loading
- Verify N8N_MCP_URL is correct
- Test n8n endpoint accessibility
- Check n8n MCP configuration

### Poor call quality
- Check network latency
- Verify sample rates match
- Review VAD sensitivity settings

## License

MIT

## Support

For issues and questions, please open a GitHub issue.
