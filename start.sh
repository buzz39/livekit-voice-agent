#!/bin/bash
# Start the LiveKit telephony agent

echo "Starting LiveKit AI Telephony Agent..."
echo "========================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please copy .env.example to .env and configure your credentials."
    exit 1
fi

# Activate virtual environment if it exists
if [ -d .venv ]; then
    source .venv/bin/activate
fi

# Run the agent
python telephony_agent.py
