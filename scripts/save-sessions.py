#!/usr/bin/env python3
"""
save-sessions.py — Capture authenticated browser sessions for booking scripts.

Supports two modes:
  1. AUTO: Imports cookies from Safari's cookie database (if accessible)
  2. MANUAL: Opens a visible Chromium window — you log in, press ENTER to save

Usage:
    python3 save-sessions.py [resy|opentable|amc|all]
    python3 save-sessions.py --manual [resy|opentable|amc|all]
    python3 save-sessions.py --check    # Check which sessions are saved/valid
"""

import sys
import json
import time
import shutil
import sqlite3
import tempfile
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright

PROFILES = {
    "resy": {
        "url": "https://resy.com",
        "profile_dir": Path.home() / ".playwright-profiles" / "resy",
        "domains": ["resy.com"],
        "login_check": lambda content: (
            "my reservations" in content.lower() or
            "account" in content.lower() and "sign in" not in content.lower()
        ),
        "name": "Resy",
    },
    "opentable": {
        "url": "https://www.opentable.com",
        "profile_dir": Path.home() / ".playwright-profiles" / "opentable",
        "domains": ["opentable.com"],
        "login_check": lambda content: (
            "sign out" in content.lower() or
            "my account" in content.lower() or
            "rewards" in content.lower()
        ),
        "name": "OpenTable",
    },
    "amc": {
        "url": "https://www.amctheatres.com",
        "profile_dir": Path.home() / ".playwright-profiles" / "amc",
        "domains": ["amctheatres.com"],
        "login_check": lambda content: (
            "sign out" in content.lower() or
            "my account" in content.lower() or
            "stubs" in content.lower()
        ),
        "name": "AMC Theatres",
    },
}

SAFARI_COOKIES_DB = Path.home() / "Library" / "Cookies" / "Cookies.binarycookies"
SAFARI_COOKIES_DIR = Path.home() / "Library" / "Containers" / "com.apple.Safari" / "Data" / "Library" / "Cookies"


def get_safari_cookies_for_domain(domain: str) -> list[dict]:
    """
    Attempt to read Safari cookies for a domain.
    Safari uses a binary format — we use a Python parser.
    """
    cookies = []

    # Try using browsercookie library if available
    try:
        import browser_cookie3
        safari_cookies = browser_cookie3.safari(domain_name=domain)
        for c in safari_cookies:
            if domain in c.domain:
                cookies.append({
                    "name": c.name,
                    "value": c.value,
                    "domain": c.domain if c.domain.startswith(".") else f".{c.domain}",
                    "path": c.path or "/",
                    "secure": c.secure,
                    "httpOnly": False,
                    "sameSite": "Lax",
                })
        if cookies:
            print(f"  📦 Imported {len(cookies)} Safari cookies for {domain} via browser_cookie3")
        return cookies
    except ImportError:
        pass
    except Exception as e:
        print(f"  ⚠️  browser_cookie3 failed: {e}")

    return cookies


