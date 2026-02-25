#!/usr/bin/env python3
"""
opentable-book.py — Book a restaurant on OpenTable using a saved browser session.

Usage:
    python3 opentable-book.py --restaurant "Via45" --date "2026-03-07" --time "19:00" --party 2
    python3 opentable-book.py --restaurant "Via45" --date "Saturday" --time "7pm" --party 2

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

PROFILE_DIR = Path.home() / ".playwright-profiles" / "opentable"
STATE_FILE = PROFILE_DIR / "state.json"
DEFAULT_LOCATION = "Monmouth County, NJ"
OT_BASE = "https://www.opentable.com"


def parse_date(date_str: str) -> str:
    """Normalize date to YYYY-MM-DD."""
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
    if re.match(r"^\d{1,2}:\d{2}$", time_str):
        h, m = time_str.split(":")
        return f"{int(h):02d}:{m}"

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
    if not STATE_FILE.exists():
        print(f"❌ No saved session at {STATE_FILE}")
        print(f"   Run: python3 save-sessions.py opentable")
        return False
    with open(STATE_FILE) as f:
        state = json.load(f)
    cookies = state.get("cookies", [])
    ot_cookies = [c for c in cookies if "opentable.com" in c.get("domain", "")]
    if not ot_cookies:
        print(f"⚠️  No OpenTable cookies found. Re-run save-sessions.py opentable")
        return False
    print(f"✅ Session loaded: {len(ot_cookies)} OpenTable cookies")
    return True


def book_opentable(restaurant: str, date: str, time_str: str, party: int,
                   location: str, dry_run: bool, headless: bool):

    date_norm = parse_date(date)
    time_norm = parse_time(time_str)

    # OpenTable wants date as MM/DD/YYYY for URL params
    dt = datetime.strptime(date_norm, "%Y-%m-%d")
    date_ot = dt.strftime("%m/%d/%Y")

    # Time in 12h for OT
    hour = int(time_norm.split(":")[0])
    minute = time_norm.split(":")[1]
    meridiem = "PM" if hour >= 12 else "AM"
    hour12 = hour % 12 or 12
    time_ot = f"{hour12}:{minute} {meridiem}"

    print(f"\n🍽️  OpenTable Booking")
    print(f"   Restaurant : {restaurant}")
    print(f"   Date       : {date_norm} ({date_ot})")
    print(f"   Time       : {time_norm} ({time_ot})")
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

        # Verify login
        print("\n🔐 Verifying login...")
        page.goto(OT_BASE, wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)

        content = page.content().lower()
        if "sign in" in content and "sign out" not in content and "my account" not in content:
            print("❌ Not logged in to OpenTable. Run: python3 save-sessions.py opentable")
            browser.close()
            sys.exit(1)
        print("✅ Logged in to OpenTable")

        # Search
        print(f"\n🔍 Searching OpenTable for '{restaurant}'...")

        search_url = (
            f"{OT_BASE}/s?"
            f"term={restaurant.replace(' ', '+')}"
            f"&dateTime={date_ot.replace('/', '%2F')}+{time_ot.replace(' ', '+').replace(':', '%3A')}"
            f"&covers={party}"
            f"&metroId=73"  # NJ metro
        )
        page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)

        print("   Scanning search results...")

        # Find restaurant in results
        results = page.query_selector_all(
            '[data-test="restaurant-name"], '
            '[class*="restaurant-name"], '
            'h2[class*="name"], '
            '[data-testid="restaurant-name"]'
        )

        target_result = None
        for result in results:
            text = result.inner_text().lower()
            if restaurant.lower() in text:
                target_result = result
                print(f"   ✅ Found: {result.inner_text().strip()}")
                break

        if not target_result:
            print(f"   First result will be used...")
            # Click first available result
            first_restaurant = page.query_selector(
                '[data-test="restaurant-name"]:first-child, '
                'a[href*="/restaurant/"]:first-child'
            )
            if first_restaurant:
                target_result = first_restaurant

        if not target_result:
            print(f"❌ Restaurant '{restaurant}' not found on OpenTable")
            browser.close()
            sys.exit(1)

        # Click restaurant
        target_result.click()
        time.sleep(2)

        # Look for available time slots
        print(f"\n🕐 Looking for available slots around {time_ot}...")
        time.sleep(2)

        slots = page.query_selector_all(
            '[data-test="timeslot"], '
            '[class*="timeslot"], '
            '[class*="time-slot"], '
            'button[data-datetime], '
            '[data-testid*="timeslot"]'
        )

        print(f"   Found {len(slots)} slot(s)")

        if not slots:
            print(f"❌ No available time slots for {date_norm}")
            browser.close()
            sys.exit(1)

        # Find closest slot
        target_minutes = int(time_norm.split(":")[0]) * 60 + int(time_norm.split(":")[1])
        best_slot = None
        best_diff = float("inf")
        best_slot_text = ""

        for slot in slots:
            slot_text = slot.inner_text().strip()
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
            browser.close()
            return

        # Click slot
        print(f"\n📅 Booking slot: {best_slot_text}...")
        best_slot.click()
        time.sleep(2)

        # Confirmation flow
        try:
            confirm_btn = page.wait_for_selector(
                'button:has-text("Complete reservation"), '
                'button:has-text("Reserve now"), '
                'button:has-text("Book"), '
                'button:has-text("Confirm")',
                timeout=10000
            )
            print(f"   Found confirmation button, proceeding...")
            confirm_btn.click()
            time.sleep(3)

            # Check success
            success = page.query_selector(
                '[class*="confirmation"], '
                'h1:has-text("confirmed"), '
                'h1:has-text("booked"), '
                '[data-test="confirmation-header"]'
            )
            if success:
                print(f"\n🎉 BOOKING CONFIRMED!")
                print(f"   {restaurant} | {date_norm} at {best_slot_text} | Party of {party}")
            else:
                print(f"\n⚠️  Booking submitted — verify in your OpenTable app/email")

        except PlaywrightTimeout:
            print(f"⚠️  Confirmation dialog not found. Check browser window.")
            input("Press ENTER when done reviewing...")

        browser.close()


def main():
    parser = argparse.ArgumentParser(
        description="Book a restaurant on OpenTable",
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

    book_opentable(
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
