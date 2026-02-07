#!/usr/bin/env python3
"""
Auto WARN Monitor + Lead Intelligence
Runs the scraper, detects new layoffs, generates outreach intel, and notifies Matt.

This is the "exciting" nightly build - competitive edge on layoff prospecting.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import requests

# Configuration
SCRIPT_DIR = Path(__file__).parent
DATA_FILE = SCRIPT_DIR / "data.json"
ALERTS_FILE = SCRIPT_DIR / "alerts.json"
SEEN_FILE = SCRIPT_DIR / "seen_alerts.json"
INTEL_FILE = SCRIPT_DIR / "lead_intel.json"

# Telegram notification (uses Clawdbot gateway)
NOTIFY_MATT = True

# Thresholds
BIG_LAYOFF = 100  # Employees - definitely worth pursuing
MEDIUM_LAYOFF = 50  # Employees - worth a look
PRIORITY_LOCATIONS = ["monmouth", "ocean", "middlesex", "mercer", "burlington", "camden", "philadelphia", "bucks", "montgomery", "chester", "delaware"]

# Load environment
sys.path.insert(0, str(SCRIPT_DIR.parent.parent / "integrations" / "xai"))


def load_json(path):
    """Load JSON file safely."""
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_json(path, data):
    """Save JSON file."""
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def get_seen_alerts():
    """Get list of alert IDs we've already processed."""
    data = load_json(SEEN_FILE)
    return set(data.get("seen", []))


def mark_alert_seen(alert_id):
    """Mark an alert as seen."""
    data = load_json(SEEN_FILE)
    seen = set(data.get("seen", []))
    seen.add(alert_id)
    save_json(SEEN_FILE, {"seen": list(seen), "last_updated": datetime.now().isoformat()})


def generate_sales_nav_url(company, state):
    """Generate Sales Navigator search URL for a company."""
    # Clean company name
    clean_company = company.strip()
    
    # Remove common suffixes for better search
    for suffix in [", Inc.", ", LLC", ", Inc", " Inc.", " LLC", " Corp.", " Corporation", " Co."]:
        if clean_company.endswith(suffix):
            clean_company = clean_company[:-len(suffix)]
    
    # URL encode
    from urllib.parse import quote
    encoded = quote(clean_company)
    
    # Basic Sales Nav search - Matt can apply his Persona for filters
    url = f"https://www.linkedin.com/sales/search/people?query=(filters:List((type:CURRENT_COMPANY,values:List((text:{encoded},selectionType:INCLUDED)))))"
    
    return url


def generate_outreach_angles(notice):
    """Generate outreach angles and talking points for a layoff."""
    company = notice.get("company", "Unknown")
    affected = notice.get("affected", 0)
    city = notice.get("city", "")
    state = notice.get("state", "")
    notice_type = notice.get("type", "Layoff")
    date = notice.get("date", "")
    
    angles = []
    
    # 401k rollover angle (always relevant)
    angles.append({
        "angle": "401k Rollover",
        "hook": f"With {company}'s {notice_type.lower()}, employees may have orphaned 401ks. Perfect rollover opportunity.",
        "opener": f"I noticed {company} recently announced changes. Many people in transition forget about their 401k options — I help people consolidate and optimize their retirement savings during career transitions."
    })
    
    # Life insurance angle (especially for closings)
    if notice_type == "Closing" or affected >= 100:
        angles.append({
            "angle": "Life Insurance Gap",
            "hook": "Group life insurance ends when employment ends. Many don't realize they're suddenly unprotected.",
            "opener": f"During transitions like what's happening at {company}, one thing people often overlook is that their group life insurance coverage typically ends. I help people ensure their families stay protected."
        })
    
    # Financial planning angle
    if affected >= 50:
        angles.append({
            "angle": "Severance & Cash Management", 
            "hook": "Severance packages need smart management. Lump sums can be optimized.",
            "opener": f"Career transitions often come with important financial decisions — severance, benefits elections, cash management. I help people navigate these transitions strategically."
        })
    
    # Executive angle (for larger layoffs)
    if affected >= 200:
        angles.append({
            "angle": "Executive Planning",
            "hook": "Senior leaders at larger companies often have complex comp (stock, deferred, etc). Need planning.",
            "opener": f"For leaders at {company} navigating this transition, there are often complex compensation elements to consider — stock options, deferred comp, executive benefits. I specialize in helping executives optimize these situations."
        })
    
    return angles


