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
    """
    Close any modal/overlay (My Wallet, What's New, etc.)
    Strategy: find visible overlay containers, click their X/close button.
    Avoid accidentally clicking nav buttons like the wallet icon in the header.
    """
    log("Dismissing modals...")

    # Wait a moment for modals to fully render
    await delay(1, 2)

    # Strategy 1: click close button INSIDE a modal/dialog/panel container
    dismissed = await page.evaluate("""() => {
        // Look for modal containers first, then close buttons within them
        const containers = [
            ...document.querySelectorAll('[role="dialog"]'),
            ...document.querySelectorAll('[class*="modal"]'),
            ...document.querySelectorAll('[class*="overlay"]'),
            ...document.querySelectorAll('[class*="slide"]'),
            ...document.querySelectorAll('[class*="panel"]'),
            ...document.querySelectorAll('[class*="drawer"]'),
        ];

        for (const container of containers) {
            const style = window.getComputedStyle(container);
            if (style.display === 'none' || style.visibility === 'hidden') continue;
            const rect = container.getBoundingClientRect();
            if (rect.width < 10 || rect.height < 10) continue;

            // Find close button inside this container
            const closeSelectors = [
                'button[aria-label*="close" i]',
                'button[aria-label*="Close" i]',
                'button[aria-label*="dismiss" i]',
                'button.close',
                'button:has(svg)',
            ];
            for (const sel of closeSelectors) {
                const btn = container.querySelector(sel);
                if (btn) {
                    const bRect = btn.getBoundingClientRect();
                    if (bRect.width > 0 && bRect.height > 0) {
                        btn.click();
                        return 'closed: ' + sel + ' in ' + container.className.slice(0, 60);
                    }
                }
            }

            // Try the first button in the container if it looks like a close (X-like text or top-right position)
            const btns = container.querySelectorAll('button');
            for (const btn of btns) {
                const t = btn.innerText?.trim();
                if (['×','✕','✖','x','X'].includes(t) || btn.getAttribute('aria-label')?.toLowerCase().includes('close')) {
                    btn.click();
                    return 'x-btn: ' + t;
                }
            }
        }

        // Strategy 2: look for backdrop/scrim and click the close button nearby
        const scrim = document.querySelector('[class*="scrim"], [class*="backdrop"], [class*="overlay"]');
        if (scrim) {
            const btn = document.querySelector('[aria-label*="close" i], button.close');
            if (btn) { btn.click(); return 'scrim close btn'; }
        }

        return null;
    }""")

    if dismissed:
        log(f"Modal dismissed via JS: {dismissed}")
        await delay(1.5, 2.5)
        await snap(page, "modal_dismissed")
        return

    # Strategy 2: Escape key
    await page.keyboard.press("Escape")
    await delay(1, 1.5)
    log("Modal: sent Escape")
    await snap(page, "after_escape")


async def wait_for_search_input(page, timeout=20000):
    """
    Find the VISIBLE search input — there are two input[name='search'] elements.
    The first is hidden (width=0), the second is the real visible one.
    Use JS to find the one with actual dimensions.
    """
    log("Waiting for visible search input...")
    start = asyncio.get_event_loop().time()
    while (asyncio.get_event_loop().time() - start) * 1000 < timeout:
        result = await page.evaluate("""() => {
            // Find ALL matching inputs, return the first with actual width
            const inputs = Array.from(document.querySelectorAll("input[name='search'], input[placeholder*='Address']"));
            for (const inp of inputs) {
                const rect = inp.getBoundingClientRect();
                if (rect.width > 50 && rect.height > 0 && !inp.disabled) {
                    return { found: true, width: rect.width, height: rect.height, top: rect.top, index: inputs.indexOf(inp) };
                }
            }
            return { found: false };
        }""")
        if result and result.get("found"):
            log(f"Visible search input found at index {result['index']}, size {result['width']}x{result['height']} ✅")
            # Return the nth matching locator
            idx = result["index"]
            return page.locator("input[name='search'], input[placeholder*='Address']").nth(idx)
        await delay(0.8, 1.2)
    return None


