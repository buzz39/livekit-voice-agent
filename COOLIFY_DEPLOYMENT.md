# Coolify Deployment Guide for LiveKit Voice Agent

## Prerequisites
- Coolify instance running (self-hosted or cloud)
- Git repo connected to Coolify
- LiveKit credentials ready

## Step-by-Step Deployment

### Step 1: Create a New Application in Coolify

1. Go to your Coolify dashboard
2. Click **"Create Application"** or **"+ New"**
3. Select **"Public Repository"** (your GitHub repo)
4. Select your repository from the list
5. Choose **main** branch (or your deployment branch)

### Step 2: Configure the Application

1. **Name:** Give it a name like `livekit-outbound-api`
2. **Port:** Set to `8000` (where server.py listens)
3. **Build Command:** Leave empty (Coolify auto-detects Docker)
4. **Start Command:** Leave empty (uses Dockerfile CMD)

### Step 3: Set Environment Variables

In Coolify dashboard, go to **Environment Variables** and add:

```
LIVEKIT_URL=your_livekit_url
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
SIP_TRUNK_ID=your_trunk_id
SIP_FROM_NUMBER=your_phone_number
```

**Where to find these:**
- `LIVEKIT_URL` - LiveKit Cloud dashboard
- `LIVEKIT_API_KEY` - Settings → API Keys
- `LIVEKIT_API_SECRET` - Same location
- `SIP_TRUNK_ID` - From your SIP configuration
- `SIP_FROM_NUMBER` - Your outbound caller ID

### Step 4: Modify Dockerfile for server.py

Your current Dockerfile runs the agent. Create a separate Dockerfile for the API server:

**Create: `Dockerfile.server`**

```dockerfile
ARG PYTHON_VERSION=3.13
FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-bookworm-slim AS base

ENV PYTHONUNBUFFERED=1

ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/app" \
    --shell "/sbin/nologin" \
    --uid "${UID}" \
    appuser

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN mkdir -p src

RUN uv sync --locked

COPY . .

RUN chown -R appuser:appuser /app

USER appuser

# Run server.py instead of agent
CMD ["uv", "run", "server.py"]
```

### Step 5: Configure Coolify to Use Custom Dockerfile

1. In Coolify, click **Settings** for your application
2. Find **"Build Settings"** or **"Docker"**
3. Set **Dockerfile:** to `Dockerfile.server`
4. Save

### Step 6: Deploy

1. Click **Deploy** button
2. Watch the logs in the **Build Logs** tab
3. Once complete, you'll see a URL like: `https://livekit-outbound-api.your-domain.com`

### Step 7: Test the API

```bash
curl -X POST https://livekit-outbound-api.your-domain.com/outbound-call \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+1-555-123-4567",
    "business_name": "Test Company",
    "agent_slug": "default_roofing_agent"
  }'
```

Expected response:
```json
{
  "status": "queued",
  "message": "Calling +1-555-123-4567 with agent default_roofing_agent",
  "data": {...}
}
```

### Step 8: Set Up SSL/HTTPS

Coolify handles SSL automatically with Let's Encrypt. Just ensure:
- Your domain is pointed to Coolify
- Certificate generation is enabled (default)

## Troubleshooting

### Build Fails
Check **Build Logs** for errors. Common issues:
- Missing dependencies in `pyproject.toml`
- Environment variables not set
- GitHub token expired

### Connection Refused
- Verify `LIVEKIT_URL` is correct and accessible
- Check `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET`
- Ensure port 8000 is not blocked

### Deployments Stuck
- Check disk space on Coolify host
- Review Docker daemon logs
- Try **Force Rebuild**

## Monitoring

In Coolify dashboard:
- **Status:** Shows if app is running
- **Logs:** Real-time application logs
- **Stats:** CPU, memory, network usage
- **Webhooks:** Configure post-deploy actions

## Next Steps

1. **Update your frontend** to call:
   ```
   https://livekit-outbound-api.your-domain.com/outbound-call
   ```

2. **Scale outbound_agent** - Deploy to LiveKit Cloud separately

3. **Monitor calls** - Check logs for issues

4. **Set up alerts** - Use Coolify webhooks to notify on failures

---

**Need help?** Check Coolify docs at https://coolify.io/docs
