#!/usr/bin/env python3
"""
book.py — Unified booking interface for Resy, OpenTable, and AMC.

Usage:
    # List all upcoming reservations and tickets (all services)
    python3 book.py --list

    # List only specific services
    python3 book.py --list --service resy
    python3 book.py --list --service opentable
    python3 book.py --list --service amc

    # Cancel a reservation (prefix with service name)
    python3 book.py --cancel resy:843499889
    python3 book.py --cancel opentable:2413049596
    python3 book.py --cancel amc:ORDER123

    # Modify a reservation
    python3 book.py --modify resy:843499889 --date "March 10" --time "7:30pm" --party 2
    python3 book.py --modify opentable:2413049596 --date "Saturday" --time "8pm"

    # Book new (uses service-specific scripts directly)
    python3 resy-book.py --restaurant "Via45" --date "Saturday" --time "7pm" --party 2
    python3 opentable-book.py --restaurant "The Raven" --date "March 15" --time "7:30pm"
    python3 amc-book.py --movie "Project Hail Mary" --date "Saturday" --time "evening"

Services:
    resy      — Resy restaurant reservations (persistent auth, API-based)
    opentable — OpenTable restaurant reservations (session-based, GraphQL)
    amc       — AMC movie tickets (browser automation)
"""

import argparse
import subprocess
import sys
import json
import os
import re
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
PYTHON = str(Path.home() / "clawd" / ".venv" / "bin" / "python3")


# ─── Helpers ───────────────────────────────────────────────────────────────────

def parse_service_id(service_id: str) -> tuple[str, str]:
    """
    Parse 'service:id' format.
    Examples:
        resy:843499889  -> ('resy', '843499889')
        opentable:12345 -> ('opentable', '12345')
        843499889       -> raises ValueError (no service prefix)
    """
    if ":" in service_id:
        service, rid = service_id.split(":", 1)
        service = service.lower().strip()
        if service not in ("resy", "opentable", "amc"):
            raise ValueError(f"Unknown service '{service}'. Use: resy, opentable, amc")
        return service, rid.strip()
    raise ValueError(
        f"Please include service prefix: resy:{service_id} or opentable:{service_id}"
    )


def run_script(script: str, extra_args: list, capture: bool = False) -> tuple[int, str]:
    """Run a booking script via subprocess."""
    cmd = [PYTHON, str(SCRIPTS_DIR / script)] + extra_args
    if capture:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode, result.stdout + result.stderr
    else:
        result = subprocess.run(cmd)
        return result.returncode, ""


# ─── --list ────────────────────────────────────────────────────────────────────

def cmd_list(services: list, json_output: bool = False):
    """List upcoming reservations across all (or specified) services."""

    target_services = services or ["resy", "opentable", "amc"]
    all_results = {}

    print("=" * 60)
    print("  UPCOMING BOOKINGS")
    print("=" * 60)

    for service in target_services:
        print(f"\n[ {service.upper()} ]")
        print()

        if service == "resy":
            rc, _ = run_script("resy-book.py", ["--list"])
            if rc != 0:
                print(f"  ⚠️  Error fetching Resy reservations (exit {rc})")

        elif service == "opentable":
            rc, _ = run_script("opentable-book.py", ["--list"])
            if rc != 0:
                print(f"  ⚠️  Error fetching OpenTable reservations (exit {rc})")

        elif service == "amc":
            rc, _ = run_script("amc-book.py", ["--list"])
            if rc != 0:
                print(f"  ⚠️  Error fetching AMC orders (exit {rc})")

    print()
    print("=" * 60)
    print("  💡 To cancel:  python3 book.py --cancel service:id")
    print("     To modify:  python3 book.py --modify service:id --date ... --time ...")
    print("=" * 60)


# ─── --cancel ──────────────────────────────────────────────────────────────────

def cmd_cancel(service_id: str):
    """Cancel a reservation by service:id."""
    try:
        service, rid = parse_service_id(service_id)
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    if service == "resy":
        run_script("resy-book.py", ["--cancel", rid])
    elif service == "opentable":
        run_script("opentable-book.py", ["--cancel", rid])
    elif service == "amc":
        run_script("amc-book.py", ["--cancel", rid])


# ─── --modify ──────────────────────────────────────────────────────────────────

def cmd_modify(service_id: str, date: str = None, time_str: str = None, party: int = None):
    """Modify a reservation by service:id."""
    try:
        service, rid = parse_service_id(service_id)
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    extra_args = ["--modify", rid]
    if date:
        extra_args += ["--date", date]
    if time_str:
        extra_args += ["--time", time_str]
    if party:
        extra_args += ["--party", str(party)]

    if service == "resy":
        run_script("resy-book.py", extra_args)
    elif service == "opentable":
        run_script("opentable-book.py", extra_args)
    elif service == "amc":
        run_script("amc-book.py", extra_args)


# ─── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Unified booking manager — Resy, OpenTable, AMC",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--list", action="store_true", help="List all upcoming bookings")
    mode.add_argument("--cancel", metavar="SERVICE:ID", help="Cancel a booking (e.g. resy:123)")
    mode.add_argument("--modify", metavar="SERVICE:ID", help="Modify a booking (e.g. opentable:456)")

    # Filter for --list
    parser.add_argument(
        "--service", "-s",
        choices=["resy", "opentable", "amc"],
        action="append",
        dest="services",
        help="Filter to specific service(s) (can repeat)",
    )

    # Modify options
    parser.add_argument("--date", "-d", metavar="DATE", help="New date (for --modify)")
    parser.add_argument("--time", "-t", metavar="TIME", help="New time (for --modify)")
    parser.add_argument("--party", "-p", type=int, metavar="N", help="New party size (for --modify)")

    # Output
    parser.add_argument("--json", action="store_true", help="JSON output (for scripts)")

    args = parser.parse_args()

    if args.list:
        cmd_list(args.services or [], json_output=args.json)
        return

    if args.cancel:
        cmd_cancel(args.cancel)
        return

    if args.modify:
        cmd_modify(
            service_id=args.modify,
            date=args.date,
            time_str=args.time,
            party=args.party,
        )
        return

    # No mode selected
    parser.print_help()
    print()
    print("Quick examples:")
    print("  python3 book.py --list")
    print("  python3 book.py --list --service resy")
    print("  python3 book.py --cancel resy:843499889")
    print("  python3 book.py --modify opentable:12345 --date 'March 15' --time '7:30pm'")


if __name__ == "__main__":
    main()
