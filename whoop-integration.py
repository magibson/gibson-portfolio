#!/usr/bin/env python3
"""
Whoop API Integration for Matthew
Handles OAuth flow and data fetching
"""

import requests
import json
import os
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import webbrowser
import threading
import time

# Whoop API Configuration
CLIENT_ID = "3108dd26-076e-495d-be16-540aad459356"
CLIENT_SECRET = "8b227cf6705ece46d4f33851390645435c761266a81c46e930c7d9b46c083387"
REDIRECT_URI = "http://localhost:8080/whoop/callback"
TOKEN_FILE = "/home/clawd/clawd/.whoop_tokens.json"

BASE_URL = "https://api.prod.whoop.com/developer"
AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"

class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/whoop/callback'):
            query_params = parse_qs(urlparse(self.path).query)
            if 'code' in query_params:
                self.server.auth_code = query_params['code'][0]
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Authorization successful! You can close this tab.")
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Authorization failed")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress logs

def save_tokens(access_token, refresh_token):
    """Save tokens to file"""
    tokens = {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'updated_at': datetime.now().isoformat()
    }
    with open(TOKEN_FILE, 'w') as f:
        json.dump(tokens, f)
    print(f"✅ Tokens saved to {TOKEN_FILE}")

def load_tokens():
    """Load tokens from file"""
    try:
        with open(TOKEN_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def get_authorization():
    """Start OAuth flow"""
    # Build authorization URL
    scopes = "read:recovery read:sleep read:cycles read:body_measurement read:workout"
    auth_url = f"{AUTH_URL}?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope={scopes}"
    
    print("🔐 Starting Whoop OAuth authorization...")
    print(f"Opening browser to: {auth_url}")
    
    # Start local server to catch callback
    server = HTTPServer(('localhost', 8080), OAuthHandler)
    server.auth_code = None
    
    # Open browser
    webbrowser.open(auth_url)
    
    print("⏳ Waiting for authorization...")
    # Handle one request (the callback)
    server.handle_request()
    
    if server.auth_code:
        print("✅ Got authorization code!")
        return server.auth_code
    else:
        print("❌ Failed to get authorization code")
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
        access_token = token_data['access_token']
        refresh_token = token_data['refresh_token']
        save_tokens(access_token, refresh_token)
        return access_token
    else:
        print(f"❌ Token exchange failed: {response.text}")
        return None

def refresh_access_token():
    """Refresh access token using refresh token"""
    tokens = load_tokens()
    if not tokens or 'refresh_token' not in tokens:
        print("❌ No refresh token available")
        return None
        
    data = {
        'grant_type': 'refresh_token',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'refresh_token': tokens['refresh_token']
    }
    
    response = requests.post(TOKEN_URL, data=data)
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data['access_token']
        refresh_token = token_data.get('refresh_token', tokens['refresh_token'])
        save_tokens(access_token, refresh_token)
        return access_token
    else:
        print(f"❌ Token refresh failed: {response.text}")
        return None

def get_access_token():
    """Get valid access token (refresh if needed)"""
    tokens = load_tokens()
    if not tokens:
        return None
    return tokens['access_token']

def whoop_api_request(endpoint, params=None):
    """Make authenticated request to Whoop API"""
    access_token = get_access_token()
    if not access_token:
        return None
        
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    url = f"{BASE_URL}{endpoint}"
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 401:
        # Try refreshing token
        print("🔄 Access token expired, refreshing...")
        new_token = refresh_access_token()
        if new_token:
            headers['Authorization'] = f'Bearer {new_token}'
            response = requests.get(url, headers=headers, params=params)
        else:
            return None
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ API request failed: {response.status_code} - {response.text}")
        return None

def get_user_profile():
    """Get user profile"""
    return whoop_api_request("/v1/user/profile/basic")

def get_recovery_data(days=7):
    """Get recovery data for last N days"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    params = {
        'start': start_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        'end': end_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    }
    
    return whoop_api_request("/v1/cycle", params)

def get_sleep_data(days=7):
    """Get sleep data for last N days"""  
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    params = {
        'start': start_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        'end': end_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    }
    
    return whoop_api_request("/v1/activity/sleep", params)

def analyze_latest_recovery():
    """Get and analyze latest recovery data"""
    data = get_recovery_data(days=1)
    if not data or not data.get('records'):
        return "❌ No recent recovery data available"
    
    latest = data['records'][0]
    recovery = latest.get('score', {})
    
    if not recovery:
        return "❌ No recovery score in latest data"
        
    score = recovery.get('recovery_score')
    hrv = recovery.get('hrv_rmssd_milli')
    rhr = recovery.get('resting_heart_rate')
    
    analysis = f"🔄 **Latest Recovery**\n"
    analysis += f"• Recovery Score: {score}%\n" if score else ""
    analysis += f"• HRV: {hrv}ms\n" if hrv else ""
    analysis += f"• Resting HR: {rhr} bpm\n" if rhr else ""
    
    # Recovery recommendations
    if score:
        if score >= 67:
            analysis += f"✅ Great recovery! Good day for training.\n"
        elif score >= 34:
            analysis += f"⚠️ Moderate recovery. Light to moderate activity.\n"
        else:
            analysis += f"🛑 Low recovery. Consider rest or very light activity.\n"
            
    return analysis

def setup_whoop_connection():
    """Complete OAuth setup flow"""
    print("🏃‍♂️ Setting up Whoop connection...")
    
    # Check if we already have tokens
    tokens = load_tokens()
    if tokens:
        print("✅ Found existing tokens, testing connection...")
        profile = get_user_profile()
        if profile:
            print(f"✅ Connected to Whoop! User: {profile.get('user_id', 'Unknown')}")
            return True
        else:
            print("❌ Existing tokens invalid, starting fresh...")
    
    # Start OAuth flow
    auth_code = get_authorization()
    if not auth_code:
        return False
        
    access_token = exchange_code_for_tokens(auth_code)
    if not access_token:
        return False
        
    # Test connection
    profile = get_user_profile()
    if profile:
        print(f"🎉 Whoop connection successful! User ID: {profile.get('user_id', 'Unknown')}")
        return True
    else:
        print("❌ Connection test failed")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 whoop-integration.py setup     # Setup OAuth connection")
        print("  python3 whoop-integration.py recovery  # Get latest recovery") 
        print("  python3 whoop-integration.py profile   # Get user profile")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "setup":
        success = setup_whoop_connection()
        sys.exit(0 if success else 1)
        
    elif command == "recovery":
        analysis = analyze_latest_recovery()
        print(analysis)
        
    elif command == "profile":
        profile = get_user_profile()
        if profile:
            print(json.dumps(profile, indent=2))
        else:
            print("❌ Failed to get profile")
            
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)