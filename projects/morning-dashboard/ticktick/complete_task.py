#!/usr/bin/env python3
"""Complete a TickTick task"""
import json
import sys
import requests
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
TOKENS_FILE = SCRIPT_DIR / "tokens.json"

def load_token():
    with open(TOKENS_FILE) as f:
        return json.load(f)["access_token"]

def complete_task(project_id, task_id):
    token = load_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get current task
    resp = requests.get(
        f"https://api.ticktick.com/open/v1/project/{project_id}/task/{task_id}",
        headers=headers
    )
    
    if resp.status_code != 200:
        return {"error": f"Failed to get task: {resp.status_code}"}
    
    task = resp.json()
    task["status"] = 2  # 2 = completed
    
    # Update task
    update_resp = requests.post(
        f"https://api.ticktick.com/open/v1/task/{task_id}",
        headers=headers,
        json=task
    )
    
    if update_resp.status_code == 200:
        return {"success": True, "task": task["title"]}
    else:
        return {"error": f"Failed to complete: {update_resp.status_code} {update_resp.text}"}

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: complete_task.py <project_id> <task_id>")
        sys.exit(1)
    result = complete_task(sys.argv[1], sys.argv[2])
    print(json.dumps(result))
