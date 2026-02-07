# LinkedIn DIY Automation: Jarvis as Your LinkedIn Assistant

*Research completed: February 2026*
*Goal: Replace $179/mo SaaS tools (Sales Nav + Expandi) with Clawdbot/Jarvis-powered automation*

---

## Executive Summary

**YES, we can do this ourselves.** Here's what I found:

| Approach | Feasibility | Risk | Cost |
|----------|-------------|------|------|
| Browser Control (Chrome Relay) | ✅ High | Medium | $0 |
| Python API (linkedin-api) | ✅ High | Medium | $0 |
| OpenOutreach (Self-hosted) | ✅ High | Medium | $0 |
| Hybrid (I research, you execute) | ✅ Very High | Low | $0 |

**Bottom line:** We can build a system that rivals Expandi for ~$0/month using existing infrastructure + some Python scripts. The main investment is setup time.

---

## Part 1: Clawdbot Browser Control Capabilities

### What We Have Right Now
Clawdbot includes a **Browser Relay** feature that can control your existing Chrome browser:

```
Browser Status:
- Profile: "chrome" (your actual Chrome)
- Control URL: http://127.0.0.1:18791
- CDP Port: 18792
- Headless: false (visible browser)
```

### How It Works
1. You install the Clawdbot Browser Relay Chrome extension
2. Click the toolbar icon on any LinkedIn tab to "attach" it
3. I gain ability to:
   - Navigate to URLs
   - Click elements
   - Fill forms
   - Take snapshots
   - Read page content

### LinkedIn-Specific Capabilities
| Action | Possible? | Method |
|--------|-----------|--------|
| View profiles | ✅ Yes | Navigate + snapshot |
| Search people | ✅ Yes | Navigate to search, read results |
| Send connection requests | ✅ Yes | Click connect button, add note |
| Send messages | ✅ Yes | Navigate to messaging, type, send |
| Scroll feeds | ✅ Yes | Scroll actions |
| Like/comment posts | ✅ Yes | Click actions |
| Export search results | ✅ Yes | Snapshot + extract data |

### Anti-Detection Considerations
**Advantages of Chrome Relay approach:**
- Uses YOUR actual Chrome session (already logged in)
- Same cookies, fingerprint, history as real browsing
- Your real IP address
- No headless browser markers
- Indistinguishable from you using the browser manually

**What we'd need to implement:**
- Human-like delays (2-5 seconds between actions)
- Randomized timing
- Session limits (max 30-50 profiles/day)
- Activity pattern mimicking (no weekends, office hours only)

---

## Part 2: Open-Source LinkedIn Tools

### Option A: linkedin-api (Python)
**Best for:** Background data collection, no browser needed

```python
from linkedin_api import Linkedin

# Uses your credentials (or a secondary account)
api = Linkedin('email@example.com', 'password')

# What it can do:
profile = api.get_profile('target-username')
contacts = api.get_profile_contact_info('target-username')
connections = api.get_profile_connections('your-profile-id')
search = api.search_people(keywords='CEO fintech New York')
messages = api.get_conversations()
api.send_message(['urn:li:member:123456'], 'Hey!')
```

**Capabilities:**
- ✅ Search profiles
- ✅ Get profile data
- ✅ Get contact info
- ✅ Send messages
- ✅ Send connection requests
- ✅ Get/react to posts
- ⚠️ No official support (but actively maintained)

**Risk:** Uses LinkedIn's internal "Voyager" API. Works great but could break if LinkedIn changes things. ~900 requests before rate limiting kicks in.

**Install:** `pip install linkedin-api`

---

### Option B: OpenOutreach (Self-Hosted Expandi Alternative)
**Best for:** Full automation pipeline, closest to Expandi

GitHub: https://github.com/eracle/OpenOutreach

**What it is:** A complete, open-source LinkedIn automation tool that:
- Uses Playwright + stealth plugins
- Mimics human behavior
- Tracks profile states (DISCOVERED → ENRICHED → CONNECTED → COMPLETED)
- Supports AI-generated personalized messages
- Runs locally or in Docker

**Features:**
- Profile discovery and enrichment
- Auto connection requests with notes
- Follow-up message sequences
- Local SQLite database (your data, your control)
- Resumable workflows
- VNC visual debugging

**Setup:**
```bash
git clone https://github.com/eracle/OpenOutreach.git
cd OpenOutreach
pip install uv
uv pip install -r requirements/local.txt
playwright install --with-deps chromium
# Configure credentials in assets/accounts.secrets.yaml
python main.py
```

---

### Option C: open-linkedin-api (Community Fork)
**Best for:** If linkedin-api stops working

GitHub: https://github.com/EseToni/open-linkedin-api

Community-maintained fork of the original library. Same API, potentially more frequent updates.

```bash
pip install open-linkedin-api
```

