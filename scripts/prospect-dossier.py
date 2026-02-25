#!/usr/bin/env python3
"""
Prospect Intelligence Dossier
==============================
Generates a 1-page research brief on a lead for Matt's financial advisor cold calls.

Usage:
    python prospect-dossier.py --name "Caitlyn Haberle" --address "2 Wendi Way, Manalapan, NJ"
    python prospect-dossier.py --name "John Smith" --linkedin "https://linkedin.com/in/john-smith"
    python prospect-dossier.py --csv ~/clawd/leads/priority_dial_2026-02-24.csv --row 1
    python prospect-dossier.py --csv ~/clawd/leads/priority_dial_2026-02-24.csv --all

Output:
    ~/clawd/leads/dossiers/<Name>_dossier.md  (and .pdf via md-to-pdf)
"""

import os
import sys
import csv
import json
import argparse
import re
from pathlib import Path
from datetime import datetime

# ── path setup ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent          # ~/clawd
sys.path.insert(0, str(ROOT / "integrations" / "gemini"))
sys.path.insert(0, str(ROOT / "integrations" / "xai"))

from gemini import ask as gemini_ask
import grok as grok_module

DOSSIER_DIR = ROOT / "leads" / "dossiers"
DOSSIER_DIR.mkdir(parents=True, exist_ok=True)


# ── helpers ───────────────────────────────────────────────────────────────────

def grok_x_search(query: str) -> str:
    """Search X/Twitter via Grok. Falls back gracefully."""
    try:
        return grok_module.search_x(query)
    except Exception as e:
        return f"[X search unavailable: {e}]"

def grok_web(query: str) -> str:
    """Web search via Grok."""
    try:
        return grok_module.web_search_grok(query)
    except Exception as e:
        return f"[Grok web search unavailable: {e}]"

def gemini(prompt: str) -> str:
    """Research via Gemini."""
    try:
        return gemini_ask(prompt)
    except Exception as e:
        return f"[Gemini unavailable: {e}]"

def slugify(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name.strip())


# ── research modules ──────────────────────────────────────────────────────────

def research_linkedin(name: str, address: str = "", linkedin_url: str = "") -> str:
    """Pull LinkedIn profile info via Gemini web search."""
    if linkedin_url:
        prompt = f"""Search LinkedIn and the web for this profile: {linkedin_url}

Extract and return:
- Full name
- Current job title and employer
- Previous roles (last 2)
- Location
- Education
- Any recent job changes (within 12 months)
- Approximate years in financial services if any
- Any public accomplishments or certifications

Be factual. If info is not findable, say 'not found'."""
    else:
        location = address.split(",")[-2].strip() if "," in address else ""
        prompt = f"""Search LinkedIn and the web for: "{name}" financial professional {location} NJ

I need their LinkedIn profile. Extract:
- Current job title and employer
- Previous roles (last 2)  
- Approximate income bracket based on title/industry (entry/mid/senior/exec = <$60k / $60-120k / $120-250k / $250k+)
- Any recent job changes (within 12 months)
- Education background
- Any certifications or notable career moves

If you find multiple people with this name, prioritize the NJ resident near {location}.
Be factual. Say 'not found' for missing fields."""
    
    return gemini(prompt)


def research_property(name: str, address: str) -> str:
    """Research the property and estimate household financial profile."""
    if not address:
        return "No address provided."
    
    prompt = f"""Research this property and homeowner profile:
Name: {name}
Address: {address}

Find and return:
1. Property details (home value estimate, year bought, purchase price if known)
2. Any recent purchase or refinance activity (within 24 months)
3. Household income estimate based on neighborhood + home value
4. Whether they have a mortgage (likely if recent purchase)
5. Any public records: marriage, divorce, new dependents, business filings for this person in NJ

Use public data sources: Zillow, Redfin, county records, Whitepages. Be factual."""
    
    return gemini(prompt)


def research_life_events(name: str, address: str = "", linkedin_url: str = "") -> str:
    """Search for recent life events: job change, new home, family events."""
    location = ""
    if address and "," in address:
        parts = [p.strip() for p in address.split(",")]
        location = parts[-2] if len(parts) >= 2 else parts[0]
    
    prompt = f"""Search for recent life events (past 12-18 months) for:
Name: {name}
Location: {location or 'New Jersey'}
{f'LinkedIn: {linkedin_url}' if linkedin_url else ''}

Look for:
- Job change or promotion (new employer, new title)
- New home purchase or move
- Marriage or new baby/children
- Business launch or acquisition
- Retirement or major career transition
- Any public announcements

Use news searches, LinkedIn, Facebook, local NJ news, public records.
List each event found with approximate date and source."""
    
    return gemini(prompt)


