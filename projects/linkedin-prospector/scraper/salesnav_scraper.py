#!/usr/bin/env python3
"""
LinkedIn Sales Navigator Automated Scraper — Jarvis
Uses a persistent Playwright profile (logged-in session).
NEVER posts, messages, or interacts with any human.
Only reads search results and extracts lead data.

Usage:
  python3 salesnav_scraper.py                    # Run all active campaigns
  python3 salesnav_scraper.py --campaign 1       # Run specific campaign by ID
  python3 salesnav_scraper.py --login            # Open browser for manual login only
  python3 salesnav_scraper.py --max-pages 3      # Limit pages per campaign
"""

import os, sys, asyncio, json, random, sqlite3, argparse, requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

# ── Config ───────────────────────────────────────────────────────────────────
ENV_PATH     = Path.home() / "clawd" / ".env"
PROFILE_DIR  = Path.home() / ".playwright-profiles" / "linkedin-salesnav"
DB_PATH      = Path.home() / "clawd/projects/linkedin-prospector/server/prospector.db"
API_BASE     = "http://127.0.0.1:8089"
LOG_FILE     = Path("/tmp/salesnav_scraper.log")
RESULTS_PER_PAGE = 25
MAX_PAGES_DEFAULT = 10   # Safety cap — Sales Nav allows up to 100 results (4 pages of 25)

# Sales Navigator search URLs per campaign
# Format: (campaign_id, name, sales_nav_url)
CAMPAIGNS = [
    {
        "id": 1,
        "name": "Local Job Changes",
        "description": "People who recently changed jobs in Monmouth County NJ — life transition = insurance review moment",
        "url": "https://www.linkedin.com/sales/search/people?query=(recentSearchParam%3A(doLogHistory%3Atrue)%2Cfilters%3AList((type%3AREGION%2Cvalues%3AList((id%3A102659333%2Ctext%3AMonmouth%2520County%252C%2520New%2520Jersey%252C%2520United%2520States%2CselectionType%3AINCLUDED)))%2C(type%3ARECENTLY_CHANGED_JOBS%2Cvalues%3AList((id%3ARPC%2CselectionType%3AINCLUDED)))))",
    },
    {
        "id": 2,
        "name": "Federal Employees at Risk",
        "description": "Federal/government employees in NJ — DOGE cuts = need life insurance conversation",
        "url": "https://www.linkedin.com/sales/search/people?query=(filters%3AList((type%3AREGION%2Cvalues%3AList((id%3A102571732%2Ctext%3ANew%2520Jersey%252C%2520United%2520States%2CselectionType%3AINCLUDED)))%2C(type%3ACURRENT_COMPANY%2Cvalues%3AList((id%3A1316%2Ctext%3AUnited%2520States%2520Federal%2520Government%2CselectionType%3AINCLUDED)%2C(id%3A3009%2Ctext%3AUS%2520Army%2CselectionType%3AINCLUDED)%2C(id%3A3013%2Ctext%3AUS%2520Navy%2CselectionType%3AINCLUDED)))))&sessionId=salesnav-federal",
    },
    {
        "id": 3,
        "name": "Young Families — Monmouth County",
        "description": "Ages 28-40 in Monmouth County — young families need life insurance",
        "url": "https://www.linkedin.com/sales/search/people?query=(filters%3AList((type%3AREGION%2Cvalues%3AList((id%3A104255643%2Ctext%3AMonmouth%2520County%252C%2520New%2520Jersey%252C%2520United%2520States%2CselectionType%3AINCLUDED)))%2C(type%3AYEARS_OF_EXPERIENCE%2Cvalues%3AList((id%3A3%2Ctext%3A3%2520to%25205%2520years%2CselectionType%3AINCLUDED)%2C(id%3A4%2Ctext%3A6%2520to%252010%2520years%2CselectionType%3AINCLUDED)))))&sessionId=salesnav-young-families",
    },
    {
        "id": 4,
        "name": "High Earners Approaching Retirement",
        "description": "Senior titles in NJ — approaching retirement, need estate/retirement planning",
        "url": "https://www.linkedin.com/sales/search/people?query=(filters%3AList((type%3AREGION%2Cvalues%3AList((id%3A102571732%2Ctext%3ANew%2520Jersey%252C%2520United%2520States%2CselectionType%3AINCLUDED)))%2C(type%3ACURRENT_TITLE%2Cvalues%3AList((id%3A10%2Ctext%3ACEO%2CselectionType%3AINCLUDED)%2C(id%3A9%2Ctext%3ACFO%2CselectionType%3AINCLUDED)%2C(id%3A13%2Ctext%3AVP%2CselectionType%3AINCLUDED)%2C(id%3A14%2Ctext%3ADirector%2CselectionType%3AINCLUDED)))%2C(type%3AYEARS_OF_EXPERIENCE%2Cvalues%3AList((id%3A5%2Ctext%3A11%2520to%252015%2520years%2CselectionType%3AINCLUDED)%2C(id%3A6%2Ctext%3AMore%2520than%252015%2520years%2CselectionType%3AINCLUDED)))))&sessionId=salesnav-high-earners",
    },
]

