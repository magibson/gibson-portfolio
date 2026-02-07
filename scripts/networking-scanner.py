#!/usr/bin/env python3
"""
Networking Events Scanner - Finds business networking events in Monmouth County, NJ
Looks 2-4 weeks ahead and compiles a list for Matt
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add xai integration
sys.path.insert(0, str(Path(__file__).parent.parent / "integrations" / "xai"))

DATA_DIR = Path(__file__).parent.parent / "data" / "networking"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Known recurring events in Monmouth County
RECURRING_EVENTS = [
    {
        "name": "Monmouth Networking Exchange",
        "schedule": "Every Wednesday",
        "time": "7:45 AM",
        "location": "Zoom (quarterly in-person in Freehold)",
        "url": "https://monmouthnetworkingexchange.com/",
        "type": "General Networking",
        "notes": "Virtual meetings, good for consistent weekly networking"
    },
    {
        "name": "Chamber Wake Up Networking",
        "schedule": "Every Wednesday",
        "time": "8:00 AM",
        "location": "Princess Maria Diner, Freehold, NJ",
        "url": "https://www.visitmonmouth.com/EventCalendar.aspx?id=12",
        "type": "Chamber of Commerce",
        "notes": "Weekly speaker + sponsor, great for meeting local professionals"
    },
    {
        "name": "Monmouth/Ocean Business Networking Group",
        "schedule": "2nd Wednesday of month",
        "time": "Evening",
        "location": "Varies - check Meetup",
        "url": "https://www.meetup.com/the-monmouth-ocean-real-estate-network/",
        "type": "Business/Real Estate",
        "notes": "Good mix of professionals, real estate focus but open to all"
    },
    {
        "name": "Young Professionals Group",
        "schedule": "Monthly events",
        "time": "Varies",
        "location": "Various Monmouth County locations",
        "url": "https://www.monmouthregionalchamber.com/young-professionals-group/",
        "type": "Young Professionals",
        "notes": "Perfect for your age group - leadership development focus"
    },
    {
        "name": "BNI Monmouth County Chapters",
        "schedule": "Weekly (various days)",
        "time": "Morning",
        "location": "Multiple locations",
        "url": "https://www.bni.com/",
        "type": "Referral Networking",
        "notes": "Structured referral groups - great for building referral partners"
    }
]

def get_upcoming_dates(weeks_ahead=4):
    """Get key dates for the next N weeks"""
    today = datetime.now()
    dates = {
        "start": today + timedelta(days=14),  # 2 weeks out minimum
        "end": today + timedelta(days=14 + (weeks_ahead * 7)),
        "wednesdays": [],
        "second_wednesdays": []
    }
    
    # Find all Wednesdays in range
    current = dates["start"]
    while current <= dates["end"]:
        if current.weekday() == 2:  # Wednesday
            dates["wednesdays"].append(current)
            # Check if it's the 2nd Wednesday of the month
            if 8 <= current.day <= 14:
                dates["second_wednesdays"].append(current)
        current += timedelta(days=1)
    
    return dates

def search_x_for_events():
    """Search X for networking events in NJ"""
    try:
        from grok import search_x
        
        query = "networking event New Jersey Monmouth County OR Red Bank OR Freehold business professionals February March 2026"
        result = search_x(query, context="Find upcoming business networking events in Monmouth County, New Jersey area. Focus on events suitable for a young financial advisor looking to network with professionals and potential clients.")
        return result
    except Exception as e:
        return f"X search unavailable: {e}"

def generate_report():
    """Generate the networking events report"""
    dates = get_upcoming_dates(4)
    
    report = []
    report.append("🤝 **NETWORKING EVENTS SCANNER**")
    report.append(f"📅 Looking ahead: {dates['start'].strftime('%b %d')} - {dates['end'].strftime('%b %d, %Y')}")
    report.append("")
    
    # Recurring events with specific dates
    report.append("## 📌 RECURRING EVENTS")
    report.append("")
    
    for event in RECURRING_EVENTS:
        report.append(f"**{event['name']}**")
        report.append(f"  📍 {event['location']}")
        report.append(f"  🕐 {event['schedule']} @ {event['time']}")
        report.append(f"  🏷️ {event['type']}")
        report.append(f"  💡 {event['notes']}")
        report.append(f"  🔗 {event['url']}")
        report.append("")
    
    # Specific upcoming dates
    report.append("## 📆 SPECIFIC DATES TO MARK")
    report.append("")
    
    for wed in dates["wednesdays"]:
        date_str = wed.strftime("%A, %B %d")
        events_that_day = ["Chamber Wake Up (8 AM)", "Monmouth Networking Exchange (7:45 AM)"]
        
        if wed in dates["second_wednesdays"]:
            events_that_day.append("Monmouth/Ocean Business Network (Evening)")
        
        report.append(f"**{date_str}**")
        for e in events_that_day:
            report.append(f"  • {e}")
        report.append("")
    
    # X search for additional events
    report.append("## 🔍 ADDITIONAL EVENTS FROM X")
    report.append("")
    x_results = search_x_for_events()
    if x_results and not x_results.startswith("X search unavailable"):
        # Truncate if too long
        if len(x_results) > 1500:
            x_results = x_results[:1500] + "...\n[truncated]"
        report.append(x_results)
    else:
        report.append("_No additional events found on X this week_")
    
    report.append("")
    report.append("---")
    report.append("💡 **Pro tip:** The Wednesday morning events are consistent and low-commitment. Great for building a routine.")
    report.append("")
    report.append("🎯 **Your goal:** Attend at least 1 networking event per week to build your referral network.")
    
    return "\n".join(report)

def save_report(report):
    """Save report to file"""
    timestamp = datetime.now().strftime("%Y-%m-%d")
    output_file = DATA_DIR / f"networking-{timestamp}.md"
    
    with open(output_file, 'w') as f:
        f.write(report)
    
    return output_file

if __name__ == "__main__":
    print("Scanning for networking events...")
    report = generate_report()
    
    if len(sys.argv) > 1 and sys.argv[1] == "save":
        output_file = save_report(report)
        print(f"\nSaved to: {output_file}")
    
    print("\n" + report)
