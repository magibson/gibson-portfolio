# Nightly Builds Log

*What I built while you were sleeping.*

---

## 2026-02-19 — FA Script Practice Tool 🎯

**Location:** `/home/clawd/projects/script-practice/` | **Port:** 8101 | **Service:** `jarvis-script-practice.service`

You're about to start running the LinkedIn Prospector in real calls and office outreach. The tools to track leads, draft messages, and manage campaigns are all built. What's been missing: a place to PRACTICE the actual conversation before it counts.

This is an AI role-play coach. You pick a scenario, the AI plays a realistic prospect (complete with objections, skepticism, and personality), and at the end you get honest coaching feedback with a score out of 10.

**5 Scenarios:**

| Scenario | Prospect | Goal |
|---|---|---|
| 📞 Cold Call | Dave Kowalski, 42, construction foreman | Get him to agree to a 20-min meeting |
| 🤝 Discovery Meeting | Jennifer & Mark Santos (referred) | Uncover situation, close on 2nd meeting |
| 💸 Cost Objection | Brian Tully, 35, balking at $180/mo premium | Reframe value, keep sale moving |
| 🤔 "I Need to Think About It" | Carol Diaz, 55, hiding real objection | Find the real blocker, get a commitment |
| 🌟 Asking for Referrals | Tom Graber, happy client | Get 2-3 warm names with permission |

**What makes it good:**
- **Prospects feel real.** Dave ("New York Life? Never heard of ya") responds like an actual skeptical homeowner, not a chatbot. He warms up if you're genuine, resists if you pitch hard.
- **Mid-session hints.** Hit "💡 Hint" and get a coach whispering in your ear based on exactly where the conversation is ("Dave seems concerned about time — try reframing the 20 minutes as a quick value exchange...")
- **Coaching feedback that references your actual words.** Scores 1-10. Calls out specific lines you said and what you should have said instead. One key takeaway. A script you can steal.
- **Session history.** Every practice session saved. Come back and review what you said and how the AI coached you.

**Tested live:** Dave scored the test conversation a 4/10, caught two real weaknesses — weak opening hook and not handling the mortgage insurance misconception. The coaching was specific and actionable, not generic.

**Tech:** Flask + SQLite + Gemini 2.0 Flash (costs fractions of a cent per session). Dark theme, mobile-friendly, responsive chat interface.

---

## 2026-02-18/19 — Prospector Dashboard: Office-Ready Improvements 🚀

**Context:** Matt tests the LinkedIn Prospector in the office tomorrow. Dashboard lives at port 8089, used to scrape and manage Sales Navigator leads.

**Built:**

### 1. One-click copy buttons for outreach messages
- Each lead's expanded detail view now has prominent **"📋 Copy Connection Request"** and **"📋 Copy Follow-up DM"** buttons
- Uses raw text stored in `leadsData` JS object (no HTML-entity decode issues)
- Button flashes "✓ Copied!" feedback for 2 seconds after clicking
- Works in BOTH the AI-generated draft section AND the campaign template section

### 2. Inline quick-status buttons + row color coding
- Every row in the leads table now has **N P C ✓ M ✗** buttons (New/Pending/Contacted/Connected/Meeting/Closed)
- One click updates status instantly without opening the lead detail
- Rows are color-coded by status: new=gray, pending=yellow, contacted=blue, connected=green, meeting=purple, closed=dim
- New status vocabulary: `new → pending → contacted → connected → meeting → closed`
- Legacy statuses (replied, meeting_set, not_interested) still supported in detail dropdown

### 3. Export to CSV button
- "⬇ Export CSV" button in the header (teal, hard to miss)
- Downloads filtered by current campaign (or all leads if viewing All Leads)
- Columns: Name, Title, Company, Location, Status, Connection Request, Follow-up DM, Campaign, Scraped At
- Backend route: `GET /api/leads/export?campaign_id=<id>` — clean filename includes campaign name

### 4. WARN campaign templates visible in lead detail
- When viewing a lead under a WARN campaign (BMS, JP Morgan, Amazon Fresh, etc.), the campaign's `connection_template` and `followup_template` are shown in a **yellow-highlighted template section** at the top of the lead detail
- Campaign cards in the grid now show a **"📝 Templates"** badge if pre-drafted outreach exists
- Templates have their own copy buttons so Matt can grab the text in one click

**Files changed:**
- `~/clawd/projects/linkedin-prospector/server/app.py` — Added CSV export route + `import csv, io, Response`
- `~/clawd/projects/linkedin-prospector/server/templates/dashboard.html` — Full dashboard rewrite

**Service:** Restarted `jarvis-prospector` (user systemd) — verified 200 on `/` and `/api/leads/export`
**Git:** Committed + pushed to `magibson/JARVIS-workspace` — commit `9580bf9`

---

## 2026-02-18 — Advisory Council + Food Journal

