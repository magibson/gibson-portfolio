# Restaurant Reservation Automation Research

**Date:** 2026-01-29  
**Purpose:** Determine the most reliable approaches for automated restaurant booking via Clawdbot

---

## Executive Summary

**Resy** is the clear winner for automation - it has a well-documented unofficial API that multiple successful bots use. The existing `resy-client.js` implementation is solid and just needs proper credentials.

**OpenTable** is harder - they have no consumer API and aggressive bot detection. The 45-second timeout on sign-in is likely Cloudflare blocking the headless Playwright instance. The solution is either (1) use Clawdbot's browser tool with the Chrome relay extension (your real browser session), or (2) implement stealth plugins + persistent session.

---

## Platform Analysis

### Resy (Highly Recommended) ⭐⭐⭐⭐⭐

**API Status:** Unofficial but reliable public API at `api.resy.com`

**Why it works:**
- Resy's API is fully functional and well-understood
- Multiple successful bots exist: [Alkaar/resy-booking-bot](https://github.com/Alkaar/resy-booking-bot), [emandel2630/Resy-Bot](https://github.com/emandel2630/Resy-Bot)
- No browser automation needed - just HTTP requests
- Supports: search, availability, booking, cancellation, waitlists

**What you need:**
1. `api_key` - Found in `Authorization` header (format: `ResyAPI api_key="..."`)
2. `auth_token` - Found in `x-resy-auth-token` header
3. Both obtained from Chrome DevTools Network tab while logged into resy.com

**Current implementation status:** ✅ `resy-client.js` is complete and correct, just needs credentials

### OpenTable ⭐⭐⭐

**API Status:** No consumer API - requires affiliate/partner status (enterprise only)

**Why the timeout happened:**
- OpenTable uses Cloudflare and similar bot detection
- Headless Playwright is easily fingerprinted
- The login page specifically checks for automation markers
- `navigator.webdriver` property, missing `window.chrome` object, canvas fingerprints

**Solutions (in order of reliability):**

1. **Use Clawdbot's Browser Relay (BEST)** - Attach your real Chrome session via the browser extension. This uses your actual authenticated browser with all cookies, no bot detection.

2. **Cookie-based session persistence** - Log in manually once, export cookies, reuse them. This is what `opentable-login.js` attempts but needs the Chrome relay.

3. **Stealth Playwright** - Use `playwright-extra` with stealth plugin. Reduces but doesn't eliminate detection.

---

## Recommended Implementation Plan

### Phase 1: Get Resy Working (15 minutes)

This is the quick win. Resy should work immediately once configured.

**Step 1: Extract Resy credentials**
1. Open Chrome, go to [resy.com](https://resy.com) and log in
2. Open DevTools → Network tab
3. Navigate to any restaurant page
4. Find a request to `api.resy.com` (e.g., `/find`)
5. Copy these headers:
   - `authorization` → The part after `api_key=` is your API key
   - `x-resy-auth-token` → This is your auth token

**Step 2: Update config.json**
```json
{
  "credentials": {
    "resy": {
      "api_key": "VbWk7s3L4KiK5fzlO7JD3Q5EYolJI7n5",  // Example format
      "auth_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI...",  // Your token
      "email": "msgibson103@gmail.com",
      "password": "your-password"  // Optional - for token refresh
    }
  }
}
```

**Step 3: Test it**
```bash
cd /home/clawd/clawd/integrations/reservations
node resy-client.js reservations  # Should list your reservations
node resy-client.js search "Italian"  # Search for restaurants
```

### Phase 2: OpenTable via Chrome Relay (Recommended)

Instead of fighting bot detection with headless Playwright, use your real browser session.

**How it works:**
1. Install Clawdbot Browser Relay Chrome extension (if not already)
2. Log into OpenTable in your Chrome browser manually
3. Click the Clawdbot toolbar button to attach the tab
4. Ask Clawdbot to book via browser - it uses YOUR authenticated session

**Example conversation:**
```
You: Book me a table at Eleven Madison Park for 2 people next Saturday at 7pm
Clawd: *uses browser tool with profile="chrome" to navigate and book*
```

**Benefits:**
- Uses your real browser fingerprint
- Already logged in with cookies
- No bot detection because it IS your browser
- Works for any site, not just OpenTable

### Phase 3: Improve Headless OpenTable (Optional/Advanced)

If you need fully autonomous headless OpenTable booking, upgrade the Playwright implementation:

**Install stealth plugin:**
```bash
cd /home/clawd/clawd/integrations/reservations
npm install playwright-extra puppeteer-extra-plugin-stealth
```

**Upgrade opentable-client.js:**
```javascript
// Replace import
import { chromium } from 'playwright-extra';
import StealthPlugin from 'puppeteer-extra-plugin-stealth';
chromium.use(StealthPlugin());

// Add to launch config
const browser = await chromium.launch({
  headless: false,  // Or 'new' for new headless mode
  args: [
    '--disable-blink-features=AutomationControlled',
    '--no-sandbox'
  ]
});

// Add init script to remove automation markers
await context.addInitScript(() => {
  Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
  window.chrome = { runtime: {} };
});
```

**Use residential proxy for IP reputation** (if still getting blocked)

---

## Token/Credential Longevity

| Platform | Token Lifetime | Refresh Method |
|----------|---------------|----------------|
| Resy | ~30 days | Re-extract from browser, or use password login API |
| OpenTable | Session-based | Keep cookies fresh, re-login if expired |

**Resy password login** (auto-refresh tokens):
```javascript
const client = new ResyClient();
await client.login('email@example.com', 'password');
// Token auto-saved to config.json
```

---

## Sniping Hard-to-Get Reservations

For popular restaurants (Carbone, Don Angie, etc.) that book up instantly:

### Resy Sniper Approach
The existing bots (Alkaar, ez-resy) implement this pattern:
1. Set up cron job to run at reservation release time (usually 9 AM or 10 AM)
2. Hit API immediately when reservations open
3. Book first available matching slot
4. Run for 10 seconds retrying if needed

**Example cron:**
```bash
# Run at 8:59:55 AM to be ready for 9 AM drops
55 8 * * * cd /home/clawd/clawd/integrations/reservations && node resy-client.js book VENUE_ID 2024-02-15 19:00 2
```

### Waitlist API (Resy)
From research: Resy has an undocumented waitlist API for walk-in queues:
```javascript
POST https://api.resy.com/3/waitlist
{
  "num_seats": 2,
  "quoted_wait_time": 14400,
  "venue_id": 1505
}
```
*(Note: Restaurants may contact you if they notice API-based waitlist adds)*

---

## Third-Party Services

| Service | What it does | Cost | Notes |
|---------|-------------|------|-------|
| Hostie.ai | AI phone reservations | Paid | For restaurants, not diners |
| TableAgent | Free reservation system | Free | For restaurants using their platform |
| Concierge bots | Custom sniper services | $$ | Grey market, YMMV |

**Recommendation:** DIY with Resy API is more reliable than third-party services.

---

## Common Pitfalls & Solutions

### 1. "401 Unauthorized" on Resy
- **Cause:** Token expired
- **Fix:** Re-extract tokens from browser, or run `resy-client.js login`

### 2. OpenTable login timeout
- **Cause:** Bot detection blocking headless browser
- **Fix:** Use Chrome relay OR implement stealth + non-headless mode

### 3. "No slots available" when slots exist
- **Cause:** API returns different results than website
- **Fix:** Check party size matches, ensure correct date format (YYYY-MM-DD)

### 4. Reservation requires payment
- **Cause:** Some restaurants require credit card on file
- **Fix:** Ensure card is saved in your Resy/OpenTable account first

### 5. Rate limiting
- **Cause:** Too many API requests
- **Fix:** Add delays between requests (2-5 seconds minimum)

---

## Files to Update

1. **`config.json`** - Add real credentials (Resy api_key, auth_token)
2. **`opentable-client.js`** - Add stealth plugin (if not using Chrome relay)
3. **`SKILL.md`** - Update with Chrome relay instructions

---

## Summary: What Matt Needs to Do

### Quick Start (Resy only - works today):
1. Go to resy.com in Chrome, log in
2. Open DevTools → Network, find api.resy.com request
3. Copy `authorization` and `x-resy-auth-token` headers
4. Update `/home/clawd/clawd/integrations/reservations/config.json` with these values
5. Test: `node resy-client.js reservations`

### For OpenTable:
Use Clawdbot's browser tool with Chrome relay:
1. Install/activate Browser Relay extension
2. Log into OpenTable in Chrome
3. Click toolbar button to attach tab
4. Ask Clawdbot to book - it will use your real browser

### For Hard-to-Get Reservations:
Set up a cron job to snipe at release time using the Resy API.

---

*This research compiled from: Alkaar/resy-booking-bot, dev.to articles, Medium post on Resy API, BrowserStack Playwright/Cloudflare guide, and analysis of existing Clawdbot reservation integration code.*
