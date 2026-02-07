#!/usr/bin/env python3
"""
WARN Act Alert Notifier
Checks for new big layoffs and notifies via Clawdbot cron wake.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent
ALERTS_FILE = BASE_DIR / "alerts.json"
SEEN_FILE = BASE_DIR / "seen_alerts.json"

def load_json(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def main():
    # Load current alerts and seen IDs
    alerts_data = load_json(ALERTS_FILE)
    seen_data = load_json(SEEN_FILE)
    seen_ids = set(seen_data.get("seen", []))
    
    big_layoffs = alerts_data.get("big_layoffs", [])
    
    # Find truly new alerts (not in seen list)
    new_alerts = [a for a in big_layoffs if a["id"] not in seen_ids]
    
    # Filter to only recent ones (within last 7 days of notice date or first_seen)
    recent_new = []
    cutoff = datetime.now() - timedelta(days=7)
    
    for alert in new_alerts:
        # Check first_seen date
        try:
            first_seen = datetime.fromisoformat(alert.get("first_seen", ""))
            if first_seen > cutoff:
                recent_new.append(alert)
        except:
            # If no valid first_seen, include it
            recent_new.append(alert)
    
    if recent_new:
        # Build notification message
        msg_lines = [f"🚨 **{len(recent_new)} New Big Layoff{'s' if len(recent_new) > 1 else ''}**\n"]
        
        # Sort by affected count (biggest first), limit to top 5
        recent_new.sort(key=lambda x: x.get("affected", 0), reverse=True)
        for alert in recent_new[:5]:
            company = alert.get("company", "Unknown")
            city = alert.get("city", "").replace("\r\n", ", ").strip()
            state = alert.get("state", "")
            affected = alert.get("affected", "?")
            date = alert.get("date", "")
            
            location = f"{city}, {state}" if city else state
            msg_lines.append(f"• **{company}** ({location})")
            msg_lines.append(f"  {affected} employees • {date or 'Date TBD'}")
            msg_lines.append("")
        
        if len(recent_new) > 5:
            msg_lines.append(f"_...and {len(recent_new) - 5} more. Check dashboard._")
        
        msg_lines.append("\n📊 [Open WARN Tracker](file:///home/clawd/clawd/projects/warn-tracker/index.html)")
        
        message = "\n".join(msg_lines)
        print(message)
        
        # Mark all current big layoffs as seen
        all_ids = [a["id"] for a in big_layoffs]
        save_json(SEEN_FILE, {"seen": all_ids, "last_check": datetime.now().isoformat()})
        
        return message
    else:
        # Still update seen list
        all_ids = [a["id"] for a in big_layoffs]
        save_json(SEEN_FILE, {"seen": all_ids, "last_check": datetime.now().isoformat()})
        print("No new big layoffs.")
        return None

if __name__ == "__main__":
    main()
