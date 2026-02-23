#!/usr/bin/env python3
"""
Jarvis Voice Server - Secure Edition
- Auth token required
- Rate limiting
- Modular backend (easy to add tools later)
"""

import os
import sys
import json
import time
import hashlib
import hmac
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from datetime import datetime

# ===== CONFIGURATION =====
HOST = "100.82.133.57"  # Tailscale IP only
PORT = 8765
AUTH_TOKEN = "1fa124bc0a493b0db3dda04174bf83f9a5d3621fc51a03b916bf5784dc2f82bf"

# Rate limiting: max requests per minute
RATE_LIMIT = 20
request_times = []

# Backend mode: "direct" (Claude API) or "clawdbot" (full tools - future)
BACKEND_MODE = "direct"

# Anthropic settings
MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 500

# ===== CONVERSATION STATE =====
conversation_history = []
MAX_HISTORY = 20

# ===== LOAD API KEY =====
def load_api_key():
    try:
        auth_file = os.path.expanduser("~/.clawdbot/agents/main/agent/auth-profiles.json")
        with open(auth_file) as f:
            data = json.load(f)
            for profile in data.get("profiles", {}).values():
                if profile.get("key"):
                    return profile["key"]
    except:
        pass
    return os.environ.get("ANTHROPIC_API_KEY")

ANTHROPIC_API_KEY = load_api_key()


def load_jarvis_context():
    """Load Jarvis personality and context"""
    import pytz
    
    try:
        eastern = pytz.timezone('America/New_York')
        now = datetime.now(eastern)
        time_str = now.strftime("%I:%M %p")
        date_str = now.strftime("%A, %B %d, %Y")
        hour = now.hour
        if 5 <= hour < 12:
            period = "morning"
        elif 12 <= hour < 17:
            period = "afternoon"
        elif 17 <= hour < 21:
            period = "evening"
        else:
            period = "night"
    except:
        time_str = "unknown"
        date_str = "unknown"
        period = "day"
    
    context = f"""You are Jarvis, Matt Gibson's AI assistant.

PERSONALITY:
- Casual and friendly, like a helpful buddy
- Address him as "Mr. Gibson" or "sir" - respectful but not stiff
- Relaxed, conversational tone - not robotic or stuffy
- Witty when it fits, but natural about it
- Helpful and to the point

VOICE GUIDELINES (responses are spoken aloud):
- Keep it short - 1-2 sentences usually
- Talk like a normal person
- Say "degrees Fahrenheit" not symbols
- Spell out numbers naturally
- No lists, no markdown, just natural speech

CURRENT TIME: {time_str} Eastern Time
DATE: {date_str}
It's currently {period}.

You're his AI assistant - helpful, casual, respectful."""

    # Load user context
    try:
        with open("/home/clawd/clawd/USER.md") as f:
            user_info = f.read()[:1500]
            context += f"\n\nAbout Matt:\n{user_info}"
    except:
        pass
    
    return context


def rate_limit_check():
    """Check if request is within rate limits"""
    global request_times
    now = time.time()
    # Remove requests older than 60 seconds
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


def get_response_direct(user_message):
    """Get response from Claude API directly"""
    global conversation_history
    
    try:
        import anthropic
    except ImportError:
        return "Error: anthropic package not installed"
    
    if not ANTHROPIC_API_KEY:
        return "Error: No API key configured"
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    conversation_history.append({"role": "user", "content": user_message})
    
    # Trim history
    if len(conversation_history) > MAX_HISTORY * 2:
        conversation_history = conversation_history[-MAX_HISTORY * 2:]
    
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=load_jarvis_context(),
            messages=conversation_history
        )
        
        assistant_message = response.content[0].text
        conversation_history.append({"role": "assistant", "content": assistant_message})
        
        return assistant_message
    except Exception as e:
        return f"Sorry, I encountered an error: {str(e)}"


def get_response(user_message):
    """Route to appropriate backend"""
    if BACKEND_MODE == "direct":
        return get_response_direct(user_message)
    elif BACKEND_MODE == "clawdbot":
        # Future: full tools integration
        return get_response_direct(user_message)  # Fallback for now
    else:
        return "Error: Unknown backend mode"


class SecureVoiceHandler(BaseHTTPRequestHandler):
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
            # Health check doesn't require auth
            self._send_json({"status": "ok"})
        elif path == "/download/menubar":
            # Serve the menubar script (no auth needed for download)
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
                "mode": BACKEND_MODE,
                "history_length": len(conversation_history)
            })
        elif path == "/clear":
            if not verify_auth(self.headers):
                self._send_json({"error": "unauthorized"}, 401)
                return
            conversation_history.clear()
            self._send_json({"status": "cleared"})
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
                
                print(f"📥 {text[:60]}{'...' if len(text) > 60 else ''}")
                
                start = time.time()
                response = get_response(text)
                elapsed = time.time() - start
                
                print(f"📤 ({elapsed:.1f}s) {response[:60]}{'...' if len(response) > 60 else ''}")
                
                self._send_json({
                    "response": response,
                    "latency_ms": int(elapsed * 1000)
                })
                
            except json.JSONDecodeError:
                self._send_json({"error": "invalid JSON"}, 400)
            except Exception as e:
                print(f"Error: {e}")
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "not found"}, 404)


def main():
    print("=" * 50)
    print("🔵 JARVIS Voice Server (Secure)")
    print("=" * 50)
    print(f"Host: {HOST}:{PORT}")
    print(f"Auth: Token required ({'✅' if AUTH_TOKEN else '❌'})")
    print(f"API Key: {'✅' if ANTHROPIC_API_KEY else '❌'}")
    print(f"Backend: {BACKEND_MODE}")
    print(f"Rate Limit: {RATE_LIMIT}/min")
    print("=" * 50)
    
    if not ANTHROPIC_API_KEY:
        print("❌ No API key found!")
        sys.exit(1)
    
    server = HTTPServer((HOST, PORT), SecureVoiceHandler)
    print(f"\n✅ Listening on http://{HOST}:{PORT}\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Shutting down")
        server.shutdown()


if __name__ == "__main__":
    main()
