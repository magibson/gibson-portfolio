#!/usr/bin/env python3
"""
book.py — Unified booking interface for restaurants (Resy/OpenTable) and movies (AMC).

Accepts natural language or structured arguments.

Usage:
    python3 book.py "dinner for 2 at Via45 Saturday 7pm"
    python3 book.py "Project Hail Mary IMAX Saturday March 21 evening 2 seats"
    python3 book.py "book Via45 on Resy Saturday 8pm party of 4"
    python3 book.py "opentable dinner at The Raven Saturday 7:30pm for 2"
    python3 book.py --restaurant "Via45" --date "Saturday" --time "7pm" --party 2
    python3 book.py --movie "Project Hail Mary" --date "Saturday" --time "evening" --seats 2 --format IMAX
    python3 book.py --help

Natural language examples:
    "dinner for 2 at Via45 Saturday 7pm"                     → Resy
    "book Via45 opentable Saturday 8pm 4 people"             → OpenTable
    "Project Hail Mary IMAX Saturday evening 2 seats"        → AMC
    "movie The Brutalist tonight 2 tickets standard"         → AMC
    "table for 3 at Porta Asbury Park tonight 8pm resy"      → Resy
"""

import argparse
import sys
import re
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

SCRIPTS_DIR = Path(__file__).parent
VENV_PYTHON = Path.home() / "clawd" / ".venv" / "bin" / "python3"
PYTHON = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable

# ─── Movie detection ───────────────────────────────────────────────────────────
MOVIE_KEYWORDS = [
    "movie", "film", "imax", "dolby", "showing", "showtime",
    "ticket", "tickets", "seats", "seat", "cinema", "theater",
    "watch", "screening", "amc"
]

# ─── Restaurant detection ───────────────────────────────────────────────────────
RESTAURANT_KEYWORDS = [
    "dinner", "lunch", "brunch", "breakfast", "restaurant", "table",
    "reservation", "dining", "eat", "food", "resy", "opentable"
]

# ─── Service detection ─────────────────────────────────────────────────────────
RESY_KEYWORDS = ["resy"]
OPENTABLE_KEYWORDS = ["opentable", "open table"]

# ─── Format detection ──────────────────────────────────────────────────────────
IMAX_KEYWORDS = ["imax"]
DOLBY_KEYWORDS = ["dolby", "atmos"]

# ─── Date parsing ──────────────────────────────────────────────────────────────
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7,
    "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def extract_date(text: str) -> str | None:
    """Extract a date from natural language text."""
    lower = text.lower()
    today = datetime.now()

    # today/tonight
    if "tonight" in lower or "today" in lower:
        return today.strftime("%Y-%m-%d")
    if "tomorrow" in lower:
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")

    # "this Saturday", "next Friday", etc.
    for day in DAYS:
        if day in lower:
            dow = DAYS.index(day)
            current_dow = today.weekday()
            diff = (dow - current_dow) % 7
            if diff == 0:
                diff = 7
            return (today + timedelta(days=diff)).strftime("%Y-%m-%d")

    # "March 21", "March 21 2026"
    for month_name, month_num in MONTHS.items():
        pattern = rf"\b{month_name}\s+(\d{{1,2}})(?:\s+(\d{{4}}))?\b"
        m = re.search(pattern, lower)
        if m:
            day = int(m.group(1))
            year = int(m.group(2)) if m.group(2) else today.year
            try:
                dt = datetime(year, month_num, day)
                if dt < today and not m.group(2):
                    dt = dt.replace(year=today.year + 1)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

    # MM/DD or MM/DD/YYYY
    m = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{4}))?\b", text)
    if m:
        mo, day = int(m.group(1)), int(m.group(2))
        year = int(m.group(3)) if m.group(3) else today.year
        try:
            return datetime(year, mo, day).strftime("%Y-%m-%d")
        except ValueError:
            pass

    return None


def extract_time(text: str) -> str | None:
    """Extract a time from natural language text."""
    lower = text.lower()

    # Fuzzy times
    if "morning" in lower:
        return "morning"
    if "afternoon" in lower or "matinee" in lower:
        return "afternoon"
    if "evening" in lower or "tonight" in lower:
        return "evening"
    if "night" in lower:
        return "evening"

    # Specific: "7:30 PM", "7pm", "19:30"
    m = re.search(r"\b(\d{1,2}):(\d{2})\s*(am|pm)?\b", lower)
    if m:
        h, mins, meridiem = int(m.group(1)), m.group(2), (m.group(3) or "").upper()
        if meridiem == "PM" and h != 12:
            h += 12
        elif meridiem == "AM" and h == 12:
            h = 0
        return f"{h:02d}:{mins}"

    m = re.search(r"\b(\d{1,2})\s*(am|pm)\b", lower)
    if m:
        h, meridiem = int(m.group(1)), m.group(2).upper()
        if meridiem == "PM" and h != 12:
            h += 12
        elif meridiem == "AM" and h == 12:
            h = 0
        return f"{h:02d}:00"

    return None


