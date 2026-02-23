#!/usr/bin/env python3
"""
World Situation Monitor
Scans global news using Grok web search and returns a formatted summary.

Usage:
    python3 world-situation-monitor.py          # Print to stdout (for morning briefing)
    python3 world-situation-monitor.py --send   # Also send to Telegram
    python3 world-situation-monitor.py --json   # Output raw JSON

Called by the daily-morning-briefing cron job.
"""

import sys
import os
import json
import argparse
import requests
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# Add clawd paths
sys.path.insert(0, str(Path.home() / "clawd"))
sys.path.insert(0, str(Path.home() / "clawd" / "integrations" / "xai"))

# Load environment
env_path = Path.home() / "clawd" / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                os.environ[key] = val


CACHE_FILE = Path.home() / "clawd" / "data" / "world-situation-cache.json"


def _load_cache() -> dict | None:
    """Load cache if it's less than 2 hours old."""
    try:
        if not CACHE_FILE.exists():
            return None
        with open(CACHE_FILE) as f:
            cache = json.load(f)
        cached_at = datetime.fromisoformat(cache.get("_cached_at", "2000-01-01"))
        age_hours = (datetime.now() - cached_at).total_seconds() / 3600
        if age_hours < 2:
            return cache
    except Exception:
        pass
    return None


def _save_cache(data: dict) -> None:
    """Save result to cache."""
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        data["_cached_at"] = datetime.now().isoformat()
        with open(CACHE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def get_world_situation() -> dict:
    """Pull top world news + geopolitical situation from Grok web search."""
    # Check cache first
    cached = _load_cache()
    if cached:
        return cached

    try:
        from grok import web_search_grok
    except ImportError:
        return {"error": "Grok module not available", "bullets": [], "summary": "World news unavailable"}

    today = datetime.now(ZoneInfo("America/New_York")).strftime("%B %d, %Y")

    prompt = f"""Today is {today}. Search the web for the most important world news from the past 24 hours.

Return a JSON object with these fields:
- "bullets": array of exactly 5 strings, each a one-sentence headline/summary (most important first)
- "cybercab": string — if there's notable Tesla/Cybercab/autonomous vehicle news today, write one sentence; otherwise null
- "market_mood": string — one sentence on overall global market/economic sentiment
- "hot_spot": string — the single most urgent geopolitical situation right now (one sentence)
- "generated_at": "{today}"

Be concise. Each bullet should be factual and specific (include country/actor/number when relevant).
Respond with ONLY the JSON object, no markdown, no code fences."""

    result = web_search_grok(prompt)

    if not result or "error" in result.lower()[:20] if isinstance(result, str) else False:
        return {"error": result, "bullets": [], "summary": "Search failed"}

    # Try to parse JSON from the result
    parsed = None
    if isinstance(result, str):
        # Try direct parse
        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            # Find JSON block in result
            import re
            match = re.search(r'\{.*\}', result, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group())
                except json.JSONDecodeError:
                    pass

    if not parsed:
        # Fallback: treat result as plain text and extract bullets
        lines = [l.strip() for l in result.split('\n') if l.strip() and not l.strip().startswith('{')]
        parsed = {
            "bullets": lines[:5] if lines else ["World news unavailable"],
            "cybercab": None,
            "market_mood": None,
            "hot_spot": None,
            "raw": result[:500]
        }

    _save_cache(parsed)
    return parsed


def get_cybercab_news() -> str | None:
    """Separate Grok X search for Cybercab/Tesla autonomy news."""
    try:
        from grok import ask_grok
    except ImportError:
        return None

    today = datetime.now(ZoneInfo("America/New_York")).strftime("%B %d, %Y")

    result = ask_grok(
        f"Is there any notable Tesla Cybercab or autonomous vehicle news from today, {today}? "
        f"Reply with EXACTLY one sentence if yes (a specific fact: milestone/accident/launch/regulatory). "
        f"Reply with exactly the word QUIET if nothing notable happened."
    )

    if not result:
        return None

    text = str(result).strip()

    # Check for "quiet" signal
    if text.upper() == "QUIET" or text.upper().startswith("QUIET"):
        return None

    # Strip common verbose prefixes Grok sometimes adds
    import re
    text = re.sub(r'^(Based on|According to|As of|On|Today,?\s)', '', text, flags=re.IGNORECASE).strip()

    # Keep only the first sentence
    first_sentence = re.split(r'(?<=[.!?])\s+', text)[0]
    if len(first_sentence) > 220:
        first_sentence = first_sentence[:217] + "..."

    # Final sanity check — if it's too generic, skip it
    vague_phrases = ["no notable", "nothing significant", "no major", "quiet", "no news"]
    if any(p in first_sentence.lower() for p in vague_phrases):
        return None

    return first_sentence


def format_for_telegram(data: dict, cybercab: str | None = None) -> str:
    """Format world situation as clean Telegram message."""
    lines = []

    lines.append("🌍 *WORLD*")

    # Hot spot first if available
    if data.get("hot_spot"):
        lines.append(f"🔴 {data['hot_spot']}")

    # Main bullets
    bullets = data.get("bullets", [])
    for bullet in bullets[:5]:
        bullet = bullet.strip().lstrip("•-* ").strip()
        if bullet:
            lines.append(f"• {bullet}")

    # Market mood
    if data.get("market_mood"):
        lines.append(f"\n📊 {data['market_mood']}")

    # Cybercab (from data or separate search)
    cab = cybercab or data.get("cybercab")
    if cab and cab.strip():
        lines.append(f"\n🚗 *CYBERCAB:* {cab}")

    return "\n".join(lines)


def format_plain(data: dict, cybercab: str | None = None) -> str:
    """Format for plain stdout (used by morning briefing)."""
    return format_for_telegram(data, cybercab)


def send_telegram(text: str) -> bool:
    """Send message via Telegram Bot API."""
    # Load from openclaw config
    try:
        config_path = Path.home() / ".openclaw" / "openclaw.json"
        with open(config_path) as f:
            config = json.load(f)
        bot_token = config.get("channels", {}).get("telegram", {}).get("botToken")
    except Exception:
        bot_token = None

    if not bot_token:
        print("No Telegram bot token found", file=sys.stderr)
        return False

    # Matt's chat ID
    chat_id = "8206180417"

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    resp = requests.post(url, json={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }, timeout=15)

    if resp.ok:
        return True
    else:
        print(f"Telegram send failed: {resp.status_code} {resp.text[:200]}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="World Situation Monitor")
    parser.add_argument("--send", action="store_true", help="Send to Telegram")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument("--no-cybercab", action="store_true", help="Skip Cybercab X search")
    args = parser.parse_args()

    # Fetch world situation
    data = get_world_situation()

    # Optionally fetch Cybercab separately (uses X search — more targeted)
    cybercab = None
    if not args.no_cybercab and not data.get("cybercab"):
        cybercab = get_cybercab_news()

    if args.json:
        if cybercab:
            data["cybercab"] = cybercab
        print(json.dumps(data, indent=2))
        return

    # Format output
    output = format_plain(data, cybercab)
    print(output)

    if args.send:
        success = send_telegram(output)
        if success:
            print("\n✅ Sent to Telegram", file=sys.stderr)
        else:
            print("\n❌ Telegram send failed", file=sys.stderr)


if __name__ == "__main__":
    main()
