# Voice Channel for Clawdbot

The voice channel routes spoken commands through the full Clawdbot system, giving Matt access to all tools (Whoop, email, calendar, web search, etc.) via voice.

## Architecture

```
Mac (jarvis-menubar.py)
    ↓ transcribes speech
    ↓ sends text via HTTP
VPS (jarvis-voice-server-clawdbot.py)
    ↓ calls `clawdbot agent` CLI
Clawdbot Gateway (full tool access)
    ↓ returns response
VPS (jarvis-voice-server-clawdbot.py)
    ↓ sends text response
Mac (Qwen3-TTS on port 5001)
    ↓ speaks response
```

## Files

- `/home/clawd/clawd/jarvis-voice-server-clawdbot.py` - Main server (Clawdbot integration)
- `/home/clawd/clawd/jarvis-voice-server-secure.py` - Old server (direct Claude API, no tools)
- `/home/clawd/clawd/jarvis-voice.service` - Systemd service file
- `/home/clawd/clawd/test-voice-server.sh` - Test script

## Security

1. **Tailscale only** - Server binds to 100.83.250.65 (Tailscale IP)
2. **Auth token required** - All requests must include `Authorization: Bearer <token>`
3. **Rate limiting** - 20 requests/minute max
4. **No public exposure** - Not accessible from internet

## Running the Server

### Manual start:
```bash
cd /home/clawd/clawd
python3 jarvis-voice-server-clawdbot.py
```

### Background:
```bash
cd /home/clawd/clawd
nohup python3 jarvis-voice-server-clawdbot.py >> /tmp/jarvis-voice.log 2>&1 &
```

### As systemd service (requires sudo):
```bash
sudo cp /home/clawd/clawd/jarvis-voice.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable jarvis-voice
sudo systemctl start jarvis-voice
```

## API Endpoints

### GET /health
Health check (no auth required).
```bash
curl http://100.83.250.65:8765/health
# {"status": "ok", "mode": "clawdbot"}
```

### GET /
Status with auth.
```bash
curl http://100.83.250.65:8765/ -H "Authorization: Bearer <token>"
# {"status": "ok", "mode": "clawdbot", "session": "agent:main:main", "tools": "full"}
```

### POST /chat
Send a voice command.
```bash
curl -X POST http://100.83.250.65:8765/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"text": "What is the weather?"}'
# {"response": "It's 55 degrees and sunny.", "latency_ms": 15000, "mode": "clawdbot"}
```

## Performance

- Simple responses: ~10-15 seconds
- Tool calls (web search, calendar, etc.): 30-60 seconds
- Cached responses: faster on repeat queries

The overhead is from the full Clawdbot agent loop with tool access. This is the tradeoff for having ALL tools available.

## Mac Client

No changes needed to the Mac client (`jarvis-menubar.py`). It continues to:
1. Send transcribed text to `/chat` endpoint
2. Receive text response
3. Send to local TTS (Qwen3-TTS on port 5001)

The server handles the Clawdbot routing transparently.

## Configuration

Edit `jarvis-voice-server-clawdbot.py` to change:
- `HOST` - Tailscale IP (default: 100.83.250.65)
- `PORT` - Server port (default: 8765)
- `AUTH_TOKEN` - Authentication token
- `SESSION_ID` - Clawdbot session (default: agent:main:main)
- `TIMEOUT_SECONDS` - Max time for Clawdbot response (default: 120)

## Testing

```bash
./test-voice-server.sh        # Basic tests
./test-voice-server.sh --full # Include tool tests
```
