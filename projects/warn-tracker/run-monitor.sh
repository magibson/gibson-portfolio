#!/bin/bash
# WARN Monitor Runner
# Runs the auto-monitor and sends notifications
# Cron: Every 6 hours - 0 */6 * * *

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/tmp/warn-monitor.log"

echo "=== WARN Monitor Run - $(date) ===" >> "$LOG_FILE"

# Activate venv if exists
if [ -d "$SCRIPT_DIR/venv" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
fi

# Run the monitor
cd "$SCRIPT_DIR"
python3 auto-monitor.py >> "$LOG_FILE" 2>&1

# Run the notifier
python3 notify-matt.py >> "$LOG_FILE" 2>&1

echo "=== Complete ===" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
