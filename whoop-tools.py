#!/usr/bin/env python3
"""
Whoop Integration Tools for Matthew
"""

import requests
import json
import sys
from datetime import datetime, timedelta

TOKEN_FILE = "/home/clawd/clawd/.whoop_tokens.json"
BASE_URL = "https://api.prod.whoop.com/developer/v2"

def get_access_token():
    """Get access token from file"""
    try:
        with open(TOKEN_FILE, 'r') as f:
            tokens = json.load(f)
            return tokens['access_token']
    except FileNotFoundError:
        return None

def whoop_api_request(endpoint, params=None):
    """Make authenticated request to Whoop API"""
    access_token = get_access_token()
    if not access_token:
        return None
        
    headers = {'Authorization': f'Bearer {access_token}'}
    url = f"{BASE_URL}{endpoint}"
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"API request failed: {response.status_code}")
        return None

def get_strain_data(days=7):
    """Get recent strain data"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    params = {
        'start': start_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        'end': end_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    }
    
    return whoop_api_request("/cycle", params)

def get_recovery_data(cycle_id):
    """Get recovery data for a specific cycle"""
    return whoop_api_request(f"/cycle/{cycle_id}/recovery")

def analyze_strain():
    """Analyze recent strain data"""
    data = get_strain_data(days=7)
    if not data or not data.get('records'):
        return "❌ No strain data available"
    
    analysis = "📊 **Strain Analysis (Last 7 Days)**\n"
    total_strain = 0
    count = 0
    
    for cycle in data['records']:
        if cycle.get('score'):
            strain = cycle['score'].get('strain', 0)
            avg_hr = cycle['score'].get('average_heart_rate')
            max_hr = cycle['score'].get('max_heart_rate')
            date = cycle.get('start', '')[:10]
            
            total_strain += strain
            count += 1
            
            # Strain interpretation
            if strain < 5:
                strain_level = "🟢 Low"
            elif strain < 10:
                strain_level = "🟡 Moderate" 
            elif strain < 15:
                strain_level = "🟠 High"
            else:
                strain_level = "🔴 Very High"
                
            analysis += f"• {date}: {strain:.1f} {strain_level} (HR: {avg_hr}-{max_hr})\n"
    
    if count > 0:
        avg_strain = total_strain / count
        analysis += f"\n**Average Strain:** {avg_strain:.1f}\n"
        
        # Recommendations
        if avg_strain < 6:
            analysis += "💡 **Recommendation:** Room for more activity, consider increasing training load.\n"
        elif avg_strain > 12:
            analysis += "⚠️ **Recommendation:** High strain week, consider a recovery day.\n"
        else:
            analysis += "✅ **Recommendation:** Good balance of strain and recovery.\n"
    
    return analysis

def get_latest_cycle():
    """Get the most recent cycle data"""
    data = get_strain_data(days=2)
    if data and data.get('records'):
        return data['records'][0]
    return None

def daily_summary():
    """Get today's summary"""
    latest = get_latest_cycle()
    if not latest:
        return "❌ No recent data available"
    
    score = latest.get('score', {})
    if not score:
        return "❌ No score data available"
    
    strain = score.get('strain', 0)
    avg_hr = score.get('average_heart_rate')
    max_hr = score.get('max_heart_rate')
    
    # Get recovery data
    cycle_id = latest.get('id')
    recovery_data = get_recovery_data(cycle_id) if cycle_id else None
    
    summary = f"🏃‍♂️ **Latest Whoop Summary**\n"
    summary += f"• **Strain:** {strain:.1f}\n"
    summary += f"• **Heart Rate:** {avg_hr} avg, {max_hr} max\n"
    
    if recovery_data and recovery_data.get('score'):
        recovery = recovery_data['score']
        recovery_score = recovery.get('recovery_score')
        hrv = recovery.get('hrv_rmssd_milli')
        rhr = recovery.get('resting_heart_rate')
        
        summary += f"• **Recovery:** {recovery_score}%\n" if recovery_score else ""
        summary += f"• **HRV:** {hrv}ms\n" if hrv else ""
        summary += f"• **Resting HR:** {rhr} bpm\n" if rhr else ""
        
        # Recovery recommendations
        if recovery_score:
            if recovery_score >= 67:
                summary += f"✅ **Status:** Great recovery, ready for training!\n"
            elif recovery_score >= 34:
                summary += f"⚠️ **Status:** Moderate recovery, light-moderate activity.\n"
            else:
                summary += f"🛑 **Status:** Low recovery, prioritize rest.\n"
    
    return summary

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 whoop-tools.py strain     # Analyze strain data")
        print("  python3 whoop-tools.py summary    # Daily summary")
        print("  python3 whoop-tools.py raw        # Raw cycle data")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "strain":
        print(analyze_strain())
    elif command == "summary":
        print(daily_summary())
    elif command == "raw":
        data = get_strain_data(days=3)
        if data:
            print(json.dumps(data, indent=2))
        else:
            print("No data available")
    else:
        print(f"Unknown command: {command}")