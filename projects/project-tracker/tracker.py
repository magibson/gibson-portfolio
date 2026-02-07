#!/usr/bin/env python3
"""
Simple Project Tracker for Jarvis/Matt
Tracks all active projects with status, location, and notes.
"""

import json
import os
from datetime import datetime

TRACKER_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_FILE = os.path.join(TRACKER_DIR, 'projects.json')

def load_projects():
    if os.path.exists(PROJECTS_FILE):
        with open(PROJECTS_FILE, 'r') as f:
            return json.load(f)
    return {"projects": []}

def save_projects(data):
    with open(PROJECTS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def list_projects(filter_status=None):
    data = load_projects()
    projects = data.get('projects', [])
    
    if filter_status:
        projects = [p for p in projects if p.get('status') == filter_status]
    
    if not projects:
        print("No projects found.")
        return
    
    print("\n" + "="*60)
    print("📁 PROJECT TRACKER")
    print("="*60)
    
    # Group by status
    active = [p for p in projects if p.get('status') == 'active']
    in_progress = [p for p in projects if p.get('status') == 'in-progress']
    paused = [p for p in projects if p.get('status') == 'paused']
    done = [p for p in projects if p.get('status') == 'done']
    
    def print_group(title, items, emoji):
        if items:
            print(f"\n{emoji} {title} ({len(items)})")
            print("-"*40)
            for p in items:
                print(f"  • {p['name']}")
                if p.get('description'):
                    print(f"    {p['description']}")
                if p.get('location'):
                    print(f"    📂 {p['location']}")
                if p.get('notes'):
                    print(f"    📝 {p['notes']}")
                if p.get('last_updated'):
                    print(f"    🕐 {p['last_updated']}")
                print()
    
    print_group("ACTIVE", active, "🟢")
    print_group("IN PROGRESS", in_progress, "🟡")
    print_group("PAUSED", paused, "⏸️")
    print_group("COMPLETED", done, "✅")
    
    print("="*60 + "\n")

def add_project(name, description="", location="", status="active", notes=""):
    data = load_projects()
    
    # Check if exists
    for p in data['projects']:
        if p['name'].lower() == name.lower():
            print(f"Project '{name}' already exists. Use 'update' to modify.")
            return
    
    project = {
        "name": name,
        "description": description,
        "location": location,
        "status": status,
        "notes": notes,
        "created": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat()
    }
    
    data['projects'].append(project)
    save_projects(data)
    print(f"✅ Added project: {name}")

def update_project(name, **kwargs):
    data = load_projects()
    
    for p in data['projects']:
        if p['name'].lower() == name.lower():
            for key, value in kwargs.items():
                if value is not None:
                    p[key] = value
            p['last_updated'] = datetime.now().isoformat()
            save_projects(data)
            print(f"✅ Updated project: {name}")
            return
    
    print(f"Project '{name}' not found.")

def complete_project(name):
    update_project(name, status="done")

def pause_project(name):
    update_project(name, status="paused")

def activate_project(name):
    update_project(name, status="active")

def show_help():
    print("""
Project Tracker - Usage:
  python tracker.py list [status]      - List all projects (optional: filter by status)
  python tracker.py add <name>         - Add a new project
  python tracker.py update <name>      - Update a project
  python tracker.py complete <name>    - Mark project as done
  python tracker.py pause <name>       - Pause a project
  python tracker.py activate <name>    - Reactivate a project
  python tracker.py help               - Show this help

Statuses: active, in-progress, paused, done
""")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        list_projects()
        sys.exit(0)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "list":
        filter_status = sys.argv[2] if len(sys.argv) > 2 else None
        list_projects(filter_status)
    
    elif cmd == "add":
        if len(sys.argv) < 3:
            print("Usage: tracker.py add <name> [description] [location] [status] [notes]")
            sys.exit(1)
        name = sys.argv[2]
        description = sys.argv[3] if len(sys.argv) > 3 else ""
        location = sys.argv[4] if len(sys.argv) > 4 else ""
        status = sys.argv[5] if len(sys.argv) > 5 else "active"
        notes = sys.argv[6] if len(sys.argv) > 6 else ""
        add_project(name, description, location, status, notes)
    
    elif cmd == "update":
        if len(sys.argv) < 3:
            print("Usage: tracker.py update <name> [field=value ...]")
            sys.exit(1)
        name = sys.argv[2]
        kwargs = {}
        for arg in sys.argv[3:]:
            if '=' in arg:
                key, value = arg.split('=', 1)
                kwargs[key] = value
        update_project(name, **kwargs)
    
    elif cmd == "complete":
        if len(sys.argv) < 3:
            print("Usage: tracker.py complete <name>")
            sys.exit(1)
        complete_project(sys.argv[2])
    
    elif cmd == "pause":
        if len(sys.argv) < 3:
            print("Usage: tracker.py pause <name>")
            sys.exit(1)
        pause_project(sys.argv[2])
    
    elif cmd == "activate":
        if len(sys.argv) < 3:
            print("Usage: tracker.py activate <name>")
            sys.exit(1)
        activate_project(sys.argv[2])
    
    elif cmd == "help":
        show_help()
    
    else:
        print(f"Unknown command: {cmd}")
        show_help()
