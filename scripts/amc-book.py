#!/usr/bin/env python3
"""
amc-book.py — Buy AMC movie tickets using a saved browser session.

Usage:
    python3 amc-book.py --movie "Project Hail Mary" --date "Saturday" --time "evening" --seats 2 --format IMAX
    python3 amc-book.py --movie "Project Hail Mary" --date "2026-03-21" --time "7:00 PM" --seats 2

Arguments:
    --movie     Movie title (required)
    --date      Date: YYYY-MM-DD, "Saturday", "March 21", etc.
    --time      Preferred time: "7:00 PM", "evening" (after 5pm), "afternoon" (12-5pm), "morning"
    --seats     Number of seats (default: 2)
    --format    IMAX, Dolby, standard, PLF (default: standard; IMAX if requested)
    --theater   Theater name (default: AMC Monmouth Mall 15)
    --dry-run   Find showtime but don't complete purchase
    --headless  Run browser headless (default: visible)
"""

import argparse
import sys
import re
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

PROFILE_DIR = Path.home() / ".playwright-profiles" / "amc"
STATE_FILE = PROFILE_DIR / "state.json"
DEFAULT_THEATER = "AMC Monmouth Mall 15"
DEFAULT_THEATER_ID = "1176"  # AMC Monmouth Mall 15, Eatontown NJ
AMC_BASE = "https://www.amctheatres.com"


def parse_date(date_str: str) -> str:
    date_str = date_str.strip()
    today = datetime.now()

    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return date_str

    days = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
    lower = date_str.lower().replace("this ","").replace("next ","")
    if lower in days:
        target_dow = days.index(lower)
        current_dow = today.weekday()
        diff = (target_dow - current_dow) % 7
        if diff == 0:
            diff = 7
        target = today + timedelta(days=diff)
        return target.strftime("%Y-%m-%d")

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

    raise ValueError(f"Cannot parse date: {date_str}")


def parse_time_preference(time_str: str):
    """
    Returns (target_minutes, is_fuzzy, label).
    Fuzzy times: 'morning', 'afternoon', 'evening', 'night'.
    """
    time_str = time_str.strip().lower()

    # Fuzzy
    if time_str in ("morning", "am"):
        return (9 * 60, True, "morning (before noon)")
    if time_str in ("afternoon", "matinee"):
        return (14 * 60, True, "afternoon (12-5pm)")
    if time_str in ("evening", "night", "pm"):
        return (19 * 60, True, "evening (after 5pm)")

    # Specific time
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

    # Default: evening
    return (19 * 60, True, "evening")


def check_session_valid() -> bool:
    if not STATE_FILE.exists():
        print(f"❌ No saved session at {STATE_FILE}")
        print(f"   Run: python3 save-sessions.py amc")
        return False
    with open(STATE_FILE) as f:
        state = json.load(f)
    cookies = state.get("cookies", [])
    amc_cookies = [c for c in cookies if "amctheatres.com" in c.get("domain", "")]
    if not amc_cookies:
        print(f"⚠️  No AMC cookies found. Re-run save-sessions.py amc")
        return False
    print(f"✅ Session loaded: {len(amc_cookies)} AMC cookies")
    return True


