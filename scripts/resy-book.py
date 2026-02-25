#!/usr/bin/env python3
"""
resy-book.py — Book a restaurant on Resy using a saved browser session.

Usage:
    python3 resy-book.py --restaurant "Via45" --date "2026-03-07" --time "19:00" --party 2
    python3 resy-book.py --restaurant "Via45" --date "Saturday" --time "7pm" --party 2 --location "Monmouth County NJ"

Arguments:
    --restaurant  Restaurant name (required)
    --date        Date: YYYY-MM-DD, "Saturday", "March 7", etc.
    --time        Time: "19:00", "7pm", "7:30 PM"
    --party       Party size (default: 2)
    --location    Location/area (default: Monmouth County NJ)
    --dry-run     Find slot but don't confirm booking
    --headless    Run browser headless (default: visible)
"""

import argparse
import sys
import re
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

PROFILE_DIR = Path.home() / ".playwright-profiles" / "resy"
STATE_FILE = PROFILE_DIR / "state.json"
DEFAULT_LOCATION = "Monmouth County, NJ"
RESY_BASE = "https://resy.com"


def parse_date(date_str: str) -> str:
    """Normalize date to YYYY-MM-DD."""
    date_str = date_str.strip()
    today = datetime.now()

    # Already in YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return date_str

    # Day of week: "Saturday", "this Saturday", "next Friday"
    days = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
    lower = date_str.lower().replace("this ","").replace("next ","")
    if lower in days:
        target_dow = days.index(lower)
        current_dow = today.weekday()
        diff = (target_dow - current_dow) % 7
        if diff == 0:
            diff = 7  # next occurrence
        target = today + timedelta(days=diff)
        return target.strftime("%Y-%m-%d")

    # "March 7", "Mar 7", "March 7 2026"
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

    # "03/07", "3/7/2026"
    for fmt in ["%m/%d/%Y", "%m/%d"]:
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.year == 1900:
                dt = dt.replace(year=today.year)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    raise ValueError(f"Cannot parse date: {date_str}")


def parse_time(time_str: str) -> str:
    """Normalize time to HH:MM (24h)."""
    time_str = time_str.strip().upper()
    # Already 24h
    if re.match(r"^\d{1,2}:\d{2}$", time_str):
        h, m = time_str.split(":")
        return f"{int(h):02d}:{m}"

    # "7pm", "7:30pm", "7:30 PM"
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(AM|PM)$", time_str)
    if m:
        h = int(m.group(1))
        mins = m.group(2) or "00"
        meridiem = m.group(3)
        if meridiem == "PM" and h != 12:
            h += 12
        if meridiem == "AM" and h == 12:
            h = 0
        return f"{h:02d}:{mins}"

    raise ValueError(f"Cannot parse time: {time_str}")


def check_session_valid() -> bool:
    """Check if saved session file exists and has cookies."""
    if not STATE_FILE.exists():
        print(f"❌ No saved session found at {STATE_FILE}")
        print(f"   Run: python3 save-sessions.py resy")
        return False
    with open(STATE_FILE) as f:
        state = json.load(f)
    cookies = state.get("cookies", [])
    resy_cookies = [c for c in cookies if "resy.com" in c.get("domain", "")]
    if not resy_cookies:
        print(f"⚠️  No Resy cookies in session. Re-run save-sessions.py resy")
        return False
    print(f"✅ Session loaded: {len(resy_cookies)} Resy cookies")
    return True