def research_social_presence(name: str, address: str = "") -> str:
    """Search X/Twitter and web for social media presence."""
    location = ""
    if address and "," in address:
        parts = [p.strip() for p in address.split(",")]
        location = parts[-2] if len(parts) >= 2 else ""
    
    query = f'"{name}" {location} NJ'
    
    x_result = grok_x_search(f"{name} {location} NJ financial OR insurance OR home OR mortgage")
    
    # Also check via Gemini for broader social presence
    web_result = gemini(f"""Search for social media presence of "{name}" from {location or 'New Jersey'}:
- Any Twitter/X account?
- Facebook profile (public)?
- Instagram?
- Any public posts about finances, home buying, career changes?
- Any mentions in local NJ news or community groups?

Return handles/URLs found and any relevant posts. Keep it brief.""")
    
    return f"X/Twitter search:\n{x_result}\n\nBroader social/web:\n{web_result}"


def generate_conversation_starters(
    name: str,
    address: str,
    linkedin_info: str,
    life_events: str,
    property_info: str,
    social_info: str
) -> str:
    """Use Gemini to synthesize 3 tailored conversation starters."""
    
    prompt = f"""You are a financial advisor coach. Based on this prospect research, write 3 SPECIFIC cold-call conversation starters for Matt, a financial advisor in New Jersey.

PROSPECT: {name}
ADDRESS: {address}

LINKEDIN/CAREER INFO:
{linkedin_info[:800]}

LIFE EVENTS:
{life_events[:600]}

PROPERTY INFO:
{property_info[:600]}

SOCIAL/OTHER:
{social_info[:400]}

Rules for conversation starters:
1. Each should be 2-3 sentences max — natural, not salesy
2. Reference a SPECIFIC detail from the research (not generic)
3. Lead with value or empathy, not a pitch
4. Tie to a financial planning need: mortgage protection, income replacement, retirement, college savings, business succession
5. Sound like a real human, not a robot

Format:
**Opener 1 — [Hook Type]:**
[The opener text]

**Opener 2 — [Hook Type]:**
[The opener text]

**Opener 3 — [Hook Type]:**
[The opener text]

Then add one line: **Best time to call:** [morning/evening/weekend based on their profile]"""
    
    return gemini(prompt)


# ── dossier assembly ──────────────────────────────────────────────────────────

def build_dossier(
    name: str,
    address: str = "",
    linkedin_url: str = "",
    email: str = "",
    phone: str = "",
    extra_context: str = ""
) -> tuple[str, Path]:
    """
    Run all research modules and assemble a 1-page dossier.
    Returns (markdown_text, output_path).
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n🔍 Building dossier for: {name}")
    print(f"   Address: {address or 'N/A'} | LinkedIn: {linkedin_url or 'N/A'}")
    
    print("   [1/5] LinkedIn & career research...")
    linkedin_info = research_linkedin(name, address, linkedin_url)
    
    print("   [2/5] Property & financial profile...")
    property_info = research_property(name, address) if address else "No address provided."
    
    print("   [3/5] Life events research...")
    life_events = research_life_events(name, address, linkedin_url)
    
    print("   [4/5] Social media presence...")
    social_info = research_social_presence(name, address)
    
    print("   [5/5] Generating conversation starters...")
    convo_starters = generate_conversation_starters(
        name, address, linkedin_info, life_events, property_info, social_info
    )
    
    # ── assemble markdown ──
    md = f"""# Prospect Intelligence Dossier
## {name}
*Generated: {now} | For: Matt's Cold Call Pipeline*

---

### 📋 Contact Info
| Field | Value |
|-------|-------|
| **Name** | {name} |
| **Address** | {address or '—'} |
| **Phone** | {phone or '—'} |
| **Email** | {email or '—'} |
| **LinkedIn** | {linkedin_url or '—'} |
{f'| **Notes** | {extra_context} |' if extra_context else ''}

---

### 💼 LinkedIn & Career Profile
{linkedin_info}

---

### 🏠 Property & Financial Snapshot
{property_info}

---

### 🔄 Recent Life Events
{life_events}

---

### 📱 Social Media Presence
{social_info}

---

### 🎯 Conversation Starters (Cold Call)
{convo_starters}