def calculate_priority(notice):
    """Calculate priority score for a notice (1-10)."""
    score = 5  # Base score
    
    affected = notice.get("affected", 0)
    city = notice.get("city", "").lower()
    county = notice.get("county", "").lower()
    state = notice.get("state", "")
    
    # Size scoring
    if affected >= 500:
        score += 3
    elif affected >= 200:
        score += 2
    elif affected >= 100:
        score += 1
    elif affected < 50:
        score -= 1
    
    # Location scoring (closer to Matt's area = higher priority)
    location = f"{city} {county}".lower()
    for priority_loc in PRIORITY_LOCATIONS:
        if priority_loc in location:
            score += 2
            break
    
    # NJ slightly higher priority than PA (Matt's home state)
    if state == "NJ":
        score += 1
    
    # Cap at 10
    return min(10, max(1, score))


def format_intel_message(notice, intel):
    """Format a Telegram message for a new layoff."""
    priority = intel["priority"]
    priority_emoji = "🔴" if priority >= 8 else "🟡" if priority >= 6 else "🟢"
    
    msg = f"""{priority_emoji} **NEW WARN ALERT** (Priority: {priority}/10)

**{notice['company']}** ({notice['state']})
📍 {notice.get('city', 'Unknown')}
👥 {notice['affected']} employees affected
📅 Effective: {notice.get('date', 'TBD')}
📋 Type: {notice.get('type', 'Layoff')}

**Top Outreach Angle:**
_{intel['angles'][0]['angle']}_
{intel['angles'][0]['hook']}

🔗 [Search on Sales Navigator]({intel['sales_nav_url']})
"""
    return msg


def run_scraper():
    """Run the main scraper script."""
    print("🔍 Running WARN scraper...")
    result = subprocess.run(
        ["python3", str(SCRIPT_DIR / "scraper.py")],
        capture_output=True,
        text=True,
        cwd=str(SCRIPT_DIR)
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"Scraper error: {result.stderr}")
    return result.returncode == 0


def notify_telegram(message):
    """Send notification via Clawdbot message tool (writes to stdout for Clawdbot to pick up)."""
    # For now, just print - the calling script can capture this
    print(f"\n📱 NOTIFICATION:\n{message}\n")
    return True


def main():
    """Main monitoring function."""
    print(f"=== Auto WARN Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    
    # Run scraper first
    if not run_scraper():
        print("⚠️ Scraper had issues, but continuing with existing data...")
    
    # Load data
    data = load_json(DATA_FILE)
    notices = data.get("notices", [])
    seen = get_seen_alerts()
    
    print(f"📊 Total notices in database: {len(notices)}")
    
    # Find new alerts we haven't processed
    new_intel = []
    
    for notice in notices:
        notice_id = notice.get("id", "")
        is_new = notice.get("is_new", False)
        affected = notice.get("affected", 0)
        
        # Process if: new AND not seen AND significant size
        if is_new and notice_id not in seen and affected >= MEDIUM_LAYOFF:
            print(f"\n🆕 New alert: {notice.get('company')} ({affected} employees)")
            
            # Generate intelligence
            intel = {
                "notice_id": notice_id,
                "company": notice.get("company"),
                "state": notice.get("state"),
                "city": notice.get("city"),
                "affected": affected,
                "date": notice.get("date"),
                "type": notice.get("type"),
                "sales_nav_url": generate_sales_nav_url(notice.get("company", ""), notice.get("state", "")),
                "angles": generate_outreach_angles(notice),
                "priority": calculate_priority(notice),
                "generated_at": datetime.now().isoformat()
            }
            
            new_intel.append(intel)
            mark_alert_seen(notice_id)
            
            # Notify for high-priority alerts
            if intel["priority"] >= 6 and NOTIFY_MATT:
                msg = format_intel_message(notice, intel)
                notify_telegram(msg)
    
    # Save all intel
    if new_intel:
        existing_intel = load_json(INTEL_FILE)
        all_intel = existing_intel.get("intel", [])
        all_intel.extend(new_intel)
        
        # Keep last 100
        all_intel = sorted(all_intel, key=lambda x: x.get("generated_at", ""), reverse=True)[:100]
        
        save_json(INTEL_FILE, {
            "intel": all_intel,
            "last_updated": datetime.now().isoformat(),
            "total_processed": len(all_intel)
        })
        
        print(f"\n✅ Generated intel for {len(new_intel)} new alerts")
        print(f"📁 Saved to {INTEL_FILE}")
    else:
        print("\n✅ No new significant layoffs detected")
    
    # Summary
    print(f"\n=== Summary ===")
    print(f"Total notices: {len(notices)}")
    print(f"New intel generated: {len(new_intel)}")
    high_priority = [i for i in new_intel if i["priority"] >= 8]
    if high_priority:
        print(f"🔴 HIGH PRIORITY alerts: {len(high_priority)}")
        for hp in high_priority:
            print(f"   - {hp['company']} ({hp['affected']} employees, {hp['state']})")


if __name__ == "__main__":
    main()