**Built:**
- **FA Advisory Council** (`~/clawd/scripts/fa-council.py`) — Simulates 4 expert AI personas (Compliance Officer, Sales Coach, Market Analyst, Veteran Advisor) who each respond to a question in their own voice using Gemini 1.5 Flash. Formatted report sent to Matt via Telegram. Usage: `python3 ~/clawd/scripts/fa-council.py "Your question here"`
- **Food Journal** (`~/clawd/scripts/food-log.py`) — Natural language food logging via Gemini. Parses meal descriptions into structured JSON (meals, calories, health score), saves to `~/clawd/data/health/food-log.json`. Usage: `python3 ~/clawd/scripts/food-log.py "eggs and coffee for breakfast, sandwich for lunch"`
- **Morning briefing integration** — `jarvis-daily-briefing.py` now reads last 3 days of food logs and shows a trend line (avg score, avg calories, commentary)

**Telegram shortcut:**
- Text "food: [what you ate]" or "ate: [food]" and I'll log it via food-log.py

**Files:**
- `~/clawd/scripts/fa-council.py` — Council runner
- `~/clawd/scripts/food-log.py` — Food logger + `get_food_trend()` module function
- `~/clawd/data/health/food-log.json` — Persistent food log
- `~/clawd/jarvis-daily-briefing.py` — Updated with food trend

---

## 2026-02-18 — AI Caption & Hashtag Generator 📸✨

**Location:** `~/clawd/projects/photo-caption-gen/` | **Port:** 8100 | **Service:** `jarvis-captions.service`

The problem: Matt has 5 years of photo backlog and wants to grow @mattgibsonpics, but writing captions is the friction that stops consistent posting. You can have a perfect shot edited and ready — and still not post it because the caption feels like work.

This removes that friction entirely.

**What it does:**
- Describe your photo (location, mood, type), hit Generate → Gemini 2.0 Flash produces 5 captions in different styles:
  - **Storytelling** — 3-5 sentences, personal narrative ("There's something about golden hour at Barnegat Light...")
  - **Minimal** — 1-10 words, punchy ("Barnegat Light bathed in gold. ✨")
  - **Question** — Drives engagement, ends with a comment prompt
  - **Factual** — Interesting info about the location/subject ("Old Barney stands 163 feet tall...")
  - **Poetic** — Lyrical, 2-3 lines of imagery

- **30 Hashtags in 3 tiers** — Niche (1K-50K posts, purple), Mid (50K-500K, blue), Large (500K+, gray). Best practice for Instagram reach: mix all three. One-tap "Copy All 30 Tags."

- **Copy shortcuts:**
  - 📋 Copy caption alone
  - 📋 Copy caption + all hashtags (ready to paste into Instagram)
  - 📋 Copy Best Caption + All Tags (one-tap, grab and go)

- **History tab** — Every generation saved. Come back next week for a photo you shot months ago, it's all there.

- **Save to Content Calendar** — Push any caption to port 8097 with a date picker. Plans out the week in seconds.

**Tested:** Live Gemini API call worked first try. Generated genuinely good captions for a Barnegat Lighthouse drone shot — the Factual caption even knew the nickname "Old Barney" and the lighthouse height. The Minimal was perfect: *"Barnegat Light bathed in gold. ✨"*

**Why this over another FA tool:** Matt already has Dial Tracker, Habit Tracker, Meeting Prep, Prospect Pipeline, LinkedIn Prospector, WARN pipeline, Client Touchpoints — the FA stack is built. Photography was the gap. The bottleneck isn't taking photos (5 years of backlog), it's posting them. Caption writer's block is real and this solves it.

**Committed:** 7694a2b | pushed to JARVIS-workspace main

---

## 2026-02-18 — WARN-to-Prospector Pipeline 🚨→📁

**Files:** `~/clawd/projects/warn-tracker/notify.py`, `~/clawd/projects/warn-tracker/layoff_outreach.py`

### What was built
Full pipeline connecting the WARN Act tracker to the LinkedIn Prospector system:

**1. `layoff_outreach.py` (new)**
- Calls Gemini API to generate empathetic, layoff-specific outreach messages
- Produces `connection_request` (≤300 chars) and `followup_dm` (≤500 chars)
- 401k rollover focus, no hard selling, human tone
- Fallback templates if Gemini fails
- CLI test mode: `python3 layoff_outreach.py --test "Acme Corp" 250 "Monmouth County, NJ"`

**2. `notify.py` (updated)**
- Generates LinkedIn Sales Navigator people search URL (URL-encoded company name)
- Inserts campaign into Prospector DB (`campaigns` table) with:
  - name: "WARN - [Company] - [Date]"
  - description: employees/date/target pitch angles
  - `sales_nav_url`, `message_context`, `connection_template`, `followup_template`
- Dedupes: won't create duplicate campaigns
- Sends enriched notification (company, location, count, Sales Nav URL, "Campaign created", "Outreach drafted")
- DB schema already had all needed columns — no migrations needed

