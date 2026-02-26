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
        last_event_time = time.time()


def reindex_loop():
    global last_event_time
    last_indexed = 0
    while True:
        now = time.time()
        if last_event_time > last_indexed and (now - last_event_time) >= DEBOUNCE:
            print(f"[watcher] Change detected — re-indexing...", flush=True)
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