def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

async def delay(lo=1.5, hi=4.0):
    await asyncio.sleep(random.uniform(lo, hi))

async def snap(page, name: str):
    path = f"/tmp/salesnav_{name}_{datetime.now().strftime('%H%M%S')}.png"
    try:
        await page.screenshot(path=path, timeout=10000)
        log(f"📸 {path}")
    except:
        pass

def get_existing_urls() -> set:
    """Get all LinkedIn URLs already in DB to avoid duplicates."""
    try:
        db = sqlite3.connect(str(DB_PATH))
        rows = db.execute("SELECT linkedin_url FROM leads WHERE linkedin_url IS NOT NULL AND linkedin_url != ''").fetchall()
        db.close()
        return {r[0] for r in rows}
    except Exception as e:
        log(f"⚠️ Could not load existing URLs: {e}")
        return set()

def post_leads_to_api(leads: list, campaign_id: int, search_name: str) -> int:
    """Post scraped leads to the Flask API. Returns count saved."""
    if not leads:
        return 0
    try:
        payload = {
            "leads": leads,
            "search_name": search_name,
            "campaign_id": campaign_id,
        }
        r = requests.post(f"{API_BASE}/api/leads", json=payload, timeout=30)
        if r.ok:
            data = r.json()
            saved = data.get("saved", 0)
            log(f"✅ API: {saved} new leads saved for campaign {campaign_id}")
            return saved
        else:
            log(f"⚠️ API error {r.status_code}: {r.text[:200]}")
            return 0
    except Exception as e:
        log(f"⚠️ API post failed: {e}")
        # Fallback: write directly to DB
        return write_leads_direct(leads, campaign_id, search_name)

