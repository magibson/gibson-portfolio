#!/usr/bin/env python3
"""
opentable-book.py — Book, list, cancel, and modify OpenTable reservations.

Usage:
    # List upcoming reservations
    python3 opentable-book.py --list

    # Cancel a reservation
    python3 opentable-book.py --cancel 2413049596

    # Modify a reservation
    python3 opentable-book.py --modify 2413049596 --date "March 10" --time "7:30pm" --party 2

    # Book a new reservation
    python3 opentable-book.py --restaurant "The Raven" --date "Saturday" --time "7pm" --party 2

Authentication:
    Uses the persistent Chromium profile at ~/.playwright-profiles/opentable/
    NOTE: OpenTable sessions expire often. If logged out, the script will attempt
    to auto-login or prompt you to run: python3 save-sessions.py opentable
    
    For reliable operation, add credentials to ~/clawd/.env:
        OPENTABLE_EMAIL=your@email.com
        OPENTABLE_PASSWORD=yourpassword

Technical notes:
    - OpenTable uses GraphQL at /dapi/fe/gql with CSRF tokens
    - HTTP/2 causes issues in headless mode — we use --disable-http2
    - Sessions expire every ~1 hour; persistent profile keeps login longer
"""

import argparse
import sys
import os
import re
import time
import json
import http.client
import urllib.parse
from pathlib import Path
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

PROFILE_DIR = Path.home() / ".playwright-profiles" / "opentable"
DEFAULT_LOCATION = "Monmouth County, NJ"
OT_BASE = "https://www.opentable.com"

ENV_FILE = Path.home() / "clawd" / ".env"


def load_env() -> dict:
    """Load environment variables from ~/clawd/.env."""
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


# ─── Session Management ────────────────────────────────────────────────────────

def get_ot_session(headless=False) -> dict:
    """
    Launch persistent context, check if logged in.
    If not logged in, attempt auto-login with env credentials.
    Returns dict with: {csrf_token, cookies, user_id, logged_in}
    
    NOTE: headless=False is required for OpenTable — headless mode hangs due to
    Akamai bot detection that blocks the page from fully loading.
    """
    env = load_env()
    email = env.get("OPENTABLE_EMAIL", "")
    password = env.get("OPENTABLE_PASSWORD", "")

    captured = {
        "csrf_token": None,
        "cookies": {},
        "logged_in": False,
        "user_id": None,
    }

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=False,  # MUST be False — OT Akamai blocks headless completely
            args=[
                "--no-sandbox",
                "--disable-http2",
                "--disable-blink-features=AutomationControlled",
            ],
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            slow_mo=100,
        )
        page = ctx.new_page()

        def handle_request(req):
            h = req.headers
            if "x-csrf-token" in h and h["x-csrf-token"]:
                captured["csrf_token"] = h["x-csrf-token"]

        def handle_response(resp):
            url = resp.url
            if "dapi/v1/session" in url and resp.status == 200:
                try:
                    data = resp.json()
                    if data and isinstance(data, dict):
                        uid = data.get("userId") or data.get("id")
                        if uid:
                            captured["user_id"] = uid
                except Exception:
                    pass

        page.on("request", handle_request)
        page.on("response", handle_response)

        try:
            page.goto(OT_BASE, wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)
        except Exception as e:
            print(f"⚠️  Navigation error: {e}")

        # Check login state
        header_text = ""
        try:
            header_text = page.inner_text("header")
        except Exception:
            header_text = page.content()

        logged_in = (
            "sign out" in header_text.lower()
            or "my dining" in header_text.lower()
            or captured["user_id"] is not None
        )

        # Auto-login if credentials available and not logged in
        if not logged_in and email and password:
            print(f"🔐 Session expired — attempting auto-login with {email}...")
            try:
                _do_login(page, email, password)
                time.sleep(3)
                header_text = page.inner_text("header") if page.query_selector("header") else ""
                logged_in = "sign out" in header_text.lower()
                if logged_in:
                    print("✅ Auto-login successful")
                    # Save updated session
                    state = ctx.storage_state()
                    state_file = PROFILE_DIR / "state.json"
                    with open(state_file, "w") as f:
                        json.dump(state, f)
            except Exception as e:
                print(f"⚠️  Auto-login failed: {e}")

        captured["logged_in"] = logged_in

        # Grab current cookies
        cookies = ctx.cookies()
        captured["cookies"] = {c["name"]: c["value"] for c in cookies if "opentable" in c.get("domain", "")}

        ctx.close()

    return captured


