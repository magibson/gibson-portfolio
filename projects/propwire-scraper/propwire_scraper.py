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

        # ── Price filter — SKIPPED, filter locally after download ────────
        # Propwire's React price input is unreliable via automation.
        # Export all Monmouth County leads and filter by Est. Value >= $700k in post-processing.
        log("Price filter: skipping (will filter locally post-download)")

        # ── Date filter — SKIPPED, filter locally after download ─────────
        # Will filter by sale date post-download in Python.
        log("Date filter: skipping (will filter locally post-download)")

        if False:  # date filter disabled — filtering locally post-download
            pass

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
        # Ensure no modal/drawer is open before interacting with results
        await delay(2, 3)

        # Select-all: use Playwright dispatchEvent to trigger React's onChange
        # The checkbox at top ~210px (results header) is the select-all
        try:
            # Use Playwright locator with force=True to bypass span interception
            # Filter to viewport-visible checkboxes only (not the off-screen ones)
            all_cbs = page.locator("input[type='checkbox']")
            cnt = await all_cbs.count()
            select_all_cb = None
            for i in range(min(cnt, 5)):  # check first 5 only
                cb = all_cbs.nth(i)
                try:
                    box = await cb.bounding_box()
                    if box and box["y"] > 150 and box["y"] < 270:
                        select_all_cb = cb
                        log(f"Select-all checkbox found at y={box['y']:.0f} (index {i})")
                        break
                except:
                    pass

            if select_all_cb:
                # Use dispatchEvent to trigger React's synthetic events
                await select_all_cb.dispatch_event("click")
                await delay(2, 3)
                await snap(page, "selected")
                log("Select-all dispatched")
            else:
                log("⚠️ Could not locate select-all checkbox by position")
        except Exception as e:
            log(f"⚠️ Select-all: {e}")

        # Check how many items are in cart
        cart_count = await page.evaluate("""() => {
            // The cart button is btn--selected with a number
            const btns = Array.from(document.querySelectorAll("button.btn--selected, button[class*='btn--selected']"));
            for (const btn of btns) {
                const t = btn.innerText?.trim();
                if (t && /^\\d+$/.test(t)) return parseInt(t);
            }
            return 0;
        }""")
        log(f"Cart count after select-all: {cart_count}")

        if cart_count == 0:
            log("⚠️ Cart still 0 after select-all — trying again with direct checkbox click")
            # Try Playwright force-click with no checks
            try:
                cb = page.locator("input[type='checkbox']").nth(1)
                await cb.click(force=True)
                await delay(2, 3)
                cart_count = await page.evaluate("""() => {
                    const btns = Array.from(document.querySelectorAll("button.btn--selected, button[class*='btn--selected']"));
                    for (const btn of btns) {
                        const t = btn.innerText?.trim();
                        if (t && /^\\d+$/.test(t)) return parseInt(t);
                    }
                    return 0;
                }""")
                log(f"Cart after retry: {cart_count}")
            except Exception as e:
                log(f"⚠️ Select-all retry: {e}")
            await snap(page, "cart_retry")
        
        # Click the cart button to open export options
        raw_file = None
        try:
            cart_btn = page.locator("button.btn--selected").first
            if await cart_btn.count() > 0:
                log("Clicking cart/export button...")
                await cart_btn.click()
                await delay(2, 3)
                await snap(page, "cart_open")
                
                # Look for export/download option in the popup
                # Click "Download" button to open the dropdown
                dl_btn = page.locator("button:has-text('Download')").first
                if await dl_btn.count() > 0:
                    log("Opening Download dropdown...")
                    await dl_btn.dispatch_event("click")
                    await delay(1.5, 2)
                    await snap(page, "download_dropdown")

                    # Click "Download Only" from dropdown
                    for opt_sel in [
                        "text='Download Only'",
                        "li:has-text('Download Only')",
                        "[role='menuitem']:has-text('Download Only')",
                    ]:
                        try:
                            opt = page.locator(opt_sel).first
                            if await opt.count() > 0:
                                log(f"Clicking 'Download Only' via {opt_sel}")
                                await opt.click(force=True)
                                await delay(1.5, 2.5)
                                await snap(page, "confirm_dialog")

                                # Step 1: "Are you sure?" confirmation dialog
                                confirm = page.locator("button:has-text('Yes, Download Only'), button:has-text('Yes, download only')").first
                                if await confirm.count() > 0:
                                    log("Clicking: Yes, Download Only")
                                    await confirm.click(force=True)
                                    await delay(1.5, 2.5)
                                    await snap(page, "data_select_dialog")

                                # Step 2: "What Data Would You Like to Download?" dialog
                                # Select extra data category checkboxes before downloading:
                                # We want: Last Sale, Mortgage/Loan, Equity
                                await delay(1.5, 2.5)
                                await snap(page, "data_categories")

                                # Find all checkboxes in the dialog and check which are unchecked
                                # Categories are labeled — we want any containing these keywords
                                WANTED_CATEGORIES = ["sale", "mortgage", "loan", "equity", "transfer"]
                                checked_cats = await page.evaluate("""(wanted) => {
                                    const results = [];
                                    // Look in any dialog/modal that's open
                                    const containers = [
                                        document.querySelector('[role="dialog"]'),
                                        document.querySelector('[class*="modal"]'),
                                        document.querySelector('[class*="download"]'),
                                        document.body
                                    ].filter(Boolean);

                                    for (const container of containers) {
                                        const labels = container.querySelectorAll('label');
                                        for (const label of labels) {
                                            const text = label.innerText?.toLowerCase() || '';
                                            const isWanted = wanted.some(w => text.includes(w));
                                            if (!isWanted) continue;

                                            // Find checkbox associated with this label
                                            let cb = label.querySelector('input[type="checkbox"]');
                                            if (!cb && label.htmlFor) {
                                                cb = document.getElementById(label.htmlFor);
                                            }
                                            if (!cb) {
                                                // Try sibling
                                                cb = label.previousElementSibling;
                                                if (!cb || cb.type !== 'checkbox') cb = label.nextElementSibling;
                                            }

                                            if (cb && cb.type === 'checkbox' && !cb.checked) {
                                                cb.click();
                                                results.push(label.innerText.trim().slice(0, 50));
                                            } else if (cb && cb.checked) {
                                                results.push('(already checked) ' + label.innerText.trim().slice(0, 50));
                                            }
                                        }
                                        if (results.length > 0) break;
                                    }
                                    return results;
                                }""", WANTED_CATEGORIES)
                                log(f"Data categories selected: {checked_cats}")
                                await delay(1, 1.5)
                                await snap(page, "categories_selected")

                                # Click "Download N Properties" button
                                # Find the "Download N Properties" button via JS (most reliable)
                                dl_btn_text = await page.evaluate("""() => {
                                    const btns = Array.from(document.querySelectorAll('button'));
                                    for (const b of btns) {
                                        const t = b.innerText?.trim();
                                        if (t && t.startsWith('Download') && /\\d/.test(t)) return t;
                                    }
                                    return null;
                                }""")
                                log(f"Download button text: {dl_btn_text}")
                                dl_props_btn = page.locator(f"button:has-text('{dl_btn_text}')").first if dl_btn_text else None
                                if not dl_props_btn or await dl_props_btn.count() == 0:
                                    dl_props_btn = page.locator("button:has-text('Download 100'), button:has-text('Download Properties'), button:has-text('Download All')").first
                                
                                if await dl_props_btn.count() > 0:
                                    log("Clicking: Download N Properties")
                                    await dl_props_btn.click(force=True)
                                    await delay(3, 5)
                                    await snap(page, "download_triggered")

                                    # The download is async — generated under "My Activity"
                                    # Dismiss the confirmation modal and go to My Activity
                                    dismiss = page.locator("button:has-text('Dismiss'), button:has-text('Go To My Activity')").first
                                    if await dismiss.count() > 0:
                                        # Navigate to My Activity
                                        go_btn = page.locator("button:has-text('Go To My Activity'), a:has-text('My Activity')").first
                                        if await go_btn.count() > 0:
                                            await go_btn.click(force=True)
                                        else:
                                            await dismiss.click(force=True)
                                            await page.goto(f"{BASE}/activity", wait_until="domcontentloaded", timeout=30000)

                                    await delay(5, 8)
                                    await snap(page, "my_activity")
                                    log("Navigated to My Activity")

                                    # Wait for download link to appear (poll up to 3 min)
                                    download_url = None
                                    for attempt in range(18):  # 18 x 10s = 3 min
                                        dl_link = await page.evaluate("""() => {
                                            // Look for CSV download links or download buttons in activity list
                                            const links = Array.from(document.querySelectorAll('a[href*=".csv"], a[href*="download"], a[download]'));
                                            if (links.length > 0) return links[0].href;
                                            // Also check buttons that trigger downloads
                                            const btns = Array.from(document.querySelectorAll('button'));
                                            for (const b of btns) {
                                                const t = b.innerText?.trim().toLowerCase();
                                                if (t.includes('download') && t.includes('csv')) return 'btn:' + t;
                                            }
                                            return null;
                                        }""")
                                        if dl_link:
                                            log(f"Download link found: {dl_link}")
                                            download_url = dl_link
                                            break
                                        log(f"Waiting for download to generate... ({attempt+1}/18)")
                                        await delay(9, 11)
                                        await page.reload(wait_until="domcontentloaded")
                                        await delay(2, 3)

                                    if download_url and not download_url.startswith("btn:"):
                                        log(f"Downloading from: {download_url}")
                                        try:
                                            async with page.expect_download(timeout=60000) as dl_info:
                                                try:
                                                    await page.goto(download_url, wait_until="commit")
                                                except Exception:
                                                    pass  # "Download is starting" is expected
                                            dl  = await dl_info.value
                                            dst = LEADS_DIR / f"propwire_raw_{datetime.now().strftime('%Y-%m-%d')}.csv"
                                            await dl.save_as(str(dst))
                                            log(f"✅ Downloaded: {dst}")
                                            raw_file = dst
                                        except Exception as e:
                                            log(f"⚠️ Download via goto: {e}")
                                            # Fallback: click the link directly on the activity page
                                            try:
                                                dl_link_el = page.locator(f"a[href='{download_url}'], a[href*='download']").first
                                                if await dl_link_el.count() > 0:
                                                    async with page.expect_download(timeout=60000) as dl_info:
                                                        await dl_link_el.click()
                                                    dl  = await dl_info.value
                                                    dst = LEADS_DIR / f"propwire_raw_{datetime.now().strftime('%Y-%m-%d')}.csv"
                                                    await dl.save_as(str(dst))
                                                    log(f"✅ Downloaded via link click: {dst}")
                                                    raw_file = dst
                                            except Exception as e2:
                                                log(f"⚠️ Download fallback: {e2}")
                                    elif download_url and download_url.startswith("btn:"):
                                        # There's a button — click it
                                        dl_btn2 = page.locator("button:has-text('Download CSV'), button:has-text('Download')").first
                                        if await dl_btn2.count() > 0:
                                            async with page.expect_download(timeout=60000) as dl_info:
                                                await dl_btn2.click(force=True)
                                            dl  = await dl_info.value
                                            dst = LEADS_DIR / f"propwire_raw_{datetime.now().strftime('%Y-%m-%d')}.csv"
                                            await dl.save_as(str(dst))
                                            log(f"✅ Downloaded via button: {dst}")
                                            raw_file = dst
                                    else:
                                        log("⚠️ Download link never appeared in My Activity")
                                        await snap(page, "activity_timeout")
                                else:
                                    log("⚠️ Could not find final Download button")
                                    await snap(page, "missing_dl_btn")
                                break
                        except Exception as e:
                            log(f"  Download Only ({opt_sel}): {e}")
                
                if not raw_file:
                    await snap(page, "export_options")
                    # Try direct download link
                    dl_link = await page.evaluate("""() => {
                        const links = Array.from(document.querySelectorAll('a[href*="export"], a[href*="download"], a[href*="csv"]'));
                        return links[0]?.href || null;
                    }""")
                    if dl_link:
                        log(f"Direct export link: {dl_link}")
                        async with page.expect_download(timeout=60000) as dl_info:
                            await page.goto(dl_link)
                        dl  = await dl_info.value
                        dst = LEADS_DIR / f"propwire_raw_{datetime.now().strftime('%Y-%m-%d')}.csv"
                        await dl.save_as(str(dst))
                        log(f"✅ Downloaded via link: {dst}")
                        raw_file = dst
        except Exception as e:
            log(f"⚠️ Cart/export: {e}")

        if not raw_file:
            log("❌ Export failed — check screenshots")
            await snap(page, "no_export")
        
        await ctx.close()

    if raw_file:
        with open(raw_file) as fh:
            reader = csv.DictReader(fh)
            rows   = list(reader)
            fields = reader.fieldnames or []

        log(f"Raw download: {len(rows)} total rows")
        log(f"Columns: {fields[:10]}")

        # ── Local price filter: Est. Value >= $700k ───────────────────
        MIN_VALUE = 700_000
        price_key = next((k for k in fields if "value" in k.lower() or "price" in k.lower()), None)
        if price_key:
            def parse_price(v):
                try:
                    return float(str(v).replace("$","").replace(",","").strip())
                except:
                    return 0
            before = len(rows)
            rows = [r for r in rows if parse_price(r.get(price_key, "0")) >= MIN_VALUE]
            log(f"Price filter (>= $700k via '{price_key}'): {before} → {len(rows)} rows")
        else:
            log("⚠️ No price/value column found — skipping price filter")

        # ── Dedup against all previously sent leads ───────────────────
        # Persistent seen-leads file: one address per line
        SEEN_FILE = LEADS_DIR / "seen_leads.txt"
        existing = set()

        # Load persistent seen list
        if SEEN_FILE.exists():
            with open(SEEN_FILE) as fh:
                for line in fh:
                    existing.add(line.strip().lower())
            log(f"Loaded {len(existing)} previously seen leads from seen_leads.txt")

        # Also scan all historical CSVs (propwire_leads, dial_ready, monmouth_*)
        for pattern in ["propwire_leads_*.csv", "dial_ready_*.csv", "monmouth_*.csv"]:
            for f in LEADS_DIR.glob(pattern):
                try:
                    with open(f) as fh:
                        for row in csv.DictReader(fh):
                            addr = (row.get("Address") or row.get("address") or
                                    row.get("Property Address") or "").strip().lower()
                            if addr:
                                existing.add(addr)
                except:
                    pass
        log(f"Total seen leads (persistent + CSV history): {len(existing)}")

        addr_key = next((k for k in fields if k.lower() == "address"), None)
        if not addr_key:
            addr_key = next((k for k in fields if "address" in k.lower()), None)
        before_dedup = len(rows)
        new_rows = [r for r in rows if not addr_key or r.get(addr_key, "").strip().lower() not in existing]
        log(f"Dedup: {before_dedup} → {len(new_rows)} new leads ({before_dedup - len(new_rows)} skipped)")

        final = LEADS_DIR / f"propwire_leads_{datetime.now().strftime('%Y-%m-%d')}.csv"
        with open(final, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(new_rows)
        log(f"✅ {len(new_rows)} leads saved → {final}")

        # Append new lead addresses to persistent seen-leads file
        if addr_key and new_rows:
            with open(SEEN_FILE, "a") as fh:
                for r in new_rows:
                    addr = r.get(addr_key, "").strip().lower()
                    if addr:
                        fh.write(addr + "\n")
            log(f"📝 {len(new_rows)} addresses appended to seen_leads.txt")
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