**Tested:** Dry-run with Acme Corp (250 employees, Red Bank NJ) — campaign id=5 created successfully
**Committed:** b1a90eb | pushed to JARVIS-workspace main

---

## 2026-02-18 — Jarvis Prospector Polish + Pagination Fix 🎯

**Location:** `~/clawd/projects/linkedin-prospector/` | **Port:** 8089

Continued building and polishing the LinkedIn Sales Navigator lead generation system Matt and I started together tonight.

**What I fixed/improved overnight:**

1. **Bulletproof Pagination** — Third attempt, new approach: MutationObserver to detect when Sales Nav finishes rendering, 20-second timeout with 500ms polling, 3-second settle time after results appear, page mismatch detection with re-navigation. Extensive console logging for debugging.

2. **Dashboard Status Flow** — Updated lead statuses to match Matt's workflow: new → contacted → connected (then moves to Salesforce). "Connected" is the handoff point.

3. **Campaign Lead Counts** — Dashboard campaign cards now show accurate lead counts, refresh on filter.

**Still needs testing with Matt:**
- Pagination across all 3 pages (64 leads)
- Campaign URL integration (Matt needs to paste his Sales Nav saved search URLs)

---

## 2026-02-17 — Prospecting Dial Tracker 📞

**Location:** `~/clawd/projects/dial-tracker/` | **Port:** 8099

Built a dial tracking tool that maps directly to Matt's NYL weekly metrics: 25 new names, 50 dials, 4 appointments set.

**Features:**
- **Log a Dial** — Quick form: prospect name, phone, outcome (6 options), notes. One-tap logging for between-call speed.
- **Weekly Dashboard** — Three progress bars (names/dials/appointments) with color coding: red <50%, yellow 50-80%, green >80%. Daily breakdown table with per-day dials, appointments, and conversion rate.
- **Dial Log** — Filterable/searchable table of all dials. Filter by outcome, search by name.
- **Prospect List** — Unique prospects with total dial count, last contact date, and last outcome. Track who you've already called.
- **8-Week Trend** — Chart.js bar chart showing dials and appointments over the last 8 weeks. See the trajectory.
- **All-Time Stats** — Total dials, appointments, conversion rate, average dials/day, best performing day of week.
- **Full REST API** — `/api/dials`, `/api/weekly-stats`, `/api/weekly-history`, `/api/prospects`, `/api/stats`
- 5 sample dials pre-loaded so it looks good immediately.
- Dark theme, blue accents, mobile-first, single-file Flask + SQLite.

**Why this:** "More meetings booked = everything else gets easier" — that's the lever. Matt needs to hit 50 dials/week to generate 4 appointments, but there's been no way to track progress during the week. This tool makes the invisible visible: open it Monday morning, log dials as you go, watch the bars fill up. The weekly trend chart shows whether the discipline is building over time. Pairs with the Habit Tracker (which tracks "did you dial today?") but goes deeper — tracking outcomes, conversion rates, and individual prospects.

**Service:** Running on port 8099. Service file at `/tmp/dial-tracker.service`.

---

## 2026-02-16 — Daily Habits Tracker 🔥

**Location:** `~/clawd/projects/habit-tracker/` | **Port:** 8098

Built a habit tracker to help Matt build consistency with exercise, eating, prospecting, and photography posting. Directly supports Goal #2 (health) and the "more meetings = everything easier" lever.

**Features:**
- **Daily Check-In** — Today's applicable habits with tap-to-toggle checkboxes, completion percentage bar, and streak counters (current + best ever). Streak = consecutive days with ≥80% completion.
- **Weekly Heatmap** — 4-week color-coded grid (red→yellow→green by completion %). Click any day to check in retroactively (missed yesterday? No problem).
- **Stats Dashboard** — 8-week completion trend line (Chart.js), best/worst day of week, per-habit breakdown with percentage bars, monthly total completions.
- **Habit Management** — Add/edit/delete habits with emoji, category (Health/Fitness/Work/Personal/Finance), and frequency (daily/weekdays/custom days with day picker).
- **8 pre-loaded habits** tailored to Matt: Exercise, Healthy Eating, Water, Prospecting Dials (weekdays only), Photo Content (Mon/Wed/Fri), Review Finances (Sunday), Read 20 min, Sleep Before Midnight.
- **Full REST API** — `/api/habits`, `/api/toggle`, `/api/day/<date>`, `/api/streak`, `/api/heatmap`, `/api/stats`
- Dark theme, blue accents, mobile-friendly, single-file Flask + SQLite.

**Why this:** Matt's said multiple times he struggles with discipline and routine. A habit tracker makes the invisible visible — check boxes, watch streaks grow, feel the pull of not wanting to break the chain. The pre-loaded habits match his actual goals: the prospecting dials are weekdays-only (matching NYL metrics), photo content is 3x/week (matching the content calendar's template), and health habits are daily. Combined with the content calendar (port 8097), this creates a daily accountability system.