def _do_login(page, email: str, password: str):
    """Perform OpenTable login on the given page."""
    # Click Sign In button
    sign_in_btn = page.query_selector(
        "button:has-text('Sign in'), a:has-text('Sign in'), [data-test*='signin']"
    )
    if sign_in_btn:
        sign_in_btn.click()
        time.sleep(2)

    # Enter email
    email_input = page.query_selector("input[type='email'], input[name='email']")
    if email_input:
        email_input.fill(email)
        time.sleep(0.5)

        # Click Continue
        continue_btn = page.query_selector("button:has-text('Continue'), button[type='submit']")
        if continue_btn:
            continue_btn.click()
            time.sleep(2)

    # Enter password
    pwd_input = page.query_selector("input[type='password'], input[name='password']")
    if pwd_input:
        pwd_input.fill(password)
        time.sleep(0.5)

        # Sign In
        signin_btn = page.query_selector(
            "button:has-text('Sign in'), button:has-text('Log in'), "
            "button[type='submit']:has-text('Sign')"
        )
        if signin_btn:
            signin_btn.click()
            time.sleep(3)


def require_login():
    """Check session and exit with helpful message if not logged in."""
    session = get_ot_session()
    if not session["logged_in"]:
        print("❌ Not logged in to OpenTable.")
        print()
        env = load_env()
        if not env.get("OPENTABLE_EMAIL"):
            print("   Add credentials to ~/clawd/.env:")
            print("     OPENTABLE_EMAIL=your@email.com")
            print("     OPENTABLE_PASSWORD=yourpassword")
        print()
        print("   Or re-login manually: python3 save-sessions.py opentable")
        sys.exit(1)
    return session


# ─── GraphQL API ───────────────────────────────────────────────────────────────

def ot_gql(query: str, variables: dict, session: dict) -> dict:
    """Make a GraphQL request to OpenTable's /dapi/fe/gql endpoint."""
    csrf = session.get("csrf_token", "")
    cookies = session.get("cookies", {})
    cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())

    headers = {
        "Content-Type": "application/json",
        "Cookie": cookie_str[:4000],
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        "Origin": "https://www.opentable.com",
        "Referer": "https://www.opentable.com/",
    }
    if csrf:
        headers["x-csrf-token"] = csrf

    body = json.dumps({"query": query, "variables": variables}).encode()
    conn = http.client.HTTPSConnection("www.opentable.com")
    conn.request("POST", "/dapi/fe/gql", body=body, headers=headers)
    resp = conn.getresponse()
    resp_body = resp.read()

    if resp.status != 200:
        raise RuntimeError(f"GraphQL error {resp.status}: {resp_body[:200].decode()}")

    data = json.loads(resp_body)
    if "errors" in data:
        raise RuntimeError(f"GraphQL errors: {data['errors']}")
    return data.get("data", {})


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


def parse_time(time_str: str) -> str:
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

UPCOMING_RESERVATIONS_QUERY = """
    query DiningHistory($upcomingAfterToken: String) {
        viewer {
            upcomingReservations(first: 20, after: $upcomingAfterToken) {
                edges {
                    node {
                        reservationId
                        dateTime
                        partySize
                        status
                        isModifiable
                        isCancellable
                        restaurant {
                            name
                            urlSlug
                            address {
                                city
                                state
                            }
                        }
                    }
                }
            }
        }
    }
"""