def save_session_manual(service_key: str, playwright):
    """Open a visible browser for manual login/verification."""
    cfg = PROFILES[service_key]
    profile_dir = cfg["profile_dir"]
    profile_dir.mkdir(parents=True, exist_ok=True)
    state_path = profile_dir / "state.json"

    print(f"\n{'='*60}")
    print(f"  MANUAL SESSION CAPTURE: {cfg['name']}")
    print(f"  Profile: {profile_dir}")
    print(f"{'='*60}")

    browser = playwright.chromium.launch(headless=False, slow_mo=300)

    # If we have existing state, pre-load it
    context_opts = {
        "viewport": {"width": 1280, "height": 900},
        "user_agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    }
    if state_path.exists():
        context_opts["storage_state"] = str(state_path)

    context = browser.new_context(**context_opts)
    page = context.new_page()

    print(f"  Opening {cfg['url']} ...")
    page.goto(cfg["url"], wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)

    # Auto-detect login
    content = page.content()
    logged_in = cfg["login_check"](content)

    if logged_in:
        print(f"  ✅ Login detected automatically!")
    else:
        print(f"\n  ⚠️  Not logged in (or could not detect). Browser is open.")
        print(f"  Please log in at: {cfg['url']}")
        print(f"  Then press ENTER here to save your session.")
        input("\n  > Press ENTER after logging in: ")

    # Save state
    context.storage_state(path=str(state_path))

    with open(state_path) as f:
        state = json.load(f)
    n = len(state.get("cookies", []))
    print(f"  ✅ Session saved: {n} cookies → {state_path}")

    browser.close()
    return state_path


def save_session_auto(service_key: str, playwright):
    """Try importing Safari cookies, then verify in browser."""
    cfg = PROFILES[service_key]
    profile_dir = cfg["profile_dir"]
    profile_dir.mkdir(parents=True, exist_ok=True)
    state_path = profile_dir / "state.json"

    print(f"\n{'='*60}")
    print(f"  AUTO SESSION CAPTURE: {cfg['name']}")
    print(f"{'='*60}")

    # Try to import Safari cookies
    safari_cookies = []
    for domain in cfg["domains"]:
        safari_cookies.extend(get_safari_cookies_for_domain(domain))

    # Build initial state
    initial_state = {"cookies": safari_cookies, "origins": []}

    # Write temp state if we have cookies
    temp_state = None
    if safari_cookies:
        import tempfile, os
        fd, temp_state = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(initial_state, f)
        print(f"  Pre-loading {len(safari_cookies)} Safari cookies...")

    # Launch browser with pre-loaded cookies
    browser = playwright.chromium.launch(headless=False, slow_mo=200)
    context_opts = {
        "viewport": {"width": 1280, "height": 900},
        "user_agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    }
    if temp_state:
        context_opts["storage_state"] = temp_state

    context = browser.new_context(**context_opts)
    page = context.new_page()

    print(f"  Navigating to {cfg['url']} ...")
    page.goto(cfg["url"], wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)

    # Check login status
    content = page.content()
    logged_in = cfg["login_check"](content)

    if logged_in:
        print(f"  ✅ Logged in to {cfg['name']}!")
        context.storage_state(path=str(state_path))
        with open(state_path) as f:
            state = json.load(f)
        n = len(state.get("cookies", []))
        print(f"  ✅ Session saved: {n} cookies → {state_path}")
    else:
        print(f"\n  ⚠️  Not logged in. Browser is open at {cfg['url']}")
        print(f"  Please log in, then press ENTER.")
        input("\n  > Press ENTER after logging in: ")
        context.storage_state(path=str(state_path))
        with open(state_path) as f:
            state = json.load(f)
        n = len(state.get("cookies", []))
        print(f"  ✅ Session saved: {n} cookies → {state_path}")

    browser.close()
    if temp_state:
        Path(temp_state).unlink(missing_ok=True)

    return state_path


def check_sessions():
    """Print status of all saved sessions."""
    print("\n🔍 Session Status:\n")
    for key, cfg in PROFILES.items():
        state_path = cfg["profile_dir"] / "state.json"
        if not state_path.exists():
            print(f"  ❌ {cfg['name']:15s} — no session saved")
            continue
        with open(state_path) as f:
            state = json.load(f)
        cookies = state.get("cookies", [])
        domain_cookies = [c for c in cookies if any(d in c.get("domain","") for d in cfg["domains"])]
        print(f"  {'✅' if domain_cookies else '⚠️ '} {cfg['name']:15s} — {len(domain_cookies)} domain cookies ({len(cookies)} total)")
    print()


def main():
    parser = argparse.ArgumentParser(description="Save browser sessions for booking scripts")
    parser.add_argument("services", nargs="*", default=["all"],
                        help="Services: resy, opentable, amc, or all")
    parser.add_argument("--manual", action="store_true",
                        help="Manual mode: always open browser for login")
    parser.add_argument("--check", action="store_true",
                        help="Check status of saved sessions")

    args = parser.parse_args()

    if args.check:
        check_sessions()
        return

    targets = args.services
    if "all" in targets:
        targets = list(PROFILES.keys())

    invalid = [t for t in targets if t not in PROFILES]
    if invalid:
        print(f"Unknown services: {invalid}. Valid: {list(PROFILES.keys())}")
        sys.exit(1)

    print(f"🎭 Session Capture — services: {', '.join(targets)}")
    print(f"   Mode: {'manual' if args.manual else 'auto (Safari import + browser verify)'}")

    with sync_playwright() as p:
        for service in targets:
            try:
                if args.manual:
                    save_session_manual(service, p)
                else:
                    save_session_auto(service, p)
            except KeyboardInterrupt:
                print(f"\n  Skipped {service}")
            except Exception as e:
                print(f"\n  ❌ Error for {service}: {e}")
                import traceback; traceback.print_exc()

    print(f"\n✅ Done. Run `python3 save-sessions.py --check` to verify.")
    print(f"   Then use: python3 book.py --help")


if __name__ == "__main__":
    main()
