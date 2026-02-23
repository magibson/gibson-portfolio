#!/usr/bin/env python3
"""
Propwire Lead Automation — Matt Gibson / NYL
Fresh browser launch → login → dismiss modal → apply filters → export CSV

Filters: Monmouth County NJ · $700k+ value · sold within last 12 months
Usage:  python3 propwire_scraper.py [--test] [--headless]
Note:   headless=False by default (DataDome blocks headless).
        The Mac mini must be running a logged-in desktop session.
"""
import os, sys, asyncio, random, csv, argparse
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
from playwright.async_api import async_playwright, TimeoutError as PWTimeout
from playwright_stealth import Stealth

# ── Config ───────────────────────────────────────────────────────────────────
ENV_PATH  = Path.home() / "clawd" / ".env"
LEADS_DIR = Path.home() / "clawd" / "leads"
LOG_FILE  = Path("/tmp/propwire_scraper.log")
BASE      = "https://propwire.com"

def log(msg: str):
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

async def delay(lo=1.0, hi=3.0):
    await asyncio.sleep(random.uniform(lo, hi))

async def snap(page, name: str):
    path = f"/tmp/propwire_{name}_{datetime.now().strftime('%H%M%S')}.png"
    try:
        await page.screenshot(path=path, timeout=10000, full_page=False)
        log(f"📸 {path}")
    except:
        pass

async def dismiss_modals(page):
    """Multi-strategy modal dismissal."""
    log("Dismissing modals...")

    # Strategy 1: JS — find close button by various patterns
    dismissed = await page.evaluate("""() => {
        // Check "Don't show this again" checkbox if present
        const checkboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'));
        for (const cb of checkboxes) {
            const label = cb.closest('label')?.innerText || document.querySelector(`label[for="${cb.id}"]`)?.innerText || '';
            if (label.toLowerCase().includes("don't show") || label.toLowerCase().includes("dont show")) {
                if (!cb.checked) cb.click();
            }
        }
        // Try to click any button in dialogs/overlays
        const patterns = [
            '[role="dialog"] button',
            '[class*="modal"] button',
            '[class*="overlay"] button',
            '[class*="popup"] button',
            '[data-testid*="close"]',
            'button[aria-label="Close"]',
            'button[aria-label="close"]',
        ];
        for (const sel of patterns) {
            const els = document.querySelectorAll(sel);
            for (const el of els) {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                if (rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden') {
                    const t = el.innerText?.trim();
                    // Prefer buttons that look like close/X buttons (small, or contain X chars)
                    if (!t || ['×','✕','✖','x','X','Close','close'].includes(t) || el.getAttribute('aria-label')?.toLowerCase().includes('close')) {
                        el.click();
                        return 'clicked: ' + sel + ' text=' + t;
                    }
                }
            }
        }
        // Click the FIRST button in any visible modal-like container
        for (const sel of ['[role="dialog"] button', '[class*="modal"] button']) {
            const el = document.querySelector(sel);
            if (el) { el.click(); return 'first-btn: ' + sel; }
        }
        return null;
    }""")
    if dismissed:
        log(f"Modal JS: {dismissed}")
        await delay(1.5, 2.5)
        await snap(page, "modal_dismissed")
        return

    # Strategy 2: Playwright locator — look for close button near "What's New" text
    for sel in [
        "button:near(:text('What'))",
        "[role='dialog'] button",
        "button:has(svg)",
        "button.close",
    ]:
        try:
            el = page.locator(sel).first
            if await el.count() > 0:
                await el.click(force=True, timeout=3000)
                log(f"Modal PW: {sel}")
                await delay(1.5, 2.5)
                return
        except:
            pass

    # Strategy 3: Escape
    await page.keyboard.press("Escape")
    await delay(1, 2)
    log("Modal: tried Escape")