def cmd_list_via_browser(session_info: dict) -> list:
    """Scrape upcoming reservations via Playwright when GraphQL fails."""
    print("🌐 Scraping reservations from web UI...")
    results = []

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=False,  # non-headless required for OT
            args=["--no-sandbox", "--disable-http2", "--disable-blink-features=AutomationControlled"],
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        page = ctx.new_page()

        gql_data = []

        def handle_response(resp):
            url = resp.url
            if "dapi/fe/gql" in url and "Reservation" in url:
                try:
                    gql_data.append(resp.json())
                except Exception:
                    pass

        page.on("response", handle_response)

        try:
            page.goto(f"{OT_BASE}/my-reservations", wait_until="domcontentloaded", timeout=30000)
            time.sleep(4)

            # Try to find reservation cards on the page
            reservation_cards = page.query_selector_all(
                "[data-test*='reservation'], [class*='reservation-card'], "
                "[class*='ReservationCard'], [class*='booking']"
            )

            for card in reservation_cards:
                text = card.inner_text()
                # Extract ID from link if possible
                links = card.query_selector_all("a")
                res_id = None
                for link in links:
                    href = link.get_attribute("href") or ""
                    id_match = re.search(r"/(\d{8,})", href)
                    if id_match:
                        res_id = id_match.group(1)
                        break

                results.append({
                    "id": res_id or "unknown",
                    "service": "opentable",
                    "raw_text": text[:200],
                })

        except Exception as e:
            print(f"   Scrape error: {e}")

        ctx.close()

    return results


def cmd_list(args) -> list:
    """List upcoming OpenTable reservations."""
    print("🔄 Loading OpenTable session...")
    session = get_ot_session()

    if not session["logged_in"]:
        print("❌ Not logged in to OpenTable.")
        print("   Add to ~/clawd/.env: OPENTABLE_EMAIL and OPENTABLE_PASSWORD")
        print("   Or run: python3 save-sessions.py opentable")
        return []

    results = []

    # Try GraphQL
    try:
        print("📋 Fetching upcoming reservations via GraphQL...")
        data = ot_gql(UPCOMING_RESERVATIONS_QUERY, {"upcomingAfterToken": None}, session)

        edges = (
            data.get("viewer", {})
            .get("upcomingReservations", {})
            .get("edges", [])
        )

        if edges is not None:
            if not edges:
                print("\n✅ No upcoming OpenTable reservations.")
                return []

            print(f"\n{'─'*55}")
            print(f"  OPENTABLE RESERVATIONS ({len(edges)} upcoming)")
            print(f"{'─'*55}")

            for edge in edges:
                node = edge.get("node", {})
                res_id = node.get("reservationId", "")
                date_time = node.get("dateTime", "")
                party = node.get("partySize", 0)
                status = node.get("status", "confirmed")
                can_modify = node.get("isModifiable", False)
                can_cancel = node.get("isCancellable", False)
                restaurant = node.get("restaurant", {})
                venue_name = restaurant.get("name", "Unknown")
                city = restaurant.get("address", {}).get("city", "")

                try:
                    dt = datetime.fromisoformat(date_time.replace("Z", "+00:00"))
                    day_display = dt.strftime("%a, %b %d %Y")
                    time_display = dt.strftime("%-I:%M %p")
                    day = dt.strftime("%Y-%m-%d")
                    time_str = dt.strftime("%H:%M")
                except Exception:
                    day_display = date_time
                    time_display = ""
                    day = date_time
                    time_str = ""

                modifiers = []
                if not can_cancel:
                    modifiers.append("no-cancel")
                if not can_modify:
                    modifiers.append("no-modify")

                print(f"\n  [{res_id}] {venue_name}")
                if city:
                    print(f"       {city}")
                print(f"       {day_display} at {time_display} · Party of {party}")
                if modifiers:
                    print(f"       ⚠️  {', '.join(modifiers)}")

                results.append({
                    "id": str(res_id),
                    "service": "opentable",
                    "venue": venue_name,
                    "date": day,
                    "time": time_str,
                    "party": party,
                    "can_cancel": can_cancel,
                    "can_modify": can_modify,
                })

            print(f"\n{'─'*55}")
            return results

    except Exception as e:
        print(f"⚠️  GraphQL failed: {e}")
        print("   Trying web scrape fallback...")
        return cmd_list_via_browser(session)

    return results


