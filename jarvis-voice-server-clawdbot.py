#!/usr/bin/env python3
"""
Jarvis Voice Server - Clawdbot Edition
Routes voice commands through the full Clawdbot system with all tools.

- Auth token required
- Rate limiting  
- Uses `clawdbot agent` CLI for full tool access (Whoop, email, calendar, web, etc.)
- Tailscale only (100.83.250.65)
"""

import os
import sys
import json
import time
import hmac
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from datetime import datetime

# ===== CONFIGURATION =====
HOST = "100.83.250.65"  # Tailscale IP only
PORT = 8765
AUTH_TOKEN = "1fa124bc0a493b0db3dda04174bf83f9a5d3621fc51a03b916bf5784dc2f82bf"

# Rate limiting: max requests per minute
RATE_LIMIT = 20
request_times = []

# Clawdbot session - uses the main agent session with full tools
SESSION_ID = "agent:main:main"
TIMEOUT_SECONDS = 120  # Allow time for tool calls

# ===== VOICE CONTEXT =====
VOICE_CONTEXT = """[VOICE] Keep response SHORT (1-2 sentences). No markdown. Speak naturally - this will be read aloud."""


def rate_limit_check():
    """Check if request is within rate limits"""
    global request_times
    now = time.time()
    request_times = [t for t in request_times if now - t < 60]
    if len(request_times) >= RATE_LIMIT:
        return False
    request_times.append(now)
    return True


def verify_auth(headers):
    """Verify authorization header"""
    auth = headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        return hmac.compare_digest(token, AUTH_TOKEN)
    return False


def get_response_clawdbot(user_message):
    """Get response from Clawdbot with full tool access"""
    
    # Add voice context to the message
    full_message = f"{VOICE_CONTEXT}\n\nMatt says: {user_message}"
    
    try:
        # Call clawdbot agent CLI
        result = subprocess.run(
            [
                "clawdbot", "agent",
                "--session-id", SESSION_ID,
                "--message", full_message,
                "--json"
            ],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            cwd="/home/clawd/clawd"
        )
        
        if result.returncode != 0:
            print(f"Clawdbot error: {result.stderr}")
            return "Sorry, I had trouble processing that. Can you try again?"
        
        # Parse JSON response
        response_data = json.loads(result.stdout)
        
        if response_data.get("status") == "ok":
            payloads = response_data.get("result", {}).get("payloads", [])
            if payloads and payloads[0].get("text"):
                return payloads[0]["text"]
        
        # Fallback
        return "I processed your request but didn't have a response."
        
    except subprocess.TimeoutExpired:
        return "Sorry, that took too long. Can you try a simpler request?"
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"Raw output: {result.stdout[:500]}")
        return "Sorry, I had trouble understanding the response."
    except Exception as e:
        print(f"Error: {e}")
        return f"Sorry, something went wrong: {str(e)}"


class VoiceHandler(BaseHTTPRequestHandler):
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
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def do_GET(self):
        path = urlparse(self.path).path
        
        if path == "/health":
            self._send_json({"status": "ok", "mode": "clawdbot"})
        elif path == "/download/menubar":
            try:
                with open("/home/clawd/clawd/jarvis-menubar.py") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.send_header('Content-Disposition', 'attachment; filename="jarvis-menubar.py"')
                self.end_headers()
                self.wfile.write(content.encode())
            except:
                self._send_json({"error": "file not found"}, 404)
        elif path == "/":
            if not verify_auth(self.headers):
                self._send_json({"error": "unauthorized"}, 401)
                return
            self._send_json({
                "status": "ok",
                "mode": "clawdbot",
                "session": SESSION_ID,
                "tools": "full"
            })
        else:
            self._send_json({"error": "not found"}, 404)
    
    def do_POST(self):
        path = urlparse(self.path).path
        
        # Auth check
        if not verify_auth(self.headers):
            self._send_json({"error": "unauthorized"}, 401)
            return
        
        # Rate limit check
        if not rate_limit_check():
            self._send_json({"error": "rate limited"}, 429)
            return
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode() if content_length > 0 else ""
        
        if path == "/chat":
            try:
                data = json.loads(body) if body else {}
                text = data.get("text", "").strip()
                
                if not text:
                    self._send_json({"error": "no text provided"}, 400)
                    return
                
                print(f"🎤 {text[:80]}{'...' if len(text) > 80 else ''}")
                
                start = time.time()
                response = get_response_clawdbot(text)
                elapsed = time.time() - start
                
                print(f"🔊 ({elapsed:.1f}s) {response[:80]}{'...' if len(response) > 80 else ''}")
                
                self._send_json({
                    "response": response,
                    "latency_ms": int(elapsed * 1000),
                    "mode": "clawdbot"
                })
                
            except json.JSONDecodeError:
                self._send_json({"error": "invalid JSON"}, 400)
            except Exception as e:
                print(f"Error: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "not found"}, 404)


def main():
    print("=" * 60)
    print("🎤 JARVIS Voice Server - CLAWDBOT EDITION")
    print("=" * 60)
    print(f"Host: {HOST}:{PORT}")
    print(f"Auth: Token required ✅")
    print(f"Mode: Full Clawdbot (all tools)")
    print(f"Session: {SESSION_ID}")
    print(f"Timeout: {TIMEOUT_SECONDS}s")
    print(f"Rate Limit: {RATE_LIMIT}/min")
    print("=" * 60)
    print("Tools available: Whoop, Email, Calendar, Web Search,")
    print("                 Browser, File Access, and more!")
    print("=" * 60)
    
    # Test clawdbot is available
    try:
        result = subprocess.run(
            ["clawdbot", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        version = result.stdout.strip() or "unknown"
        print(f"Clawdbot: {version}")
    except Exception as e:
        print(f"⚠️ Warning: clawdbot CLI check failed: {e}")
    
    server = HTTPServer((HOST, PORT), VoiceHandler)
    print(f"\n✅ Listening on http://{HOST}:{PORT}\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Shutting down")
        server.shutdown()


if __name__ == "__main__":
    main()
