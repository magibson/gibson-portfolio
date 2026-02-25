#!/usr/bin/env python3
"""
amc-book.py — Buy AMC movie tickets, list orders, and cancel/refund.

Usage:
    # List upcoming orders/tickets
    python3 amc-book.py --list

    # Cancel/refund a ticket order
    python3 amc-book.py --cancel ORDER_ID

    # Buy new tickets
    python3 amc-book.py --movie "Project Hail Mary" --date "Saturday" --time "evening" --seats 2

Authentication:
    Uses persistent Chromium profile at ~/.playwright-profiles/amc/
    AMC uses Cloudflare — headless mode often blocked, non-headless used by default.
    
    If logged out, add credentials to ~/clawd/.env:
        AMC_EMAIL=your@email.com
        AMC_PASSWORD=yourpassword
    Or re-login: python3 save-sessions.py amc
    
Notes:
    - AMC has no public API; all operations use browser automation
    - Refunds are only available before showtime for certain ticket types
    - A-List and Stubs members have different refund policies
"""

import argparse
import sys
import os
import re
import time
import json
import urllib.parse
from pathlib import Path
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

PROFILE_DIR = Path.home() / ".playwright-profiles" / "amc"
DEFAULT_THEATER = "AMC Monmouth Mall 15"
DEFAULT_THEATER_ID = "1176"
AMC_BASE = "https://www.amctheatres.com"
ENV_FILE = Path.home() / "clawd" / ".env"


def load_env() -> dict:
    env = {}
    if ENV_FILE.exists():
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    env.update(os.environ)
    return env


# ─── Date/Time Parsing ─────────────────────────────────────────────────────────

def parse_date(date_str: str) -> str:
    date_str = date_str.strip()
    today = datetime.now()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return date_str
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    lower = date_str.lower().replace("this ", "").replace("next ", "")
    if lower in days:
        target_dow = days.index(lower)
        diff = (target_dow - today.weekday()) % 7 or 7
        return (today + timedelta(days=diff)).strftime("%Y-%m-%d")
    for fmt in ["%B %d %Y", "%b %d %Y", "%B %d", "%b %d"]:
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.year == 1900:
                dt = dt.replace(year=today.year)
                if dt < today:
                    dt = dt.replace(year=today.year + 1)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {date_str!r}")


def parse_time_preference(time_str: str):
    """Returns (target_minutes, is_fuzzy, label)."""
    time_str = time_str.strip().lower()
    if time_str in ("morning", "am"):
        return (9 * 60, True, "morning (before noon)")
    if time_str in ("afternoon", "matinee"):
        return (14 * 60, True, "afternoon (12-5pm)")
    if time_str in ("evening", "night", "pm"):
        return (19 * 60, True, "evening (after 5pm)")
    upper = time_str.upper()
    if re.match(r"^\d{1,2}:\d{2}$", upper):
        h, m = upper.split(":")
        return (int(h) * 60 + int(m), False, upper)
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(AM|PM)?$", upper)
    if m:
        h = int(m.group(1))
        mins = int(m.group(2) or 0)
        meridiem = m.group(3) or ""
        if meridiem == "PM" and h != 12:
            h += 12
        if meridiem == "AM" and h == 12:
            h = 0
        return (h * 60 + mins, False, f"{h:02d}:{mins:02d}")
    return (19 * 60, True, "evening")


# ─── Session Helpers ───────────────────────────────────────────────────────────

def get_amc_page(headless=False):
    """
    Launch AMC persistent context, check login, auto-login if needed.
    Returns (context, page, logged_in).
    """
    env = load_env()
    email = env.get("AMC_EMAIL", "")
    password = env.get("AMC_PASSWORD", "")

    p = sync_playwright().start()
    ctx = p.chromium.launch_persistent_context(
        str(PROFILE_DIR),
        headless=headless,
        args=[
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
        ],
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        slow_mo=300,
    )
    page = ctx.new_page()

    try:
        page.goto(AMC_BASE, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)
    except Exception:
        pass

    header_text = ""
    try:
        header_text = page.inner_text("header")
    except Exception:
        pass

    logged_in = (
        "sign out" in header_text.lower()
        or "my account" in header_text.lower()
        or "stubs" in header_text.lower()
    )

    if not logged_in and email and password:
        print(f"🔐 Auto-logging in to AMC ({email})...")
        try:
            _do_amc_login(page, email, password)
            time.sleep(3)
            header_text = page.inner_text("header") if page.query_selector("header") else ""
            logged_in = "sign out" in header_text.lower() or "my account" in header_text.lower()
            if logged_in:
                print("✅ Auto-login successful")
        except Exception as e:
            print(f"⚠️  Auto-login failed: {e}")

    return p, ctx, page, logged_in


