# Mac Mini Project Ideas (Feb 23 2026)

1. Kalshi/Polymarket arbitrage bot (Medium)
2. Real estate deal auto-underwriter (Medium)
3. AI podcast — your voice, zero recording (Medium)
4. LinkedIn content machine (Easy-Medium) — OpenClaw skill exists now
5. Prospect intelligence dossier generator (Medium)
6. AI security camera brain — Frigate + LLM (Medium-Hard)
7. Personal finance autopilot — Plaid + local AI (Easy-Medium)
8. Whoop + Sleep → Day Optimizer (Easy) ← build first
9. Local AI second brain — RAG over everything (Medium)
10. Automated meeting debrief + CRM update (Easy-Medium)
11. Home Assistant hub (Medium)
12. News sentiment → position signal bot (Medium)
13. Competitor/market intelligence stalker (Easy-Medium)
14. AI-powered lead scoring engine (Medium)
15. "What should I build next?" agent — weekly self-improvement scanner (Easy)

Top 3 to build first: Whoop Optimizer, Kalshi Arb Bot, LinkedIn Content Machine

---

# Wholesaler SaaS — "DealSource" (Feb 23 2026)

## Concept
All-in-one lead gen tool for real estate wholesalers. Starts with attorney finder (probate/estate/divorce attorneys by county) + skip tracing + AI outreach sequences. Expands into distressed property lists + CRM.

## Positioning
"The only wholesaler tool that finds the attorneys, not just the properties."

## Pricing
$99/month MVP → $149/month with property lists

## Plan
1. DM 20 wholesalers this week to validate
2. Build attorney finder + skip tracing UI + AI outreach (weeks 2-6)
3. 3 free beta users → testimonials (weeks 7-8)
4. Launch $99/month week 9
5. Add property lists month 3+ (once revenue covers data costs)

## Key risks
- Slow ROI for users (attorney pipeline takes 60-90 days)
- Distribution — need YouTube demo + wholesaler community presence
- Not an insider — beta feedback is critical

## Stack
State bar sites (free) + Google Maps API + Tracerfy (already built) + Claude outreach
LinkedIn = optional enrichment only, not core dependency

## Target
50 users @ $149/month = $7,500 MRR

---

# Self-Improvement Scout Finds — Feb 27, 2026

## 1. AI Website Lead Capture Widget — onleads.chat (Easy, ~$0 to test)
**What it is:** AI chat widget that engages website visitors, qualifies leads, and books appointments automatically. 14-day free trial.
**Why it helps Matt:** If Matt ever builds a financial advisor landing page, this converts cold traffic into booked appointments with zero manual effort. Shown 16.7% visitor-to-lead rate and 34.6% lead-to-booking rate in live tests. CRM sync (HubSpot) included.
**Next step:** Worth testing once a landing page exists. Free trial, 5-min setup.

## 2. obra/superpowers — Agentic Skills Framework (Easy, free, open source)
**What it is:** GitHub-trending (~64k stars, 8k this week) composable "skills" framework for coding agents. Works with Claude Code + Cursor. Automated TDD, spec-driven development, subagent orchestration.
**Why it helps:** When building DealSource or other projects, this gives Claude Code a methodology that reduces hallucination/deviation. Lets me work autonomously for hours without going off-plan.
**Next step:** Install as Claude Code plugin: `/plugin marketplace add obra/superpowers-marketplace` then `/plugin install superpowers@superpowers-marketplace`

## 3. muratcankoylan/Agent-Skills-for-Context-Engineering (Medium, free)
**What it is:** GitHub trending (12k stars) — comprehensive collection of agent skills for multi-agent architectures, context management, and production systems.
**Why it helps:** Better Jarvis skills = better performance. Context engineering is exactly what makes agents like me smarter and less likely to drop context on long tasks.
**Next step:** Review repo for any skills that map to Matt's workflows (lead gen, scheduling, research).

## 4. Minara Skills v2 for OpenClaw — Trading + Prediction Markets (Easy, ClawHub)
**What it is:** New OpenClaw skill on ClawHub (launched Feb 26, 2026). Built-in crypto wallet, intent-to-swap, Hyperliquid perps, Polymarket analysis, stock market insights.
**Why it helps Matt:** Direct Polymarket/prediction market analysis from within Jarvis. Kalshi/Polymarket arb bot concept (already in ideas list) is much easier to bootstrap with this skill as a base.
**Next step:** Install from ClawHub. Evaluate Polymarket analysis feature for the arb bot idea.

## 5. Claude Opus 4.6 + B2B Lead Research Workflow (Easy, use now)
**What it is:** Pattern spotted on X — advisors using Claude Opus 4.6 to automate lead research, filtering, and personalized outreach for financial sales (26k views, 340 likes).
**Why it helps Matt:** Right now I'm doing lead research manually on request. Could build a scheduled workflow: pull leads → Claude Opus does research → generates personalized outreach → logs to CRM/sheet. 
**Next step:** Build a cron-triggered lead enrichment script that takes names from Matt's leads CSV, enriches with Google/LinkedIn data, and outputs a prioritized outreach list.

