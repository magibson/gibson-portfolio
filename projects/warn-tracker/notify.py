#!/usr/bin/env python3
"""
WARN Act Alert Notifier — with Prospector Pipeline
Checks for new big layoffs (100+ employees) and:
  1. Notifies Matt via Telegram
  2. Creates a Sales Navigator search URL
  3. Inserts a campaign into the Prospector DB
  4. Pre-drafts layoff outreach messages via Gemini
"""

import json
import os
import sqlite3
import sys
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent
ALERTS_FILE = BASE_DIR / "alerts.json"
SEEN_FILE = BASE_DIR / "seen_alerts.json"

# Prospector DB path (absolute, works from any cwd)
PROSPECTOR_DB = Path.home() / "clawd" / "projects" / "linkedin-prospector" / "server" / "prospector.db"

# ── Helpers ──────────────────────────────────────────────────────────────────

def load_json(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def make_sales_nav_url(company_name: str) -> str:
    """Generate a LinkedIn Sales Navigator people search URL for a company."""
    encoded = urllib.parse.quote(company_name, safe="")
    return (
        "https://www.linkedin.com/sales/search/people?"
        "query=(filters:List((type:CURRENT_COMPANY,values:List("
        f"(text:{encoded},selectionType:INCLUDED)))))"
    )


def insert_campaign(company_name: str, affected: int, date_str: str,
                    sales_nav_url: str, message_context: str,
                    connection_template: str = "", followup_template: str = ""):
    """Insert a new campaign into the Prospector DB. Returns campaign id or None."""
    if not PROSPECTOR_DB.exists():
        print(f"⚠️  Prospector DB not found at {PROSPECTOR_DB}", file=sys.stderr)
        return None

    campaign_name = f"WARN - {company_name} - {date_str}"
    description = (
        f"{affected} employees laid off on {date_str} per WARN Act. "
        f"Target: 401k rollover, severance investment, insurance gap."
    )

    try:
        conn = sqlite3.connect(str(PROSPECTOR_DB))
        cur = conn.cursor()

        # Check if a campaign with this name already exists
        cur.execute("SELECT id FROM campaigns WHERE name = ?", (campaign_name,))
        existing = cur.fetchone()
        if existing:
            print(f"  ℹ️  Campaign already exists (id={existing[0]}): {campaign_name}")
            conn.close()
            return existing[0]

        cur.execute(
            """INSERT INTO campaigns
               (name, description, sales_nav_url, message_context,
                connection_template, followup_template, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, 'active', datetime('now'), datetime('now'))""",
            (campaign_name, description, sales_nav_url, message_context,
             connection_template, followup_template)
        )
        conn.commit()
        campaign_id = cur.lastrowid
        conn.close()
        print(f"  ✅ Campaign created (id={campaign_id}): {campaign_name}")
        return campaign_id
    except Exception as e:
        print(f"  ❌ DB error: {e}", file=sys.stderr)
        return None


def generate_outreach(company_name: str, affected: int, location: str) -> dict:
    """Generate outreach messages via layoff_outreach module."""
    try:
        sys.path.insert(0, str(BASE_DIR))
        from layoff_outreach import generate_layoff_messages
        return generate_layoff_messages(company_name, affected, location)
    except Exception as e:
        print(f"  ⚠️  Outreach generation failed: {e}", file=sys.stderr)
        encoded = urllib.parse.quote(company_name, safe="")
        return {
            "connection_request": (
                f"Hi [Name], I saw {company_name} recently went through some changes. "
                f"I work with people navigating career transitions on the financial side — happy to connect."
            )[:300],
            "followup_dm": (
                f"Thanks for connecting! With the transition at {company_name}, one key decision "
                f"coming up is what to do with your 401k — it's time-sensitive and often overlooked. "
                f"I offer a free 30-min call to walk through options, no pressure. Interested?"
            )[:500],
            "sales_nav_url": (
                "https://www.linkedin.com/sales/search/people?query=(filters:List((type:CURRENT_COMPANY,"
                f"values:List((text:{encoded},selectionType:INCLUDED)))))"
            )
        }


def format_notification(alert: dict, sales_nav_url: str, campaign_name: str) -> str:
    """Format the enriched Telegram notification for a single layoff alert."""
    company  = alert.get("company", "Unknown")
    city     = alert.get("city", "").replace("\r\n", ", ").strip()
    state    = alert.get("state", "")
    affected = alert.get("affected", "?")
    date     = alert.get("date", "TBD")
    location = f"{city}, {state}".strip(", ") if city else state

    lines = [
        f"🚨 WARN Alert — New Layoff Opportunity",
        f"",
        f"🏢 {company}",
        f"📍 {location}",
        f"👥 {affected} employees",
        f"📅 Effective: {date}",
        f"",
        f"🔗 Sales Nav Search:",
        f"{sales_nav_url}",
        f"",
        f"📁 Campaign created in Prospector: {campaign_name}",
        f"",
        f"✉️  Outreach drafted — open extension and scrape to get leads",
    ]
    return "\n".join(lines)


def main():
    # Load current alerts and seen IDs
    alerts_data = load_json(ALERTS_FILE)
    seen_data   = load_json(SEEN_FILE)
    seen_ids    = set(seen_data.get("seen", []))

    big_layoffs = alerts_data.get("big_layoffs", [])

    # Find truly new alerts (not in seen list)
    new_alerts = [a for a in big_layoffs if a["id"] not in seen_ids]

    # Filter to only recent ones (within last 7 days of first_seen)
    recent_new = []
    cutoff = datetime.now() - timedelta(days=7)
    for alert in new_alerts:
        try:
            first_seen = datetime.fromisoformat(alert.get("first_seen", ""))
            if first_seen > cutoff:
                recent_new.append(alert)
        except Exception:
            recent_new.append(alert)  # include if no valid first_seen

    if not recent_new:
        all_ids = [a["id"] for a in big_layoffs]
        save_json(SEEN_FILE, {"seen": all_ids, "last_check": datetime.now().isoformat()})
        print("No new big layoffs.")
        return None

    # Sort biggest first, cap at 5 for the notification
    recent_new.sort(key=lambda x: x.get("affected", 0), reverse=True)
    notification_alerts = recent_new[:5]

    print(f"🔍 Found {len(recent_new)} new layoff(s) ≥100 employees. Processing top {len(notification_alerts)}...\n")

    notification_blocks = []
    for alert in notification_alerts:
        company  = alert.get("company", "Unknown")
        affected = alert.get("affected", 0)
        city     = alert.get("city", "").replace("\r\n", ", ").strip()
        state    = alert.get("state", "")
        date_str = alert.get("date", datetime.now().strftime("%Y-%m-%d"))
        location = f"{city}, {state}".strip(", ") if city else state

        print(f"  → {company} ({affected} employees, {location})")

        # 1. Build Sales Nav URL
        sales_nav_url = make_sales_nav_url(company)
        print(f"     Sales Nav URL generated")

        # 2. Generate outreach via Gemini
        print(f"     Generating outreach messages via Gemini...")
        outreach = generate_outreach(company, affected, location)

        # 3. Insert Prospector campaign
        message_context = "career transition / layoff - empathetic approach, focus on 401k rollover decision"
        campaign_id = insert_campaign(
            company_name       = company,
            affected           = affected,
            date_str           = date_str,
            sales_nav_url      = sales_nav_url,
            message_context    = message_context,
            connection_template = outreach.get("connection_request", ""),
            followup_template  = outreach.get("followup_dm", ""),
        )
        campaign_name = f"WARN - {company} - {date_str}"

        # 4. Build notification block
        notification_blocks.append(
            format_notification(alert, sales_nav_url, campaign_name)
        )

    # Build full message
    header = f"🚨 **{len(recent_new)} New Big Layoff{'s' if len(recent_new) > 1 else ''}** (WARN Act)\n"
    if len(recent_new) > 5:
        footer = f"\n_...and {len(recent_new) - 5} more. Check dashboard._"
    else:
        footer = ""

    message = header + "\n─────────────────────\n".join(notification_blocks) + footer

    print("\n" + "="*60)
    print("📱 NOTIFICATION TO MATT:")
    print(message)
    print("="*60)

    # Mark all current big layoffs as seen
    all_ids = [a["id"] for a in big_layoffs]
    save_json(SEEN_FILE, {"seen": all_ids, "last_check": datetime.now().isoformat()})

    return message


if __name__ == "__main__":
    main()
