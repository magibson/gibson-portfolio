#!/usr/bin/env python3
"""
Jarvis Voice Server - Fast voice conversation bridge
Runs on VPS, listens on Tailscale IP

Uses Anthropic API directly with Jarvis's personality/memory for instant responses.
Maintains conversation history within the voice session.

Mac client sends transcribed speech, gets text response to TTS.
"""

import os
import sys
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# Check for anthropic package
try:
    import anthropic
except ImportError:
    print("Installing anthropic...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "anthropic", "-q"])
    import anthropic

# ===== CONFIGURATION =====
HOST = "100.83.250.65"  # Tailscale IP
PORT = 8765
MODEL = "claude-sonnet-4-20250514"  # Fast model for voice
MAX_HISTORY = 20  # Keep last N exchanges

# Load API key from environment
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Jarvis workspace path
WORKSPACE = "/home/clawd/clawd"

# ===== CONVERSATION STATE =====
conversation_history = []

def load_jarvis_context():
    """Load Jarvis's personality and memory for voice conversations"""
    
    # Get current time in Eastern
    from datetime import datetime
    import pytz
    try:
        eastern = pytz.timezone('America/New_York')
        now = datetime.now(eastern)
        time_str = now.strftime("%I:%M %p on %A, %B %d")
        hour = now.hour
        if 5 <= hour < 12:
            greeting_time = "morning"
        elif 12 <= hour < 17:
            greeting_time = "afternoon"
        elif 17 <= hour < 21:
            greeting_time = "evening"
        else:
            greeting_time = "night"
    except:
        time_str = "unknown"
        greeting_time = "day"
    
    context_parts = []
    
    # Core identity - Casual Jarvis
    context_parts.append(f"""You are Jarvis, Matt Gibson's AI assistant.

PERSONALITY:
- Casual and friendly, like a helpful buddy
- Address him as "Mr. Gibson" or "sir" - respectful but not stiff
- Relaxed, conversational tone - not robotic or stuffy
- Witty when it fits, but natural about it
- Helpful and to the point

VOICE GUIDELINES (this is spoken aloud):
- Keep it short - 1-2 sentences usually
- Talk like a normal person, not a butler
- Say "degrees Fahrenheit" not symbols
- No lists, no markdown, just natural speech

CURRENT TIME: {time_str} (Eastern Time)
It's {greeting_time}.

You're his AI assistant - helpful, casual, respectful.""")
    
    # Load IDENTITY.md
    try:
        with open(os.path.join(WORKSPACE, "IDENTITY.md")) as f:
            context_parts.append(f"Identity:\n{f.read()}")
    except:
        pass
    
    # Load USER.md
    try:
        with open(os.path.join(WORKSPACE, "USER.md")) as f:
            content = f.read()
            # Truncate if too long
            if len(content) > 2000:
                content = content[:2000] + "..."
            context_parts.append(f"About the user:\n{content}")
    except:
        pass
    
    # Load recent memory (today's notes)
    today = time.strftime("%Y-%m-%d")
    try:
        with open(os.path.join(WORKSPACE, f"memory/{today}.md")) as f:
            content = f.read()
            if len(content) > 3000:
                content = content[-3000:]  # Keep recent part
            context_parts.append(f"Today's context:\n{content}")
    except:
        pass
    
    # Load MEMORY.md (long-term)
    try:
        with open(os.path.join(WORKSPACE, "MEMORY.md")) as f:
            content = f.read()
            if len(content) > 2000:
                content = content[:2000] + "..."
            context_parts.append(f"Long-term memory:\n{content}")
    except:
        pass
    
    return "\n\n---\n\n".join(context_parts)


def get_jarvis_response(user_message):
    """Get response from Jarvis via Anthropic API"""
    global conversation_history
    
    if not ANTHROPIC_API_KEY:
        return "Error: ANTHROPIC_API_KEY not set"
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # Add user message to history
    conversation_history.append({
        "role": "user",
        "content": user_message
    })
    
    # Trim history if too long
    if len(conversation_history) > MAX_HISTORY * 2:
        conversation_history = conversation_history[-MAX_HISTORY * 2:]
    
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=500,  # Keep responses concise for voice
            system=load_jarvis_context(),
            messages=conversation_history
        )
        
        assistant_message = response.content[0].text
        
        # Add to history
        conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })
        
        return assistant_message
        
    except Exception as e:
        return f"Sorry, I encountered an error: {str(e)}"


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
        
        if path == "/":
            self._send_json({
                "service": "Jarvis Voice Server",
                "status": "ready",
                "history_length": len(conversation_history)
            })
        
        elif path == "/clear":
            conversation_history.clear()
            self._send_json({"status": "history cleared"})
        
        elif path == "/health":
            self._send_json({"status": "ok"})
        
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
                
                start = time.time()
                response = get_jarvis_response(text)
                elapsed = time.time() - start
                
                print(f"📤 ({elapsed:.1f}s) {response[:60]}{'...' if len(response) > 60 else ''}")
                
                self._send_json({
                    "response": response,
                    "latency_ms": int(elapsed * 1000)
                })
                
            except json.JSONDecodeError:
                self._send_json({"error": "invalid JSON"}, 400)
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
        
        else:
            self._send_json({"error": "not found"}, 404)


def main():
    if not ANTHROPIC_API_KEY:
        print("⚠️  ANTHROPIC_API_KEY not set!")
        print("   Export it or add to environment")
        print("   export ANTHROPIC_API_KEY='sk-ant-...'")
        print()
    
    print("=" * 50)
    print("🔵 JARVIS Voice Server")
    print("=" * 50)
    print(f"Tailscale: http://{HOST}:{PORT}")
    print(f"Model: {MODEL}")
    print(f"Workspace: {WORKSPACE}")
    print()
    print("Endpoints:")
    print("  POST /chat  - Send text, get Jarvis response")
    print("  GET  /clear - Clear conversation history")
    print("  GET  /      - Status")
    print("=" * 50)
    
    # Test context loading
    ctx = load_jarvis_context()
    print(f"\n✅ Context loaded ({len(ctx)} chars)")
    print(f"✅ Listening on http://{HOST}:{PORT}\n")
    
    server = HTTPServer((HOST, PORT), VoiceServerHandler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Jarvis Voice Server shutting down")
        server.shutdown()


if __name__ == "__main__":
    main()
