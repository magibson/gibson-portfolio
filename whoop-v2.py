#!/usr/bin/env python3
"""
Whoop v2 API Integration
"""

import json
import sys
import requests
from datetime import datetime

TOKEN_FILE = "/Users/jarvis/clawd/.whoop_tokens.json"
CLIENT_ID = "3108dd26-076e-495d-be16-540aad459356"
CLIENT_SECRET = "8b227cf6705ece46d4f33851390645435c761266a81c46e930c7d9b46c083387"
BASE_URL = "https://api.prod.whoop.com/developer/v2"

def load_tokens():
    with open(TOKEN_FILE) as f:
        return json.load(f)

def save_tokens(tokens):
    tokens["updated_at"] = datetime.now().isoformat()
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f, indent=2)

def refresh_token():
    tokens = load_tokens()
    resp = requests.post(
        "https://api.prod.whoop.com/oauth/oauth2/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        }
    )
    if resp.status_code == 200:
        new_tokens = resp.json()
        tokens["access_token"] = new_tokens["access_token"]
        if "refresh_token" in new_tokens:
            tokens["refresh_token"] = new_tokens["refresh_token"]
        save_tokens(tokens)
        return tokens["access_token"]
    return None

def api_get(endpoint, params=None):
    tokens = load_tokens()
    resp = requests.get(
        f"{BASE_URL}{endpoint}",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        params=params or {}
    )
    if resp.status_code == 401:
        # Try refresh
        new_token = refresh_token()
        if new_token:
            resp = requests.get(
                f"{BASE_URL}{endpoint}",
                headers={"Authorization": f"Bearer {new_token}"},
                params=params or {}
            )
    return resp

def get_recovery():
    """Get latest recovery data"""
    resp = api_get("/recovery", {"limit": 1})
    if resp.status_code == 200:
        records = resp.json().get("records", [])
        if records:
            score = records[0].get("score", {})
            return {
                "recovery_score": score.get("recovery_score"),
                "hrv": score.get("hrv_rmssd_milli"),
                "resting_hr": score.get("resting_heart_rate"),
                "spo2": score.get("spo2_percentage"),
                "skin_temp": score.get("skin_temp_celsius"),
            }
    return None

def get_sleep():
    """Get latest sleep data"""
    resp = api_get("/activity/sleep", {"limit": 1})
    if resp.status_code == 200:
        records = resp.json().get("records", [])
        if records:
            score = records[0].get("score", {})
            stages = score.get("stage_summary", {})
            return {
                "performance": score.get("sleep_performance_percentage"),
                "efficiency": score.get("sleep_efficiency_percentage"),
                "consistency": score.get("sleep_consistency_percentage"),
                "total_sleep_mins": stages.get("total_in_bed_time_milli", 0) / 60000,
                "rem_mins": stages.get("total_rem_sleep_time_milli", 0) / 60000,
                "deep_mins": stages.get("total_slow_wave_sleep_time_milli", 0) / 60000,
            }
    return None

def get_strain():
    """Get latest strain/cycle data"""
    resp = api_get("/cycle", {"limit": 1})
    if resp.status_code == 200:
        records = resp.json().get("records", [])
        if records:
            score = records[0].get("score", {})
            return {
                "strain": score.get("strain"),
                "avg_hr": score.get("average_heart_rate"),
                "max_hr": score.get("max_heart_rate"),
                "calories": score.get("kilojoule", 0) * 0.239,  # kJ to kcal
            }
    return None

def get_summary():
    """Get full daily summary"""
    recovery = get_recovery()
    sleep = get_sleep()
    strain = get_strain()
    
    return {
        "recovery": recovery,
        "sleep": sleep, 
        "strain": strain,
        "timestamp": datetime.now().isoformat()
    }

def print_summary():
    """Print formatted summary"""
    print("📊 WHOOP Daily Summary")
    print("=" * 40)
    
    recovery = get_recovery()
    if recovery:
        print(f"\n💚 Recovery: {recovery['recovery_score']}%")
        print(f"   HRV: {recovery['hrv']:.1f}ms")
        print(f"   Resting HR: {recovery['resting_hr']} bpm")
        if recovery.get('spo2'):
            print(f"   SpO2: {recovery['spo2']:.1f}%")
    else:
        print("\n❌ Recovery data unavailable")
    
    sleep = get_sleep()
    if sleep:
        hours = sleep['total_sleep_mins'] / 60
        print(f"\n😴 Sleep Performance: {sleep['performance']}%")
        print(f"   Total: {hours:.1f} hours")
        print(f"   REM: {sleep['rem_mins']:.0f} min | Deep: {sleep['deep_mins']:.0f} min")
        print(f"   Efficiency: {sleep['efficiency']}%")
    else:
        print("\n❌ Sleep data unavailable")
    
    strain = get_strain()
    if strain:
        print(f"\n🔥 Strain: {strain['strain']:.1f}")
        print(f"   Avg HR: {strain['avg_hr']} bpm | Max: {strain['max_hr']} bpm")
        print(f"   Calories: {strain['calories']:.0f} kcal")
    else:
        print("\n❌ Strain data unavailable")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "recovery":
            data = get_recovery()
            print(json.dumps(data, indent=2) if data else "No data")
        elif cmd == "sleep":
            data = get_sleep()
            print(json.dumps(data, indent=2) if data else "No data")
        elif cmd == "strain":
            data = get_strain()
            print(json.dumps(data, indent=2) if data else "No data")
        elif cmd == "json":
            print(json.dumps(get_summary(), indent=2))
        else:
            print_summary()
    else:
        print_summary()
