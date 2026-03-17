#!/bin/bash
set -e

echo "Starting LiveKit Voice Agent..."

# Start the FastAPI server in the background
uv run uvicorn server:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!
echo "FastAPI server started (PID: $SERVER_PID)"

# Start the LiveKit agent worker in the background
uv run outbound_agent.py start &
AGENT_PID=$!
echo "LiveKit agent worker started (PID: $AGENT_PID)"

# Wait for both — if either exits, the container exits too
wait -n $SERVER_PID $AGENT_PID
EXIT_CODE=$?
echo "A process exited with code $EXIT_CODE"
exit $EXIT_CODE
