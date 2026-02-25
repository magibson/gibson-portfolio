#!/usr/bin/env python3
"""
resy-book.py — Book, list, cancel, and modify Resy reservations.

Usage:
    # List upcoming reservations
    python3 resy-book.py --list

    # Cancel a reservation
    python3 resy-book.py --cancel 843499889

    # Modify a reservation
    python3 resy-book.py --modify 843499889 --date "March 10" --time "7:30pm" --party 2

    # Book a new reservation
    python3 resy-book.py --restaurant "Via45" --date "Saturday" --time "7pm" --party 2

Authentication:
    Uses the persistent Chromium profile at ~/.playwright-profiles/resy/
    Tokens are extracted automatically at runtime — no manual re-login needed.
    If login required: python3 save-sessions.py resy
"""

import argparse
import sys
import re
import time
import json
import http.client
import urllib.parse
from pathlib import Path
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

PROFILE_DIR = Path.home() / ".playwright-profiles" / "resy"
DEFAULT_LOCATION = "Monmouth County, NJ"
RESY_BASE = "https://resy.com"
API_BASE = "api.resy.com"


# ─── Auth / Session ────────────────────────────────────────────────────────────

def get_resy_auth() -> dict:
    """
    Extract fresh auth headers from the Resy persistent browser profile.
    Navigates to resy.com, intercepts the x-resy-auth-token header.
    Returns a dict of headers ready for API calls.
    """
    captured = {}
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        page = ctx.new_page()

        def handle_request(req):
            h = req.headers
            if "api.resy.com" in req.url and "x-resy-auth-token" in h:
                captured.update(dict(h))

        page.on("request", handle_request)
        try:
            page.goto(RESY_BASE, wait_until="domcontentloaded", timeout=15000)
            time.sleep(3)
        except Exception:
            pass
        ctx.close()

    if not captured:
        print("❌ Could not extract Resy auth token.")
        print("   Make sure you're logged in: python3 save-sessions.py resy")
        sys.exit(1)

    return {
        "Authorization": captured.get("authorization", ""),
        "x-resy-auth-token": captured.get("x-resy-auth-token", ""),
        "x-resy-universal-auth": captured.get("x-resy-universal-auth", ""),
        "Origin": "https://resy.com",
        "Referer": "https://resy.com/",
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "x-origin": "https://resy.com",
    }


def resy_get(path: str, params: dict = None, headers: dict = None) -> dict:
    """GET request to Resy API."""
    url = path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    conn = http.client.HTTPSConnection(API_BASE)
    conn.request("GET", url, headers=headers)
    resp = conn.getresponse()
    body = resp.read()
    if resp.status != 200:
        raise RuntimeError(f"API error {resp.status}: {body[:200].decode()}")
    return json.loads(body)


def resy_delete(path: str, form_data: dict, headers: dict) -> dict:
    """DELETE request to Resy API with form-encoded body."""
    h = dict(headers)
    h["Content-Type"] = "application/x-www-form-urlencoded"
    body = urllib.parse.urlencode(form_data).encode()
    conn = http.client.HTTPSConnection(API_BASE)
    conn.request("DELETE", path, body=body, headers=h)
    resp = conn.getresponse()
    body = resp.read()
    if resp.status not in (200, 201, 204):
        raise RuntimeError(f"API error {resp.status}: {body[:200].decode()}")
    try:
        return json.loads(body) if body else {}
    except Exception:
        return {}


def resy_post(path: str, form_data: dict = None, json_data: dict = None, headers: dict = None) -> dict:
    """POST request to Resy API."""
    h = dict(headers)
    if json_data:
        h["Content-Type"] = "application/json"
        body = json.dumps(json_data).encode()
    else:
        h["Content-Type"] = "application/x-www-form-urlencoded"
        body = urllib.parse.urlencode(form_data or {}).encode()
    conn = http.client.HTTPSConnection(API_BASE)
    conn.request("POST", path, body=body, headers=h)
    resp = conn.getresponse()
    body = resp.read()
    if resp.status not in (200, 201, 204):
        raise RuntimeError(f"API error {resp.status}: {body[:300].decode()}")
    try:
        return json.loads(body) if body else {}
    except Exception:
        return {}


