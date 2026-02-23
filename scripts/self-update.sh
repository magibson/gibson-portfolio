#!/bin/bash
# Jarvis self-update script
# Checks for openclaw updates, applies them, restarts gateway if needed
# Runs weekly via LaunchAgent

LOG="/tmp/jarvis-self-update.log"
exec >> "$LOG" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Checking for OpenClaw updates..."

CURRENT=$(openclaw --version 2>/dev/null)
LATEST=$(npm show openclaw version 2>/dev/null)

if [ -z "$LATEST" ]; then
    echo "Could not fetch latest version — skipping"
    exit 1
fi

echo "Current: $CURRENT | Latest: $LATEST"

if [ "$CURRENT" = "$LATEST" ]; then
    echo "Already up to date."
    exit 0
fi

echo "Update available: $CURRENT → $LATEST — installing..."
npm install -g openclaw 2>&1

# Verify install
NEW=$(openclaw --version 2>/dev/null)
echo "Installed version: $NEW"

# Restart gateway
echo "Restarting gateway..."
/opt/homebrew/bin/openclaw gateway restart 2>&1
sleep 3

STATUS=$(openclaw status 2>&1 | grep -c "agent:main" || true)
if [ "$STATUS" -gt 0 ]; then
    echo "✅ Gateway running after update to $NEW"
else
    echo "⚠️ Gateway may need manual check"
fi

echo "Update complete."
