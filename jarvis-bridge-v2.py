#!/usr/bin/env python3
"""
Jarvis Voice Bridge v2 - Two-way communication
Runs on VPS, Mac connects via Tailscale

Endpoints:
- POST /chat - Send message, get response (waits for Jarvis reply)
- GET /speak - Poll for queued TTS messages (legacy)
- POST /speak - Queue a message for TTS (legacy)
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import time
import subprocess
import threading
from urllib.parse import urlparse, parse_qs

# Configuration
HOST = "100.82.133.57"  # Tailscale IP
PORT = 8765
QUEUE_FILE = "/tmp/jarvis_queue.txt"
RESPONSE_TIMEOUT = 60  # seconds

# Track pending requests
pending_responses = {}
response_lock = threading.Lock()


class JarvisBridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress default logging
        pass
    
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        path = urlparse(self.path).path
        
        if path == "/":
            self._send_json({"status": "ok", "service": "Jarvis Voice Bridge v2"})
        
        elif path == "/speak":
            # Legacy: Mac polls for TTS messages
            if os.path.exists(QUEUE_FILE):
                with open(QUEUE_FILE, 'r') as f:
                    text = f.read().strip()
                if text:
                    open(QUEUE_FILE, 'w').close()  # Clear
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(text.encode())
                    return
            self.send_response(204)
            self.end_headers()
        
        else:
            self._send_json({"error": "Not found"}, 404)
    
    def do_POST(self):
        path = urlparse(self.path).path
        
        # Read body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode() if content_length > 0 else ""
        
        if path == "/chat":
            # Two-way chat endpoint
            try:
                data = json.loads(body) if body else {}
                text = data.get("text", "").strip()
                
                if not text:
                    self._send_json({"error": "No text provided"}, 400)
                    return
                
                print(f"📥 Received: {text[:50]}...")
                
                # Send to Jarvis via clawdbot session
                response = send_to_jarvis(text)
                
                if response:
                    print(f"📤 Response: {response[:50]}...")
                    self._send_json({"response": response})
                else:
                    self._send_json({"error": "No response received"}, 504)
                    
            except json.JSONDecodeError:
                self._send_json({"error": "Invalid JSON"}, 400)
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
        
        elif path == "/speak":
            # Legacy: Queue TTS message
            try:
                data = json.loads(body) if body else {}
                text = data.get("text", "").strip()
                if text:
                    with open(QUEUE_FILE, 'w') as f:
                        f.write(text)
                    self._send_json({"status": "queued"})
                else:
                    self._send_json({"error": "No text"}, 400)
            except:
                self._send_json({"error": "Invalid request"}, 400)
        
        else:
            self._send_json({"error": "Not found"}, 404)


def send_to_jarvis(text):
    """
    Send message to Jarvis and get response.
    Uses Telegram bot API since Clawdbot session messaging is async.
    """
    import requests
    
    # Get bot token from environment or config
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        # Try to read from clawdbot config
        try:
            config_path = os.path.expanduser("~/.config/clawdbot/config.yaml")
            if os.path.exists(config_path):
                import yaml
                with open(config_path) as f:
                    config = yaml.safe_load(f)
                    bot_token = config.get("telegram", {}).get("botToken")
                    chat_id = config.get("telegram", {}).get("allowedUsers", [None])[0]
        except:
            pass
    
    if not bot_token or not chat_id:
        return "Error: Telegram credentials not configured"
    
    # Get current update_id to know where to start listening
    updates_url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    try:
        resp = requests.get(updates_url, params={"limit": 1, "offset": -1}, timeout=5)
        updates = resp.json().get("result", [])
        last_update_id = updates[-1]["update_id"] if updates else 0
    except:
        last_update_id = 0
    
    # Send message
    send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        requests.post(send_url, json={"chat_id": chat_id, "text": text}, timeout=10)
    except Exception as e:
        return f"Error sending message: {e}"
    
    # Wait for response (poll for new messages from bot)
    start_time = time.time()
    while time.time() - start_time < RESPONSE_TIMEOUT:
        try:
            resp = requests.get(updates_url, params={
                "offset": last_update_id + 1,
                "timeout": 10
            }, timeout=15)
            
            updates = resp.json().get("result", [])
            for update in updates:
                last_update_id = update["update_id"]
                msg = update.get("message", {})
                
                # Check if this is from the bot (Jarvis's response)
                if msg.get("from", {}).get("is_bot"):
                    return msg.get("text", "")
                    
        except Exception as e:
            print(f"Poll error: {e}")
            time.sleep(1)
    
    return None


def main():
    print("=" * 50)
    print("🔵 Jarvis Voice Bridge v2")
    print("=" * 50)
    print(f"Host: {HOST}:{PORT}")
    print(f"Endpoints:")
    print(f"  POST /chat - Two-way chat (send text, get response)")
    print(f"  GET  /speak - Poll for TTS queue")
    print(f"  POST /speak - Queue TTS message")
    print("=" * 50)
    
    server = HTTPServer((HOST, PORT), JarvisBridgeHandler)
    print(f"\n✅ Listening on http://{HOST}:{PORT}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