# ─── Date/Time Parsing ─────────────────────────────────────────────────────────

def parse_date(date_str: str) -> str:
    """Normalize date to YYYY-MM-DD."""
    date_str = date_str.strip()
    today = datetime.now()

    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return date_str

    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    lower = date_str.lower().replace("this ", "").replace("next ", "")
    if lower in days:
        target_dow = days.index(lower)
        current_dow = today.weekday()
        diff = (target_dow - current_dow) % 7
        if diff == 0:
            diff = 7
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

    for fmt in ["%m/%d/%Y", "%m/%d"]:
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.year == 1900:
                dt = dt.replace(year=today.year)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    raise ValueError(f"Cannot parse date: {date_str!r}")


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
    raise ValueError(f"Cannot parse time: {time_str!r}")


# ─── --list ────────────────────────────────────────────────────────────────────

def cmd_list(args):
    """Show upcoming Resy reservations."""
    print("🔄 Fetching Resy auth token...")
    headers = get_resy_auth()

    print("📋 Fetching upcoming reservations...")
    data = resy_get("/3/user/reservations", {"limit": 20, "offset": 0}, headers=headers)

    reservations = data.get("reservations", [])
    venues = data.get("venues", {})

    if not reservations:
        print("\n✅ No upcoming Resy reservations.")
        return []

    results = []
    print(f"\n{'─'*55}")
    print(f"  RESY RESERVATIONS ({len(reservations)} upcoming)")
    print(f"{'─'*55}")

    for r in reservations:
        rid = r.get("reservation_id")
        day = r.get("day", "")
        time_slot = r.get("time_slot", "")[:5]  # HH:MM
        venue_id = str(r.get("venue", {}).get("id", ""))
        venue_info = venues.get(venue_id, {})
        venue_name = venue_info.get("name", "Unknown Venue")
        seats = r.get("num_seats", 0)
        cancel_ok = r.get("cancellation", {}).get("allowed", False)
        change_ok = r.get("change", {}).get("allowed", False)

        # Format date nicely
        try:
            dt = datetime.strptime(day, "%Y-%m-%d")
            day_display = dt.strftime("%a, %b %d %Y")
        except Exception:
            day_display = day

        # Format time
        try:
            t = datetime.strptime(time_slot, "%H:%M")
            time_display = t.strftime("%-I:%M %p")
        except Exception:
            time_display = time_slot

        modifiers = []
        if not cancel_ok:
            modifiers.append("no-cancel")
        if not change_ok:
            modifiers.append("no-modify")

        print(f"\n  [{rid}] {venue_name}")
        print(f"       {day_display} at {time_display} · Party of {seats}")
        if modifiers:
            print(f"       ⚠️  {', '.join(modifiers)}")

        results.append({
            "id": str(rid),
            "service": "resy",
            "venue": venue_name,
            "date": day,
            "time": time_slot,
            "party": seats,
            "can_cancel": cancel_ok,
            "can_modify": change_ok,
            "resy_token": r.get("resy_token", ""),
        })

    print(f"\n{'─'*55}")
    return results


# ─── --cancel ──────────────────────────────────────────────────────────────────

