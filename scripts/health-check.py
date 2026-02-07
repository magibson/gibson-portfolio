#!/usr/bin/env python3
"""
Integration Health Check
Run periodically to catch broken integrations before Matt notices
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Try imports, track what's available
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

RESULTS_FILE = Path("/home/clawd/clawd/memory/health-check-results.json")

def check_gmail():
    """Check if Gmail/himalaya is working"""
    import subprocess
    try:
        result = subprocess.run(
            ["/home/clawd/bin/himalaya", "envelope", "list", "--page-size", "1"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and "ID" in result.stdout:
            return {"status": "ok", "message": "Gmail accessible"}
        else:
            return {"status": "error", "message": f"himalaya failed: {result.stderr[:100]}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def check_google_calendar():
    """Check if Google Calendar tokens are valid"""
    tokens_file = Path("/home/clawd/clawd/google-tokens.json")
    creds_file = Path("/home/clawd/clawd/google-credentials.json")
    
    if not tokens_file.exists():
        return {"status": "error", "message": "No tokens file"}
    
    try:
        with open(tokens_file) as f:
            tokens = json.load(f)
        
        # Try a simple API call
        response = requests.get(
            "https://www.googleapis.com/calendar/v3/calendars/primary",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            timeout=10
        )
        
        if response.status_code == 200:
            return {"status": "ok", "message": "Calendar API working"}
        elif response.status_code == 401:
            # Try to refresh
            with open(creds_file) as f:
                creds = json.load(f)["installed"]
            
            refresh_resp = requests.post("https://oauth2.googleapis.com/token", data={
                "client_id": creds["client_id"],
                "client_secret": creds["client_secret"],
                "refresh_token": tokens["refresh_token"],
                "grant_type": "refresh_token"
            }, timeout=10)
            
            if refresh_resp.status_code == 200:
                new_tokens = refresh_resp.json()
                tokens["access_token"] = new_tokens["access_token"]
                tokens["created_at"] = datetime.now().isoformat()
                with open(tokens_file, "w") as f:
                    json.dump(tokens, f, indent=2)
                return {"status": "ok", "message": "Calendar refreshed"}
            else:
                return {"status": "error", "message": "Token refresh failed - needs reauth"}
        else:
            return {"status": "error", "message": f"API error {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def check_whoop():
    """Check if Whoop tokens are valid (using v2 API)"""
    tokens_file = Path("/home/clawd/clawd/.whoop_tokens.json")
    
    if not tokens_file.exists():
        return {"status": "error", "message": "No tokens file"}
    
    try:
        with open(tokens_file) as f:
            tokens = json.load(f)
        
        # Use v2 API - v1 is broken
        response = requests.get(
            "https://api.prod.whoop.com/developer/v2/recovery",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            params={"limit": 1},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("records"):
                score = data["records"][0].get("score", {})
                return {"status": "ok", "message": f"Whoop working (Recovery: {score.get('recovery_score')}%)"}
            return {"status": "ok", "message": "Whoop API working"}
        elif response.status_code == 401:
            # Try refresh
            refresh_resp = requests.post(
                "https://api.prod.whoop.com/oauth/oauth2/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": tokens["refresh_token"],
                    "client_id": "3108dd26-076e-495d-be16-540aad459356",
                    "client_secret": "8b227cf6705ece46d4f33851390645435c761266a81c46e930c7d9b46c083387",
                },
                timeout=10
            )
            
            if refresh_resp.status_code == 200:
                new_tokens = refresh_resp.json()
                tokens["access_token"] = new_tokens["access_token"]
                tokens["refresh_token"] = new_tokens.get("refresh_token", tokens["refresh_token"])
                tokens["updated_at"] = datetime.now().isoformat()
                with open(tokens_file, "w") as f:
                    json.dump(tokens, f)
                return {"status": "ok", "message": "Whoop refreshed"}
            else:
                return {"status": "error", "message": "Whoop needs reauth"}
        else:
            return {"status": "error", "message": f"API error {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def main():
    """Run all health checks"""
    print(f"🔍 Running health checks at {datetime.now().isoformat()}")
    print("=" * 50)
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    all_ok = True
    alerts = []
    
    # Gmail
    gmail = check_gmail()
    results["checks"]["gmail"] = gmail
    status_icon = "✅" if gmail["status"] == "ok" else "❌"
    print(f"{status_icon} Gmail: {gmail['message']}")
    if gmail["status"] != "ok":
        all_ok = False
        alerts.append(f"Gmail: {gmail['message']}")
    
    # Google Calendar
    calendar = check_google_calendar()
    results["checks"]["google_calendar"] = calendar
    status_icon = "✅" if calendar["status"] == "ok" else "❌"
    print(f"{status_icon} Google Calendar: {calendar['message']}")
    if calendar["status"] != "ok":
        all_ok = False
        alerts.append(f"Google Calendar: {calendar['message']}")
    
    # Whoop
    whoop = check_whoop()
    results["checks"]["whoop"] = whoop
    status_icon = "✅" if whoop["status"] == "ok" else "❌"
    print(f"{status_icon} Whoop: {whoop['message']}")
    if whoop["status"] != "ok":
        all_ok = False
        alerts.append(f"Whoop: {whoop['message']}")
    
    print("=" * 50)
    
    # Save results
    results["all_ok"] = all_ok
    results["alerts"] = alerts
    
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)
    
    if all_ok:
        print("✅ All integrations healthy")
        return 0
    else:
        print(f"⚠️ {len(alerts)} integration(s) need attention:")
        for alert in alerts:
            print(f"   • {alert}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
