#!/usr/bin/env python3
"""
Jarvis Work Log Calendar Integration
Logs work activities to a dedicated Google Calendar
"""

import json
import requests
import sys
from datetime import datetime, timedelta, timezone
import os

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLAWD_DIR = os.path.dirname(SCRIPT_DIR)
TOKEN_FILE = os.path.join(CLAWD_DIR, "google-tokens.json")
CALENDAR_ID = "11a34db3d866cd424bc38cf32716465a45e9eff7370e9d46ceb289d65de060e8@group.calendar.google.com"

# Timezone handling - Matt is in Eastern
try:
    from zoneinfo import ZoneInfo
    EASTERN = ZoneInfo("America/New_York")
except ImportError:
    # Fallback for older Python
    EASTERN = timezone(timedelta(hours=-5))  # EST (not handling DST perfectly)

def get_eastern_now():
    """Get current time in Eastern timezone"""
    return datetime.now(timezone.utc).astimezone(EASTERN)

def get_access_token():
    """Get valid access token"""
    try:
        with open(TOKEN_FILE, 'r') as f:
            tokens = json.load(f)
        return tokens.get('access_token')
    except FileNotFoundError:
        print("❌ No tokens found")
        return None

def log_work(title, description="", duration_minutes=30, start_time=None):
    """
    Log a work item to Jarvis Work Log calendar
    
    Args:
        title: Event title (e.g., "Research: Sales Navigator strategies")
        description: Optional details
        duration_minutes: How long the task took (default 30)
        start_time: When work started (default: now in Eastern)
    """
    access_token = get_access_token()
    if not access_token:
        return None
    
    if start_time is None:
        start_time = get_eastern_now()
    elif isinstance(start_time, str):
        start_time = datetime.fromisoformat(start_time)
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=EASTERN)
    
    end_time = start_time + timedelta(minutes=duration_minutes)
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    event_data = {
        'summary': title,
        'description': description,
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'America/New_York'
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': 'America/New_York'
        },
        'colorId': '9'  # Blue color
    }
    
    response = requests.post(
        f'https://www.googleapis.com/calendar/v3/calendars/{CALENDAR_ID}/events',
        headers=headers,
        json=event_data
    )
    
    if response.status_code == 200:
        event = response.json()
        print(f"✅ Logged: {title}")
        return event
    else:
        print(f"❌ Failed to log: {response.status_code}")
        print(response.text)
        return None

def log_task_completed(task_name, details=""):
    """Quick helper for logging completed tasks"""
    return log_work(
        title=f"✓ {task_name}",
        description=details,
        duration_minutes=15
    )

def log_research(topic, findings=""):
    """Log research activities"""
    return log_work(
        title=f"🔍 Research: {topic}",
        description=findings,
        duration_minutes=30
    )

def log_build(project, changes=""):
    """Log nightly builds or coding work"""
    return log_work(
        title=f"🔧 Build: {project}",
        description=changes,
        duration_minutes=60
    )

def log_heartbeat(status="OK"):
    """Log heartbeat checks"""
    return log_work(
        title=f"💓 Heartbeat: {status}",
        description="",
        duration_minutes=5
    )

def get_recent_logs(days=7):
    """Get recent work log entries"""
    access_token = get_access_token()
    if not access_token:
        return None
    
    now = datetime.now()
    time_min = (now - timedelta(days=days)).isoformat() + 'Z'
    time_max = now.isoformat() + 'Z'
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }
    
    params = {
        'timeMin': time_min,
        'timeMax': time_max,
        'maxResults': 50,
        'singleEvents': True,
        'orderBy': 'startTime'
    }
    
    response = requests.get(
        f'https://www.googleapis.com/calendar/v3/calendars/{CALENDAR_ID}/events',
        headers=headers,
        params=params
    )
    
    if response.status_code == 200:
        return response.json().get('items', [])
    else:
        print(f"❌ Failed to get logs: {response.status_code}")
        return None

def show_summary():
    """Show work log summary"""
    events = get_recent_logs(days=7)
    
    if not events:
        print("📅 No work logged in the past 7 days")
        return
    
    print(f"📅 **Jarvis Work Log (Last 7 Days):**\n")
    
    # Group by day
    by_day = {}
    for event in events:
        start = event.get('start', {}).get('dateTime', '')
        if start:
            day = start[:10]
            if day not in by_day:
                by_day[day] = []
            by_day[day].append(event.get('summary', 'Untitled'))
    
    for day in sorted(by_day.keys(), reverse=True):
        print(f"**{day}:**")
        for task in by_day[day]:
            print(f"  • {task}")
        print()

