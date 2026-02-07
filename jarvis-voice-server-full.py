#!/usr/bin/env python3
"""
Jarvis Voice Server - Full Tools Version
Routes voice through Clawdbot for full tool access (Whoop, email, web, etc.)
"""

import os
import sys
import json
import time
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# Configuration
HOST = "100.83.250.65"  # Tailscale IP
PORT = 8765
TIMEOUT = 120  # Longer timeout for tool calls

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
            self._send_json({"status": "ok", "mode": "full-tools"})
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
                
                # Add voice context to the message
                voice_text = f"[Voice input] {text}"
                
                start = time.time()
                response = self.send_to_clawdbot(voice_text)
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
    
    def send_to_clawdbot(self, text):
        """Send message through Clawdbot agent for full tool access"""
        try:
            # Use clawdbot agent command to process with tools
            # --local runs embedded, --json for parseable output
            cmd = [
                "clawdbot", "agent",
                "--message", text,
                "--timeout", str(TIMEOUT),
                "--json"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=TIMEOUT + 10,
                cwd="/home/clawd/clawd"
            )
            
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    # Extract the assistant's response
                    response = data.get("response", data.get("content", ""))
                    if isinstance(response, list):
                        # Handle content blocks
                        text_parts = [b.get("text", "") for b in response if b.get("type") == "text"]
                        response = " ".join(text_parts)
                    return response.strip() or "I processed that but have no response."
                except json.JSONDecodeError:
                    # Not JSON, return raw output
                    return result.stdout.strip() or "Done."
            else:
                print(f"Clawdbot error: {result.stderr}")
                return f"Sorry, I had trouble processing that. {result.stderr[:100]}"
                
        except subprocess.TimeoutExpired:
            return "Sorry, that took too long. Try a simpler request."
        except Exception as e:
            print(f"Error calling clawdbot: {e}")
            return f"Sorry, I encountered an error: {str(e)}"


def main():
    print("=" * 50)
    print("🔵 JARVIS Voice Server (Full Tools)")
    print("=" * 50)
    print(f"Tailscale: http://{HOST}:{PORT}")
    print(f"Mode: Full Clawdbot integration (tools enabled)")
    print()
    print("Endpoints:")
    print("  POST /chat - Send text, get response with tool access")
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
