#!/usr/bin/env python3
"""
WARN Alert Notifier
Sends new high-priority alerts to Matt via Telegram using Clawdbot gateway.
Run after auto-monitor.py to push notifications.
"""

import json
import os
import sys
import requests
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
INTEL_FILE = SCRIPT_DIR / "lead_intel.json"
NOTIFIED_FILE = SCRIPT_DIR / "notified_alerts.json"

# Clawdbot Gateway config
GATEWAY_URL = os.environ.get("CLAWDBOT_GATEWAY_URL", "http://localhost:3033")
GATEWAY_TOKEN = os.environ.get("CLAWDBOT_GATEWAY_TOKEN", "")

# Load token from config if not in env
if not GATEWAY_TOKEN:
    try:
        config_path = Path.home() / ".config" / "clawdbot" / "config.yaml"
        if config_path.exists():
            import yaml
            with open(config_path) as f:
                config = yaml.safe_load(f)
                GATEWAY_TOKEN = config.get("gateway", {}).get("token", "")
    except:
        pass


def load_json(path):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except:
        return {}


def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def get_notified():
    """Get set of already-notified alert IDs."""
    data = load_json(NOTIFIED_FILE)
    return set(data.get("notified", []))


def mark_notified(alert_id):
    """Mark alert as notified."""
    data = load_json(NOTIFIED_FILE)
    notified = set(data.get("notified", []))
    notified.add(alert_id)
    save_json(NOTIFIED_FILE, {"notified": list(notified), "last_updated": datetime.now().isoformat()})


def format_telegram_message(intel):
    """Format alert for Telegram (no markdown links - use plain text)."""
    priority = intel["priority"]
    priority_emoji = "🔴" if priority >= 8 else "🟡" if priority >= 6 else "🟢"
    
    angles = intel.get("angles", [])
    top_angle = angles[0] if angles else {"angle": "General", "hook": "Potential 401k rollover opportunity"}
    
    msg = f"""{priority_emoji} NEW WARN ALERT (Priority {priority}/10)

📍 {intel['company']} ({intel['state']})
   {intel.get('city', 'Unknown location')}
👥 {intel['affected']} employees affected
📅 Effective: {intel.get('date', 'TBD')}
📋 Type: {intel.get('type', 'Layoff')}

💡 Top Angle: {top_angle['angle']}
{top_angle['hook']}

🔗 Sales Nav: {intel['sales_nav_url']}
"""
    return msg.strip()


def send_telegram(message):
    """Send message via Clawdbot gateway."""
    # Just print for now - Clawdbot will pick up from the caller
    print(f"[TELEGRAM MESSAGE]\n{message}\n")
    return True


def main():
    """Check for unnotified alerts and send them."""
    print(f"=== WARN Notifier - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    
    intel_data = load_json(INTEL_FILE)
    all_intel = intel_data.get("intel", [])
    notified = get_notified()
    
    # Find high-priority alerts we haven't notified about
    to_notify = []
    for intel in all_intel:
        alert_id = intel.get("notice_id", "")
        priority = intel.get("priority", 0)
        
        if alert_id and alert_id not in notified and priority >= 6:
            to_notify.append(intel)
    
    if not to_notify:
        print("✅ No new high-priority alerts to notify")
        return
    
    print(f"📢 {len(to_notify)} alerts to send\n")
    
    for intel in to_notify:
        msg = format_telegram_message(intel)
        print(msg)
        print("-" * 40)
        mark_notified(intel.get("notice_id", ""))
    
    print(f"\n✅ Processed {len(to_notify)} notifications")


if __name__ == "__main__":
    main()
