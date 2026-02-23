#!/usr/bin/env python3
"""
Propwire Lead Automation — Matt Gibson / NYL
Logs in → applies filters → exports CSV → deduplicates → saves to ~/clawd/leads/

Filters: Monmouth County NJ, property value $700k+, sale date within last 12 months
Run: python3 propwire_scraper.py [--headless] [--test]
"""
import os
import sys
import asyncio
import random
import csv
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth

# ── Config ──────────────────────────────────────────────────────────────────
PROFILE_DIR = Path.home() / ".playwright-profiles" / "propwire"
ENV_PATH    = Path.home() / "clawd" / ".env"
LEADS_DIR   = Path.home() / "clawd" / "leads"
LOG_FILE    = Path("/tmp/propwire_scraper.log")
LOGIN_URL   = "https://propwire.com/login"
SEARCH_URL  = "https://propwire.com/search"

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

async def human_delay(min_s=1.0, max_s=3.0):
    await asyncio.sleep(random.uniform(min_s, max_s))

async def screenshot(page, name):
    path = f"/tmp/propwire_{name}_{datetime.now().strftime('%H%M%S')}.png"
    try:
        await page.screenshot(path=path, timeout=10000, full_page=False)
        log(f"Screenshot: {path}")
    except Exception as e:
        log(f"Screenshot failed ({name}): {e}")
    return path

async def login(page, email, password):
    log("Navigating to login page...")
    try:
        await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
    except PlaywrightTimeoutError:
        await page.goto(LOGIN_URL, wait_until="commit", timeout=30000)
    await human_delay(2, 3)

    # Check if already logged in (redirected to search/dashboard)
    if "/login" not in page.url:
        log(f"Already logged in. URL: {page.url}")
        return True

    log("Performing login...")
    await screenshot(page, "before_login")

    try:
        await page.fill("input[type='email'], input[name='email']", email)
        await human_delay(0.5, 1.5)
        await page.fill("input[type='password'], input[name='password']", password)
        await human_delay(0.5, 1.5)

        await page.click("button[type='submit']")
        await page.wait_for_load_state("domcontentloaded", timeout=15000)
        await human_delay(2, 3)

        if "/login" in page.url:
            log("ERROR: Still on login page after submit")
            await screenshot(page, "login_failed")
            return False

        log(f"Login successful. URL: {page.url}")
        await screenshot(page, "after_login")
        return True

    except Exception as e:
        log(f"Login error: {e}")
        await screenshot(page, "login_error")
        return False

async def apply_filters_and_export(page):
    """Navigate to search, apply filters, select all, export CSV."""
    log(f"Navigating to search...")
    try:
        await page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=30000)
    except PlaywrightTimeoutError:
        await page.goto(SEARCH_URL, wait_until="commit", timeout=30000)

    await human_delay(3, 5)
    log(f"Page: {await page.title()} | URL: {page.url}")
    await screenshot(page, "search_loaded")

    # ── Step 1: Search for Monmouth County, NJ ───────────────────────────
    log("Setting location: Monmouth County, NJ")
    try:
        search_input = page.locator("input[placeholder*='Address' i]").first
        await search_input.wait_for(timeout=10000)
        await search_input.click()
        await human_delay(0.5, 1)
        await search_input.fill("Monmouth County, NJ")
        await human_delay(1.5, 2.5)

        # Click autocomplete suggestion
        try:
            suggestion = page.locator("[role='option']:has-text('Monmouth'), li:has-text('Monmouth County')").first
            await suggestion.wait_for(timeout=4000)
            await suggestion.click()
            log("Clicked Monmouth County autocomplete suggestion")
        except:
            await page.keyboard.press("Enter")
            log("Pressed Enter for location search")

        await human_delay(3, 5)
        await screenshot(page, "location_set")
    except Exception as e:
        log(f"Location filter error: {e}")
        await screenshot(page, "location_error")

    # ── Step 2: Price filter ($700k+) ─────────────────────────────────────
    log("Setting Price filter: $700k+")
    try:
        price_btn = page.locator("button:has-text('Price')").first
        await price_btn.wait_for(timeout=5000)
        await price_btn.click()
        await human_delay(1, 2)
        await screenshot(page, "price_open")

        min_input = page.locator("input[placeholder*='Min' i], input[placeholder*='No min' i]").first
        if await min_input.count() > 0:
            await min_input.fill("700000")
            await human_delay(0.5, 1)
            log("Set min price: $700,000")

        # Close by pressing Escape or clicking Apply
        apply = page.locator("button:has-text('Apply'), button:has-text('Done')").first
        if await apply.count() > 0:
            await apply.click()
        else:
            await page.keyboard.press("Escape")
        await human_delay(1, 2)
    except Exception as e:
        log(f"Price filter error: {e}")

    # ── Step 3: Sale date (last 12 months) via "More" ─────────────────────
    log("Setting sale date filter: last 12 months")
    try:
        more_btn = page.locator("button:has-text('More')").first
        await more_btn.wait_for(timeout=5000)
        await more_btn.click()
        await human_delay(1.5, 2.5)
        await screenshot(page, "more_open")

        # Try "Last Sale Date" section
        from_date = (datetime.now() - timedelta(days=365)).strftime("%m/%d/%Y")
        to_date = datetime.now().strftime("%m/%d/%Y")

        # Look for sale date inputs
        date_inputs = page.locator("input[placeholder*='MM/DD/YYYY' i], input[type='date']")
        count = await date_inputs.count()
        if count >= 2:
            await date_inputs.nth(0).fill(from_date)
            await human_delay(0.3, 0.8)
            await date_inputs.nth(1).fill(to_date)
            log(f"Set sale date: {from_date} to {to_date}")
        elif count == 1:
            await date_inputs.nth(0).fill(from_date)
            log(f"Set sale date from: {from_date}")

        apply = page.locator("button:has-text('Apply'), button:has-text('Done'), button:has-text('Search')").first
        if await apply.count() > 0:
            await apply.click()
            log("Applied More filters")
        else:
            await page.keyboard.press("Escape")
        await human_delay(2, 4)
        await screenshot(page, "filters_applied")
    except Exception as e:
        log(f"More filters error: {e}")

    # ── Step 4: Wait for results ──────────────────────────────────────────
    log("Waiting for results...")
    await human_delay(3, 5)
    await screenshot(page, "results")

    # ── Step 5: Select all & Export ───────────────────────────────────────
    log("Selecting all and exporting...")
    LEADS_DIR.mkdir(parents=True, exist_ok=True)

    # Try select-all checkbox
    try:
        select_all = page.locator("input[type='checkbox']").first
        if await select_all.count() > 0:
            await select_all.click()
            await human_delay(1, 2)
            log("Clicked select-all")
    except Exception as e:
        log(f"Select all warning: {e}")

    # Find export button
    export_btn = None
    for sel in ["button:has-text('Export')", "button:has-text('Download')", "a:has-text('Export')", "[aria-label*='export' i]"]:
        try:
            el = page.locator(sel).first
            if await el.count() > 0:
                export_btn = el
                log(f"Found export: {sel}")
                break
        except:
            continue

    if not export_btn:
        log("No export button found — taking diagnostic screenshot")
        await screenshot(page, "no_export")
        return None

    try:
        async with page.expect_download(timeout=60000) as dl_info:
            await export_btn.click()
            await human_delay(1, 2)

        download = await dl_info.value
        date_str = datetime.now().strftime("%Y-%m-%d")
        dest = LEADS_DIR / f"propwire_raw_{date_str}.csv"
        await download.save_as(str(dest))
        log(f"✅ Downloaded: {dest}")
        return dest

    except PlaywrightTimeoutError:
        log("Export download timed out")
        await screenshot(page, "export_timeout")
        return None
    except Exception as e:
        log(f"Export error: {e}")
        await screenshot(page, "export_error")
        return None

