#!/bin/bash
# Test the Jarvis Voice Server with Clawdbot

TOKEN="1fa124bc0a493b0db3dda04174bf83f9a5d3621fc51a03b916bf5784dc2f82bf"
HOST="100.83.250.65:8765"

echo "=== Jarvis Voice Server Tests ==="
echo ""

# Health check
echo "1. Health check..."
curl -s "http://${HOST}/health"
echo ""
echo ""

# Auth check
echo "2. Auth check (should show status:ok)..."
curl -s "http://${HOST}/" -H "Authorization: Bearer ${TOKEN}"
echo ""
echo ""

# Simple chat
echo "3. Simple chat test..."
time curl -s -X POST "http://${HOST}/chat" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"text": "What time is it?"}'
echo ""
echo ""

# Tool test (optional, takes longer)
if [ "$1" == "--full" ]; then
  echo "4. Tool test (web search)..."
  time curl -s -X POST "http://${HOST}/chat" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"text": "What is the current temperature in NYC?"}'
  echo ""
fi

echo ""
echo "=== Done ==="
