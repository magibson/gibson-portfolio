# Lessons Learned

*Patterns to avoid repeating mistakes. Review at session start.*

---

## Deliverables

- **Maps:** Use `staticmap` or `folium` with real tiles. Never matplotlib scatter plots.
- **PDFs:** Visual check before sending. Test text wrapping, margins, cutoffs.
- **Reports:** Confirm requirements before building. "List" ≠ "schedule".

## Token Efficiency

- **Research/summarization:** Route to Gemini first, not Claude.
- **X/Twitter search:** Use Grok (`integrations/xai/grok.py`).
- **Claude:** Reserve for reasoning, judgment, conversation.
- **Complex tasks:** Spawn sub-agent, don't block main thread.

## Sub-Agents

- Send requirement updates BEFORE spawning, not after (messages may timeout).
- Be explicit about what NOT to include.
- Check sub-agent understood requirements before it starts heavy work.

## Communication

- Don't declare "done" without verifying output quality.
- Ask "Would a staff engineer approve this?" before sending.
- When corrected, update this file immediately.

## Pre-Send Checklist (Deliverables)

Before sending any file/report to Matt:
- [ ] Does it actually address what he asked for?
- [ ] Did I visually verify the output (not just assume it worked)?
- [ ] Are there any obvious issues (cut-off text, broken formatting, placeholder content)?
- [ ] Would I be embarrassed if this was wrong?

---

## Testing

- **Test before confirming:** Don't say "fixed" until you verify the fix works end-to-end.
- **Use Matt's access path:** Test via Tailscale IP (100.83.250.65), not localhost or public IP.
- **Browser caching:** Hard refresh or incognito aren't always enough - verify server is serving updated content.
- **Flask templates:** Add `TEMPLATES_AUTO_RELOAD = True` to avoid stale template caching.

## Changelog

- **2026-02-03:** Added testing lessons after Polymarket "undefined" bug - told Matt it was fixed before actually verifying. Also: always test from Matt's access path (Tailscale).
- **2026-02-02:** Created after PDF/map mistakes. Lessons: real map tiles, visual QA, route research to Gemini, spawn agents for complex work, confirm requirements before building.