def _do_amc_login(page, email: str, password: str):
    """
    Perform AMC login.
    AMC uses a modal sign-in triggered by clicking "Sign In" on the main page.
    There's no standalone /account/signin page (SPA).
    """
    # Make sure we're on the main page
    if "amctheatres.com" not in page.url or "movie" in page.url:
        page.goto(AMC_BASE, wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)

    # Click the Sign In button (opens modal)
    sign_in_btn = page.query_selector(
        "a:has-text('Sign In'), button:has-text('Sign In'), "
        "[data-testid*='signin'], [aria-label*='sign in' i]"
    )
    if sign_in_btn:
        sign_in_btn.click()
        time.sleep(2)

    # Wait for email input to appear
    try:
        email_input = page.wait_for_selector(
            "input[type='email'], input[name='email'], input[placeholder*='email' i]",
            timeout=10000,
        )
        email_input.fill(email)
        time.sleep(0.5)
    except Exception as e:
        print(f"   ⚠️  Could not find email input: {e}")
        return

    # Look for Continue button first (some flows separate email + password)
    continue_btn = page.query_selector(
        "button:has-text('Continue'), button:has-text('Next'), "
        "button[type='submit']:not([aria-label*='password' i])"
    )
    if continue_btn and "Sign In" not in (continue_btn.inner_text() or ""):
        continue_btn.click()
        time.sleep(2)

    # Enter password
    pwd_input = page.query_selector("input[type='password'], input[name='password']")
    if pwd_input:
        pwd_input.fill(password)
        time.sleep(0.5)

        submit_btn = page.query_selector(
            "button[type='submit'], button:has-text('Sign In'), "
            "button:has-text('Log In'), button:has-text('Continue')"
        )
        if submit_btn:
            submit_btn.click()
            time.sleep(3)

    # Save updated session
    try:
        state = page.context.storage_state()
        state_file = PROFILE_DIR / "state.json"
        with open(state_file, "w") as f:
            json.dump(state, f)
    except Exception:
        pass


# ─── --list ────────────────────────────────────────────────────────────────────

def cmd_list(args) -> list:
    """List upcoming AMC ticket orders."""
    print("🔄 Loading AMC session...")
    p, ctx, page, logged_in = get_amc_page(headless=False)
    results = []

    try:
        if not logged_in:
            print("❌ Not logged in to AMC.")
            env = load_env()
            if not env.get("AMC_EMAIL"):
                print("   Add to ~/clawd/.env: AMC_EMAIL and AMC_PASSWORD")
            print("   Or run: python3 save-sessions.py amc")
            return []

        print("📋 Fetching upcoming orders...")

        # Navigate to order history (AMC SPA - wait for content to load)
        order_pages = [
            f"{AMC_BASE}/account/order-history",
            f"{AMC_BASE}/account/tickets",
            f"{AMC_BASE}/account/orders",
            f"{AMC_BASE}/account/purchase-history",
        ]

        for url in order_pages:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(5)  # AMC SPA needs time to render
            content = page.content().lower()
            title = page.title().lower()
            if "404" not in content and "went wrong" not in content and "error 404" not in content:
                print(f"   Using URL: {url}")
                break

        # Look for order items
        print("🔍 Scanning orders...")
        order_items = page.query_selector_all(
            "[class*='order-item'], [class*='OrderItem'], [class*='purchase'], "
            "[class*='ticket'], [data-testid*='order'], [class*='booking']"
        )

        if not order_items:
            # Try getting all text and parsing
            page_text = page.inner_text("body")[:5000]

            # Look for upcoming reservations section
            if "upcoming" in page_text.lower() or "order" in page_text.lower():
                print("   Found page content, parsing...")
                # Try to find movie/date/order info
                lines = [l.strip() for l in page_text.split("\n") if l.strip()]

                # Find order numbers
                order_matches = re.findall(r"(?:order|confirmation)[:\s#]*([A-Z0-9]{6,})", page_text, re.IGNORECASE)
                for oid in order_matches[:10]:
                    results.append({
                        "id": oid,
                        "service": "amc",
                        "venue": DEFAULT_THEATER,
                        "raw": True,
                    })
            else:
                print("\n   No upcoming orders found (or need to scroll)")

        else:
            print(f"   Found {len(order_items)} order(s)")
            for item in order_items:
                text = item.inner_text()

                # Extract order ID
                order_id = None
                id_match = re.search(r"(?:order|#|id)[:\s]*([A-Z0-9]{6,})", text, re.IGNORECASE)
                if id_match:
                    order_id = id_match.group(1)

                # Extract movie name (usually first bold/large text)
                movie = "Unknown Movie"
                movie_el = item.query_selector("h2, h3, [class*='title'], [class*='movie-name']")
                if movie_el:
                    movie = movie_el.inner_text().strip()

                # Extract date
                date_match = re.search(
                    r"(\w+,?\s+\w+\s+\d{1,2},?\s+\d{4}|\d{1,2}/\d{1,2}/\d{4})", text
                )
                date_str = date_match.group(1) if date_match else ""

                # Extract time
                time_match = re.search(r"(\d{1,2}:\d{2}\s*[AP]M)", text, re.IGNORECASE)
                time_str = time_match.group(1) if time_match else ""

                can_cancel = "cancel" in text.lower() or "refund" in text.lower()

                result = {
                    "id": order_id or "unknown",
                    "service": "amc",
                    "movie": movie,
                    "date": date_str,
                    "time": time_str,
                    "can_cancel": can_cancel,
                }
                results.append(result)

        if results:
            print(f"\n{'─'*55}")
            print(f"  AMC ORDERS ({len(results)} upcoming)")
            print(f"{'─'*55}")
            for r in results:
                print(f"\n  [{r.get('id', 'N/A')}] {r.get('movie', r.get('venue', 'AMC'))}")
                if r.get("date"):
                    print(f"       {r['date']} {r.get('time', '')}")
                if r.get("raw"):
                    print(f"       (partial data — check AMC app for details)")
            print(f"\n{'─'*55}")
        else:
            print("\n✅ No upcoming AMC orders found.")
            print(f"   Check manually: {AMC_BASE}/account/orders")

    finally:
        ctx.close()
        p.stop()

    return results


