#!/usr/bin/env python3
"""Quick OAuth flow for Google Calendar write access"""
import json
import sys
import urllib.parse
import requests

CREDENTIALS_FILE = "/home/clawd/clawd/google-credentials.json"
TOKENS_FILE = "/home/clawd/clawd/google-tokens.json"
REDIRECT_URI = "http://localhost"

# Scopes - adding calendar write
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar",  # Full calendar access (read+write)
]

def get_auth_url():
    with open(CREDENTIALS_FILE) as f:
        creds = json.load(f)["installed"]
    
    params = {
        "client_id": creds["client_id"],
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    
    url = "https://accounts.google.com/o/oauth2/auth?" + urllib.parse.urlencode(params)
    print(url)

def exchange_code(code):
    with open(CREDENTIALS_FILE) as f:
        creds = json.load(f)["installed"]
    
    response = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    })
    
    if response.status_code == 200:
        tokens = response.json()
        # Preserve refresh token if not in response
        try:
            with open(TOKENS_FILE) as f:
                old_tokens = json.load(f)
            if "refresh_token" not in tokens and "refresh_token" in old_tokens:
                tokens["refresh_token"] = old_tokens["refresh_token"]
        except:
            pass
        
        from datetime import datetime
        tokens["created_at"] = datetime.now().isoformat()
        
        with open(TOKENS_FILE, "w") as f:
            json.dump(tokens, f, indent=2)
        
        print("✓ Tokens saved successfully!")
        print(f"Scopes: {tokens.get('scope', 'N/A')}")
    else:
        print(f"Error: {response.text}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python google-oauth-calendar.py [url|CODE]")
        sys.exit(1)
    
    if sys.argv[1] == "url":
        get_auth_url()
    else:
        exchange_code(sys.argv[1])
