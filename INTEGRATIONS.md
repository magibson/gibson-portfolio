# INTEGRATIONS.md - What I Can Do

**Read this file at the start of every session to remember my capabilities.**

## Email (Gmail)
- **Status:** ✅ Working
- **Access:** Read emails via himalaya CLI
- **Config:** `~/.config/himalaya/config.toml`
- **Account:** msgibson103@gmail.com
- **Commands:**
  - `~/bin/himalaya envelope list` - list emails
  - `~/bin/himalaya message read <ID>` - read email
  - `~/bin/himalaya envelope list --folder "Sent"` - other folders

## Google Calendar
- **Status:** ✅ Working (read + write)
- **Credentials:** `~/clawd/google-credentials.json`
- **Tokens:** `~/clawd/google-tokens.json`
- **Scopes:** calendar (full), gmail.readonly
- **Can do:** Read events, CREATE events, modify events
- **API:** Direct Google Calendar API calls with OAuth tokens

## Voice (Jarvis TTS on Mac)
- **Status:** ✅ Working (requires Matt's Mac)
- **Server:** `python jarvis_server_5001.py` in `~/mlx-audio/jarvis_clips`
- **Client:** `python jarvis-menubar.py` (menubar app with Cmd+Shift+J)
- **VPS endpoint:** `http://100.83.250.65:8765` (Tailscale)
- **Requires:** Tailscale connected on Mac

## Voice Calls (Retell AI)
- **Status:** ✅ Configured
- **Use for:** Outbound phone calls, appointment booking
- **Note:** Check `~/clawd/.env` for API keys

## TickTick (Tasks)
- **Status:** 🔄 Partial (OAuth needs setup)
- **Credentials:** Client ID/Secret in env

## Whoop (Health Data)
- **Status:** ✅ Working (v2 API)
- **Script:** `python3 ~/clawd/whoop-v2.py`
- **Data:** Recovery, Sleep, Strain/Cycles
- **Credentials:** Matt's own app (3108dd26...)
- **Note:** v1 API broken, v2 works - always use v2 endpoints

## Market Data
- **Status:** ✅ Working
- **Source:** Yahoo Finance API (free, no key needed)
- **Symbols:** S&P 500, VIX, 10Y Treasury, TSLA

## Weather
- **Status:** ✅ Working
- **Source:** Open-Meteo API (free)
- **Location:** Red Bank, NJ

## Reservations
- **OpenTable:** 🔄 Needs browser session
- **Resy:** 🔄 Needs API tokens
- **Yelp:** 🔄 Needs API key

---

## Matt's Info (for bookings)
- **Name:** Matthew Gibson
- **Email:** msgibson103@gmail.com
- **Phone:** (check USER.md or memory)

---

*Last updated: 2026-01-30*