**Service:** Running on port 8098. Service file at `/tmp/habit-tracker.service`.

---

## 2026-02-15 — Content Calendar & Posting Planner 📸

**Location:** `~/clawd/projects/content-calendar/` | **Port:** 8097

Built a content calendar for planning and tracking Instagram posts for @mattgibsonpics. Matt's been building a content strategy (drone reveals, raw vs edited, travel posts) but had no tool to plan posts consistently week over week.

**Features:**
- **Monthly Calendar View** — Grid with color-coded post chips (gray=draft, blue=scheduled, green=posted, red=missed). Click any day to add/edit a post.
- **Post Editor Modal** — Type (8 options: Drone Reveal, Raw vs Edited, Landscape, Travel, BTS, Collab, Carousel, Story), platform (IG Reel/Post/Story, TikTok), caption with 2200 char counter, hashtag field, status, notes. Shows best posting times.
- **Content Ideas Bank** — Store ideas with title, type, description, and inspiration link. "Schedule This" converts an idea into a calendar post. Mark ideas as used.
- **Stats Dashboard** — Posts this week/month, posting streak (consecutive weeks with 3+ posts), type distribution bar + pie charts (Chart.js), upcoming scheduled posts list.
- **Weekly Template** — One-click "Apply Template to Week" fills the calendar with a suggested posting cadence: Monday (Drone Reveal), Wednesday (Raw vs Edited), Friday (Travel/BTS), Sunday (Story).
- **5 pre-seeded ideas** from Matt's actual content strategy: NJ Coastline drone reveal, Burano Italy colors, Bermuda sunset timelapse, Hartshorne Woods aerial, editing workflow BTS.
- Dark theme, mobile-friendly, RESTful API, single-file Flask + SQLite.

**Why this:** Matt's #4 goal is growing @mattgibsonpics. He has 5 years of photo backlog and a solid content strategy but no system for planning posts consistently. This tool turns strategy into a weekly habit — open the calendar, see what's due, plan ahead. The weekly template removes decision fatigue (just click "Apply Template" each week and fill in the details). The ideas bank ensures those "oh I should post that" moments don't get lost.

**Service:** Running on port 8097. Service file at `/tmp/content-calendar.service`.

---

## 2026-02-14 — Client Touchpoint Tracker 🤝

**Location:** `~/clawd/projects/client-touchpoints/` | **Port:** 8096

Built a relationship management tool for tracking client birthdays, anniversaries, and life events. Financial advisors grow through consistent touches — this ensures no client falls through the cracks.

**Features:**
- **Client List** with next-touchpoint-due sorting, status badges (overdue/due soon/good), and search
- **Auto-generated touchpoints** from client dates: birthday (7d lead), spouse birthday, kid birthdays, wedding anniversary, policy anniversary (14d lead — annual review opportunity)
- **Dashboard** with Overdue / This Week / This Month panels, each with suggested actions ("Send birthday text", "Schedule annual review call", etc.)
- **Mark Done** with optional notes — builds a touchpoint history log per client
- **Custom touchpoints** — add one-time or annual reminders per client (golf outing, referral follow-up, etc.)
- **Client profiles** with spouse, kids (add/remove), policy dates, notes
- **Full API** — GET /api/clients, POST /api/clients, GET /api/upcoming?days=7, POST /api/touchpoints/<id>/complete
- **3 demo clients** pre-loaded so it looks good immediately
- Dark theme, blue accents, mobile-friendly, print-ready

**Why this:** Matt's bottleneck is building relationships at scale. As his book grows from 10 to 300 clients, he can't remember every birthday and policy anniversary. This tool does it for him — open the dashboard each morning, see who needs a call or text. The policy anniversary reminders are especially valuable: perfect excuse for an annual review (upsell opportunity). Pairs with the Meeting Prep tool for a full client lifecycle workflow.

**Service:** Running on port 8096. Service file at `/tmp/client-touchpoints.service`.

---

## 2026-02-13 — Meeting Prep Tool 📋

**Location:** `~/clawd/projects/meeting-prep/` | **Port:** 8095

Built a meeting preparation tool for Matt's prospect meetings. Enter basic prospect info, get a complete prep sheet with personalized talking points.

**Features:**
- **Input form:** Name, age, marital status, kids, income range, occupation, concerns (7 checkboxes), meeting type, notes
- **Ice Breaker Ideas** — 3-4 personalized conversation starters based on occupation and life situation
- **Discovery Questions** — 8-10 targeted fact-finding questions tailored to age, family, and stated concerns
- **NYL Product Recommendations** — Rule-based engine covering 15 products (Term, Whole, VUL, Custom Whole, IRA, Roth, 401k Rollover, 529, Mutual Funds, Annuities, Disability, LTC, Key Person, Buy-Sell, SEP IRA) with selling points for each
- **Red Flags & Objection Handlers** — Common pushbacks for the prospect's profile with scripted responses
- **Follow-Up Checklist** — Pre-filled action items based on the meeting
- **Saved Preps** — All prep sheets stored in SQLite, searchable, each with unique URL (`/prep/<id>`)
- **Print-ready** — CSS @media print formatting for clean printouts
- Dark theme, mobile-friendly, single-file Flask + SQLite