def deduplicate(new_file: Path) -> int:
    """Remove addresses already in existing lead files."""
    if not new_file.exists():
        return 0

    existing = set()
    for f in LEADS_DIR.glob("propwire_leads_*.csv"):
        try:
            with open(f) as fh:
                for row in csv.DictReader(fh):
                    addr = row.get("address", row.get("Address", "")).strip().lower()
                    if addr:
                        existing.add(addr)
        except:
            pass

    try:
        with open(new_file) as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)
            fieldnames = reader.fieldnames or []

        addr_key = next((k for k in fieldnames if "address" in k.lower()), None)
        if not addr_key:
            log(f"No address column. Columns: {fieldnames}")
            return len(rows)

        new_rows = [r for r in rows if r.get(addr_key, "").strip().lower() not in existing]
        dupes = len(rows) - len(new_rows)

        final = LEADS_DIR / f"propwire_leads_{datetime.now().strftime('%Y-%m-%d')}.csv"
        with open(final, "w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(new_rows)

        log(f"Dedup: {len(rows)} total → {len(new_rows)} new, {dupes} dupes skipped")
        log(f"Final leads: {final}")
        return len(new_rows)
    except Exception as e:
        log(f"Dedup error: {e}")
        return 0

async def run(headless=False, test_only=False):
    load_dotenv(dotenv_path=ENV_PATH)
    email = os.getenv("PROPWIRE_EMAIL")
    password = os.getenv("PROPWIRE_PASSWORD")

    if not email or not password:
        log("ERROR: PROPWIRE_EMAIL or PROPWIRE_PASSWORD not set in ~/clawd/.env")
        sys.exit(1)

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    log(f"Starting Propwire scraper | headless={headless} | test={test_only}")

    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=headless,
            viewport={"width": 1280, "height": 900},
            downloads_path=str(LEADS_DIR),
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            args=["--disable-blink-features=AutomationControlled"],
        )

        page = await ctx.new_page()
        await Stealth().apply_stealth_async(page)

        ok = await login(page, email, password)
        if not ok:
            log("Login failed")
            await ctx.close()
            sys.exit(1)

        if test_only:
            log("✅ Test mode — login verified")
            await screenshot(page, "test_done")
            await ctx.close()
            return

        raw_file = await apply_filters_and_export(page)
        await ctx.close()

    if raw_file:
        count = deduplicate(raw_file)
        log(f"✅ Done. {count} new leads.")
    else:
        log("No file downloaded. Check /tmp/propwire_*.png screenshots.")

def main():
    parser = argparse.ArgumentParser(description="Propwire Lead Scraper")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--test", action="store_true", help="Just verify login")
    args = parser.parse_args()
    asyncio.run(run(headless=args.headless, test_only=args.test))

if __name__ == "__main__":
    main()