def cmd_cancel(reservation_id: str):
    """Cancel a Resy reservation by ID."""
    print(f"🔄 Fetching Resy auth token...")
    headers = get_resy_auth()

    # Get reservations to find the resy_token for this ID
    print(f"🔍 Looking up reservation {reservation_id}...")
    data = resy_get("/3/user/reservations", {"limit": 20, "offset": 0}, headers=headers)
    reservations = data.get("reservations", [])
    venues = data.get("venues", {})

    target = None
    for r in reservations:
        if str(r.get("reservation_id")) == str(reservation_id):
            target = r
            break

    if not target:
        print(f"❌ Reservation {reservation_id} not found in your upcoming reservations.")
        print("   Run --list to see your current reservations.")
        sys.exit(1)

    venue_id = str(target.get("venue", {}).get("id", ""))
    venue_name = venues.get(venue_id, {}).get("name", "Unknown")
    day = target.get("day", "")
    time_slot = target.get("time_slot", "")[:5]
    cancel_ok = target.get("cancellation", {}).get("allowed", False)
    resy_token = target.get("resy_token", "")

    if not cancel_ok:
        print(f"❌ Reservation {reservation_id} cannot be cancelled.")
        print(f"   Venue: {venue_name} | {day} @ {time_slot}")
        sys.exit(1)

    print(f"\n⚠️  CANCEL RESERVATION")
    print(f"   Venue: {venue_name}")
    print(f"   Date:  {day} at {time_slot}")
    print(f"   ID:    {reservation_id}")
    print()
    confirm = input("   Type 'yes' to confirm cancellation: ").strip().lower()
    if confirm != "yes":
        print("   Cancelled — no changes made.")
        sys.exit(0)

    print(f"\n🗑️  Cancelling reservation {reservation_id}...")
    try:
        result = resy_delete(
            "/3/user/reservations",
            {"resy_token": resy_token},
            headers=headers,
        )
        print(f"✅ Reservation cancelled successfully!")
        print(f"   {venue_name} | {day} @ {time_slot}")
    except RuntimeError as e:
        print(f"❌ Cancellation failed: {e}")
        sys.exit(1)


# ─── --modify ──────────────────────────────────────────────────────────────────

def cmd_modify(reservation_id: str, new_date: str, new_time: str, new_party: int):
    """
    Modify a Resy reservation.
    Resy's modify flow: find a new slot at the same venue, then use the change API.
    """
    print(f"🔄 Fetching Resy auth token...")
    headers = get_resy_auth()

    # Look up the reservation
    print(f"🔍 Looking up reservation {reservation_id}...")
    data = resy_get("/3/user/reservations", {"limit": 20, "offset": 0}, headers=headers)
    reservations = data.get("reservations", [])
    venues = data.get("venues", {})

    target = None
    for r in reservations:
        if str(r.get("reservation_id")) == str(reservation_id):
            target = r
            break

    if not target:
        print(f"❌ Reservation {reservation_id} not found.")
        sys.exit(1)

    venue_id = str(target.get("venue", {}).get("id", ""))
    venue_name = venues.get(venue_id, {}).get("name", "Unknown")
    service_type_id = target.get("service_type_id", 2)
    change_ok = target.get("change", {}).get("allowed", False)

    if not change_ok:
        print(f"❌ Reservation {reservation_id} cannot be modified.")
        print(f"   Venue: {venue_name}")
        sys.exit(1)

    date_norm = parse_date(new_date) if new_date else target.get("day", "")
    time_norm = parse_time(new_time) if new_time else target.get("time_slot", "19:00")[:5]
    party = new_party or target.get("num_seats", 2)

    print(f"\n📅 Modifying reservation {reservation_id}:")
    print(f"   Venue:     {venue_name}")
    print(f"   New date:  {date_norm}")
    print(f"   New time:  {time_norm}")
    print(f"   New party: {party}")

    # Step 1: Search for available slots at same venue
    print(f"\n🔍 Searching for available slots...")
    try:
        venue_data = resy_get(
            "/4/find",
            {
                "lat": 0,
                "long": 0,
                "day": date_norm,
                "party_size": party,
                "venue_id": venue_id,
            },
            headers=headers,
        )
        # Try alternative endpoint
    except Exception:
        pass

    # Use venue details endpoint
    try:
        venue_details = resy_get(
            "/3/venue",
            {
                "url_slug": venues.get(venue_id, {}).get("url_slug", ""),
                "location": "new-york-ny",
                "day": date_norm,
                "party_size": party,
            },
            headers=headers,
        )
        slots = venue_details.get("slots", [])
    except Exception as e:
        print(f"   Could not fetch slots: {e}")
        slots = []

    if not slots:
        # Fall back to the Resy web UI for modification
        print(f"\n⚠️  Could not find available slots via API.")
        print(f"   Please modify via the Resy app or website:")
        print(f"   https://resy.com/profile/reservations")
        sys.exit(1)

    # Find closest slot to requested time
    target_minutes = int(time_norm.split(":")[0]) * 60 + int(time_norm.split(":")[1])
    best_slot = None
    best_diff = float("inf")

    for slot in slots:
        config = slot.get("config", {})
        slot_id = config.get("id")
        slot_token = slot.get("token", "")
        slot_time = config.get("time_slot", "")
        if not slot_time:
            continue

        try:
            h, m = slot_time[:5].split(":")
            slot_minutes = int(h) * 60 + int(m)
            diff = abs(slot_minutes - target_minutes)
            if diff < best_diff:
                best_diff = diff
                best_slot = slot
                best_slot_time = slot_time
        except Exception:
            continue

    if not best_slot:
        print(f"❌ No available slots found for {date_norm}")
        sys.exit(1)

    slot_token = best_slot.get("token", "")
    print(f"   Found slot: {best_slot_time}")

    # Step 2: Get a new resy_token for the new slot
    try:
        book_data = resy_post(
            "/3/details",
            form_data={
                "config_id": best_slot.get("config", {}).get("id", ""),
                "day": date_norm,
                "party_size": party,
            },
            headers=headers,
        )
        new_book_token = book_data.get("book_token", {}).get("value", "")
    except Exception as e:
        print(f"❌ Could not get booking token: {e}")
        sys.exit(1)

    # Step 3: Use the change/rebook endpoint
    try:
        result = resy_post(
            "/3/user/reservations",
            form_data={
                "book_token": new_book_token,
                "source_id": "resy.com-venue-details",
            },
            headers=headers,
        )

        # Cancel the old reservation
        old_token = target.get("resy_token", "")
        resy_delete("/3/user/reservations", {"resy_token": old_token}, headers=headers)

        print(f"\n✅ Reservation modified!")
        print(f"   {venue_name} | {date_norm} at {best_slot_time} | Party of {party}")
    except Exception as e:
        print(f"❌ Modification failed: {e}")
        print(f"   Try modifying directly: https://resy.com/profile/reservations")
        sys.exit(1)