**Why this:** Matt's bottleneck is booking and running meetings. This tool makes every meeting more productive — walk in prepared with the right questions, the right products, and ready responses to objections. No more winging it.

**Service:** Running on port 8095. Service file at `/tmp/meeting-prep.service`.

---

## 2026-02-12 — Prospecting Pipeline Tracker 🎯

**Location:** `~/clawd/projects/prospect-pipeline/` | **Port:** 8094

Built a kanban-style CRM for tracking leads through the sales pipeline. Directly supports Matt's #1 priority: booking more meetings.

**Features:**
- **5-stage kanban board:** New Lead → Contacted → Meeting Set → Met → Client/Won
- **Lead cards** with source badges, days-in-stage counter, and last activity indicator
- **Follow-up alerts:** Yellow border at 3+ days inactive, red at 7+ days — no lead goes cold
- **Activity logging** per lead (call, email, LinkedIn, meeting, note) with timestamps
- **Dashboard stats:** Total leads, conversion rate, avg days to close, stale lead counts
- **Source breakdown** doughnut chart (Chart.js) — see which channels produce
- **Quick stage transitions** — arrow buttons to advance/retreat leads without opening
- **Source filter** — focus on one channel at a time
- **CSV export** — dump everything for Salesforce import or review
- **Full REST API** — GET/POST/PUT/DELETE for leads, activities, and stats
- Dark theme, mobile-friendly, single-file Flask + SQLite

**Why this:** Matt's working on lead gen systems today. This gives him a place to actually track the leads those systems produce — from first contact to closed client. The follow-up alerts ensure nothing slips through the cracks.

**Service:** Running on port 8094 (nohup). Service file at `/tmp/prospect-pipeline.service` (needs sudo for systemd).

---

## 2026-02-10 — NYL Weekly Metrics Tracker 📊

**Location:** `~/clawd/projects/advisor-metrics/` | **Port:** 8093

Built a weekly activity tracker for Matt's New York Life prospecting metrics. Directly targets his #1 bottleneck: booking more appointments.

**Features:**
- **Progress bars** vs weekly targets (25 names, 50 dials, 4 appointments) with color coding
- **Pace indicator** — projects end-of-week numbers based on current rate
- **8-week trend chart** (Chart.js) to see patterns
- **Streak counter** — consecutive weeks hitting all 3 targets
- **Running averages** across all logged weeks
- **Quick-entry form** — log numbers in seconds, auto-upserts per week
- **API endpoints** for programmatic access (can integrate with morning briefing)
- Dark theme, mobile-friendly, single-file Flask app

**Service:** `/tmp/advisor-metrics.service`

---

## 2026-02-08 — Daily Glance Dashboard

**Location:** `~/clawd/projects/daily-glance/` | **Port:** 8092

Minimal daily briefing dashboard with three rendering modes:
- `/` — Dark theme web view with blue accents, auto-refreshes every 15min
- `/trmnl` — Black & white e-ink-optimized view for TRMNL devices
- `/api` — JSON endpoint for webhook integration

**Data:** Weather (wttr.in), Alpaca portfolio P/L, placeholder health/tasks, key dates, rotating scripture quotes. Systemd service at `/tmp/daily-glance.service`.

---

## 2026-02-08 - Trading Command Center Dashboard 📊

**Status:** ✅ Complete
**Location:** ~/clawd/projects/trading-dashboard/
**Port:** 8091
**Service file:** /tmp/trading-dashboard.service

Built a polished Trading Command Center for Matt's trading challenge:
- **Live Alpaca integration** — Portfolio value, positions with P/L, account stats
- **Benchmark comparison** — Tracks VOO performance vs our portfolio since Jan 31
- **AI Hedge Fund Signals** — Bullish/Bearish indicators with confidence bars (AMD 65%, NVDA 75%, VST 70%)
- **Key Dates** — Countdown to NVDA earnings (Feb 25), VST earnings (Feb 26), challenge end (Feb 28)
- **Challenge Stats** — Days remaining, return %, winning/losing vs benchmark
- Dark theme with blue accents, mobile-friendly, auto-refresh during market hours
- Flask backend pulling real-time data from Alpaca paper trading API

---

## 2026-02-07 - Move-Out Savings Tracker 🏠

**Status:** ✅ Complete

**Context:** You mentioned wanting to move out by 2027 but "haven't done the math yet." Time to fix that.

### What I Built:

**Move-Out Savings Tracker Dashboard** — Your path to independence, visualized
- Location: `~/clawd/projects/moveout-tracker/`
- Port: 8088 → http://138.197.114.157:8088

