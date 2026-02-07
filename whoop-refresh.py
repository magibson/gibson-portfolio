#!/usr/bin/env python3
"""Auto-refresh Whoop tokens before they expire"""
import json
import requests
from datetime import datetime, timedelta
import os

TOKEN_FILE = os.path.expanduser("~/clawd/.whoop_tokens.json")

def refresh_tokens():
    try:
        with open(TOKEN_FILE) as f:
            tokens = json.load(f)
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': tokens['refresh_token'],
            'client_id': '3108dd26-076e-495d-be16-540aad459356',
            'client_secret': '8b227cf6705ece46d4f3385139064545c761266a81c46e930c7d9b46c083387'
        }
        r = requests.post('https://api.prod.whoop.com/oauth/oauth2/token', data=data)
        
        if r.status_code == 200:
            new_tokens = r.json()
            tokens['access_token'] = new_tokens['access_token']
            tokens['refresh_token'] = new_tokens['refresh_token']
            tokens['expires_at'] = (datetime.now() + timedelta(seconds=new_tokens['expires_in'])).isoformat()
            tokens['updated_at'] = datetime.now().isoformat()
            with open(TOKEN_FILE, 'w') as f:
                json.dump(tokens, f)
            print(f"✅ Whoop tokens refreshed at {datetime.now()}")
        else:
            print(f"❌ Refresh failed: {r.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    refresh_tokens()
