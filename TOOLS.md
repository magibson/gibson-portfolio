# TOOLS.md - Local Notes

Skills define *how* tools work. This file is for *your* specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:
- Camera names and locations
- SSH hosts and aliases  
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras
- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH
- home-server → 192.168.1.100, user: admin

### TTS
- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

### Codex CLI
- **Use for:** ALL coding tasks (daytime AND nightly) — NOT just background work
- **Location:** /home/clawd/.npm-global/bin/codex
- **Auth:** Needs `codex login` to authenticate with OpenAI

### Gemini
- **Use for:** Research, summarization, one-shot questions
- **Saves Claude budget for conversations/reasoning**

---

Add whatever helps you do your job. This is your cheat sheet.

### X Research (via Grok)
- **Always include X in research tasks** - Matt's preference
- Location: `~/clawd/integrations/xai/grok.py`
- Usage: `from grok import search_x; result = search_x("query", "context")`
- Provides: Real-time sentiment, trader chatter, breaking news
- Pre-built scans: `~/clawd/scripts/x-research-scan.py [morning|noon|evening]`
- Cost: Uses xAI API credits (reasonable, not expensive)