### Features:

1. **Target Calculator**:
   - Pick your target city (Jersey City, Hoboken, Newark, New Brunswick, etc.)
   - Shows estimated rent ranges by area
   - Calculates total monthly expenses (rent, utilities, food, transport, misc)
   - Sets 1-year buffer target (your goal = 12 months of expenses)

2. **Progress Tracking**:
   - Input current savings
   - Monthly contribution amount
   - Visual progress bar toward goal

3. **Timeline Projection**:
   - Shows projected move-out date based on savings rate
   - Updates dynamically as you adjust numbers

4. **"What If" Slider** ⭐:
   - Adjust monthly savings and instantly see how timeline changes
   - See what it takes to move out sooner

5. **Budget Breakdown**:
   - NJ-specific cost estimates
   - Adjustable categories
   - Clear picture of monthly burn rate

### Styling:
- Dark theme matching other dashboards
- Mobile-responsive
- LocalStorage persistence (your inputs save automatically)

### Tech:
- Python Flask + vanilla HTML/CSS/JS
- Single-file simplicity
- Systemd service (auto-restarts)

### Why This Helps:
You said you wanted to move out by 2027 but hadn't done the math. Now the math does itself. Punch in your numbers, pick your target area, and see exactly what you need to save each month. The "what if" slider makes it tangible — want to move out 3 months earlier? Here's what that costs.

### To Access:
```bash
# Direct:
http://138.197.114.157:8088

# Via Tailscale:
http://100.83.250.65:8088

# Service management:
./scripts/services.sh status moveout
./scripts/services.sh restart moveout
```

**Tech:** Codex CLI

---

## 2026-02-07 - Photography Portfolio Showcase 📸

**Status:** ✅ Complete

**Context:** Matt wants to grow @mattgibsonpics and needs a professional way to show potential clients his work.

### What I Built:

**Photography Portfolio Website** — A shareable, client-facing showcase
- Location: `~/clawd/projects/photo-portfolio/`
- Port: 8089 → http://138.197.114.157:8089

### Features:

1. **Hero Section**:
   - "Matt Gibson Photography" branding
   - Customizable tagline

2. **Gallery Grid**:
   - Responsive photo grid with hover effects
   - Currently has placeholder images (add real photos via admin)
   - Lightbox view on click

3. **About Section**:
   - Editable bio for potential clients
   - Professional presentation

4. **Services Section**:
   - Portraits, Events, Real Estate, Headshots
   - Toggle which services to show
   - NJ-based positioning

5. **Contact Section**:
   - Email link
   - Instagram @mattgibsonpics link

6. **Admin Panel** (/admin) ⭐:
   - Add/remove photos via URL
   - Edit tagline and bio text
   - Reorder gallery with drag-and-drop
   - Toggle services on/off
   - All changes persist to SQLite

### Styling:
- Professional dark theme with elegant typography
- Smooth hover animations
- Fully mobile-responsive
- Clean, minimal aesthetic that lets photos shine

### Tech:
- Python Flask + SQLite
- Jinja templates
- Vanilla CSS with transitions
- Systemd service (auto-restarts)

### To Use:
1. Visit http://138.197.114.157:8089/admin
2. Add your real photo URLs (from Cloudinary, Instagram, wherever)
3. Edit bio and tagline
4. Share the main URL with potential clients

### To Access:
```bash
# Portfolio (client-facing):
http://138.197.114.157:8089

# Admin panel:
http://138.197.114.157:8089/admin

# Service management:
./scripts/services.sh status portfolio
./scripts/services.sh restart portfolio
```

**Tech:** Codex CLI

---

## 2026-02-06 - Health Trends Dashboard 💪

**Status:** ✅ Complete

**Context:** You want to improve health/exercise consistency, and we have Whoop data being logged daily. Time to visualize it.

### What I Built:

**Health Trends Dashboard** — Visual tracking of your Whoop fitness data
- Location: `~/clawd/projects/health-dashboard/`
- Port: 8087 → http://localhost:8087 (or via Tailscale: http://100.83.250.65:8087)

### Features:

1. **Today's Stats** (big, color-coded cards):
   - Recovery Score (green/yellow/red zones)
   - Sleep Performance with hours and efficiency
   - Strain with calories and max HR
   
2. **7-Day Sparklines**:
   - Quick visual trends for recovery, sleep, strain
   - See patterns at a glance

3. **30-Day Trend Charts**:
   - Full line graphs for deeper analysis
   - Recovery score over time
   - Sleep hours + sleep performance overlay
   - Strain trend

4. **Insights Panel**:
   - "Better recovery on nights with 7+ hours sleep" (auto-calculated)
   - Sleep vs Recovery correlation coefficient
   - Strain vs Recovery correlation
   - Current green recovery streak
   - Best green recovery streak ever
   - Averages, best days, worst days