def book_resy(restaurant: str, date: str, time_str: str, party: int,
              location: str, dry_run: bool, headless: bool):

    date_norm = parse_date(date)
    time_norm = parse_time(time_str)

    print(f"\n🍽️  Resy Booking")
    print(f"   Restaurant : {restaurant}")
    print(f"   Date       : {date_norm}")
    print(f"   Time       : {time_norm}")
    print(f"   Party      : {party}")
    print(f"   Location   : {location}")
    print(f"   Dry run    : {dry_run}")

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

        # Navigate to Resy and verify login
        print("\n🔐 Verifying login...")
        page.goto(RESY_BASE, wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)

        # Check for sign-in indicators
        page_content = page.content().lower()
        if "sign in" in page_content and "log out" not in page_content and "account" not in page_content:
            print("❌ Not logged in to Resy. Run: python3 save-sessions.py resy")
            browser.close()
            sys.exit(1)
        print("✅ Logged in to Resy")

        # Search for the restaurant
        print(f"\n🔍 Searching for '{restaurant}' on Resy...")

        # Build search URL
        search_url = (
            f"{RESY_BASE}/search?"
            f"query={restaurant.replace(' ', '+')}"
            f"&location={location.replace(' ', '+').replace(',', '%2C')}"
            f"&day={date_norm}&party_size={party}"
        )
        page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)

        # Try to find restaurant in results
        print("   Scanning search results...")

        # Look for restaurant name in results
        restaurant_link = None
        try:
            # Resy search results
            results = page.query_selector_all('[data-test-id="search-result"], .VenueCard, .venue-card, [class*="VenueCard"], [class*="venue-result"]')
            print(f"   Found {len(results)} result(s)")

            for result in results:
                text = result.inner_text().lower()
                if restaurant.lower() in text:
                    restaurant_link = result
                    print(f"   ✅ Found matching restaurant")
                    break
        except Exception as e:
            print(f"   ⚠️  Selector search failed: {e}")

        # If no exact match, try clicking the first result
        if not restaurant_link:
            print(f"   Trying first available result...")
            try:
                first = page.query_selector('[data-test-id="search-result"]:first-child, .VenueCard:first-child')
                if first:
                    restaurant_link = first
            except Exception:
                pass

        if not restaurant_link:
            # Try direct venue search
            print(f"   Attempting direct venue page navigation...")
            # Resy uses slug-based URLs
            slug = restaurant.lower().replace(" ", "-").replace("'", "")
            venue_url = f"{RESY_BASE}/cities/nj/{slug}"
            page.goto(venue_url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)
            if "404" in page.title() or "not found" in page.content().lower():
                print(f"❌ Restaurant '{restaurant}' not found on Resy")
                browser.close()
                sys.exit(1)
        else:
            restaurant_link.click()
            time.sleep(2)

        # Now on the venue page — find available time slots
        print(f"\n🕐 Looking for available slots around {time_norm}...")

        # Resy uses a reservation widget
        # Set date and party size if needed
        try:
            # Look for date picker
            date_input = page.query_selector('[data-test-id="resy-date-picker"], input[type="date"], [aria-label*="date"]')
            if date_input:
                date_input.fill(date_norm)
                time.sleep(1)

            # Party size
            party_select = page.query_selector('[data-test-id="party-size-select"], select[name*="party"], [aria-label*="party"]')
            if party_select:
                party_select.select_option(str(party))
                time.sleep(1)
        except Exception as e:
            print(f"   Note: Could not set filters: {e}")

        time.sleep(2)

        # Find time slots
        slots = page.query_selector_all(
            '[data-test-id="reservation-button"], '
            '.ReservationButton, '
            '[class*="ReservationButton"], '
            '[class*="reservation-slot"], '
            'button[data-time], '
            '[data-cy="time-slot"]'
        )

        print(f"   Found {len(slots)} time slot(s)")

        if not slots:
            print(f"❌ No available time slots found for {date_norm}")
            browser.close()
            sys.exit(1)

        # Find closest slot to requested time
        target_minutes = int(time_norm.split(":")[0]) * 60 + int(time_norm.split(":")[1])
        best_slot = None
        best_diff = float("inf")

        for slot in slots:
            slot_text = slot.inner_text().strip()
            # Parse time from slot text (e.g., "7:00 PM", "7:30 PM")
            m = re.search(r"(\d{1,2}):?(\d{2})?\s*(AM|PM)?", slot_text, re.IGNORECASE)
            if m:
                h = int(m.group(1))
                mins = int(m.group(2) or 0)
                meridiem = (m.group(3) or "").upper()
                if meridiem == "PM" and h != 12:
                    h += 12
                elif meridiem == "AM" and h == 12:
                    h = 0
                slot_minutes = h * 60 + mins
                diff = abs(slot_minutes - target_minutes)
                if diff < best_diff:
                    best_diff = diff
                    best_slot = slot
                    best_slot_text = slot_text

        if not best_slot:
            best_slot = slots[0]
            best_slot_text = slots[0].inner_text().strip()

        print(f"   Selected slot: {best_slot_text}")

        if dry_run:
            print(f"\n✅ DRY RUN — Would book: {best_slot_text} at {restaurant}")
            print(f"   (No booking made — remove --dry-run to confirm)")
            browser.close()
            return

        # Click the time slot
        print(f"\n📅 Booking slot: {best_slot_text}...")
        best_slot.click()
        time.sleep(2)

        # Look for confirmation/booking modal
        try:
            # Resy confirmation flow
            confirm_btn = page.wait_for_selector(
                '[data-test-id="confirm-button"], '
                'button:has-text("Reserve"), '
                'button:has-text("Book"), '
                'button:has-text("Confirm")',
                timeout=10000
            )
            print(f"   Found confirmation button, proceeding...")

            if dry_run:
                print(f"✅ DRY RUN complete — slot found and ready to confirm")
            else:
                confirm_btn.click()
                time.sleep(3)

                # Check for success
                success = page.query_selector(
                    '[data-test-id="confirmation"], '
                    '[class*="confirmation"], '
                    'h1:has-text("confirmed"), '
                    'h2:has-text("See you")'
                )
                if success:
                    print(f"\n🎉 BOOKING CONFIRMED!")
                    print(f"   {restaurant} | {date_norm} at {best_slot_text} | Party of {party}")
                else:
                    print(f"\n⚠️  Booking submitted — please verify in your Resy app/email")

        except PlaywrightTimeout:
            print(f"⚠️  Confirmation dialog not found. Check browser window.")
            input("Press ENTER when done reviewing...")

        browser.close()


def main():
    parser = argparse.ArgumentParser(
        description="Book a restaurant on Resy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--restaurant", "-r", required=True, help="Restaurant name")
    parser.add_argument("--date", "-d", default="today", help="Date (YYYY-MM-DD, Saturday, March 7)")
    parser.add_argument("--time", "-t", default="19:00", help="Time (7pm, 19:00, 7:30 PM)")
    parser.add_argument("--party", "-p", type=int, default=2, help="Party size")
    parser.add_argument("--location", "-l", default=DEFAULT_LOCATION, help="Location/area")
    parser.add_argument("--dry-run", action="store_true", help="Find slot but don't confirm")
    parser.add_argument("--headless", action="store_true", help="Run browser headless")

    args = parser.parse_args()

    book_resy(
        restaurant=args.restaurant,
        date=args.date,
        time_str=args.time,
        party=args.party,
        location=args.location,
        dry_run=args.dry_run,
        headless=args.headless,
    )


if __name__ == "__main__":
    main()