def extract_party_size(text: str) -> int | None:
    """Extract party/seat count."""
    lower = text.lower()

    # "for 2", "party of 4", "2 people", "2 guests", "2 seats", "2 tickets"
    patterns = [
        r"for\s+(\d+)",
        r"party\s+of\s+(\d+)",
        r"(\d+)\s+people",
        r"(\d+)\s+guests?",
        r"(\d+)\s+seats?",
        r"(\d+)\s+tickets?",
        r"table\s+for\s+(\d+)",
        r"(\d+)\s+persons?",
    ]
    for pat in patterns:
        m = re.search(pat, lower)
        if m:
            return int(m.group(1))
    return None


def extract_movie_format(text: str) -> str:
    """Extract screening format."""
    lower = text.lower()
    if "imax" in lower:
        return "IMAX"
    if "dolby" in lower or "atmos" in lower:
        return "Dolby"
    if "plf" in lower or "prime" in lower:
        return "PLF"
    return "standard"


def extract_restaurant_name(text: str, service_hints: list[str]) -> str | None:
    """
    Extract restaurant name from text.
    Looks for patterns like "at [Name]", "at [Name] restaurant", etc.
    """
    # "at Via45", "at the Raven and the Peach"
    m = re.search(r"\bat\s+(?:the\s+)?([A-Z][^,\.]+?)(?:\s+(?:on|in|for|saturday|sunday|monday|tuesday|wednesday|thursday|friday|tonight|tomorrow|\d))", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    # "at Via45" at end of phrase
    m = re.search(r"\bat\s+(?:the\s+)?([A-Z][^\s,\.]+(?:\s+[A-Z][^\s,\.]+){0,4})", text, re.IGNORECASE)
    if m:
        name = m.group(1).strip()
        # Remove trailing keywords
        for kw in ["resy", "opentable", "saturday", "sunday", "tonight", "tomorrow"]:
            name = re.sub(rf"\s+{kw}.*$", "", name, flags=re.IGNORECASE)
        return name.strip()

    return None


def extract_movie_title(text: str) -> str | None:
    """
    Extract movie title. Strip common keywords around it.
    """
    # Remove leading booking words
    cleaned = re.sub(
        r"^(?:book|get|buy|see|watch|reserve|find)\s+",
        "", text.strip(), flags=re.IGNORECASE
    )

    # Remove trailing context (date, time, seats, format)
    patterns_to_remove = [
        r"\s+(?:imax|dolby|standard|plf)\b.*$",
        r"\s+(?:saturday|sunday|monday|tuesday|wednesday|thursday|friday|tonight|tomorrow)\b.*$",
        r"\s+\d{4}-\d{2}-\d{2}.*$",
        r"\s+(?:march|april|may|june|july|august|september|october|november|december|january|february)\s+\d+.*$",
        r"\s+\d+\s+(?:seat|ticket|person|people).*$",
        r"\s+(?:evening|morning|afternoon|night)\b.*$",
        r"\s+\d{1,2}(?::\d{2})?\s*(?:am|pm).*$",
        r"\s+amc\b.*$",
    ]

    title = cleaned
    for pat in patterns_to_remove:
        title = re.sub(pat, "", title, flags=re.IGNORECASE).strip()

    # Clean up movie keywords at the start
    title = re.sub(r"^(?:movie|film|ticket|tickets?)\s+(?:for\s+)?", "", title, flags=re.IGNORECASE).strip()

    return title if title else None


def parse_natural_language(text: str) -> dict:
    """Parse a natural language booking request into structured params."""
    lower = text.lower()
    result = {}

    # Determine booking type
    is_movie = any(kw in lower for kw in MOVIE_KEYWORDS)
    is_restaurant = any(kw in lower for kw in RESTAURANT_KEYWORDS)

    # Heuristic: if both detected, presence of specific movie keywords wins
    if is_movie and not is_restaurant:
        result["type"] = "movie"
    elif is_restaurant and not is_movie:
        result["type"] = "restaurant"
    elif is_movie and is_restaurant:
        # "dinner and a movie" → restaurant
        # If "imax" or specific movie keywords are stronger
        if any(kw in lower for kw in ["imax", "dolby", "ticket", "seats"]):
            result["type"] = "movie"
        else:
            result["type"] = "restaurant"
    else:
        # Unknown — check if first capitalized word could be a movie title
        result["type"] = "restaurant"  # default

    # Service preference (restaurant only)
    if result["type"] == "restaurant":
        if any(kw in lower for kw in RESY_KEYWORDS):
            result["service"] = "resy"
        elif any(kw in lower for kw in OPENTABLE_KEYWORDS):
            result["service"] = "opentable"
        else:
            result["service"] = "resy"  # default

    # Date
    result["date"] = extract_date(text) or "Saturday"

    # Time
    result["time"] = extract_time(text) or ("evening" if result["type"] == "movie" else "19:00")

    # Party / seats
    count = extract_party_size(text)
    if result["type"] == "movie":
        result["seats"] = count or 2
    else:
        result["party"] = count or 2

    # Movie-specific
    if result["type"] == "movie":
        result["format"] = extract_movie_format(text)
        result["title"] = extract_movie_title(text)

    # Restaurant-specific
    if result["type"] == "restaurant":
        result["restaurant"] = extract_restaurant_name(text, [])

    return result


def run_script(script: str, args: list[str]):
    """Run a booking subscript with the venv python."""
    cmd = [PYTHON, str(SCRIPTS_DIR / script)] + args
    print(f"\n▶  {' '.join(cmd)}\n")
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


def main():
    # Check if first arg looks like a natural language request
    if len(sys.argv) == 2 and not sys.argv[1].startswith("--") and len(sys.argv[1]) > 5:
        text = sys.argv[1]
        print(f"🧠 Parsing: \"{text}\"")
        params = parse_natural_language(text)
        print(f"   Detected: {params}")

        if params["type"] == "movie":
            title = params.get("title")
            if not title:
                print("❌ Could not extract movie title from request")
                sys.exit(1)
            args = [
                "--movie", title,
                "--date", str(params["date"]),
                "--time", str(params["time"]),
                "--seats", str(params.get("seats", 2)),
                "--format", params.get("format", "standard"),
            ]
            run_script("amc-book.py", args)

        elif params["type"] == "restaurant":
            restaurant = params.get("restaurant")
            if not restaurant:
                print("❌ Could not extract restaurant name from request")
                sys.exit(1)
            args = [
                "--restaurant", restaurant,
                "--date", str(params["date"]),
                "--time", str(params["time"]),
                "--party", str(params.get("party", 2)),
            ]
            service = params.get("service", "resy")
            if service == "opentable":
                run_script("opentable-book.py", args)
            else:
                run_script("resy-book.py", args)

    # Otherwise, parse structured args
    parser = argparse.ArgumentParser(
        description="Unified booking interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # Mode selection
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--restaurant", "-r", metavar="NAME", help="Restaurant name (uses Resy by default)")
    mode.add_argument("--movie", "-m", metavar="TITLE", help="Movie title (uses AMC)")

    # Shared
    parser.add_argument("--date", "-d", help="Date (YYYY-MM-DD, Saturday, March 21)")
    parser.add_argument("--time", "-t", help="Time (7pm, 19:00, evening)")
    parser.add_argument("--dry-run", action="store_true", help="Find but don't confirm/purchase")
    parser.add_argument("--headless", action="store_true", help="Run browser headless")

    # Restaurant
    parser.add_argument("--party", "-p", type=int, help="Party size (default: 2)")
    parser.add_argument("--location", "-l", help="Location (default: Monmouth County NJ)")
    parser.add_argument("--service", choices=["resy", "opentable"], default="resy",
                        help="Booking service for restaurants (default: resy)")

    # Movie
    parser.add_argument("--seats", "-s", type=int, help="Number of seats (default: 2)")
    parser.add_argument("--format", "-f", help="Format: IMAX, Dolby, standard (default: standard)")
    parser.add_argument("--theater", help="Theater name (default: AMC Monmouth Mall 15)")

    args = parser.parse_args()

    if not args.restaurant and not args.movie:
        parser.print_help()
        sys.exit(0)

    # Build command
    extra = []
    if args.dry_run:
        extra.append("--dry-run")
    if args.headless:
        extra.append("--headless")

    if args.movie:
        cmd_args = ["--movie", args.movie]
        if args.date:
            cmd_args += ["--date", args.date]
        if args.time:
            cmd_args += ["--time", args.time]
        if args.seats:
            cmd_args += ["--seats", str(args.seats)]
        if args.format:
            cmd_args += ["--format", args.format]
        if args.theater:
            cmd_args += ["--theater", args.theater]
        run_script("amc-book.py", cmd_args + extra)

    elif args.restaurant:
        cmd_args = ["--restaurant", args.restaurant]
        if args.date:
            cmd_args += ["--date", args.date]
        if args.time:
            cmd_args += ["--time", args.time]
        if args.party:
            cmd_args += ["--party", str(args.party)]
        if args.location:
            cmd_args += ["--location", args.location]

        script = "opentable-book.py" if args.service == "opentable" else "resy-book.py"
        run_script(script, cmd_args + extra)


if __name__ == "__main__":
    main()