def parse_time(time_str):
    """
    Parse flexible time formats:
    - "3pm", "3:30pm", "15:00" -> today at that time
    - "2026-02-06 14:00" -> specific datetime
    - "yesterday 3pm" -> yesterday at that time
    """
    now = get_eastern_now()
    time_str = time_str.lower().strip()
    
    # Handle "yesterday"
    day_offset = 0
    if time_str.startswith("yesterday"):
        day_offset = -1
        time_str = time_str.replace("yesterday", "").strip()
    
    # Try ISO format first (2026-02-06 14:00)
    if "-" in time_str and len(time_str) > 10:
        try:
            dt = datetime.fromisoformat(time_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=EASTERN)
            return dt
        except:
            pass
    
    # Handle "3pm", "3:30pm", "15:00" formats
    import re
    
    # Match "3pm", "3:30pm", "3:30 pm"
    match = re.match(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', time_str)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        ampm = match.group(3)
        
        if ampm == 'pm' and hour < 12:
            hour += 12
        elif ampm == 'am' and hour == 12:
            hour = 0
        
        result = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if day_offset:
            result = result + timedelta(days=day_offset)
        return result
    
    return None

def delete_event(event_id):
    """Delete a calendar event by ID"""
    access_token = get_access_token()
    if not access_token:
        return False
    
    headers = {'Authorization': f'Bearer {access_token}'}
    
    response = requests.delete(
        f'https://www.googleapis.com/calendar/v3/calendars/{CALENDAR_ID}/events/{event_id}',
        headers=headers
    )
    
    return response.status_code == 204

def clear_today():
    """Clear all events from today (for re-logging)"""
    access_token = get_access_token()
    if not access_token:
        return
    
    now = get_eastern_now()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }
    
    params = {
        'timeMin': start_of_day.isoformat(),
        'timeMax': end_of_day.isoformat(),
        'singleEvents': True
    }
    
    response = requests.get(
        f'https://www.googleapis.com/calendar/v3/calendars/{CALENDAR_ID}/events',
        headers=headers,
        params=params
    )
    
    if response.status_code == 200:
        events = response.json().get('items', [])
        for event in events:
            if delete_event(event['id']):
                print(f"  Deleted: {event.get('summary', 'Untitled')}")
        print(f"✅ Cleared {len(events)} events from today")
    else:
        print(f"❌ Failed to get events: {response.status_code}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("📅 Jarvis Work Log")
        print("Commands:")
        print("  python3 jarvis-calendar.py log 'Title' ['desc'] [duration] [time]")
        print("  python3 jarvis-calendar.py task 'Completed task'")
        print("  python3 jarvis-calendar.py research 'Topic' [time]")
        print("  python3 jarvis-calendar.py build 'Project' [time]")
        print("  python3 jarvis-calendar.py summary")
        print("  python3 jarvis-calendar.py clear-today")
        print("")
        print("Time formats: '3pm', '14:00', 'yesterday 3pm', '2026-02-06 14:00'")
        sys.exit(0)
    
    command = sys.argv[1]
    
    if command == "log":
        title = sys.argv[2] if len(sys.argv) > 2 else "Work"
        desc = sys.argv[3] if len(sys.argv) > 3 else ""
        duration = int(sys.argv[4]) if len(sys.argv) > 4 else 30
        start = parse_time(sys.argv[5]) if len(sys.argv) > 5 else None
        log_work(title, desc, duration, start)
    
    elif command == "task":
        task = sys.argv[2] if len(sys.argv) > 2 else "Task completed"
        start = parse_time(sys.argv[3]) if len(sys.argv) > 3 else None
        log_work(f"✓ {task}", "", 15, start)
    
    elif command == "research":
        topic = sys.argv[2] if len(sys.argv) > 2 else "General research"
        start = parse_time(sys.argv[3]) if len(sys.argv) > 3 else None
        log_work(f"🔍 Research: {topic}", "", 30, start)
    
    elif command == "build":
        project = sys.argv[2] if len(sys.argv) > 2 else "Project"
        start = parse_time(sys.argv[3]) if len(sys.argv) > 3 else None
        log_work(f"🔧 Build: {project}", "", 60, start)
    
    elif command == "summary":
        show_summary()
    
    elif command == "clear-today":
        clear_today()
    
    else:
        print(f"❌ Unknown command: {command}")