# ─── --restaurant (book new) ───────────────────────────────────────────────────

def book_resy(restaurant: str, date: str, time_str: str, party: int,
              location: str, dry_run: bool, headless: bool):
    """Book a new Resy reservation via the web UI."""

    date_norm = parse_date(date)
    time_norm = parse_time(time_str)

    print(f"\n🍽️  Resy Booking")
    print(f"   Restaurant : {restaurant}")
    print(f"   Date       : {date_norm}")
    print(f"   Time       : {time_norm}")
    print(f"   Party      : {party}")
    print(f"   Location   : {location}")
    print(f"   Dry run    : {dry_run}")

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=headless,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            slow_mo=200,
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        page = ctx.new_page()

        print("\n🔐 Navigating to Resy...")
        page.goto(RESY_BASE, wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)

        content = page.content().lower()
        if "sign in" in content and "log out" not in content and "account" not in content:
            print("❌ Not logged in. Run: python3 save-sessions.py resy")
            ctx.close()
            sys.exit(1)

        print("✅ Logged in to Resy")

        # Search
        print(f"\n🔍 Searching for '{restaurant}'...")
        search_url = (
            f"{RESY_BASE}/search?"
            f"query={urllib.parse.quote(restaurant)}"
            f"&location={urllib.parse.quote(location)}"
            f"&day={date_norm}&party_size={party}"
        )
        page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)

        results = page.query_selector_all(
            "[data-test-id='search-result'], .VenueCard, [class*='VenueCard'], [class*='venue-result']"
        )
        print(f"   Found {len(results)} result(s)")

        restaurant_el = None
        for result in results:
            if restaurant.lower() in result.inner_text().lower():
                restaurant_el = result
                print("   ✅ Found matching restaurant")
                break

        if not restaurant_el and results:
            restaurant_el = results[0]

        if not restaurant_el:
            slug = restaurant.lower().replace(" ", "-").replace("'", "")
            venue_url = f"{RESY_BASE}/cities/nj/{slug}"
            page.goto(venue_url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)
            if "404" in page.title() or "not found" in page.content().lower():
                print(f"❌ Restaurant '{restaurant}' not found on Resy")
                ctx.close()
                sys.exit(1)
        else:
            restaurant_el.click()
            time.sleep(2)

        print(f"\n🕐 Looking for available slots around {time_norm}...")
        time.sleep(2)

        slots = page.query_selector_all(
            "[data-test-id='reservation-button'], "
            ".ReservationButton, [class*='ReservationButton'], "
            "button[data-time], [data-cy='time-slot']"
        )
        print(f"   Found {len(slots)} time slot(s)")

        if not slots:
            print(f"❌ No available time slots for {date_norm}")
            ctx.close()
            sys.exit(1)

        target_min = int(time_norm.split(":")[0]) * 60 + int(time_norm.split(":")[1])
        best_slot = None
        best_diff = float("inf")
        best_text = ""

        for slot in slots:
            text = slot.inner_text().strip()
            m = re.search(r"(\d{1,2}):?(\d{2})?\s*(AM|PM)?", text, re.IGNORECASE)
            if m:
                h = int(m.group(1))
                mins = int(m.group(2) or 0)
                meridiem = (m.group(3) or "").upper()
                if meridiem == "PM" and h != 12:
                    h += 12
                elif meridiem == "AM" and h == 12:
                    h = 0
                diff = abs(h * 60 + mins - target_min)
                if diff < best_diff:
                    best_diff = diff
                    best_slot = slot
                    best_text = text

        if not best_slot:
            best_slot = slots[0]
            best_text = slots[0].inner_text().strip()

        print(f"   Selected: {best_text}")

        if dry_run:
            print(f"\n✅ DRY RUN — Would book: {best_text} at {restaurant}")
            ctx.close()
            return

        print(f"\n📅 Booking: {best_text}...")
        best_slot.click()
        time.sleep(2)

        try:
            confirm_btn = page.wait_for_selector(
                "[data-test-id='confirm-button'], button:has-text('Reserve'), "
                "button:has-text('Book'), button:has-text('Confirm')",
                timeout=10000,
            )
            confirm_btn.click()
            time.sleep(3)

            success = page.query_selector(
                "[data-test-id='confirmation'], [class*='confirmation'], "
                "h1:has-text('confirmed'), h2:has-text('See you')"
            )
            if success:
                print(f"\n🎉 BOOKING CONFIRMED!")
                print(f"   {restaurant} | {date_norm} at {best_text} | Party of {party}")
            else:
                print(f"\n⚠️  Booking submitted — verify in your Resy app/email")

        except PlaywrightTimeout:
            print(f"⚠️  Confirmation dialog not found. Check browser window.")
            if not headless:
                input("Press ENTER when done reviewing...")

        ctx.close()


