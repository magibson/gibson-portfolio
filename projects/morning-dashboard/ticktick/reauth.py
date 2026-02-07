#!/usr/bin/env python3
"""Re-authorize TickTick with write access"""
import json
import sys
import urllib.parse
from pathlib import Path
import requests

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"
TOKENS_FILE = SCRIPT_DIR / "tokens.json"

with open(CONFIG_FILE) as f:
    config = json.load(f)

def get_auth_url():
    """Generate authorization URL"""
    # Use httpbin for easy code capture
    redirect_uri = "https://httpbin.org/get"
    
    auth_url = (
        f"https://ticktick.com/oauth/authorize?"
        f"client_id={config['client_id']}&"
        f"redirect_uri={urllib.parse.quote(redirect_uri)}&"
        f"response_type=code&"
        f"scope={urllib.parse.quote(config['scope'])}"
    )
    return auth_url, redirect_uri

def exchange_code(code, redirect_uri):
    """Exchange authorization code for tokens"""
    token_url = "https://ticktick.com/oauth/token"
    data = {
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
        "scope": config["scope"]
    }
    
    resp = requests.post(token_url, data=data)
    if resp.status_code == 200:
        tokens = resp.json()
        with open(TOKENS_FILE, "w") as f:
            json.dump(tokens, f, indent=2)
        print(f"✅ Tokens saved! New scope: {tokens.get('scope')}")
        return True
    else:
        print(f"❌ Token exchange failed: {resp.status_code} {resp.text}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        auth_url, _ = get_auth_url()
        print("Visit this URL to authorize:")
        print(auth_url)
        print("\nThen run: python reauth.py <CODE>")
    else:
        code = sys.argv[1]
        redirect_uri = "https://httpbin.org/get"
        exchange_code(code, redirect_uri)