async def run(headless=False, test_only=False):
    load_dotenv(dotenv_path=ENV_PATH)
    email    = os.getenv("PROPWIRE_EMAIL")
    password = os.getenv("PROPWIRE_PASSWORD")
    if not email or not password:
        log("❌ PROPWIRE_EMAIL / PROPWIRE_PASSWORD missing from .env")
        sys.exit(1)

    PROFILE_DIR = Path.home() / ".playwright-profiles" / "propwire"
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    # Clean stale lock files
    for lock in ["SingletonLock", "SingletonSocket"]:
        (PROFILE_DIR / lock).unlink(missing_ok=True)

    LEADS_DIR.mkdir(parents=True, exist_ok=True)
    log(f"🚀 Starting | headless={headless} test={test_only}")

    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=headless,
            viewport={"width": 1280, "height": 900},
            accept_downloads=True,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        page = await ctx.new_page()
        await Stealth().apply_stealth_async(page)

        # ── Login ────────────────────────────────────────────────────────
        await page.goto(f"{BASE}/login", wait_until="domcontentloaded", timeout=30000)
        await delay(2, 3)

        # Check for CAPTCHA
        if "captcha" in page.url or "captcha" in (await page.content()).lower()[:2000]:
            log("⚠️ CAPTCHA detected — DataDome rate limit. Try again later.")
            await snap(page, "captcha_block")
            await ctx.close()
            sys.exit(2)

        if "/login" not in page.url:
            log(f"✅ Session valid — already logged in → {page.url}")
        else:
            log("Logging in with credentials...")
            await snap(page, "login_page")
            await page.fill("input[type='email'], input[name='email']", email)
            await delay(0.5, 1)
            await page.fill("input[type='password'], input[name='password']", password)
            await delay(0.5, 1)
            await page.click("button[type='submit']")
            await page.wait_for_load_state("domcontentloaded", timeout=20000)
            await delay(2, 3)

            # Re-check for CAPTCHA after login attempt
            if "captcha" in page.url or await page.locator("text=Slide right").count() > 0:
                log("⚠️ CAPTCHA after login — rate limited. Try again in 30-60 min.")
                await snap(page, "captcha_post_login")
                await ctx.close()
                sys.exit(2)

            if "/login" in page.url:
                log("❌ Login failed — check credentials")
                await snap(page, "login_fail")
                await ctx.close()
                sys.exit(1)

            log(f"✅ Logged in → {page.url}")

        await snap(page, "after_login")
        if test_only:
            log("✅ Test done")
            await ctx.close()
            return

        # ── Search page ──────────────────────────────────────────────────
        if "/search" not in page.url:
            await page.goto(f"{BASE}/search", wait_until="domcontentloaded", timeout=30000)
        await delay(3, 5)
        await dismiss_modals(page)
        await snap(page, "search_ready")

        # ── Location filter ──────────────────────────────────────────────
        log("Location: Monmouth County, NJ")
        try:
            inp = page.locator("input[placeholder*='Address'], input[name='search']").first
            # Wait for visible — modal must be gone before input becomes interactive
            await inp.wait_for(state="visible", timeout=12000)
            await inp.click(force=True)
            await delay(0.5, 1)
            await inp.fill("Monmouth County, NJ")
            await delay(1.5, 2.5)
            try:
                sugg = page.locator("[role='option']:has-text('Monmouth'), li:has-text('Monmouth County')").first
                await sugg.wait_for(timeout=5000)
                await sugg.click()
            except:
                await page.keyboard.press("Enter")
            await delay(3, 5)
            await snap(page, "location_set")
        except Exception as e:
            log(f"⚠️ Location: {e}")
            # Fallback: force-type into the input
            try:
                await page.evaluate("document.querySelector('input[name=\\'search\\']')?.click()")
                await delay(0.5, 1)
                await page.keyboard.type("Monmouth County, NJ", delay=50)
                await delay(1.5, 2.5)
                await page.keyboard.press("Enter")
                await delay(3, 5)
                log("Location: used JS fallback")
            except Exception as e2:
                log(f"⚠️ Location fallback: {e2}")

        # ── Price filter ─────────────────────────────────────────────────
        log("Price: $700k+")
        try:
            price_btn = page.locator("button:has-text('Price')").first
            await price_btn.wait_for(timeout=6000)
            await price_btn.click()
            await delay(1, 2)
            min_f = page.locator("input[placeholder*='Min' i], input[placeholder*='No min' i]").first
            if await min_f.count() > 0:
                await min_f.fill("700000")
                await page.keyboard.press("Tab")
                await delay(0.5, 1)
            apply = page.locator("button:has-text('Apply'), button:has-text('Done')").first
            if await apply.count() > 0:
                await apply.click()
            else:
                await price_btn.click()
            await delay(1, 2)
            await snap(page, "price_set")
        except Exception as e:
            log(f"⚠️ Price: {e}")

        # ── Date filter (last 12 months via More) ────────────────────────
        log("Sale date: last 12 months")
        try:
            more = page.locator("button:has-text('More')").first
            await more.wait_for(timeout=6000)
            await more.click()
            await delay(1.5, 2.5)
            await snap(page, "more_open")

            from_d = (datetime.now() - timedelta(days=365)).strftime("%m/%d/%Y")
            to_d   = datetime.now().strftime("%m/%d/%Y")
            date_ins = page.locator("input[placeholder*='MM/DD/YYYY' i], input[placeholder*='Start' i]")
            cnt = await date_ins.count()
            if cnt >= 2:
                await date_ins.nth(0).fill(from_d)
                await delay(0.3, 0.7)
                await date_ins.nth(1).fill(to_d)
                log(f"Dates: {from_d} – {to_d}")

            apply = page.locator("button:has-text('Apply'), button:has-text('Done'), button:has-text('Search')").first
            if await apply.count() > 0:
                await apply.click()
            else:
                await page.keyboard.press("Escape")
            await delay(2, 4)
            await snap(page, "date_set")
        except Exception as e:
            log(f"⚠️ Date: {e}")

        # ── Results + Export ─────────────────────────────────────────────
        await delay(3, 5)
        await snap(page, "results")

        # Select all
        try:
            cb = page.locator("input[type='checkbox']").first
            if await cb.count() > 0:
                await cb.click()
                await delay(1, 2)
                log("Select-all clicked")
        except:
            pass

        # Export
        raw_file = None
        for sel in ["button:has-text('Export')", "button:has-text('Download')",
                    "a:has-text('Export')", "[aria-label*='export' i]"]:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    log(f"Export button: {sel}")
                    async with page.expect_download(timeout=60000) as dl_info:
                        await el.click()
                        await delay(1, 2)
                    dl  = await dl_info.value
                    dst = LEADS_DIR / f"propwire_raw_{datetime.now().strftime('%Y-%m-%d')}.csv"
                    await dl.save_as(str(dst))
                    log(f"✅ Downloaded: {dst}")
                    raw_file = dst
                    break
            except Exception as e:
                log(f"Export ({sel}): {e}")

        if not raw_file:
            log("❌ Export failed — check screenshots")
            await snap(page, "no_export")

        await ctx.close()

    if raw_file:
        # Dedup
        existing = set()
        for f in LEADS_DIR.glob("propwire_leads_*.csv"):
            try:
                with open(f) as fh:
                    for row in csv.DictReader(fh):
                        addr = row.get("address", row.get("Address","")).strip().lower()
                        if addr: existing.add(addr)
            except: pass
        with open(raw_file) as fh:
            reader = csv.DictReader(fh)
            rows = list(reader); fields = reader.fieldnames or []
        addr_key = next((k for k in fields if "address" in k.lower()), None)
        new_rows = [r for r in rows if not addr_key or r.get(addr_key,"").strip().lower() not in existing]
        final = LEADS_DIR / f"propwire_leads_{datetime.now().strftime('%Y-%m-%d')}.csv"
        with open(final,"w",newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(new_rows)
        log(f"✅ {len(new_rows)} new leads → {final}")
    else:
        log("No leads saved")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--test", action="store_true")
    p.add_argument("--headless", action="store_true")
    args = p.parse_args()
    asyncio.run(run(headless=args.headless, test_only=args.test))

if __name__ == "__main__":
    main()
