#!/usr/bin/env python3
"""TickTick OAuth flow"""
import json
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import requests

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"
TOKENS_FILE = SCRIPT_DIR / "tokens.json"

with open(CONFIG_FILE) as f:
    config = json.load(f)

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        
        if 'code' in params:
            code = params['code'][0]
            print(f"\nGot authorization code: {code[:10]}...")
            
            # Exchange code for token
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
                print(f"Tokens saved to {TOKENS_FILE}")
                
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h1>Success!</h1><p>You can close this window.</p>")
            else:
                print(f"Token exchange failed: {resp.status_code} {resp.text}")
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Token exchange failed")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"No code received")
        
        # Stop server after handling
        self.server.should_stop = True
    
    def log_message(self, format, *args):
        pass

def main():
    auth_url = (
        f"https://ticktick.com/oauth/authorize?"
        f"client_id={config['client_id']}&"
        f"redirect_uri={urllib.parse.quote(config['redirect_uri'])}&"
        f"response_type=code&"
        f"scope={config['scope']}"
    )
    
    print("Opening browser for TickTick authorization...")
    print(f"\nIf browser doesn't open, visit:\n{auth_url}\n")
    
    # Start callback server
    server = HTTPServer(("localhost", 8585), CallbackHandler)
    server.should_stop = False
    
    webbrowser.open(auth_url)
    
    print("Waiting for callback...")
    while not server.should_stop:
        server.handle_request()
    
    print("Done!")

if __name__ == "__main__":
    main()
