#!/usr/bin/env python3
"""
Daily Health Logger
Logs Whoop data to memory for trend analysis
Run once per day (morning after sleep is scored)
Uses whoop-v2.py for API calls (handles token refresh)
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent dir to path for whoop-v2 module
sys.path.insert(0, str(Path(__file__).parent.parent))

MEMORY_DIR = Path("/Users/jarvis/clawd/memory")
HEALTH_LOG = MEMORY_DIR / "health-log.json"

def get_whoop_data():
    """Get current Whoop data using whoop-v2 module (handles token refresh)"""
    try:
        # Import from whoop-v2.py which handles token refresh
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location("whoop_v2", "/Users/jarvis/clawd/whoop-v2.py")
        whoop = module_from_spec(spec)
        spec.loader.exec_module(whoop)
        
        data = {}
        
        # Recovery
        recovery = whoop.get_recovery()
        if recovery:
            data["recovery"] = {
                "score": recovery.get("recovery_score"),
                "hrv": recovery.get("hrv"),
                "resting_hr": recovery.get("resting_hr"),
                "spo2": recovery.get("spo2"),
            }
        
        # Sleep
        sleep = whoop.get_sleep()
        if sleep:
            data["sleep"] = {
                "performance": sleep.get("performance"),
                "efficiency": sleep.get("efficiency"),
                "hours": round(sleep.get("total_sleep_mins", 0) / 60, 1),
                "rem_mins": round(sleep.get("rem_mins", 0)),
                "deep_mins": round(sleep.get("deep_mins", 0)),
            }
        
        # Strain
        strain = whoop.get_strain()
        if strain:
            data["strain"] = {
                "score": round(strain.get("strain", 0), 1),
                "calories": round(strain.get("calories", 0)),
                "avg_hr": strain.get("avg_hr"),
                "max_hr": strain.get("max_hr"),
            }
        
        return data
    except Exception as e:
        print(f"Error fetching Whoop data: {e}")
        return None

def load_log():
    """Load existing health log"""
    if HEALTH_LOG.exists():
        with open(HEALTH_LOG) as f:
            return json.load(f)
    return {"entries": []}

def save_log(log):
    """Save health log"""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with open(HEALTH_LOG, "w") as f:
        json.dump(log, f, indent=2)

def check_alerts(data):
    """Check for alert conditions"""
    alerts = []
    
    recovery = data.get("recovery", {})
    if recovery.get("score") and recovery["score"] < 50:
        alerts.append(f"⚠️ Low recovery ({recovery['score']}%) - consider rest day")
    
    sleep = data.get("sleep", {})
    if sleep.get("hours") and sleep["hours"] < 6:
        alerts.append(f"⚠️ Low sleep ({sleep['hours']} hrs) - prioritize rest tonight")
    
    if sleep.get("performance") and sleep["performance"] < 60:
        alerts.append(f"⚠️ Poor sleep quality ({sleep['performance']}%)")
    
    return alerts

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    
    print(f"📊 Logging health data for {today}")
    
    # Get Whoop data
    data = get_whoop_data()
    
    if not data:
        print("❌ Could not fetch Whoop data (tokens missing — re-auth needed)")
        return 0  # Exit 0 so LaunchAgent doesn't keep marking as failed
    
    # Add timestamp
    data["date"] = today
    data["logged_at"] = datetime.now().isoformat()
    
    # Load log and append
    log = load_log()
    
    # Check if we already have an entry for today
    existing = [i for i, e in enumerate(log["entries"]) if e.get("date") == today]
    if existing:
        log["entries"][existing[0]] = data
        print("  Updated existing entry")
    else:
        log["entries"].append(data)
        print("  Added new entry")
    
    # Keep last 90 days
    log["entries"] = log["entries"][-90:]
    log["last_updated"] = datetime.now().isoformat()
    
    save_log(log)
    
    # Print summary
    recovery = data.get("recovery", {})
    sleep = data.get("sleep", {})
    strain = data.get("strain", {})
    
    print(f"\n  Recovery: {recovery.get('score', 'N/A')}%")
    print(f"  Sleep: {sleep.get('hours', 'N/A')} hrs ({sleep.get('performance', 'N/A')}%)")
    print(f"  Yesterday's Strain: {strain.get('score', 'N/A')}")
    
    # Check alerts
    alerts = check_alerts(data)
    if alerts:
        print("\n  Alerts:")
        for alert in alerts:
            print(f"    {alert}")
        return 2  # Exit code 2 = has alerts
    
    print("\n✅ Health data logged")
    return 0

if __name__ == "__main__":
    sys.exit(main())
