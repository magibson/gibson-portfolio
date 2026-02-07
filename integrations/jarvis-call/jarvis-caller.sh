#!/bin/bash
# Jarvis Phone Call Script
# Usage: ./jarvis-caller.sh "Your message here"
# Or: ./jarvis-caller.sh --briefing (for morning briefing mode)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../reservations/retell/.env"

MESSAGE="${1:-Hey Matt, this is Jarvis checking in. Just wanted to see if you need anything. Let me know!}"
CALL_TYPE="${2:-checkin}"

# Read the agent prompt
AGENT_PROMPT=$(cat "$SCRIPT_DIR/agent-prompt.txt")

# Create a temporary LLM with the Jarvis prompt + specific message
echo "📞 Creating Jarvis call agent..."

LLM_RESPONSE=$(curl -s -X POST "https://api.retellai.com/create-retell-llm" \
  -H "Authorization: Bearer $RETELL_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"general_prompt\": \"$AGENT_PROMPT\n\nYour current task: $MESSAGE\n\nDeliver this information naturally, then ask if Matt has any questions or needs anything else.\"
  }")

LLM_ID=$(echo "$LLM_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('llm_id',''))" 2>/dev/null)

if [ -z "$LLM_ID" ]; then
  echo "❌ Failed to create LLM"
  echo "$LLM_RESPONSE"
  exit 1
fi

echo "✅ LLM created: $LLM_ID"

# Create the agent
AGENT_RESPONSE=$(curl -s -X POST "https://api.retellai.com/create-agent" \
  -H "Authorization: Bearer $RETELL_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"agent_name\": \"Jarvis Call - $(date +%Y%m%d-%H%M%S)\",
    \"voice_id\": \"11labs-Adrian\",
    \"response_engine\": {
      \"type\": \"retell-llm\",
      \"llm_id\": \"$LLM_ID\"
    },
    \"voice_temperature\": 0.8,
    \"voice_speed\": 1.0,
    \"language\": \"en-US\",
    \"max_call_duration_ms\": 180000,
    \"end_call_after_silence_ms\": 10000,
    \"enable_voicemail_detection\": true,
    \"voicemail_message\": \"Hey Matt, it's Jarvis. I was calling to let you know: $MESSAGE. Text me if you want more details. Talk later!\"
  }")

AGENT_ID=$(echo "$AGENT_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('agent_id',''))" 2>/dev/null)

if [ -z "$AGENT_ID" ]; then
  echo "❌ Failed to create agent"
  echo "$AGENT_RESPONSE"
  exit 1
fi

echo "✅ Agent created: $AGENT_ID"

# Make the call
echo "📱 Calling Matt at $CALLBACK_PHONE..."

CALL_RESPONSE=$(curl -s -X POST "https://api.retellai.com/v2/create-phone-call" \
  -H "Authorization: Bearer $RETELL_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"from_number\": \"$RETELL_PHONE_NUMBER_ID\",
    \"to_number\": \"$CALLBACK_PHONE\",
    \"agent_id\": \"$AGENT_ID\"
  }")

CALL_ID=$(echo "$CALL_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('call_id',''))" 2>/dev/null)

if [ -z "$CALL_ID" ]; then
  echo "❌ Failed to initiate call"
  echo "$CALL_RESPONSE"
  exit 1
fi

echo "✅ Call initiated!"
echo "   Call ID: $CALL_ID"
echo "   From: $RETELL_PHONE_NUMBER_ID"
echo "   To: $CALLBACK_PHONE"
echo ""
echo "📞 Jarvis is calling Matt now..."