# ─── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Resy — book, list, cancel, and modify restaurant reservations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Modes
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--list", action="store_true", help="List upcoming reservations")
    mode.add_argument("--cancel", metavar="ID", help="Cancel reservation by ID")
    mode.add_argument("--modify", metavar="ID", help="Modify reservation by ID")
    mode.add_argument("--restaurant", "-r", metavar="NAME", help="Book a new reservation")

    # Book new
    parser.add_argument("--date", "-d", default="today", help="Date (YYYY-MM-DD, Saturday, March 7)")
    parser.add_argument("--time", "-t", default="19:00", help="Time (7pm, 19:00, 7:30 PM)")
    parser.add_argument("--party", "-p", type=int, default=2, help="Party size")
    parser.add_argument("--location", "-l", default=DEFAULT_LOCATION, help="Location/area")
    parser.add_argument("--dry-run", action="store_true", help="Find slot but don't confirm")
    parser.add_argument("--headless", action="store_true", help="Run browser headless")

    # JSON output (for book.py --list aggregation)
    parser.add_argument("--json", action="store_true", help="Output JSON (for scripting)")

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
            reservation_id=args.modify,
            new_date=args.date if args.date != "today" else None,
            new_time=args.time if args.time != "19:00" else None,
            new_party=args.party if args.party != 2 else None,
        )
        return

    if args.restaurant:
        book_resy(
            restaurant=args.restaurant,
            date=args.date,
            time_str=args.time,
            party=args.party,
            location=args.location,
            dry_run=args.dry_run,
            headless=args.headless,
        )
        return

    parser.print_help()


if __name__ == "__main__":
    main()
