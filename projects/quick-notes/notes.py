#!/usr/bin/env python3
"""
Quick Notes - Fast persistent note capture for Jarvis
Captures ideas, reminders, and context across sessions.
"""

import json
import os
from datetime import datetime

NOTES_DIR = os.path.dirname(os.path.abspath(__file__))
NOTES_FILE = os.path.join(NOTES_DIR, 'notes.json')

def load_notes():
    if os.path.exists(NOTES_FILE):
        with open(NOTES_FILE, 'r') as f:
            return json.load(f)
    return {"notes": []}

def save_notes(data):
    with open(NOTES_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def add_note(text, category="general", priority="normal"):
    data = load_notes()
    note = {
        "id": len(data['notes']) + 1,
        "text": text,
        "category": category,
        "priority": priority,
        "created": datetime.now().isoformat(),
        "done": False
    }
    data['notes'].append(note)
    save_notes(data)
    print(f"📝 Added note #{note['id']}: {text[:50]}{'...' if len(text) > 50 else ''}")

def list_notes(show_done=False, category=None):
    data = load_notes()
    notes = data.get('notes', [])
    
    if not show_done:
        notes = [n for n in notes if not n.get('done')]
    if category:
        notes = [n for n in notes if n.get('category') == category]
    
    if not notes:
        print("📭 No notes found.")
        return
    
    print("\n" + "="*50)
    print("📝 QUICK NOTES")
    print("="*50)
    
    # Group by priority
    high = [n for n in notes if n.get('priority') == 'high']
    normal = [n for n in notes if n.get('priority') == 'normal']
    low = [n for n in notes if n.get('priority') == 'low']
    
    def print_notes(items, emoji):
        for n in items:
            status = "✅" if n.get('done') else "◻️"
            cat = f"[{n.get('category', 'general')}]" if n.get('category') != 'general' else ""
            print(f"  {status} #{n['id']} {emoji} {n['text']} {cat}")
    
    if high:
        print("\n🔴 HIGH PRIORITY")
        print_notes(high, "🔴")
    if normal:
        print("\n🟡 NORMAL")
        print_notes(normal, "")
    if low:
        print("\n🟢 LOW")
        print_notes(low, "")
    
    print("\n" + "="*50)

def done_note(note_id):
    data = load_notes()
    for n in data['notes']:
        if n['id'] == note_id:
            n['done'] = True
            n['completed'] = datetime.now().isoformat()
            save_notes(data)
            print(f"✅ Marked note #{note_id} as done")
            return
    print(f"Note #{note_id} not found")

def delete_note(note_id):
    data = load_notes()
    data['notes'] = [n for n in data['notes'] if n['id'] != note_id]
    save_notes(data)
    print(f"🗑️ Deleted note #{note_id}")

def clear_done():
    data = load_notes()
    count = len([n for n in data['notes'] if n.get('done')])
    data['notes'] = [n for n in data['notes'] if not n.get('done')]
    save_notes(data)
    print(f"🧹 Cleared {count} completed notes")

def search_notes(query):
    data = load_notes()
    results = [n for n in data['notes'] if query.lower() in n['text'].lower()]
    if results:
        print(f"\n🔍 Found {len(results)} notes matching '{query}':")
        for n in results:
            print(f"  #{n['id']}: {n['text']}")
    else:
        print(f"No notes found matching '{query}'")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        list_notes()
        sys.exit(0)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "add":
        if len(sys.argv) < 3:
            print("Usage: notes.py add <text> [category] [priority]")
            sys.exit(1)
        text = sys.argv[2]
        category = sys.argv[3] if len(sys.argv) > 3 else "general"
        priority = sys.argv[4] if len(sys.argv) > 4 else "normal"
        add_note(text, category, priority)
    
    elif cmd == "list":
        show_done = "--all" in sys.argv
        category = None
        for arg in sys.argv[2:]:
            if not arg.startswith("-"):
                category = arg
        list_notes(show_done, category)
    
    elif cmd == "done":
        if len(sys.argv) < 3:
            print("Usage: notes.py done <note_id>")
            sys.exit(1)
        done_note(int(sys.argv[2]))
    
    elif cmd == "delete":
        if len(sys.argv) < 3:
            print("Usage: notes.py delete <note_id>")
            sys.exit(1)
        delete_note(int(sys.argv[2]))
    
    elif cmd == "clear":
        clear_done()
    
    elif cmd == "search":
        if len(sys.argv) < 3:
            print("Usage: notes.py search <query>")
            sys.exit(1)
        search_notes(sys.argv[2])
    
    elif cmd == "help":
        print("""
Quick Notes - Usage:
  notes.py                     - List active notes
  notes.py add <text> [cat] [pri] - Add a note
  notes.py list [--all] [cat]  - List notes (--all includes done)
  notes.py done <id>           - Mark note as done
  notes.py delete <id>         - Delete a note
  notes.py clear               - Clear all done notes
  notes.py search <query>      - Search notes

Categories: general, idea, reminder, todo, followup
Priorities: high, normal, low
        """)
    else:
        # Treat as quick add
        add_note(" ".join(sys.argv[1:]))