# ─── --cancel ──────────────────────────────────────────────────────────────────

def cmd_cancel(order_id: str):
    """Cancel/refund an AMC order."""
    print("🔄 Loading AMC session...")
    p, ctx, page, logged_in = get_amc_page(headless=False)

    try:
        if not logged_in:
            print("❌ Not logged in to AMC.")
            print("   Run: python3 save-sessions.py amc")
            return

        print(f"\n⚠️  CANCEL AMC ORDER")
        print(f"   Order ID: {order_id}")
        print()
        confirm = input("   Type 'yes' to proceed with cancellation: ").strip().lower()
        if confirm != "yes":
            print("   Cancelled — no changes made.")
            return

        print(f"\n🗑️  Opening order cancellation page...")

        # Try order-specific cancellation URL patterns
        cancel_urls = [
            f"{AMC_BASE}/account/orders/{order_id}/cancel",
            f"{AMC_BASE}/account/orders/{order_id}",
            f"{AMC_BASE}/order/refund/{order_id}",
            f"{AMC_BASE}/account/orders",
        ]

        for url in cancel_urls:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)
            if "404" not in page.content().lower():
                break

        # Look for cancel/refund button
        cancel_btn = page.query_selector(
            "button:has-text('Cancel'), button:has-text('Refund'), "
            "a:has-text('Cancel'), a:has-text('Refund'), "
            "[data-test*='cancel'], [data-testid*='cancel']"
        )

        if cancel_btn:
            cancel_btn.click()
            time.sleep(2)

            # Confirm cancellation modal
            confirm_btn = page.query_selector(
                "button:has-text('Confirm'), button:has-text('Yes'), "
                "button:has-text('Submit'), button:has-text('Proceed')"
            )
            if confirm_btn:
                confirm_btn.click()
                time.sleep(3)
                print(f"✅ Cancellation submitted for order {order_id}")
                print("   Check your email for confirmation.")
            else:
                print(f"⚠️  Confirm button not found — please confirm in browser window")
                input("Press ENTER when done...")
        else:
            print(f"⚠️  Cancel button not found on page.")
            print(f"   Current URL: {page.url}")
            print(f"   Browser is open — please cancel manually.")
            print(f"   Or call AMC: 1-888-AMC-4FUN")
            input("Press ENTER when done...")

    finally:
        ctx.close()
        p.stop()


# ─── --modify (not supported) ──────────────────────────────────────────────────

