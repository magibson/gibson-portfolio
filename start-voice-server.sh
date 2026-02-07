#!/bin/bash
# Start Jarvis Voice Server with API key from Clawdbot config

# Extract API key
API_KEY=$(grep -o '"key": "[^"]*"' ~/.clawdbot/agents/main/agent/auth-profiles.json | head -1 | cut -d'"' -f4)

if [ -z "$API_KEY" ]; then
    echo "❌ Could not find Anthropic API key"
    exit 1
fi

export ANTHROPIC_API_KEY="$API_KEY"
export PATH="$HOME/.local/bin:$PATH"

echo "🔵 Starting Jarvis Voice Server..."
cd ~/clawd
python3 jarvis-voice-server.py