# ─── --cancel ──────────────────────────────────────────────────────────────────

CANCEL_RESERVATION_MUTATION = """
    mutation CancelReservation($input: CancelReservationInput!) {
        cancelReservation(input: $input) {
            status
            errors {
                message
                code
            }
        }
    }
"""


def cmd_cancel(reservation_id: str):
    """Cancel an OpenTable reservation."""
    print("🔄 Loading OpenTable session...")
    session = get_ot_session()

    if not session["logged_in"]:
        print("❌ Not logged in to OpenTable.")
        print("   Run: python3 save-sessions.py opentable")
        sys.exit(1)

    # Get reservations first to confirm
    reservations = cmd_list(argparse.Namespace(json=False))
    target = next((r for r in reservations if str(r["id"]) == str(reservation_id)), None)

    if not target:
        print(f"❌ Reservation {reservation_id} not found.")
        sys.exit(1)

    if not target.get("can_cancel", False):
        print(f"❌ Reservation {reservation_id} cannot be cancelled.")
        print(f"   {target['venue']} | {target['date']} @ {target['time']}")
        sys.exit(1)

    print(f"\n⚠️  CANCEL RESERVATION")
    print(f"   Venue: {target['venue']}")
    print(f"   Date:  {target['date']} at {target['time']}")
    print(f"   ID:    {reservation_id}")
    print()
    confirm = input("   Type 'yes' to confirm cancellation: ").strip().lower()
    if confirm != "yes":
        print("   Cancelled — no changes made.")
        sys.exit(0)

    print(f"\n🗑️  Cancelling reservation {reservation_id}...")
    try:
        result = ot_gql(
            CANCEL_RESERVATION_MUTATION,
            {"input": {"reservationId": int(reservation_id)}},
            session,
        )
        cancel_result = result.get("cancelReservation", {})
        errors = cancel_result.get("errors", [])
        if errors:
            raise RuntimeError("; ".join(e.get("message", "") for e in errors))
        print(f"✅ Reservation cancelled successfully!")
        print(f"   {target['venue']} | {target['date']} @ {target['time']}")
    except RuntimeError as e:
        # Fall back to web UI
        print(f"⚠️  API cancel failed: {e}")
        print(f"   Opening cancellation page in browser...")
        _cancel_via_browser(str(reservation_id))