def cmd_modify(order_id: str, new_date: str, new_time: str, new_party: int):
    """
    AMC does not support modifying existing orders.
    The recommended approach is: cancel + rebook.
    """
    print("⚠️  AMC does not support modifying existing ticket orders.")
    print("   To change showtimes or seats:")
    print("   1. Cancel the original order:  python3 amc-book.py --cancel ORDER_ID")
    print("   2. Book new tickets:           python3 amc-book.py --movie 'Title' --date 'Date' ...")
    print()
    print(f"   Order {order_id} — check eligibility at {AMC_BASE}/account/orders")


# ─── Book New ──────────────────────────────────────────────────────────────────

def book_amc(movie: str, date: str, time_str: str, seats: int,
             format_pref: str, theater: str, dry_run: bool, headless: bool):
    """Book AMC movie tickets via browser automation."""

    date_norm = parse_date(date)
    target_minutes, is_fuzzy_time, time_label = parse_time_preference(time_str)
    dt = datetime.strptime(date_norm, "%Y-%m-%d")
    date_display = dt.strftime("%A, %B %d %Y")

    print(f"\n🎬 AMC Ticket Booking")
    print(f"   Movie    : {movie}")
    print(f"   Date     : {date_norm} ({date_display})")
    print(f"   Time     : {time_label}")
    print(f"   Seats    : {seats}")
    print(f"   Format   : {format_pref}")
    print(f"   Theater  : {theater}")
    print(f"   Dry run  : {dry_run}")

    p, ctx, page, logged_in = get_amc_page(headless=headless)

    try:
        if not logged_in:
            print("❌ Not logged in to AMC. Run: python3 save-sessions.py amc")
            return

        print("✅ Logged in to AMC")
        print(f"\n🔍 Searching for '{movie}'...")

        search_url = f"{AMC_BASE}/movies/search?q={urllib.parse.quote(movie)}"
        page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)

        movie_links = page.query_selector_all(
            "[data-testid='movie-title'], [class*='movie-title'], "
            "h2[class*='title'], .movie-card h2, a[href*='/movies/']"
        )

        target_movie = None
        for link in movie_links:
            text = link.inner_text().lower()
            if movie.lower() in text or any(
                word in text for word in movie.lower().split() if len(word) > 3
            ):
                target_movie = link
                print(f"   ✅ Found: {link.inner_text().strip()}")
                break

        if not target_movie and movie_links:
            target_movie = movie_links[0]
            print(f"   Using first result: {movie_links[0].inner_text().strip()}")

        if not target_movie:
            print(f"❌ Movie '{movie}' not found on AMC")
            return

        target_movie.click()
        time.sleep(2)

        print(f"\n📅 Finding showtimes on {date_display}...")
        current_url = page.url
        movie_slug = re.search(r"/movies/([^/]+)", current_url)
        if movie_slug:
            slug = movie_slug.group(1)
            showtime_url = (
                f"{AMC_BASE}/movies/{slug}/showtimes/{date_norm}/"
                f"{DEFAULT_THEATER_ID}/all-screenings"
            )
            page.goto(showtime_url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

        showtimes = page.query_selector_all(
            "[data-testid='showtime-button'], [class*='showtime-button'], "
            "button[data-showtime], [class*='Showtime'], a[href*='/showtimes/']"
        )
        print(f"   Found {len(showtimes)} showtime(s)")

        if not showtimes:
            print(f"❌ No showtimes found for {movie} on {date_norm}")
            print(f"   Check: {AMC_BASE}/movies")
            return

        # Filter by format
        format_filter = format_pref.lower()
        filtered = []
        for st in showtimes:
            text = st.inner_text().lower()
            if format_filter == "imax" and "imax" not in text:
                continue
            elif format_filter == "dolby" and "dolby" not in text:
                continue
            filtered.append(st)

        if not filtered:
            filtered = showtimes

        # Find best showtime
        best_showtime = None
        best_diff = float("inf")
        best_text = ""

        for st in filtered:
            text = st.inner_text().strip()
            m = re.search(r"(\d{1,2}):?(\d{2})?\s*(AM|PM)?", text, re.IGNORECASE)
            if m:
                h = int(m.group(1))
                mins = int(m.group(2) or 0)
                meridiem = (m.group(3) or "").upper()
                if meridiem == "PM" and h != 12:
                    h += 12
                elif meridiem == "AM" and h == 12:
                    h = 0
                st_minutes = h * 60 + mins

                if is_fuzzy_time:
                    if "morning" in time_label and st_minutes >= 12 * 60:
                        continue
                    if "afternoon" in time_label and (st_minutes < 12 * 60 or st_minutes >= 17 * 60):
                        continue
                    if "evening" in time_label and st_minutes < 17 * 60:
                        continue

                diff = abs(st_minutes - target_minutes)
                if diff < best_diff:
                    best_diff = diff
                    best_showtime = st
                    best_text = text

        if not best_showtime:
            best_showtime = filtered[0]
            best_text = filtered[0].inner_text().strip()

        print(f"   Selected: {best_text}")

        if dry_run:
            print(f"\n✅ DRY RUN — Would book: {movie} | {best_text} | {seats} seat(s)")
            return

        print(f"\n🎟️  Selecting showtime: {best_text}...")
        best_showtime.click()
        time.sleep(2)

        # Seat selection
        print(f"   Selecting {seats} seat(s)...")
        try:
            best_avail_btn = page.query_selector(
                "button:has-text('Best Available'), [data-testid='best-available']"
            )
            if best_avail_btn:
                best_avail_btn.click()
                time.sleep(1)

            # Try to set seat count
            add_btn = page.query_selector("button[aria-label='Add'], button:has-text('+')")
            if add_btn:
                for _ in range(seats - 1):
                    add_btn.click()
                    time.sleep(0.3)
        except Exception as e:
            print(f"   Note: Seat automation: {e}")

        # Checkout
        try:
            checkout_btn = page.wait_for_selector(
                "button:has-text('Continue'), button:has-text('Checkout'), "
                "button:has-text('Purchase'), button:has-text('Buy Tickets')",
                timeout=10000,
            )
            print(f"   Proceeding to checkout...")
            checkout_btn.click()
            time.sleep(3)

            confirm_btn = page.query_selector(
                "button:has-text('Complete Purchase'), button:has-text('Place Order'), "
                "button:has-text('Confirm')"
            )
            if confirm_btn:
                confirm_btn.click()
                time.sleep(3)

                success = page.query_selector(
                    "[class*='confirmation'], h1:has-text('confirmed'), "
                    "h1:has-text('enjoy'), [data-testid='confirmation']"
                )
                if success:
                    print(f"\n🎉 TICKETS PURCHASED!")
                    print(f"   {movie} | {best_text} | {seats} seat(s)")
                    print(f"   Theater: {theater}")
                else:
                    print(f"\n⚠️  Purchase submitted — check AMC app/email")
            else:
                print(f"\n⚠️  Purchase page open — complete manually in browser")
                input("Press ENTER when done...")

        except PlaywrightTimeout:
            print(f"⚠️  Checkout flow timed out.")
            input("Press ENTER when done reviewing...")

    finally:
        ctx.close()
        p.stop()


# ─── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="AMC — buy tickets, list orders, and cancel",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--list", action="store_true", help="List upcoming orders")
    mode.add_argument("--cancel", metavar="ID", help="Cancel order by ID")
    mode.add_argument("--modify", metavar="ID", help="Modify order (shows instructions)")
    mode.add_argument("--movie", "-m", metavar="TITLE", help="Buy tickets for a movie")

    parser.add_argument("--date", "-d", default="today", help="Date")
    parser.add_argument("--time", "-t", default="evening", help="Time preference")
    parser.add_argument("--seats", "-s", type=int, default=2, help="Number of seats")
    parser.add_argument("--format", "-f", default="standard", help="Format (IMAX, Dolby, standard)")
    parser.add_argument("--theater", default=DEFAULT_THEATER, help="Theater name")
    parser.add_argument("--party", "-p", type=int, default=2, help="Party size (alias for --seats)")
    parser.add_argument("--dry-run", action="store_true", help="Find showtime but don't purchase")
    parser.add_argument("--headless", action="store_true", help="Run headless (may be blocked)")
    parser.add_argument("--json", action="store_true", help="Output JSON")

    args = parser.parse_args()

    if args.list:
        results = cmd_list(args)
        if args.json:
            print(json.dumps(results))
        return

    if args.cancel:
        cmd_cancel(args.cancel)
        return

    if args.modify:
        cmd_modify(
            order_id=args.modify,
            new_date=args.date,
            new_time=args.time,
            new_party=args.party or args.seats,
        )
        return

    if args.movie:
        book_amc(
            movie=args.movie,
            date=args.date,
            time_str=args.time,
            seats=args.seats or args.party,
            format_pref=args.format,
            theater=args.theater,
            dry_run=args.dry_run,
            headless=args.headless,
        )
        return

    parser.print_help()


if __name__ == "__main__":
    main()
