#!/usr/bin/env python3
"""
Simple Whoop Integration - Manual OAuth
"""

import requests
import json
import sys
from datetime import datetime, timedelta

# Whoop API Configuration
CLIENT_ID = "3108dd26-076e-495d-be16-540aad459356"
CLIENT_SECRET = "8b227cf6705ece46d4f33851390645435c761266a81c46e930c7d9b46c083387"
REDIRECT_URI = "https://httpbin.org/get"
TOKEN_FILE = "/home/clawd/clawd/.whoop_tokens.json"

BASE_URL = "https://api.prod.whoop.com/developer"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"

def save_tokens(access_token, refresh_token):
    """Save tokens to file"""
    tokens = {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'updated_at': datetime.now().isoformat()
    }
    with open(TOKEN_FILE, 'w') as f:
        json.dump(tokens, f)
    print(f"Tokens saved successfully")

def load_tokens():
    """Load tokens from file"""
    try:
        with open(TOKEN_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def exchange_code_for_tokens(auth_code):
    """Exchange authorization code for access token"""
    data = {
        'grant_type': 'authorization_code',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': auth_code,
        'redirect_uri': REDIRECT_URI
    }
    
    response = requests.post(TOKEN_URL, data=data)
    if response.status_code == 200:
        token_data = response.json()
        print(f"Token response: {json.dumps(token_data, indent=2)}")
        access_token = token_data['access_token']
        refresh_token = token_data.get('refresh_token', '')
        save_tokens(access_token, refresh_token)
        return access_token
    else:
        print(f"Token exchange failed: {response.status_code} - {response.text}")
        return None

def get_access_token():
    """Get valid access token"""
    tokens = load_tokens()
    if not tokens:
        return None
    return tokens['access_token']

def whoop_api_request(endpoint, params=None):
    """Make authenticated request to Whoop API"""
    access_token = get_access_token()
    if not access_token:
        print("No access token available. Run setup first.")
        return None
        
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    url = f"{BASE_URL}{endpoint}"
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"API request failed: {response.status_code} - {response.text}")
        return None

def get_user_profile():
    """Get user profile"""
    return whoop_api_request("/v1/user/profile/basic")

def get_recovery_data():
    """Get latest recovery data"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=2)
    
    params = {
        'start': start_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        'end': end_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    }
    
    return whoop_api_request("/v1/cycle", params)

def print_auth_url():
    """Print the authorization URL"""
    import secrets
    state = secrets.token_urlsafe(16)
    scopes = "read:recovery read:sleep read:cycles read:body_measurement read:workout"
    auth_url = f"https://api.prod.whoop.com/oauth/oauth2/auth?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope={scopes}&state={state}"
    print(f"Visit this URL to authorize: {auth_url}")
    print(f"State parameter: {state}")
    
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 whoop-simple.py auth-url           # Get authorization URL")
        print("  python3 whoop-simple.py setup <code>       # Setup with auth code")  
        print("  python3 whoop-simple.py recovery           # Get recovery data")
        print("  python3 whoop-simple.py profile            # Get profile")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "auth-url":
        print_auth_url()
        
    elif command == "setup":
        if len(sys.argv) < 3:
            print("Need authorization code. Usage: python3 whoop-simple.py setup <code>")
            sys.exit(1)
        auth_code = sys.argv[2]
        token = exchange_code_for_tokens(auth_code)
        if token:
            profile = get_user_profile()
            if profile:
                print(f"Setup successful! Connected to user: {profile.get('user_id', 'Unknown')}")
            else:
                print("Setup completed but couldn't test connection")
        
    elif command == "recovery":
        data = get_recovery_data()
        if data and data.get('records'):
            latest = data['records'][0]
            recovery = latest.get('score', {})
            if recovery:
                score = recovery.get('recovery_score')
                hrv = recovery.get('hrv_rmssd_milli') 
                rhr = recovery.get('resting_heart_rate')
                print(f"Recovery Score: {score}%")
                print(f"HRV: {hrv}ms")
                print(f"Resting HR: {rhr} bpm")
            else:
                print("No recovery data in response")
        else:
            print("No recovery data available")
            
    elif command == "profile":
        profile = get_user_profile()
        if profile:
            print(json.dumps(profile, indent=2))
        else:
            print("Failed to get profile")
            
    else:
        print(f"Unknown command: {command}")