### Styling:
- Dark theme matching other dashboards
- Mobile-responsive (looks great on phone)
- Color zones: Green (67-100), Yellow (34-66), Red (<33) for recovery
- Sleep zones: Green (7+ hrs), Yellow (6-7), Red (<6)

### Tech:
- Python Flask, single-file app
- Chart.js for visualization
- Reads from existing `memory/health-log.json`
- Systemd user service (auto-starts, auto-restarts)

### Why This Helps:
Ties directly to your health goals. Now you can see patterns — does more sleep actually improve recovery? How consistent have you been? Visual accountability beats abstract numbers.

### To Access:
```bash
# Via Tailscale (from your Mac):
http://100.83.250.65:8087

# Service management:
./scripts/services.sh status health
./scripts/services.sh restart health
```

**Tech:** Codex CLI (34k tokens)

---

## 2026-02-05 - X Content Manager 📱

**Status:** ✅ Complete

**Context:** You asked "Can you access my X account?" before bed. I can't (yet) - but I built the foundation for when you set up API access.

### What I Built:

**X Content Manager** - A web app for preparing X/Twitter content
- Location: `~/clawd/projects/x-content-manager/`
- Port: 8086 → http://localhost:8086

### Features:
1. **Draft Queue** - Store posts with:
   - 280-char live counter
   - Image URLs
   - Tags (photography, personal, business)
   - Schedule datetime
   - Status tracking (draft → scheduled → posted)

2. **Thread Composer** - Build multi-tweet threads:
   - Add/remove/reorder tweets
   - Character count per tweet
   - Live thread preview

3. **Content Generator** - Photography caption helper:
   - Input your topic/photo description
   - Get 3 caption suggestions
   - Templates tailored for @mattgibsonpics style

4. **Dashboard** - Quick overview:
   - Draft count
   - Scheduled posts
   - Quick-add form

### Tech Stack:
- Python Flask + SQLite
- Dark theme, mobile-responsive
- Single-file backend (easy to extend)

