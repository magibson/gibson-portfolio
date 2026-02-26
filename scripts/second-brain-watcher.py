#!/usr/bin/env python3
"""
File watcher for the second brain.
Watches ~/clawd/notes/ and ~/clawd/memory/ for changes and re-indexes within seconds.
"""
import time
import subprocess
import sys
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

CLAWD_DIR = Path.home() / "clawd"
WATCH_DIRS = [
    CLAWD_DIR / "notes",
    CLAWD_DIR / "memory",
    CLAWD_DIR / "reference",
]
INDEXER = CLAWD_DIR / "scripts" / "second-brain-index.py"
PYTHON = Path.home() / "clawd" / "second-brain-env" / "bin" / "python3"

# Debounce — wait 3s after last change before re-indexing
DEBOUNCE = 3.0
last_event_time = 0
reindex_scheduled = False


class ChangeHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        global last_event_time, reindex_scheduled
        if event.is_directory:
            return
        # Only watch markdown and text files
        if not str(event.src_path).endswith(('.md', '.txt', '.csv')):
            return
        # Ignore the trigger file itself to avoid loops
        if '.proactive-review-trigger' in str(event.src_path):
            return
        last_event_time = time.time()


def get_changed_notes(since: float) -> list:
    """Return list of note files modified since given timestamp."""
    changed = []
    notes_dir = CLAWD_DIR / "notes"
    for f in notes_dir.rglob("*.md"):
        if f.stat().st_mtime > since and ".trash" not in str(f):
            changed.append(f)
    return changed

def proactive_review(changed_files: list):
    """Send changed note contents to OpenClaw for proactive review."""
    if not changed_files:
        return
    notes_content = ""
    for f in changed_files:
        try:
            content = f.read_text().strip()
            if content:
                notes_content += f"\n\n## {f.name}\n{content}"
        except:
            pass
    if not notes_content:
        return

    # Write a trigger file that OpenClaw's heartbeat will pick up
    trigger_path = CLAWD_DIR / "notes" / ".proactive-review-trigger.md"
    trigger_path.write_text(
        f"PROACTIVE_REVIEW_TRIGGER\n"
        f"Changed notes:\n{notes_content}\n\n"
        f"Read these notes and think: what can I do to help? What is Matt missing? "
        f"What action items should I take or flag? Act on anything I can do automatically. "
        f"For things that need Matt's input, send a brief Telegram message."
    )
    print(f"[watcher] Proactive review triggered for: {[f.name for f in changed_files]}", flush=True)

def reindex_loop():
    global last_event_time
    last_indexed = 0
    while True:
        now = time.time()
        if last_event_time > last_indexed and (now - last_event_time) >= DEBOUNCE:
            print(f"[watcher] Change detected — re-indexing...", flush=True)
            changed = get_changed_notes(last_indexed if last_indexed > 0 else (now - 60))
            try:
                result = subprocess.run(
                    [str(PYTHON), str(INDEXER)],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode == 0:
                    print(f"[watcher] Re-index complete", flush=True)
                else:
                    print(f"[watcher] Re-index error: {result.stderr[:200]}", flush=True)
            except Exception as e:
                print(f"[watcher] Error: {e}", flush=True)
            # Trigger proactive review
            if changed:
                proactive_review(changed)
            last_indexed = now
        time.sleep(1)


if __name__ == "__main__":
    # Ensure watch dirs exist
    for d in WATCH_DIRS:
        d.mkdir(parents=True, exist_ok=True)

    observer = Observer()
    handler = ChangeHandler()
    for d in WATCH_DIRS:
        observer.schedule(handler, str(d), recursive=True)
        print(f"[watcher] Watching {d}", flush=True)

    observer.start()
    print("[watcher] Started. Waiting for changes...", flush=True)

    try:
        reindex_loop()
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
