#!/usr/bin/env python3
"""
Food Journal — Jarvis Tool for Matt Gibson
Logs meals using natural language via Gemini API.

Usage:
    python3 food-log.py "had eggs and coffee for breakfast, subway sandwich for lunch, pizza for dinner"

Data saved to: ~/clawd/data/health/food-log.json

Telegram shortcut:
    Text me: "food: [what you ate]" or "ate: [food description]"
    I'll call this script automatically.
"""

import sys
import json
import os
import requests
from datetime import datetime, timezone

# ─── Config ──────────────────────────────────────────────────────────────────
GEMINI_API_KEY = "AIzaSyCcuSJULuk7MFemZtUrzS0x0WtEJGR2IGM"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
FOOD_LOG_PATH = os.path.expanduser("~/clawd/data/health/food-log.json")

PARSE_PROMPT = """You are a nutrition assistant. Parse the following meal description into structured JSON.

Rules:
- Identify each distinct meal (breakfast, lunch, dinner, snack).
- List individual foods for each meal.
- Estimate calories per meal (be conservative and realistic).
- Give a daily health score from 1-10 (10 = perfectly clean eating, 1 = all junk).
- Sum up total daily calories.
- Add brief notes if relevant (e.g., "Subway = fast food", "coffee = no calories if black").
- If a meal type is ambiguous, infer from context or time references.

Respond ONLY with valid JSON, no markdown, no explanation. Format:
{
  "meals": [
    {
      "type": "breakfast",
      "foods": ["eggs", "coffee"],
      "calories_est": 250,
      "notes": ""
    }
  ],
  "daily_score": 6,
  "daily_calories_est": 1800
}

Meal description: """


# ─── Gemini Call ─────────────────────────────────────────────────────────────
def parse_food_with_gemini(description: str) -> dict:
    """Use Gemini to parse natural language food input into structured data."""
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": PARSE_PROMPT + description}],
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 500,
        },
    }

    resp = requests.post(
        f"{GEMINI_URL}?key={GEMINI_API_KEY}",
        headers=headers,
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    raw = data["candidates"][0]["content"]["parts"][0]["text"].strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    return json.loads(raw)


# ─── Storage ──────────────────────────────────────────────────────────────────
def load_log() -> dict:
    """Load existing food log or create empty structure."""
    if os.path.exists(FOOD_LOG_PATH):
        with open(FOOD_LOG_PATH) as f:
            return json.load(f)
    return {"entries": []}


def save_log(log: dict) -> None:
    """Save food log to disk."""
    os.makedirs(os.path.dirname(FOOD_LOG_PATH), exist_ok=True)
    with open(FOOD_LOG_PATH, "w") as f:
        json.dump(log, f, indent=2)


def get_today_str() -> str:
    """Get today's date as YYYY-MM-DD."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def upsert_entry(log: dict, parsed: dict, raw_input: str) -> dict:
    """Add or update today's entry in the log."""
    today = get_today_str()
    entries = log.get("entries", [])

    # Find existing entry for today
    existing = next((e for e in entries if e.get("date") == today), None)

    if existing:
        # Merge meals: add new meals, avoid duplicates by type
        existing_types = {m["type"] for m in existing["meals"]}
        for meal in parsed.get("meals", []):
            if meal["type"] not in existing_types:
                existing["meals"].append(meal)
            else:
                # Update existing meal of same type
                for em in existing["meals"]:
                    if em["type"] == meal["type"]:
                        em["foods"] = list(set(em["foods"] + meal["foods"]))
                        em["calories_est"] = meal["calories_est"]
                        em["notes"] = meal.get("notes", "")

        # Recalculate totals
        existing["daily_calories_est"] = sum(m.get("calories_est", 0) for m in existing["meals"])
        existing["daily_score"] = parsed.get("daily_score", existing.get("daily_score", 5))
        existing["raw_input"] = existing.get("raw_input", "") + " | " + raw_input
        return existing
    else:
        new_entry = {
            "date": today,
            "meals": parsed.get("meals", []),
            "daily_score": parsed.get("daily_score", 5),
            "daily_calories_est": parsed.get("daily_calories_est", 0),
            "raw_input": raw_input,
        }
        entries.append(new_entry)
        log["entries"] = entries
        return new_entry


# ─── Confirmation Print ───────────────────────────────────────────────────────
def format_confirmation(entry: dict) -> str:
    """Format a brief confirmation line."""
    parts = []
    for meal in entry.get("meals", []):
        meal_type = meal["type"].capitalize()
        foods = ", ".join(meal.get("foods", []))
        cal = meal.get("calories_est", 0)
        notes = meal.get("notes", "")
        label = f"{meal_type} ({foods} ~{cal}cal)"
        if notes:
            label += f" [{notes}]"
        parts.append(label)

    score = entry.get("daily_score", "?")
    total_cal = entry.get("daily_calories_est", 0)
    confirmation = " · ".join(parts)
    return f"Logged: {confirmation} · Daily score: {score}/10 · Est. total: ~{total_cal}cal"


# ─── Main ─────────────────────────────────────────────────────────────────────
def log_food(description: str) -> dict:
    """Full pipeline: parse → store → confirm."""
    print(f"🍽️  Parsing food log with Gemini...", end="", flush=True)
    parsed = parse_food_with_gemini(description)
    print(" ✓")

    log = load_log()
    entry = upsert_entry(log, parsed, description)
    save_log(log)

    confirmation = format_confirmation(entry)
    print(confirmation)
    return entry


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 food-log.py \"had eggs and coffee for breakfast, sandwich for lunch\"")
        print("\nTelegram shortcut: Text me 'food: [what you ate]' or 'ate: [food]'")
        sys.exit(1)

    description = " ".join(sys.argv[1:])
    log_food(description)


if __name__ == "__main__":
    main()


# ─── Module Interface (for briefing integration) ──────────────────────────────
def get_food_trend(days: int = 3) -> str:
    """
    Read last N days of food logs and return a trend string for morning briefing.
    Returns: "🍽️ Food: 3-day avg score 5/10 — room to improve"
    """
    if not os.path.exists(FOOD_LOG_PATH):
        return "🍽️ Food: No food logs yet — start logging with food-log.py"

    with open(FOOD_LOG_PATH) as f:
        log = json.load(f)

    entries = log.get("entries", [])
    if not entries:
        return "🍽️ Food: No entries logged"

    # Sort by date descending, take last N days
    entries_sorted = sorted(entries, key=lambda e: e.get("date", ""), reverse=True)
    recent = entries_sorted[:days]

    if not recent:
        return "🍽️ Food: No recent entries"

    scores = [e.get("daily_score", 0) for e in recent if e.get("daily_score")]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0

    avg_cal = round(sum(e.get("daily_calories_est", 0) for e in recent) / len(recent))

    # Trend commentary
    if avg_score >= 8:
        comment = "great streak 💪"
    elif avg_score >= 6:
        comment = "solid, keep it up"
    elif avg_score >= 4:
        comment = "room to improve"
    else:
        comment = "time to clean it up"

    days_actual = len(recent)
    return f"🍽️ Food: {days_actual}-day avg score {avg_score}/10, ~{avg_cal}cal/day — {comment}"