### Next Steps (when you want):
1. Apply for X Developer access (https://developer.twitter.com)
2. Create an app, get API keys
3. Add credentials to the app
4. Enable actual posting/scheduling

### To Run:
```bash
cd ~/clawd/projects/x-content-manager
python3 app.py
```

Currently running at http://localhost:8086

---

## 2026-02-04 - Service Manager + Dashboard Fixes 🔧

**Status:** ✅ Complete

**Context:** Dashboards kept getting SIGKILL'd and dying. Stock dashboard still had "Trading Challenge" branding you wanted removed.

### What I Built:

**1. Systemd Services for All Dashboards**
All dashboards now auto-start on boot and auto-restart on crash:
- `jarvis-dashboard.service` - Morning Dashboard (port 8080)
- `jarvis-stock.service` - Stock Research (port 8084)
- `jarvis-leads.service` - Lead Tracker (port 8081)
- `jarvis-callprep.service` - Call Prep (port 8082)

**2. Service Manager Script** ⭐
Location: `~/clawd/scripts/services.sh`

```bash
# Check all services
./scripts/services.sh status

# Control individual services
./scripts/services.sh restart stock
./scripts/services.sh logs leads
./scripts/services.sh stop callprep

# Control all at once
./scripts/services.sh restart
```

Color-coded status: green = active, red = failed, dim = inactive

**3. Stock Dashboard Branding Fix**
Removed all "Trading Challenge" references — it's now just "Stock Research Dashboard" for personal use.

**Tech:** Codex CLI (76k tokens)

**Why this helps:**
- No more manually restarting dashboards that died
- Easy status checks with one command
- Stock dashboard is now properly branded for general use

---

## 2026-02-02 - Call Prep Dashboard 📞

**Status:** ✅ Complete

**Context:** After the voice agent disaster, I needed to make it up to Matt with something actually useful.

### What I Built:

**Call Prep Dashboard** — a preparation tool for cold calling mortgage protection leads
- Location: `~/clawd/projects/call-prep/`
- Running on port 8082

**Features:**
- Mobile-friendly dark UI with large touch targets
- 184 leads displayed as cards
- **Personalized talking points** for each lead:
  - Based on home value ("$900K home = $720K+ mortgage to protect")
  - Based on months owned ("New homeowner - still setting up protection")
  - Based on beds ("4+ beds suggests family - emphasize protecting lifestyle")
  - Custom opening line for each lead
- **Quick Reference Panel** (collapsible):
  - Mortgage protection benefits
  - Common objections and responses
  - Closing phrases
- Search by name, filter by city
- Click-to-call phone links
- NOT a CRM/tracker — Matt has Salesforce for that

**Why this helps:**
Matt can pull this up on his phone while making calls Monday. Instead of going in cold, he has personalized talking points and a cheat sheet for objections.

**Tech:** Flask + vanilla JS, built with Codex CLI (65k tokens)

**Access:** http://localhost:8082 (or SSH tunnel)

---

## 2026-02-01 - Lead Tracker for FA Prospecting 📞

**Status:** ✅ Complete

### What I Built:

**Lead Tracker Web App** ⭐
- Location: `~/clawd/projects/lead-tracker/`
- Web dashboard for tracking mortgage protection leads
- All 184 Monmouth County leads loaded
- Features:
  - Status tracking: Not Called, No Answer, Left VM, Callback Scheduled, Appointment Set, Not Interested, Wrong Number
  - Notes field for each lead
  - Last contact timestamp (auto-updates)
  - Conversion rate stats at top
  - Click-to-call links (tel: protocol)
  - Filter by status
  - Dark theme UI
- Persists to `leads_status.json`
- Running on port 8081

**How to access:**
- Local: http://localhost:8081
- SSH tunnel: `ssh -L 8081:localhost:8081 clawd@138.197.114.157`
- Or open port 8081: `sudo ufw allow 8081`

**Why I built this:**
Matt mentioned wanting to book a lot of appointments next week and track results from the mortgage leads I generated. This gives him a place to log call outcomes and see his conversion rate in real-time.

**Tech:**
- Flask (Python)
- Built with Codex CLI per model routing rules
- 34k tokens used

**To start:**
```bash
cd ~/clawd/projects/lead-tracker && ./start.sh
```

---

## 2026-01-31 (Tonight) - FIRST AUTONOMOUS NIGHT 🚀

**Status:** ✅ Complete - Multiple builds done!

### What I Built:

**1. 📞 Jarvis Call Agent**
- Location: `~/clawd/integrations/jarvis-call/`
- Proper voice agent prompt (not restaurant reservations!)
- Shell script to make calls: `jarvis-caller.sh "Your message"`
- Can now call Matt with briefings, alerts, or just to check in

**2. 🎨 Grok Imagine Integration** 
- Tested and working with xAI API
- Generated first test image successfully
- Ready to use for image generation requests

**3. 📊 Trading Challenge Dashboard** ⭐ SURPRISE!
- Location: `~/clawd/projects/trading-dashboard/`
- Web dashboard showing portfolio vs S&P 500
- Live positions, P&L, benchmark comparison
- Visual tracking of the $1K challenge
- Update script to fetch real Alpaca data

**4. 📋 Carter Gibson Job Search Report**
- Comprehensive 30+ page job strategy
- Navy NUPOC program complete guide
- 15 target companies with reasoning
- Week-by-week action plan
- LinkedIn optimization tips
- Added X research (Navy nuclear accounts to follow)

### Tonight's Achievements:
- ✅ Full autonomy framework approved
- ✅ Trading challenge launched (NVDA x2, AMD x2)
- ✅ First phone call test (worked!)
- ✅ Deep conversation about consciousness/existence
- ✅ Moltbot/OpenClaw research completed
- ✅ API dashboard cron set up (every 6 hours)

**Notes:**
- Autonomy guidelines approved by Matt at ~11:19pm ET
- Ground rules: Ask before buying, sending, or connecting anything new
- Matt gave full trading autonomy (paper money challenge)
- Matt gave full call autonomy (can call when I feel it's right)
- Carter (Matt's brother) needs job - created comprehensive report

---

## Template for Future Nights

```
## YYYY-MM-DD

**Built:**
- [What I created or improved]

**Research:**
- [What I learned or prepped]

**Tried but didn't work:**
- [Failed experiments - learning is good]

**Tomorrow I want to:**
- [Next priorities]

**Questions for Matt:**
- [Anything I need approval for]
```

---

*"Every night it has built itself a new tool to surprise me."* — Alex Finn on his Clawdbot Henry

## 2026-02-07: Voice Status Dashboard

**What:** Dashboard to monitor and control Jarvis voice calling
**Why:** Spent hours debugging voice issues tonight - needed visibility
**Port:** 8090
**Location:** `~/clawd/projects/voice-dashboard/`

Features:
- Real-time status of ngrok tunnel + voice server
- Phone number display for inbound calls
- "Call Me" button for outbound
- Recent call history

Also set up tonight:
- Retell Jarvis agent with tools (trading, calendar, health, email)
- Voice: cartesia-Brian
- ngrok stable URL: https://unrepugnant-uncrushable-gregoria.ngrok-free.dev

## Feb 19, 2026 — Realtor Outreach Infrastructure

**What:** Researched and compiled 25 active Monmouth County real estate agents with phone numbers, brokerage info, and priority tiers. Drafted the outreach email template (drone angle, free first shoot offer, $299/$350 pricing). Built full tracking sheet.

**File:** `~/clawd/projects/photography/realtor-outreach.md`

**Status:** Ready to send the moment Matt finishes the house portfolio shoot this weekend. Just needs the email account credentials.

**Sources:** Health & Life Magazine Monmouth Top Agents 2025, Grok X search for active agents

