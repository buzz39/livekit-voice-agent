# Whispey Observability Integration

## Overview
Whispey is now integrated into your LiveKit voice agents to provide comprehensive observability:
- 📊 Call metrics and analytics
- 📝 Transcript viewing and search
- 🎙️ Call recordings playback
- ⚡ Latency and performance tracking
- 📈 Real-time dashboards

## Quick Setup (5 minutes)

### 1. Sign Up for Whispey
```bash
# Visit https://whispey.com or the self-hosted instance
# Create an account and get your credentials
```

### 2. Get Your Credentials
From the Whispey dashboard:
1. Navigate to **Settings** → **API Keys**
2. Copy your **API Key**
3. Go to **Agents** → **Create Agent** (or use existing)
4. Copy the **Agent ID**

### 3. Add to Environment Variables
Edit your `.env` file:
```bash
# Whispey Observability
WHISPEY_API_KEY=wsp_your_actual_api_key_here
WHISPEY_AGENT_ID=your-agent-id-from-dashboard
```

### 4. Install Whispey SDK
```bash
# Using uv (recommended)
uv pip install whispey

# Or using pip
pip install whispey
```

### 5. Restart Your Agents
```bash
# Inbound agent
python inbound_agent.py dev

# Outbound agent (separate terminal)
python outbound_agent.py dev
```

## Verification

After starting your agents, you should see in the logs:
```
INFO:outbound-agent:Whispey observability enabled for agent: your-agent-id
```

If you see a warning instead:
```
WARNING:outbound-agent:WHISPEY_API_KEY not set, observability disabled
```
→ Check your `.env` file has the correct variables.

## What Gets Tracked

### Automatic Tracking
✅ Call start/end times
✅ Call duration
✅ Participant information
✅ Full transcripts (agent + user)
✅ Audio recordings
✅ Latency metrics (STT, LLM, TTS)
✅ Error tracking

### Integration Points
The integration is automatic once enabled. Whispey captures:
- Every call through both `inbound_agent.py` and `outbound_agent.py`
- Real-time conversation flow
- Tool/function calls made by the agent
- Any errors or failures

## Viewing Your Data

### Whispey Dashboard
1. Log into https://whispey.com (or your self-hosted URL)
2. Navigate to **Calls** to see all recorded calls
3. Click any call to view:
   - Full transcript with timestamps
   - Audio recording playback
   - Performance metrics
   - Agent actions and tool calls

### Key Features
- **Search transcripts**: Find calls by keyword
- **Filter by agent**: Separate inbound vs outbound calls
- **Analytics**: View trends over time
- **Export data**: Download transcripts and metrics

## Multiple Agents

To track different agents separately, use different Agent IDs:

```bash
# .env file
WHISPEY_API_KEY=wsp_same_key_for_all

# Inbound calls
WHISPEY_INBOUND_AGENT_ID=roofing-inbound

# Outbound calls  
WHISPEY_OUTBOUND_AGENT_ID=roofing-outbound
```

Then modify the agents to use specific IDs:
```python
# In inbound_agent.py
whispey_agent_id = os.getenv("WHISPEY_INBOUND_AGENT_ID", os.getenv("WHISPEY_AGENT_ID", "inbound-agent"))

# In outbound_agent.py
whispey_agent_id = os.getenv("WHISPEY_OUTBOUND_AGENT_ID", os.getenv("WHISPEY_AGENT_ID", "outbound-agent"))
```

## Troubleshooting

### No data appearing in Whispey
1. Check API key is correct
2. Verify agent is running with Whispey enabled (check logs)
3. Make a test call and wait 1-2 minutes for data sync
4. Check Whispey API status

### Import error when starting agents
```
ImportError: No module named 'whispey'
```
→ Run `pip install whispey` or `uv pip install whispey`

### API key errors
```
ERROR:outbound-agent:Failed to initialize Whispey: Invalid API key
```
→ Double-check your `WHISPEY_API_KEY` in `.env` file

## Self-Hosted Whispey

If using the open-source self-hosted version from https://github.com/PYPE-AI-MAIN/whispey:

1. Deploy Whispey to your infrastructure
2. Update the SDK to point to your instance:
```python
whispey = LivekitObserve(
    agent_id=whispey_agent_id,
    apikey=whispey_api_key,
    base_url="https://your-whispey-instance.com"  # Add this
)
```

Alternatively, set `WHISPEY_BASE_URL` in your `.env` file to support self-hosted instances without code changes:
```bash
WHISPEY_BASE_URL=https://your-whispey-instance.com
```

## Benefits vs Building Custom

### Using Whispey ✅
- Ready in 5 minutes
- Professional UI/UX
- Maintained and updated
- Built-in analytics
- Focus on your agents, not dashboards

### Building Custom ❌
- 2-3 weeks of development
- Ongoing maintenance burden
- Need to handle scalability
- Build your own analytics
- Distraction from core product

## Next Steps

1. ✅ Integration complete (already done)
2. Make a test call to verify data appears in Whispey
3. Explore the Whispey dashboard features
4. (Optional) Build simple Next.js app for agent configuration
5. Deploy to LiveKit Cloud for production use

## Support

- **Whispey Docs**: https://whispey.com/docs
- **GitHub**: https://github.com/PYPE-AI-MAIN/whispey
- **LiveKit Docs**: https://docs.livekit.io/agents/observability