---

## Part 3: Hybrid Approach (Recommended Starting Point)

### The "Jarvis Does Research, Matt Executes" Model

**Phase 1: Prospect Discovery (I do 100%)**
1. You give me target criteria: "CTOs at fintech startups, NYC, 10-50 employees"
2. I search via:
   - X/Twitter (using Grok integration)
   - Google search
   - Company databases
   - Crunchbase data
   - AngelList
3. I compile a list with:
   - Name, title, company
   - LinkedIn URL (found via Google search: "site:linkedin.com [name] [company]")
   - Recent posts/tweets (for personalization hooks)
   - Company funding stage, news
   - Recommended message angle

**Phase 2: Message Drafting (I do 100%)**
```
Target: Sarah Chen, CTO at Finflow
LinkedIn: linkedin.com/in/sarah-chen-finflow
Recent: Tweeted about AI in payments (Jan 28)
Company: Just raised Series A

Draft message:
"Hi Sarah - saw your thread on AI agents in payment 
infrastructure. Resonated with me since I've been building 
in that space. Would love to connect and compare notes 
on what's working."
```

**Phase 3: Execution (You or Me)**
- **Manual:** You review my list, copy messages, send yourself
- **Semi-auto:** I use browser relay to navigate, you click send
- **Full auto:** I handle everything via browser relay (higher risk)

---

## Part 4: Technical Feasibility Assessment

### Can Clawdbot's Browser Tool Handle LinkedIn's Anti-Bot?

**Short answer:** Yes, IF we're careful.

| Detection Vector | Browser Relay Status | Mitigation |
|-----------------|---------------------|------------|
| Headless browser markers | ✅ Not applicable | We use real Chrome |
| WebRTC leak | ✅ Not applicable | Real browser |
| Canvas fingerprint | ✅ Matches your real FP | - |
| Mouse movements | ⚠️ Needs work | Add human-like curves |
| Timing patterns | ⚠️ Needs work | Random delays |
| Request rate | ⚠️ Critical | Strict daily limits |
| IP address | ✅ Your real IP | - |
| Session tokens | ✅ Your real session | - |

### Safe Operating Limits
Based on research, here are the "don't get banned" numbers:

| Action | Daily Limit | Weekly Limit |
|--------|-------------|--------------|
| Profile views | 50-80 | 300-400 |
| Connection requests | 15-20 | 100 max |
| Messages (1st degree) | 50-100 | No hard limit |
| InMails | 10-15 | 50 |
| Searches | 100-150 | Commercial limit applies |

**Critical rules:**
1. Warm up new automation gradually (start at 5/day, increase by 2/day)
2. No activity on weekends
3. Office hours only (9am-6pm)
4. Clear pending connection requests older than 3 weeks
5. Keep acceptance rate above 50%

### Risk Comparison: DIY vs. Expandi

| Factor | DIY (Jarvis) | Expandi |
|--------|--------------|---------|
| Detection risk | Medium | Medium-Low |
| Account ban recovery | You handle appeals | They handle appeals |
| Data ownership | 100% yours | On their servers |
| Cost | $0 | $99/mo |
| Customization | Unlimited | Limited templates |
| AI integration | Native (I am AI) | Extra cost |
| Setup effort | Medium | Low |
| LinkedIn ToS compliance | Neither | Neither |

---

## Part 5: Cost Comparison

### Current Proposed Stack: Sales Nav + Expandi
| Service | Monthly Cost |
|---------|--------------|
| LinkedIn Sales Navigator | $80/mo |
| Expandi | $99/mo |
| **Total** | **$179/mo** |

### DIY Stack Cost
| Service | Monthly Cost |
|---------|--------------|
| Clawdbot | Already have |
| DigitalOcean VPS | Already have ($4-6/mo) |
| linkedin-api | Free |
| OpenOutreach | Free |
| Proxy (optional, for safety) | $0-30/mo |
| Burner LinkedIn account (optional) | $0 (just make one) |
| **Total** | **$0-36/mo** |

**Savings: $143-179/month = $1,716-2,148/year**

### Do You Even Need Sales Navigator?

Maybe not. What Sales Nav gives you:
- Advanced search filters → I can search via other sources + basic LinkedIn
- InMail credits → Connection requests + messages work fine
- Lead lists → I can build these for you
- CRM sync → We can build our own tracking

**Verdict:** Try without it first. If search is too limited, add it later ($80/mo).

---

## Part 6: Implementation Plan

### Phase 1: Foundation (Week 1)
**Day 1-2: Python API Setup**
```bash
# On the VPS
cd ~/clawd
mkdir -p integrations/linkedin
cd integrations/linkedin

# Install the library
pip install linkedin-api

# Create wrapper script
touch linkedin_client.py
```

