# MEMORY.md - Long-Term Memory

## Matt Gibson
- 25, NJ (Eastern TZ), lives with parents
- Financial Advisor @ New York Life (Life/Health, SIE, Series 6, 63)
- Email: msgibson103@gmail.com | Phone: 732-533-3025
- Casual, witty, efficient — hates fluff
- Dad: Michael (michael.gibson@ey.com) | Brother: Carter (carterg24@icloud.com)
- Use "Matthew" with family

## 2026-2027 Goals
1. Grow book of business (advisor)
2. Health: exercise + nutrition
3. Photography: @mattgibsonpics growth
4. Creative: Premiere Pro, color grading
5. Move out by 2027

## Active Projects
- **Kalshi Prediction Markets:** Full API integration at `~/clawd/integrations/kalshi/`. ~41 positions, $481 total ($86 cash + $395 positions). Rebalanced Feb 10: sold dead-weight long-dated NOs, deployed into 3-6 month catalyst plays. **5-layer monitoring:** sync 4x daily, healthcheck daily, weekly report Sundays, resting order monitor 2x daily, daily self-audit 9 AM ET. Scripts: `kalshi-sync.py`, `kalshi-healthcheck.py`, `kalshi-weekly-report.py`, `kalshi-resting-monitor.py`, `kalshi-weather.py`, `kalshi-weather-paper.py`, `kalshi-weather-score.py`, `daily-self-audit.py`. Data: `data/kalshi/snapshots/`, `data/audits/`. Weather paper trading: 2-week test Feb 11-24, σ bug fixed (1.5 flat). **RULES: Show FULL trade list before executing. Include fees in P/L. No trades without Matt's approval. VERIFY subagent cron creation.**
- **Voice Calling:** ElevenLabs + Claude bridge, port 8013, `jarvis-voice.service`
- **AI Hedge Fund:** `~/clawd/projects/ai-hedge-fund/` — 18 AI analyst agents, yfinance data (free), use Claude Opus
- **Trading Challenge:** Jan 31 - Feb 28, beat S&P 500 (see `memory/trading-challenge.md`). Monday rebalance: trim AMD → add VST
- **Mortgage Leads:** Propwire → Tracerfy → dial lists (Monmouth County, $900K+)
- **Jarvis Prospector:** LinkedIn Sales Nav lead scraper. Chrome extension + Flask API (port 8089). 4 campaigns: Local Job Changes, Federal Employees, Young Families, High Earners. AI-drafted connection requests + follow-up DMs via Gemini. Dashboard at 100.83.250.65:8089. Extension in `projects/linkedin-prospector/extension/`. Matt tracks leads post-connection in Salesforce (NYL internal).
- **Photography:** gibsoncaptures.com (Matt's own site, already has his photos)
- **Move-Out Tracker:** Savings calculator for 2027 independence (port 8088)
- **Dashboard:** http://100.83.250.65:8080 (Tailscale)
- **GitHub:** github.com/magibson/JARVIS-workspace (private, auto-push enabled)

## Integrations
- Gmail/Calendar: Google API ✅
- Search: Brave API ✅
- Voice: Menu bar app (Cmd+Shift+J) ✅
- Fitness: Whoop v2 API ✅
- Research: Always include X via Grok (`~/clawd/integrations/xai/grok.py`)
- **Notion: API key at `~/.config/notion/api_key` ✅** (ntn_b21808...). Integration named "Jarvis" connected to Matt's workspace. DO NOT ask Matt to set this up again.

## Preferences
- Model: Claude Sonnet primary
- TTS: Disabled (cost savings)
- Heartbeats: 30-min intervals
- Nightly builds: Small, visible improvements (wake up surprised)

### Model Routing (Cost Optimization)
- **Codex CLI** → ALL coding (daytime and nightly)
- **Gemini** → Research, summarization, one-shot questions
- **Grok** → X/social media search and sentiment
- **Claude** → Conversations, reasoning, planning, judgment

## Narration Leak Fix (Feb 9-11 2026)
- **Root cause:** Draft streaming (`streamMode: "partial"`) auto-disables block streaming (line 37177: `disableBlockStreaming = Boolean(draftStream)`). With block streaming off, the coalescer never runs, so each assistant turn's text becomes a separate Telegram message.
- **Config fix applied Feb 11:** `streamMode: "off"` (disables draft streaming), `blockStreaming: true` (enables block reply pipeline), `blockStreamingCoalesce: { minChars: 100000, maxChars: 100000, idleMs: 300000 }` (holds all text until run end). Pipeline flushes once → one merged message. `shouldDropFinalPayloads` drops redundant per-entry final reply.
- **Trade-off:** No typing indicator (draft streaming disabled). Clean single messages.
- **Previous wrong conclusion:** I claimed no config fix existed. Was wrong — the coalescer works, just couldn't activate with draft streaming on.

## EY Audit Independence Restriction (PERMANENT)
- Matt's dad Michael works at EY → Matt cannot buy EY audit clients
- Restricted: AMZN, GOOGL, META, AAPL, CRM, T, VZ, ORCL, LMT, COF, PG, HPQ, STT
- Clear: TSLA, NVDA, COIN, PLTR, AVGO, RKLB, UNH, TRGP, CCJ
- Full list: `reference/ey-restricted-stocks.md`
- **Always check before recommending stocks**

## Standing Rules
- Nightly builds → `NIGHTLY-BUILDS.md`
- Task review: Morning (~8-9 AM ET) + Evening (~6-7 PM ET)
- Be productive during downtime
- Build things Matt can SEE and USE, not just internal tools
- **NO outbound phone calls without explicit approval first**
- **NO Kalshi trades without Matt's explicit approval**
- Use Tailscale (100.83.250.65) for dashboard access, not public ports
- Don't spam Matt with play-by-play updates — batch results, send once

## Lessons Learned
- Use Google API for email (not himalaya in sandbox)
- Drone: Cold weather = info only, not no-fly
- Keep token usage efficient
- Retell voice agent doesn't follow prompt instructions reliably — DO NOT use for reservations until fixed
- When something fails twice, STOP and ask — don't keep trying variations

---
*For project details, search `memory/` files*
