#!/usr/bin/env python3
"""Manual TickTick token exchange"""
import json
import sys
import requests
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"
TOKENS_FILE = SCRIPT_DIR / "tokens.json"

with open(CONFIG_FILE) as f:
    config = json.load(f)

def exchange_code(code):
    token_url = "https://ticktick.com/oauth/token"
    data = {
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": config["redirect_uri"],
        "scope": config["scope"]
    }
    
    resp = requests.post(token_url, data=data)
    if resp.status_code == 200:
        tokens = resp.json()
        with open(TOKENS_FILE, "w") as f:
            json.dump(tokens, f, indent=2)
        print(f"✓ Tokens saved!")
        print(f"  Access token: {tokens.get('access_token', 'N/A')[:20]}...")
        return True
    else:
        print(f"✗ Failed: {resp.status_code}")
        print(resp.text)
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python get_token.py <authorization_code>")
        sys.exit(1)
    exchange_code(sys.argv[1])