def book_amc(movie: str, date: str, time_str: str, seats: int,
             format_pref: str, theater: str, dry_run: bool, headless: bool):

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

    if not check_session_valid():
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=200)
        context = browser.new_context(
            storage_state=str(STATE_FILE),
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        # Verify login
        print("\n🔐 Verifying AMC login...")
        page.goto(AMC_BASE, wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)

        content = page.content().lower()
        if "sign in" in content and "sign out" not in content and "my account" not in content:
            print("❌ Not logged in to AMC. Run: python3 save-sessions.py amc")
            browser.close()
            sys.exit(1)
        print("✅ Logged in to AMC")

        # Search for movie
        print(f"\n🔍 Searching for '{movie}'...")

        # AMC movie search
        search_url = f"{AMC_BASE}/movies/search?q={movie.replace(' ', '+')}"
        page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)

        # Find movie in results
        movie_links = page.query_selector_all(
            '[data-testid="movie-title"], '
            '[class*="movie-title"], '
            'h2[class*="title"], '
            '.movie-card h2, '
            'a[href*="/movies/"]'
        )

        target_movie = None
        for link in movie_links:
            text = link.inner_text().lower()
            if movie.lower() in text or any(word in text for word in movie.lower().split() if len(word) > 3):
                target_movie = link
                print(f"   ✅ Found: {link.inner_text().strip()}")
                break

        if not target_movie and movie_links:
            target_movie = movie_links[0]
            print(f"   Using first result: {movie_links[0].inner_text().strip()}")

        if not target_movie:
            print(f"❌ Movie '{movie}' not found on AMC")
            browser.close()
            sys.exit(1)

        target_movie.click()
        time.sleep(2)

        # We're on the movie page — find showtimes
        print(f"\n📅 Looking for showtimes on {date_display}...")

        # Try navigating to showtimes section
        # AMC URL pattern: /movies/{slug}/showtimes/{date}/{theater-id}
        current_url = page.url
        movie_slug = re.search(r"/movies/([^/]+)", current_url)
        if movie_slug:
            slug = movie_slug.group(1)
            showtime_url = (
                f"{AMC_BASE}/movies/{slug}/showtimes/{date_norm}/"
                f"{DEFAULT_THEATER_ID}/all-screenings"
            )
            print(f"   Navigating to showtimes: {showtime_url}")
            page.goto(showtime_url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

        # Look for showtime buttons
        showtimes = page.query_selector_all(
            '[data-testid="showtime-button"], '
            '[class*="showtime-button"], '
            'button[data-showtime], '
            '[class*="Showtime"], '
            'a[href*="/showtimes/"]'
        )

        print(f"   Found {len(showtimes)} showtime(s)")

        if not showtimes:
            print(f"❌ No showtimes found for {movie} on {date_norm}")
            print(f"   Try checking amctheatres.com directly")
            browser.close()
            sys.exit(1)

        # Filter by format preference if specified
        format_filter = format_pref.lower()
        filtered = []
        for st in showtimes:
            text = st.inner_text().lower()
            attr = st.get_attribute("data-format") or ""
            if format_filter in ("imax",) and ("imax" in text or "imax" in attr):
                filtered.append(st)
            elif format_filter in ("dolby",) and ("dolby" in text or "dolby" in attr):
                filtered.append(st)
            elif format_filter in ("standard", "regular") and not any(x in text for x in ["imax", "dolby", "plf", "prime"]):
                filtered.append(st)
            else:
                filtered.append(st)

        if not filtered:
            filtered = showtimes

        # Find closest to target time
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

                # For fuzzy times, apply range filters
                if is_fuzzy_time:
                    if time_label.startswith("morning") and st_minutes >= 12 * 60:
                        continue
                    if time_label.startswith("afternoon") and (st_minutes < 12 * 60 or st_minutes >= 17 * 60):
                        continue
                    if time_label.startswith("evening") and st_minutes < 17 * 60:
                        continue

                diff = abs(st_minutes - target_minutes)
                if diff < best_diff:
                    best_diff = diff
                    best_showtime = st
                    best_text = text

        if not best_showtime:
            # Fall back to first showtime
            best_showtime = filtered[0]
            best_text = filtered[0].inner_text().strip()

        print(f"   Selected showtime: {best_text}")

        if dry_run:
            print(f"\n✅ DRY RUN — Would book: {movie} | {best_text} | {seats} seat(s)")
            print(f"   Format: {format_pref} | Theater: {theater}")
            browser.close()
            return

        # Click showtime
        print(f"\n🎟️  Selecting showtime: {best_text}...")
        best_showtime.click()
        time.sleep(2)

        # Select seats
        print(f"   Selecting {seats} seat(s)...")

        # AMC seat selection page
        # Try to auto-select seats (best available)
        try:
            best_avail_btn = page.query_selector(
                'button:has-text("Best Available"), '
                '[data-testid="best-available"], '
                'button[class*="best-available"]'
            )
            if best_avail_btn:
                best_avail_btn.click()
                time.sleep(1)

            # Set quantity
            qty_input = page.query_selector('input[type="number"], [data-testid="ticket-quantity"]')
            if qty_input:
                qty_input.fill(str(seats))
                time.sleep(1)
            else:
                # Click + button to add seats
                add_btn = page.query_selector('button[aria-label="Add"], button:has-text("+")')
                if add_btn:
                    for _ in range(seats - 1):  # usually starts at 1
                        add_btn.click()
                        time.sleep(0.5)

        except Exception as e:
            print(f"   Note: Seat selection automation: {e}")

        # Proceed to checkout
        try:
            checkout_btn = page.wait_for_selector(
                'button:has-text("Continue"), '
                'button:has-text("Checkout"), '
                'button:has-text("Purchase"), '
                'button:has-text("Buy Tickets"), '
                'button:has-text("Proceed")',
                timeout=10000
            )
            print(f"   Found checkout button...")
            checkout_btn.click()
            time.sleep(3)

            # Final confirmation
            confirm_btn = page.query_selector(
                'button:has-text("Complete Purchase"), '
                'button:has-text("Place Order"), '
                'button:has-text("Confirm")'
            )
            if confirm_btn:
                confirm_btn.click()
                time.sleep(3)

                # Check success
                success = page.query_selector(
                    '[class*="confirmation"], '
                    'h1:has-text("confirmed"), '
                    'h1:has-text("enjoy"), '
                    '[data-testid="confirmation"]'
                )
                if success:
                    print(f"\n🎉 TICKETS PURCHASED!")
                    print(f"   {movie} | {best_text} | {seats} seat(s)")
                    print(f"   Theater: {theater}")
                    print(f"   Format: {format_pref}")
                else:
                    print(f"\n⚠️  Purchase submitted — check your AMC app/email for confirmation")
            else:
                print(f"\n⚠️  Purchase page open — complete manually in browser window")
                input("Press ENTER when done...")

        except PlaywrightTimeout:
            print(f"⚠️  Checkout flow timed out. Check browser window.")
            input("Press ENTER when done reviewing...")

        browser.close()


def main():
    parser = argparse.ArgumentParser(
        description="Buy AMC movie tickets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--movie", "-m", required=True, help="Movie title")
    parser.add_argument("--date", "-d", default="today", help="Date (YYYY-MM-DD, Saturday, March 21)")
    parser.add_argument("--time", "-t", default="evening", help="Preferred time (7pm, evening, afternoon)")
    parser.add_argument("--seats", "-s", type=int, default=2, help="Number of seats")
    parser.add_argument("--format", "-f", default="standard", help="Format: IMAX, Dolby, standard")
    parser.add_argument("--theater", default=DEFAULT_THEATER, help="Theater name")
    parser.add_argument("--dry-run", action="store_true", help="Find showtime but don't purchase")
    parser.add_argument("--headless", action="store_true", help="Run browser headless")

    args = parser.parse_args()

    book_amc(
        movie=args.movie,
        date=args.date,
        time_str=args.time,
        seats=args.seats,
        format_pref=args.format,
        theater=args.theater,
        dry_run=args.dry_run,
        headless=args.headless,
    )


if __name__ == "__main__":
    main()
