#!/usr/bin/env python3
"""Fetch TickTick tasks"""
import json
import requests
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
TOKENS_FILE = SCRIPT_DIR / "tokens.json"

def load_token():
    with open(TOKENS_FILE) as f:
        return json.load(f)["access_token"]

def fetch_tasks():
    token = load_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get all projects first
    projects_resp = requests.get(
        "https://api.ticktick.com/open/v1/project",
        headers=headers
    )
    
    if projects_resp.status_code != 200:
        print(f"Failed to fetch projects: {projects_resp.status_code}")
        print(projects_resp.text)
        return None
    
    projects = {p["id"]: p["name"] for p in projects_resp.json()}
    
    # Get tasks from each project
    all_tasks = []
    for project_id, project_name in projects.items():
        tasks_resp = requests.get(
            f"https://api.ticktick.com/open/v1/project/{project_id}/data",
            headers=headers
        )
        if tasks_resp.status_code == 200:
            data = tasks_resp.json()
            for task in data.get("tasks", []):
                task["projectName"] = project_name
                all_tasks.append(task)
    
    # Sort by due date
    def sort_key(t):
        due = t.get("dueDate")
        if due:
            return due
        return "9999"
    
    all_tasks.sort(key=sort_key)
    
    return {
        "tasks": all_tasks,
        "projects": list(projects.values()),
        "fetched": datetime.now().isoformat()
    }

if __name__ == "__main__":
    result = fetch_tasks()
    if result:
        print(json.dumps(result, indent=2, default=str))