def write_leads_direct(leads: list, campaign_id: int, search_name: str) -> int:
    """Fallback: write directly to SQLite if API is down."""
    saved = 0
    try:
        db = sqlite3.connect(str(DB_PATH))
        db.execute('PRAGMA journal_mode=WAL')
        existing = {r[0] for r in db.execute("SELECT linkedin_url FROM leads").fetchall()}
        for lead in leads:
            url = lead.get("linkedin_url", "")
            if url and url in existing:
                continue
            db.execute("""
                INSERT OR IGNORE INTO leads
                (linkedin_url, name, title, company, location, connection_degree,
                 time_in_role, profile_image_url, search_name, campaign_id, scraped_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                url,
                lead.get("name",""),
                lead.get("title",""),
                lead.get("company",""),
                lead.get("location",""),
                lead.get("connection_degree",""),
                lead.get("time_in_role",""),
                lead.get("profile_image_url",""),
                search_name,
                campaign_id,
                datetime.now().isoformat(),
            ))
            saved += 1
        db.commit()
        db.close()
        log(f"✅ Direct DB: {saved} leads written")
    except Exception as e:
        log(f"❌ Direct DB write failed: {e}")
    return saved

SCRAPE_JS = """
() => {
    const leads = [];
    const CARD_SELECTORS = 'li.artdeco-list__item, [data-view-name="search-results-lead-card"], ol.artdeco-list li, .search-results__result-list li, [class*="search-results"] li[class*="artdeco"]';
    const cards = document.querySelectorAll(CARD_SELECTORS);

    function getText(el, sel) {
        if (!el) return '';
        const t = sel ? el.querySelector(sel) : el;
        return t ? t.textContent.trim() : '';
    }

    cards.forEach(card => {
        try {
            const name =
                getText(card, '[data-anonymize="person-name"]') ||
                getText(card, '.artdeco-entity-lockup__title a span') ||
                getText(card, 'a[data-control-name="view_lead_panel_via_search_lead_name"] span') ||
                getText(card, '.result-lockup__name a') ||
                getText(card, 'dt a span');

            if (!name || name.length < 2) return;

            const title =
                getText(card, '[data-anonymize="title"]') ||
                getText(card, '.artdeco-entity-lockup__subtitle span') ||
                getText(card, '.result-lockup__highlight-keyword') ||
                getText(card, 'dd[class*="lockup__subtitle"] span');

            const company =
                getText(card, '[data-anonymize="company-name"]') ||
                getText(card, 'a[data-control-name="view_lead_panel_via_search_lead_company_name"]') ||
                getText(card, '.result-lockup__misc-item a') || '';

            const location =
                getText(card, '[data-anonymize="location"]') ||
                getText(card, '.artdeco-entity-lockup__caption span') ||
                getText(card, '.result-lockup__misc-item:not(:has(a))') || '';

            let profileUrl = '';
            const profileLink = card.querySelector(
                'a[href*="/sales/lead/"], a[href*="/sales/people/"], .artdeco-entity-lockup__title a, a[data-control-name="view_lead_panel_via_search_lead_name"]'
            );
            if (profileLink) {
                profileUrl = profileLink.href || '';
                if (profileUrl && !profileUrl.startsWith('http')) profileUrl = 'https://www.linkedin.com' + profileUrl;
            }

            let degree = getText(card, '.artdeco-entity-lockup__degree') || '';
            if (!degree) {
                for (const b of card.querySelectorAll('span')) {
                    const t = b.textContent.trim();
                    if (/^(1st|2nd|3rd|Out of Network)$/i.test(t)) { degree = t; break; }
                }
            }

            let timeInRole = '';
            for (const s of card.querySelectorAll('span, dd')) {
                const t = s.textContent.trim();
                if (/\\d+\\s*(yr|year|mo|month)/i.test(t)) { timeInRole = t; break; }
            }

            const img = card.querySelector('img[src*="profile"], img.artdeco-entity-lockup__image');

            leads.push({
                name, title, company, location,
                linkedin_url: profileUrl,
                connection_degree: degree,
                time_in_role: timeInRole,
                profile_image_url: img ? img.src : '',
                scraped_at: new Date().toISOString()
            });
        } catch(e) {}
    });
    return leads;
}
"""

async def scrape_campaign(page, campaign: dict, max_pages: int, existing_urls: set) -> list:
    """Scrape one campaign. Returns list of new leads."""
    cid  = campaign["id"]
    name = campaign["name"]
    url  = campaign["url"]
    all_leads = []
    page_num = 1

    log(f"━━━ Campaign {cid}: {name} ━━━")

    # Navigate to first page
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    await delay(4, 6)

    # Check if we're logged in
    if "login" in page.url or "authwall" in page.url or "checkpoint" in page.url:
        log(f"❌ Not logged in — got redirected to {page.url}")
        log("Run with --login flag to authenticate first")
        return []

    if "/sales/" not in page.url:
        log(f"⚠️ Unexpected URL after navigation: {page.url}")
        await snap(page, f"campaign_{cid}_unexpected")
        return []

    log(f"✅ On Sales Nav search page: {page.url[:80]}")
    await snap(page, f"campaign_{cid}_page1")

    while page_num <= max_pages:
        log(f"Scraping page {page_num}...")
        await delay(2, 4)

        # Wait for results to load
        try:
            await page.wait_for_selector(
                'li.artdeco-list__item, [data-view-name="search-results-lead-card"], ol.artdeco-list li',
                timeout=15000
            )
        except PWTimeout:
            log(f"⚠️ Results didn't load on page {page_num} — stopping")
            await snap(page, f"campaign_{cid}_timeout_p{page_num}")
            break

        # Scroll to load lazy content
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        await delay(1, 2)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await delay(1.5, 2.5)

        # Scrape current page
        leads = await page.evaluate(SCRAPE_JS)
        log(f"Page {page_num}: extracted {len(leads)} leads")

        # Dedup against existing DB entries
        new_leads = [l for l in leads if l.get("linkedin_url") not in existing_urls]
        dupes = len(leads) - len(new_leads)
        if dupes > 0:
            log(f"  Skipped {dupes} already-seen leads")

        # Add campaign metadata
        for l in new_leads:
            l["search_name"] = name
            l["campaign_id"] = cid
            existing_urls.add(l.get("linkedin_url",""))

        all_leads.extend(new_leads)
        log(f"  {len(new_leads)} new leads this page ({len(all_leads)} total so far)")

        # Check if there's a next page
        if len(leads) < RESULTS_PER_PAGE:
            log(f"  Only {len(leads)} results (< {RESULTS_PER_PAGE}) — last page reached")
            break

        # Navigate to next page
        page_num += 1
        if page_num > max_pages:
            log(f"  Hit max_pages={max_pages} limit")
            break

        # Build next page URL
        next_url = update_page_param(page.url, page_num)
        log(f"Navigating to page {page_num}...")
        await page.goto(next_url, wait_until="domcontentloaded", timeout=30000)
        await delay(4, 7)  # Be respectful — randomized delay between pages

    log(f"Campaign {cid} done: {len(all_leads)} total new leads")
    return all_leads

def update_page_param(url: str, page_num: int) -> str:
    """Add or update ?page= in URL."""
    from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    params["page"] = [str(page_num)]
    new_query = urlencode({k: v[0] for k, v in params.items()})
    return urlunparse(parsed._replace(query=new_query))

async def run(campaign_ids: list = None, max_pages: int = MAX_PAGES_DEFAULT, login_only: bool = False):
    load_dotenv(dotenv_path=ENV_PATH)

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    for lock in ["SingletonLock", "SingletonSocket"]:
        (PROFILE_DIR / lock).unlink(missing_ok=True)

    log(f"🚀 Sales Nav Scraper starting | campaigns={campaign_ids or 'all'} max_pages={max_pages}")

    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1400, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        page = await ctx.new_page()

        if login_only:
            log("Opening LinkedIn login page for manual authentication...")
            await page.goto("https://www.linkedin.com/sales/", wait_until="domcontentloaded", timeout=30000)
            log("Please log in manually. Close the browser window when done.")
            log("Press Ctrl+C when finished.")
            try:
                await asyncio.sleep(300)  # Wait up to 5 min
            except KeyboardInterrupt:
                pass
            await ctx.close()
            return

        # Check login
        await page.goto("https://www.linkedin.com/sales/home", wait_until="domcontentloaded", timeout=30000)
        await delay(3, 5)

        if "login" in page.url or "authwall" in page.url:
            log("❌ Not logged in. Run with --login to authenticate.")
            await snap(page, "not_logged_in")
            await ctx.close()
            return

        log(f"✅ Logged in to LinkedIn Sales Navigator")

        # Load existing leads to avoid duplicates
        existing_urls = get_existing_urls()
        log(f"Loaded {len(existing_urls)} existing lead URLs for dedup")

        # Filter campaigns
        campaigns_to_run = CAMPAIGNS
        if campaign_ids:
            campaigns_to_run = [c for c in CAMPAIGNS if c["id"] in campaign_ids]
            log(f"Running campaigns: {[c['name'] for c in campaigns_to_run]}")

        total_saved = 0
        results_summary = []

        for campaign in campaigns_to_run:
            try:
                leads = await scrape_campaign(page, campaign, max_pages, existing_urls)
                if leads:
                    saved = post_leads_to_api(leads, campaign["id"], campaign["name"])
                    total_saved += saved
                    results_summary.append(f"• {campaign['name']}: {saved} new leads")
                else:
                    results_summary.append(f"• {campaign['name']}: 0 new leads")

                # Pause between campaigns
                if campaign != campaigns_to_run[-1]:
                    wait = random.uniform(8, 15)
                    log(f"Pausing {wait:.0f}s between campaigns...")
                    await asyncio.sleep(wait)

            except Exception as e:
                log(f"❌ Campaign {campaign['id']} error: {e}")
                results_summary.append(f"• {campaign['name']}: ERROR — {e}")
                await snap(page, f"error_campaign_{campaign['id']}")

        await ctx.close()

    log(f"✅ All done. Total new leads saved: {total_saved}")
    log("Summary:\n" + "\n".join(results_summary))

    # Notify via OpenClaw
    summary_text = f"Sales Nav scrape complete: {total_saved} new leads\n" + "\n".join(results_summary)
    os.system(f'/opt/homebrew/bin/openclaw message send --target 8206180417 --message "{summary_text}"')

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--campaign", type=int, nargs="*", help="Campaign IDs to run (default: all)")
    p.add_argument("--max-pages", type=int, default=MAX_PAGES_DEFAULT, help="Max pages per campaign")
    p.add_argument("--login", action="store_true", help="Open browser for manual login")
    args = p.parse_args()
    asyncio.run(run(
        campaign_ids=args.campaign,
        max_pages=args.max_pages,
        login_only=args.login,
    ))

if __name__ == "__main__":
    main()
