#!/usr/bin/env python3
"""
Withings API Integration
"""

import json
import sys
import urllib.parse
import requests
from datetime import datetime, timedelta
from pathlib import Path

CLIENT_ID = "27a426200edde10a4cc1cdaf2b95de1b3e28c83f33725d4bef93a0ceff517b2e"
CLIENT_SECRET = "04145b158f65ea54d594561eead8dcbe5835d96a5a37ed716090a6a6d50bccbb"
REDIRECT_URI = "https://httpbin.org/get"
TOKEN_FILE = Path("/home/clawd/clawd/.withings_tokens.json")

SCOPES = "user.metrics,user.activity"

def get_auth_url():
    """Generate OAuth authorization URL"""
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": "jarvis_withings",
    }
    url = "https://account.withings.com/oauth2_user/authorize2?" + urllib.parse.urlencode(params)
    return url

def exchange_code(code):
    """Exchange authorization code for tokens"""
    response = requests.post(
        "https://wbsapi.withings.net/v2/oauth2",
        data={
            "action": "requesttoken",
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "redirect_uri": REDIRECT_URI,
        }
    )
    
    data = response.json()
    if data.get("status") == 0:
        tokens = data.get("body", {})
        tokens["updated_at"] = datetime.now().isoformat()
        with open(TOKEN_FILE, "w") as f:
            json.dump(tokens, f, indent=2)
        print("✅ Withings tokens saved!")
        return tokens
    else:
        print(f"❌ Error: {data}")
        return None

def refresh_tokens():
    """Refresh access token"""
    if not TOKEN_FILE.exists():
        return None
    
    with open(TOKEN_FILE) as f:
        tokens = json.load(f)
    
    response = requests.post(
        "https://wbsapi.withings.net/v2/oauth2",
        data={
            "action": "requesttoken",
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": tokens["refresh_token"],
        }
    )
    
    data = response.json()
    if data.get("status") == 0:
        new_tokens = data.get("body", {})
        new_tokens["updated_at"] = datetime.now().isoformat()
        with open(TOKEN_FILE, "w") as f:
            json.dump(new_tokens, f, indent=2)
        return new_tokens
    return None

def get_access_token():
    """Get valid access token, refreshing if needed"""
    if not TOKEN_FILE.exists():
        return None
    
    with open(TOKEN_FILE) as f:
        tokens = json.load(f)
    
    # Check if expired
    expires_in = tokens.get("expires_in", 0)
    updated_at = tokens.get("updated_at", "")
    if updated_at:
        try:
            updated = datetime.fromisoformat(updated_at)
            if datetime.now() > updated + timedelta(seconds=expires_in - 300):
                new_tokens = refresh_tokens()
                if new_tokens:
                    return new_tokens.get("access_token")
        except:
            pass
    
    return tokens.get("access_token")

def get_measurements(meas_type=None, days=30):
    """
    Get body measurements
    Types: 1=weight, 6=fat%, 5=fat-free mass, 8=fat mass, 
           76=muscle mass, 77=hydration, 88=bone mass, 91=PWV
    """
    token = get_access_token()
    if not token:
        return None
    
    start = int((datetime.now() - timedelta(days=days)).timestamp())
    end = int(datetime.now().timestamp())
    
    params = {
        "action": "getmeas",
        "startdate": start,
        "enddate": end,
    }
    if meas_type:
        params["meastype"] = meas_type
    
    response = requests.post(
        "https://wbsapi.withings.net/measure",
        headers={"Authorization": f"Bearer {token}"},
        data=params
    )
    
    data = response.json()
    if data.get("status") == 0:
        return data.get("body", {})
    elif data.get("status") == 401:
        # Try refresh
        new_tokens = refresh_tokens()
        if new_tokens:
            return get_measurements(meas_type, days)
    return None

def parse_measurement(measure):
    """Parse a measurement value (handles Withings decimal format)"""
    value = measure.get("value", 0)
    unit = measure.get("unit", 0)
    return value * (10 ** unit)

def get_weight_history(days=30):
    """Get weight measurements"""
    data = get_measurements(meas_type=1, days=days)
    if not data:
        return []
    
    weights = []
    for group in data.get("measuregrps", []):
        date = datetime.fromtimestamp(group["date"])
        for m in group.get("measures", []):
            if m.get("type") == 1:  # Weight
                kg = parse_measurement(m)
                weights.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "datetime": date.isoformat(),
                    "kg": round(kg, 1),
                    "lbs": round(kg * 2.205, 1)
                })
    return sorted(weights, key=lambda x: x["datetime"], reverse=True)

def get_body_composition(days=30):
    """Get full body composition"""
    data = get_measurements(days=days)
    if not data:
        return None
    
    # Get most recent of each type
    latest = {}
    type_names = {
        1: "weight_kg",
        6: "fat_percent",
        5: "fat_free_mass_kg",
        8: "fat_mass_kg",
        76: "muscle_mass_kg",
        77: "hydration_kg",
        88: "bone_mass_kg",
    }
    
    for group in data.get("measuregrps", []):
        date = datetime.fromtimestamp(group["date"])
        for m in group.get("measures", []):
            mtype = m.get("type")
            if mtype in type_names:
                name = type_names[mtype]
                if name not in latest or date > datetime.fromisoformat(latest[name]["date"]):
                    latest[name] = {
                        "value": round(parse_measurement(m), 2),
                        "date": date.isoformat()
                    }
    
    return latest

def print_summary():
    """Print current body composition"""
    print("📊 Withings Body Composition")
    print("=" * 40)
    
    comp = get_body_composition(days=7)
    if not comp:
        print("❌ No data available")
        return
    
    if "weight_kg" in comp:
        kg = comp["weight_kg"]["value"]
        lbs = kg * 2.205
        print(f"\n⚖️  Weight: {kg} kg ({lbs:.1f} lbs)")
    
    if "fat_percent" in comp:
        print(f"   Body Fat: {comp['fat_percent']['value']}%")
    
    if "muscle_mass_kg" in comp:
        print(f"   Muscle Mass: {comp['muscle_mass_kg']['value']} kg")
    
    if "fat_mass_kg" in comp:
        print(f"   Fat Mass: {comp['fat_mass_kg']['value']} kg")
    
    if "hydration_kg" in comp:
        print(f"   Hydration: {comp['hydration_kg']['value']} kg")
    
    if "bone_mass_kg" in comp:
        print(f"   Bone Mass: {comp['bone_mass_kg']['value']} kg")
    
    # Weight trend
    print("\n📈 Recent Weights:")
    weights = get_weight_history(days=14)
    for w in weights[:5]:
        print(f"   {w['date']}: {w['lbs']} lbs")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python withings-integration.py auth       - Get auth URL")
        print("  python withings-integration.py code CODE  - Exchange code")
        print("  python withings-integration.py summary    - Show body comp")
        print("  python withings-integration.py weight     - Weight history")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "auth":
        print(get_auth_url())
    elif cmd == "code" and len(sys.argv) > 2:
        exchange_code(sys.argv[2])
    elif cmd == "summary":
        print_summary()
    elif cmd == "weight":
        weights = get_weight_history(days=30)
        for w in weights:
            print(f"{w['date']}: {w['lbs']} lbs ({w['kg']} kg)")
    else:
        print("Unknown command")