---
*Dossier built by Jarvis | Sources: Gemini (web/LinkedIn research), Grok (X search) | {now}*
"""
    
    # ── save file ──
    slug = slugify(name)
    date_str = datetime.now().strftime("%Y%m%d")
    out_path = DOSSIER_DIR / f"{slug}_dossier_{date_str}.md"
    out_path.write_text(md, encoding="utf-8")
    print(f"\n✅ Dossier saved: {out_path}")
    
    return md, out_path


def pdf_render(md_path: Path) -> Path | None:
    """Attempt to render markdown to PDF using the existing md-to-pdf script."""
    pdf_script = ROOT / "scripts" / "md-to-pdf-playwright.py"
    if not pdf_script.exists():
        pdf_script = ROOT / "scripts" / "md-to-pdf.py"
    if not pdf_script.exists():
        return None
    
    import subprocess
    pdf_path = md_path.with_suffix(".pdf")
    result = subprocess.run(
        [sys.executable, str(pdf_script), str(md_path), str(pdf_path)],
        capture_output=True, text=True
    )
    if result.returncode == 0 and pdf_path.exists():
        print(f"📄 PDF saved: {pdf_path}")
        return pdf_path
    else:
        print(f"  (PDF render skipped/failed: {result.stderr[:100]})")
        return None


def print_dossier(md: str):
    """Print a clean version to terminal."""
    print("\n" + "═" * 70)
    # Strip markdown tables for cleaner terminal display
    for line in md.split("\n"):
        print(line)
    print("═" * 70)


# ── CSV pipeline integration ──────────────────────────────────────────────────

def load_lead_from_csv(csv_path: str, row_num: int = 1) -> dict:
    """Load a single lead from the standard priority_dial CSV format."""
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    if row_num < 1 or row_num > len(rows):
        raise ValueError(f"Row {row_num} out of range (CSV has {len(rows)} data rows)")
    
    row = rows[row_num - 1]
    
    # Normalize field names (handle both CSV formats)
    name = row.get("Name", row.get("name", ""))
    address_parts = [
        row.get("Property Address", row.get("Address", "")),
        row.get("City", ""),
        row.get("State", "NJ"),
        row.get("Zip", ""),
    ]
    address = ", ".join(p for p in address_parts if p.strip())
    
    return {
        "name": name,
        "address": address,
        "email": row.get("Email", row.get("email", "")),
        "phone": row.get("Phone 1", row.get("Phone", "")),
        "extra_context": row.get("Call Blurb", row.get("Score", "")),
        "linkedin_url": row.get("LinkedIn URL", row.get("linkedin_url", "")),
    }


def process_all_csv(csv_path: str, limit: int = 5):
    """Build dossiers for top N leads in a CSV."""
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"\n📂 Processing {min(limit, len(rows))} leads from {csv_path}")
    results = []
    
    for i, row in enumerate(rows[:limit], 1):
        lead = load_lead_from_csv(csv_path, i)
        if not lead["name"]:
            continue
        md, path = build_dossier(**lead)
        results.append((lead["name"], path))
        print(f"  [{i}/{min(limit, len(rows))}] Done: {lead['name']}")
    
    return results


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Prospect Intelligence Dossier — generates 1-page research brief for cold calls"
    )
    
    # Input modes
    parser.add_argument("--name", help="Lead's full name")
    parser.add_argument("--address", default="", help="Property address (e.g. '2 Wendi Way, Manalapan, NJ')")
    parser.add_argument("--linkedin", default="", help="LinkedIn profile URL")
    parser.add_argument("--email", default="", help="Email address")
    parser.add_argument("--phone", default="", help="Phone number")
    parser.add_argument("--context", default="", help="Extra context (e.g. 'new homeowner, 4BR')")
    
    # CSV pipeline
    parser.add_argument("--csv", help="Path to leads CSV (priority_dial format)")
    parser.add_argument("--row", type=int, default=1, help="Row number in CSV (1-indexed, default: 1)")
    parser.add_argument("--all", action="store_true", help="Process all leads in CSV (up to --limit)")
    parser.add_argument("--limit", type=int, default=5, help="Max leads when using --all (default: 5)")
    
    # Output
    parser.add_argument("--pdf", action="store_true", help="Also render to PDF")
    parser.add_argument("--quiet", action="store_true", help="Don't print dossier to terminal")
    
    args = parser.parse_args()
    
    # ── CSV mode ──
    if args.csv:
        if args.all:
            results = process_all_csv(args.csv, limit=args.limit)
            print(f"\n✅ Built {len(results)} dossiers in {DOSSIER_DIR}/")
            return
        else:
            lead = load_lead_from_csv(args.csv, args.row)
            md, path = build_dossier(**lead)
    
    # ── Manual mode ──
    elif args.name:
        md, path = build_dossier(
            name=args.name,
            address=args.address,
            linkedin_url=args.linkedin,
            email=args.email,
            phone=args.phone,
            extra_context=args.context,
        )
    
    else:
        parser.print_help()
        sys.exit(1)
    
    # ── output ──
    if not args.quiet:
        print_dossier(md)
    
    if args.pdf:
        pdf_render(path)
    
    print(f"\n📁 Saved to: {path}")


if __name__ == "__main__":
    main()