I'll create `linkedin_client.py` with:
- Safe rate-limited methods
- Automatic delay injection
- Error handling for challenges
- Local SQLite storage for prospects

**Day 3-4: Test Basic Operations**
- Search for test targets
- Fetch profiles
- Store in database
- Generate sample outreach drafts

**Day 5-7: Browser Relay Setup**
- Configure Chrome extension
- Test basic navigation on LinkedIn
- Implement human-like delay functions
- Create safety checks

### Phase 2: Prospect Pipeline (Week 2)
**Build the research workflow:**

1. **Input:** You tell me target criteria
2. **Discovery:** I search X, Google, LinkedIn API
3. **Enrichment:** I pull profile data, recent activity, company info
4. **Scoring:** I rank prospects by fit + accessibility
5. **Drafting:** I generate personalized connection notes and follow-up messages
6. **Output:** Spreadsheet/database ready for outreach

### Phase 3: Outreach Automation (Week 3)
**Start with semi-automated:**
1. I queue up daily targets (15-20)
2. I open LinkedIn, navigate to profile
3. You review, click connect/send
4. I track response in database

**Gradually automate:**
1. Test full auto on 5 targets/day
2. Monitor for restrictions
3. Increase if stable

### Phase 4: Response Management (Week 4+)
- I check for new messages/acceptances
- I draft responses
- You review and send
- I track pipeline stage

---

## What We'd Need to Build

### Scripts/Tools
1. **linkedin_client.py** - Wrapper around linkedin-api with safety
2. **prospect_db.py** - SQLite storage for targets
3. **message_generator.py** - AI message drafting
4. **browser_linkedin.py** - Clawdbot browser automation for LinkedIn
5. **daily_outreach.py** - Orchestrator script

### Data Structure
```
prospects/
├── discovered/      # Raw targets
├── enriched/        # With full profile data
├── queued/          # Ready for outreach
├── connected/       # Accepted connections
├── messaged/        # Follow-ups sent
└── converted/       # Replied/meetings booked
```

---

## Risk Assessment

### What Could Go Wrong

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Account restriction (temp) | Medium | Medium | Use conservative limits, appeal |
| Account ban (perm) | Low | High | Use secondary account for automation |
| LinkedIn API changes | Low | Medium | Fall back to browser automation |
| Detection of automation | Medium | Medium | Human-like patterns, real Chrome |

### Recommended Safety Measures
1. **Don't automate your main account** - Create a secondary professional account
2. **Start slow** - 5 connections/day for first 2 weeks
3. **Personalize everything** - No templates, always customized
4. **Engage naturally** - Like posts, comment, don't just sell
5. **Monitor inbox** - Keep response rate healthy
6. **Keep manual fallback** - Always review before sending

---

## Conclusion & Recommendation

### What Jarvis Can Do Today
- ✅ Research prospects via X, Google, and other sources
- ✅ Find LinkedIn URLs without API
- ✅ Generate personalized message drafts
- ✅ Track pipeline in local database
- ✅ Use browser relay for semi-automated execution

### What We Can Build This Week
- Python LinkedIn API integration
- Prospect database system
- AI message generation
- Basic browser automation with safety limits

### What I Recommend
**Start with Option A (Hybrid):**
1. I do all research and message drafting
2. You review and execute manually for 2 weeks
3. We gradually add browser automation
4. If stable, move to full auto with secondary account

This gives you 80% of the value with 20% of the risk. You learn what works, we iterate, and you save $179/month from day one.

---

## Ready to Start?

Tell me your first target profile:
- Industry?
- Titles?
- Company size?
- Geography?
- What's the pitch?

I'll build you a prospect list with personalized outreach messages within the hour.

*- Jarvis*

---

## Appendix: Key Resources

### Open Source Tools
- [linkedin-api](https://pypi.org/project/linkedin-api/) - Python unofficial API
- [open-linkedin-api](https://github.com/EseToni/open-linkedin-api) - Community fork
- [OpenOutreach](https://github.com/eracle/OpenOutreach) - Self-hosted automation
- [Playwright Stealth](https://github.com/nickvdyck/playwright-extra-stealth) - Anti-detection

### Research Sources
- [LinkedIn Automation Safety Guide (Dux-Soup)](https://www.dux-soup.com/blog/linkedin-automation-safety-guide-how-to-avoid-account-restrictions-in-2026)
- [LinkedIn Jail Guide (Expandi)](https://expandi.io/blog/linkedin-jail/)
- [LinkedIn Prohibited Software Policy](https://www.linkedin.com/help/linkedin/answer/a1341387)

### Safe Limits Reference
- Connection requests: 100/week max (LinkedIn official)
- Profile views: 300-400/week (community consensus)
- Messages: 100/day to 1st degree (no hard limit)
- Warm-up period: 2-3 weeks recommended
