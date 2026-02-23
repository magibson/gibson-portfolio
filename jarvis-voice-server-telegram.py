#!/usr/bin/env python3
"""
Jarvis Voice Server - Telegram Route
Routes voice through Telegram for full tool access
"""

import os
import sys
import json
import time
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# Configuration
HOST = "100.82.133.57"
PORT = 8765

# Load Telegram config
def load_telegram_config():
    config_path = os.path.expanduser("~/.clawdbot/clawdbot.json")
    try:
        with open(config_path) as f:
            config = json.load(f)
            return config.get("telegram", {})
    except:
        return {}

telegram_config = load_telegram_config()
BOT_TOKEN = telegram_config.get("botToken", os.environ.get("TELEGRAM_BOT_TOKEN"))
CHAT_ID = "8206180417"  # Matt's Telegram ID

last_update_id = 0

def get_last_update_id():
    """Get the latest update ID to know where to start listening"""
    global last_update_id
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        r = requests.get(url, params={"limit": 1, "offset": -1}, timeout=5)
        updates = r.json().get("result", [])
        if updates:
            last_update_id = updates[-1]["update_id"]
    except:
        pass
    return last_update_id

def send_telegram_message(text):
    """Send message to Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": f"🎤 {text}"
        }, timeout=10)
        return r.json().get("ok", False)
    except Exception as e:
        print(f"Send error: {e}")
        return False

def wait_for_response(timeout=90):
    """Wait for bot's response"""
    global last_update_id
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    start = time.time()
    
    while time.time() - start < timeout:
        try:
            r = requests.get(url, params={
                "offset": last_update_id + 1,
                "timeout": 10
            }, timeout=15)
            
            updates = r.json().get("result", [])
            for update in updates:
                last_update_id = update["update_id"]
                msg = update.get("message", {})
                
                # Check if it's from the bot (my response)
                if msg.get("from", {}).get("is_bot"):
                    text = msg.get("text", "")
                    # Skip if it's my own voice message echo
                    if text.startswith("🎤"):
                        continue
                    return text
        except Exception as e:
            print(f"Poll error: {e}")
            time.sleep(1)
    
    return None


class VoiceServerHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[{time.strftime('%H:%M:%S')}] {args[0]}")
    
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
        if path == "/" or path == "/health":
            self._send_json({
                "status": "ok", 
                "mode": "telegram-tools",
                "bot_configured": bool(BOT_TOKEN)
            })
        else:
            self._send_json({"error": "not found"}, 404)
    
    def do_POST(self):
        path = urlparse(self.path).path
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode() if content_length > 0 else ""
        
        if path == "/chat":
            try:
                data = json.loads(body) if body else {}
                text = data.get("text", "").strip()
                
                if not text:
                    self._send_json({"error": "no text provided"}, 400)
                    return
                
                print(f"📥 {text[:60]}{'...' if len(text) > 60 else ''}")
                
                # Get current update ID before sending
                get_last_update_id()
                
                start = time.time()
                
                # Send to Telegram
                if not send_telegram_message(text):
                    self._send_json({"error": "Failed to send to Telegram"}, 500)
                    return
                
                # Wait for my response
                response = wait_for_response(timeout=90)
                elapsed = time.time() - start
                
                if response:
                    print(f"📤 ({elapsed:.1f}s) {response[:60]}{'...' if len(response) > 60 else ''}")
                    self._send_json({
                        "response": response,
                        "latency_ms": int(elapsed * 1000)
                    })
                else:
                    self._send_json({"error": "No response received"}, 504)
                
            except json.JSONDecodeError:
                self._send_json({"error": "invalid JSON"}, 400)
            except Exception as e:
                print(f"Error: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "not found"}, 404)


def main():
    global last_update_id
    
    print("=" * 50)
    print("🔵 JARVIS Voice Server (Telegram Tools)")
    print("=" * 50)
    print(f"Tailscale: http://{HOST}:{PORT}")
    print(f"Bot Token: {'✅' if BOT_TOKEN else '❌'}")
    print(f"Chat ID: {CHAT_ID}")
    print()
    
    if not BOT_TOKEN:
        print("❌ No Telegram bot token found!")
        sys.exit(1)
    
    # Initialize update ID
    get_last_update_id()
    print(f"Starting from update ID: {last_update_id}")
    
    print()
    print("Endpoints:")
    print("  POST /chat - Voice text → Telegram → Tools → Response")
    print("  GET  /     - Status")
    print("=" * 50)
    print()
    
    server = HTTPServer((HOST, PORT), VoiceServerHandler)
    print(f"✅ Listening on http://{HOST}:{PORT}\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Shutting down")
        server.shutdown()


if __name__ == "__main__":
    main()