def _cancel_via_browser(reservation_id: str):
    """Cancel a reservation via browser UI as fallback."""
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=False,
            args=["--no-sandbox", "--disable-http2", "--disable-blink-features=AutomationControlled"],
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        page = ctx.new_page()
        page.goto(
            f"{OT_BASE}/reservation-details?rid={reservation_id}",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        time.sleep(3)

        cancel_btn = page.query_selector(
            "button:has-text('Cancel'), a:has-text('Cancel reservation'), "
            "[data-test*='cancel']"
        )
        if cancel_btn:
            cancel_btn.click()
            time.sleep(2)
            confirm_btn = page.query_selector(
                "button:has-text('Confirm'), button:has-text('Yes, cancel')"
            )
            if confirm_btn:
                confirm_btn.click()
                time.sleep(2)
                print("✅ Cancellation submitted via browser")
            else:
                print("⚠️  Please confirm cancellation in browser window")
                input("Press ENTER when done...")
        else:
            print(f"⚠️  Could not find cancel button. URL: {page.url}")
            print(f"   Manual: {OT_BASE}/reservation-details?rid={reservation_id}")
            input("Press ENTER when done...")

        ctx.close()


# ─── --modify ──────────────────────────────────────────────────────────────────

MODIFY_RESERVATION_MUTATION = """
    mutation ModifyReservation($input: ModifyReservationInput!) {
        modifyReservation(input: $input) {
            reservationId
            dateTime
            partySize
            status
            errors {
                message
                code
            }
        }
    }
"""


def cmd_modify(reservation_id: str, new_date: str, new_time: str, new_party: int):
    """Modify an OpenTable reservation — date, time, or party size."""
    print("🔄 Loading OpenTable session...")
    session = get_ot_session()

    if not session["logged_in"]:
        print("❌ Not logged in to OpenTable.")
        sys.exit(1)

    # Get current reservation info
    reservations = cmd_list(argparse.Namespace(json=False))
    target = next((r for r in reservations if str(r["id"]) == str(reservation_id)), None)

    if not target:
        print(f"❌ Reservation {reservation_id} not found.")
        sys.exit(1)

    if not target.get("can_modify", False):
        print(f"❌ Reservation {reservation_id} cannot be modified.")
        sys.exit(1)

    # Build new values
    date_norm = parse_date(new_date) if new_date else target["date"]
    time_norm = parse_time(new_time) if new_time else target["time"]
    party = new_party or target["party"]

    # Combine into ISO datetime
    try:
        new_dt = datetime.strptime(f"{date_norm} {time_norm}", "%Y-%m-%d %H:%M")
        new_dt_iso = new_dt.isoformat()
    except ValueError as e:
        print(f"❌ Date/time parse error: {e}")
        sys.exit(1)

    print(f"\n📅 Modifying reservation {reservation_id}:")
    print(f"   Venue:     {target['venue']}")
    print(f"   New date:  {date_norm}")
    print(f"   New time:  {time_norm}")
    print(f"   New party: {party}")

    try:
        result = ot_gql(
            MODIFY_RESERVATION_MUTATION,
            {
                "input": {
                    "reservationId": int(reservation_id),
                    "dateTime": new_dt_iso,
                    "partySize": party,
                }
            },
            session,
        )
        modify_result = result.get("modifyReservation", {})
        errors = modify_result.get("errors", [])
        if errors:
            raise RuntimeError("; ".join(e.get("message", "") for e in errors))
        print(f"✅ Reservation modified!")
        print(f"   {target['venue']} | {date_norm} at {time_norm} | Party of {party}")

    except RuntimeError as e:
        print(f"⚠️  API modify failed: {e}")
        print(f"   Opening modification page in browser...")
        _modify_via_browser(str(reservation_id), date_norm, time_norm, party)


def _modify_via_browser(reservation_id: str, date: str, time_str: str, party: int):
    """Modify a reservation via browser UI as fallback."""
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=False,
            args=["--no-sandbox", "--disable-http2", "--disable-blink-features=AutomationControlled"],
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        page = ctx.new_page()
        page.goto(
            f"{OT_BASE}/reservation-details?rid={reservation_id}",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        time.sleep(3)
        print(f"\n📌 Browser opened to reservation details.")
        print(f"   Date: {date} | Time: {time_str} | Party: {party}")
        print(f"   URL: {page.url}")
        input("Press ENTER when modification is complete...")
        ctx.close()


# ─── Book New ──────────────────────────────────────────────────────────────────

def book_opentable(restaurant: str, date: str, time_str: str, party: int,
                   location: str, dry_run: bool, headless: bool):
    """Book a new OpenTable reservation via the web UI."""

    date_norm = parse_date(date)
    time_norm = parse_time(time_str)
    dt = datetime.strptime(date_norm, "%Y-%m-%d")
    date_ot = dt.strftime("%m/%d/%Y")

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
    print(f"   Dry run    : {dry_run}")

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-http2",
                "--disable-blink-features=AutomationControlled",
            ],
            slow_mo=200,
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        page = ctx.new_page()

        print("\n🔐 Checking login...")
        page.goto(OT_BASE, wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)

        header_text = page.inner_text("header") if page.query_selector("header") else ""
        if "sign in" in header_text.lower():
            env = load_env()
            email = env.get("OPENTABLE_EMAIL", "")
            password = env.get("OPENTABLE_PASSWORD", "")
            if email and password:
                print("🔐 Auto-logging in...")
                _do_login(page, email, password)
            else:
                print("❌ Not logged in. Add OPENTABLE_EMAIL/OPENTABLE_PASSWORD to ~/clawd/.env")
                ctx.close()
                sys.exit(1)

        print("✅ Logged in to OpenTable")

        # Search
        print(f"\n🔍 Searching for '{restaurant}'...")
        search_url = (
            f"{OT_BASE}/s?"
            f"term={urllib.parse.quote(restaurant)}"
            f"&dateTime={date_ot.replace('/', '%2F')}+{urllib.parse.quote(time_ot)}"
            f"&covers={party}&metroId=73"
        )
        page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)

        results = page.query_selector_all(
            "[data-test='restaurant-name'], [class*='restaurant-name'], "
            "h2[class*='name'], [data-testid='restaurant-name']"
        )

        target_result = None
        for result in results:
            if restaurant.lower() in result.inner_text().lower():
                target_result = result
                print(f"   ✅ Found: {result.inner_text().strip()}")
                break

        if not target_result:
            first = page.query_selector(
                "[data-test='restaurant-name'], a[href*='/restaurant/']"
            )
            if first:
                target_result = first
                print(f"   Using: {first.inner_text().strip()[:60]}")

        if not target_result:
            print(f"❌ Restaurant '{restaurant}' not found on OpenTable")
            ctx.close()
            sys.exit(1)

        target_result.click()
        time.sleep(2)

        print(f"\n🕐 Looking for slots around {time_ot}...")
        time.sleep(2)

        slots = page.query_selector_all(
            "[data-test='timeslot'], [class*='timeslot'], [class*='time-slot'], "
            "button[data-datetime], [data-testid*='timeslot']"
        )
        print(f"   Found {len(slots)} slot(s)")

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
                "button:has-text('Complete reservation'), button:has-text('Reserve now'), "
                "button:has-text('Book'), button:has-text('Confirm')",
                timeout=10000,
            )
            confirm_btn.click()
            time.sleep(3)

            success = page.query_selector(
                "[class*='confirmation'], h1:has-text('confirmed'), "
                "[data-test='confirmation-header']"
            )
            if success:
                print(f"\n🎉 BOOKING CONFIRMED!")
                print(f"   {restaurant} | {date_norm} at {best_text} | Party of {party}")
            else:
                print(f"\n⚠️  Booking submitted — verify in your OpenTable app/email")

        except PlaywrightTimeout:
            print(f"⚠️  Confirmation dialog not found.")
            if not headless:
                input("Press ENTER when done reviewing...")

        ctx.close()


# ─── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="OpenTable — book, list, cancel, and modify reservations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--list", action="store_true", help="List upcoming reservations")
    mode.add_argument("--cancel", metavar="ID", help="Cancel reservation by ID")
    mode.add_argument("--modify", metavar="ID", help="Modify reservation by ID")
    mode.add_argument("--restaurant", "-r", metavar="NAME", help="Book a new reservation")

    parser.add_argument("--date", "-d", default="today", help="Date")
    parser.add_argument("--time", "-t", default="19:00", help="Time")
    parser.add_argument("--party", "-p", type=int, default=2, help="Party size")
    parser.add_argument("--location", "-l", default=DEFAULT_LOCATION, help="Location")
    parser.add_argument("--dry-run", action="store_true", help="Find slot but don't confirm")
    parser.add_argument("--headless", action="store_true", help="Run browser headless")
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
            reservation_id=args.modify,
            new_date=args.date if args.date != "today" else None,
            new_time=args.time if args.time != "19:00" else None,
            new_party=args.party if args.party != 2 else None,
        )
        return

    if args.restaurant:
        book_opentable(
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
