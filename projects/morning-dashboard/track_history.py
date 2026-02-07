#!/usr/bin/env python3
"""Track daily portfolio snapshots for line chart"""
import json
import os
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
HISTORY_FILE = SCRIPT_DIR / "data" / "portfolio_history.json"
DATA_FILE = SCRIPT_DIR / "data.json"

def load_history():
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return {"snapshots": []}

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def main():
    # Load current portfolio value
    if not DATA_FILE.exists():
        print("No data.json found")
        return
    
    with open(DATA_FILE) as f:
        data = json.load(f)
    
    portfolio = data.get("portfolio")
    if not portfolio:
        print("No portfolio data")
        return
    
    today = datetime.now().strftime("%Y-%m-%d")
    value = portfolio["total_value"]
    
    history = load_history()
    
    # Check if we already have today's snapshot
    if history["snapshots"] and history["snapshots"][-1]["date"] == today:
        # Update today's value
        history["snapshots"][-1]["value"] = value
        print(f"Updated {today}: ${value}")
    else:
        # Add new snapshot
        history["snapshots"].append({"date": today, "value": value})
        print(f"Added {today}: ${value}")
    
    # Keep only last 30 days
    history["snapshots"] = history["snapshots"][-30:]
    
    save_history(history)

if __name__ == "__main__":
    main()