async def run(headless=False, test_only=False):
    load_dotenv(dotenv_path=ENV_PATH)
    email    = os.getenv("PROPWIRE_EMAIL")
    password = os.getenv("PROPWIRE_PASSWORD")
    if not email or not password:
        log("❌ PROPWIRE_EMAIL / PROPWIRE_PASSWORD missing from .env")
        sys.exit(1)

    PROFILE_DIR = Path.home() / ".playwright-profiles" / "propwire"
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
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

        if "captcha" in page.url or "captcha" in (await page.content()).lower()[:2000]:
            log("⚠️ CAPTCHA detected — try again later.")
            await snap(page, "captcha_block")
            await ctx.close()
            sys.exit(2)

        if "/login" not in page.url:
            log(f"✅ Session valid — already logged in → {page.url}")
        else:
            log("Logging in...")
            await snap(page, "login_page")
            await page.fill("input[type='email'], input[name='email']", email)
            await delay(0.5, 1)
            await page.fill("input[type='password'], input[name='password']", password)
            await delay(0.5, 1)
            await page.click("button[type='submit']")
            await page.wait_for_load_state("domcontentloaded", timeout=20000)
            await delay(2, 3)

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

        # ── Navigate to search ───────────────────────────────────────────
        if "/search" not in page.url:
            await page.goto(f"{BASE}/search", wait_until="domcontentloaded", timeout=30000)
        await delay(3, 5)
        await snap(page, "search_loaded")

        # ── Dismiss any open modal/overlay ───────────────────────────────
        # Check if any modal-like overlay exists before dismissing
        has_modal = await page.evaluate("""() => {
            const containers = [
                ...document.querySelectorAll('[role="dialog"]'),
                ...document.querySelectorAll('[class*="modal"]'),
                ...document.querySelectorAll('[class*="slide"]'),
                ...document.querySelectorAll('[class*="drawer"]'),
            ];
            for (const c of containers) {
                const s = window.getComputedStyle(c);
                const r = c.getBoundingClientRect();
                if (s.display !== 'none' && s.visibility !== 'hidden' && r.width > 50 && r.height > 50) {
                    return c.className.slice(0, 80);
                }
            }
            return null;
        }""")

        if has_modal:
            log(f"Modal detected: {has_modal}")
            await dismiss_modals(page)
            await delay(1, 2)
        else:
            log("No modal detected, proceeding.")

        await snap(page, "search_ready")

        # ── Location search ──────────────────────────────────────────────
        log("Setting location: Monmouth County, NJ")

        search_input = await wait_for_search_input(page, timeout=15000)
        if not search_input:
            log("❌ Search input never became interactive. Taking screenshot.")
            await snap(page, "search_input_stuck")
            await ctx.close()
            sys.exit(1)

        # Use JS to focus the VISIBLE input (there are 2, first is hidden)
        await page.evaluate("""() => {
            const inputs = Array.from(document.querySelectorAll("input[name='search'], input[placeholder*='Address']"));
            for (const inp of inputs) {
                const rect = inp.getBoundingClientRect();
                if (rect.width > 50) { inp.focus(); inp.click(); break; }
            }
        }""")
        await delay(0.5, 1)
        await search_input.fill("")
        # Type "Monmouth" — autocomplete shows "Monmouth, NJ → County" as first result
        await page.keyboard.type("Monmouth", delay=60)
        await delay(2.5, 3.5)
        await snap(page, "location_typed")

        # Click the "Monmouth, NJ — County" dropdown option (first result, class=dropdown-option)
        suggestion_found = False
        for sugg_sel in [
            "li.dropdown-option:has-text('Monmouth, NJ')",
            "li.dropdown-option:first-child",
            "li:has-text('Monmouth, NJ')",
            ".dropdown-option",  # first visible one
        ]:
            try:
                sugg = page.locator(sugg_sel).first
                await sugg.wait_for(state="visible", timeout=6000)
                text = await sugg.inner_text()
                log(f"Clicking suggestion: '{text.strip()[:50]}' via {sugg_sel}")
                await sugg.click()
                suggestion_found = True
                break
            except:
                continue

        if not suggestion_found:
            log("⚠️ No dropdown suggestion clicked, trying ArrowDown+Enter")
            await page.keyboard.press("ArrowDown")
            await delay(0.3, 0.5)
            await page.keyboard.press("Enter")

        await delay(4, 6)
        await snap(page, "location_set")

        # ── Price filter ─────────────────────────────────────────────────
        # Filter buttons are div.custom-input elements, NOT <button> tags
        log("Setting price filter: $700k+")
        try:
            price_div = page.locator("div.custom-input:has-text('Price')").first
            await price_div.wait_for(state="visible", timeout=12000)
            await price_div.click()
            await delay(1.5, 2)
            await snap(page, "price_open")

            # The price panel has input[name='start'] (min) and input[name='end'] (max)
            min_input = page.locator("input[name='start']").first
            if await min_input.count() > 0:
                await min_input.triple_click()
                await min_input.type("700000", delay=50)
                await delay(0.5, 1)
                log("Min price set: $700,000")

            # Apply: look for any apply/done button inside the open panel
            apply_btn = page.locator("button:has-text('Apply'), button:has-text('Done'), button:has-text('Search')").first
            if await apply_btn.count() > 0 and await apply_btn.is_visible():
                await apply_btn.click()
            else:
                await price_div.click()  # toggle closed
            await delay(1.5, 2.5)
            await snap(page, "price_set")
            log("✅ Price filter applied")
        except Exception as e:
            log(f"⚠️ Price filter: {e}")

        # ── Date filter via More ─────────────────────────────────────────
        log("Setting date filter: last 12 months")
        try:
            more_div = page.locator("div.custom-input:has-text('More')").first
            await more_div.wait_for(state="visible", timeout=8000)
            await more_div.click()
            await delay(1.5, 2.5)
            await snap(page, "more_open")

            from_d = (datetime.now() - timedelta(days=365)).strftime("%m/%d/%Y")
            to_d   = datetime.now().strftime("%m/%d/%Y")

            date_inputs = page.locator("input[placeholder*='MM/DD/YYYY' i], input[placeholder*='Start date' i], input[placeholder*='From' i]")
            cnt = await date_inputs.count()
            if cnt >= 2:
                await date_inputs.nth(0).fill(from_d)
                await delay(0.3, 0.6)
                await date_inputs.nth(1).fill(to_d)
                log(f"Date range: {from_d} → {to_d}")
            elif cnt == 1:
                await date_inputs.nth(0).fill(from_d)
                log(f"Single date input: {from_d}")

            apply_btn = page.locator("button:has-text('Apply'), button:has-text('Search'), button:has-text('Done')").first
            if await apply_btn.count() > 0 and await apply_btn.is_visible():
                await apply_btn.click()
            else:
                await page.keyboard.press("Escape")
            await delay(3, 5)
            await snap(page, "date_set")
            log("✅ Date filter applied")
        except Exception as e:
            log(f"⚠️ Date filter: {e}")

        # ── Wait for results ──────────────────────────────────────────────
        await delay(3, 5)
        await snap(page, "results")

        # Check result count
        count_text = ""
        try:
            count_el = page.locator("text=/\\d+ Results/i, text=/of \\d+/i").first
            if await count_el.count() > 0:
                count_text = await count_el.inner_text()
                log(f"Results: {count_text}")
        except:
            pass

        # ── Select all & Export ───────────────────────────────────────────
        # Select all records
        try:
            select_all = page.locator("input[type='checkbox']").first
            if await select_all.count() > 0 and await select_all.is_visible():
                await select_all.click()
                await delay(1, 2)
                log("Select-all clicked")
                await snap(page, "selected")
        except Exception as e:
            log(f"⚠️ Select-all: {e}")

        # Export
        raw_file = None
        for sel in [
            "button:has-text('Export')",
            "button:has-text('Download')",
            "a:has-text('Export')",
            "[aria-label*='export' i]",
            "button:has-text('CSV')",
        ]:
            try:
                el = page.locator(sel).first
                if await el.count() > 0 and await el.is_visible():
                    log(f"Export button found: {sel}")
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
        # Dedup against existing leads
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

        with open(raw_file) as fh:
            reader = csv.DictReader(fh)
            rows   = list(reader)
            fields = reader.fieldnames or []

        addr_key = next((k for k in fields if "address" in k.lower()), None)
        new_rows = [r for r in rows if not addr_key or r.get(addr_key, "").strip().lower() not in existing]

        final = LEADS_DIR / f"propwire_leads_{datetime.now().strftime('%Y-%m-%d')}.csv"
        with open(final, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(new_rows)
        log(f"✅ {len(new_rows)} new leads saved → {final}")
        log(f"   ({len(rows) - len(new_rows)} dupes skipped)")
    else:
        log("❌ No leads saved — export failed")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--test", action="store_true", help="Login test only, no scraping")
    p.add_argument("--headless", action="store_true", help="Run headless (may trigger DataDome)")
    args = p.parse_args()
    asyncio.run(run(headless=args.headless, test_only=args.test))


if __name__ == "__main__":
    main()
