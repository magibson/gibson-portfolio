# HEARTBEAT.md

## Model Routing (ALWAYS FOLLOW)
- **Codex CLI** → ALL coding tasks
- **Gemini** → Research, summarization
- **Grok** → X/social search
- **Claude** → Conversations, reasoning, planning, judgment

Use judgment for edge cases (e.g., trivial inline fixes don't need Codex).

## Research Rule
Include X via Grok in research tasks: `from grok import search_x`

## Morning (~8-9 AM ET)
- Log Whoop: `python3 ~/clawd/scripts/daily-health-log.py` (uses whoop-v2.py for token refresh)
- Health alerts (recovery <50%, sleep <6h)
- Review TickTick tasks
- Prep 8:30 AM briefing

## Evening (~6-7 PM ET)
- Health check: `python3 ~/clawd/scripts/health-check.py`
- Review new tasks
- Plan nightly build

## Trading Challenge (ACTIVE)
**Details:** `memory/trading-challenge.md`
- Check positions via Alpaca
- Compare vs VOO
- Watch stop losses (-5% position, -10% portfolio)
- Current: AMD, NVDA, VST

## Nightly Builds
- Pick ONE improvement
- Use Codex CLI (saves Claude tokens)
- Log to `NIGHTLY-BUILDS.md`
- Goal: Matt wakes up surprised

## Standing Tasks
- Kanban: `~/clawd/projects/morning-dashboard/kanban.json`
- Reference folder: `~/clawd/reference/` (resurface saved items when relevant)
- **Calendar logging:** Log work activities in real-time using `python3 ~/clawd/scripts/jarvis-calendar.py`
