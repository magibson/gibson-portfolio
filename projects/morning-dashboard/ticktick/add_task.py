#!/usr/bin/env python3
"""Add a task to TickTick"""
import json
import sys
import requests
from pathlib import Path
from datetime import datetime, timedelta

SCRIPT_DIR = Path(__file__).parent
TOKENS_FILE = SCRIPT_DIR / "tokens.json"
CONFIG_FILE = SCRIPT_DIR / "task_config.json"

def get_headers():
    with open(TOKENS_FILE) as f:
        tokens = json.load(f)
    return {
        'Authorization': f'Bearer {tokens["access_token"]}',
        'Content-Type': 'application/json'
    }

def get_project_id(category="work"):
    """Get project ID - 'work' for NYL stuff, 'life' for personal"""
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    return config["projects"].get(category, config["projects"]["work"])["id"]

def add_task(title, category="work", due_date=None, priority=0):
    """
    Add a task to TickTick
    
    Args:
        title: Task title
        category: 'work' (NYL/career) or 'life' (personal)
        due_date: Optional due date (datetime or string 'YYYY-MM-DD')
        priority: 0=none, 1=low, 3=medium, 5=high
    
    Returns:
        Task object if successful, None if failed
    """
    headers = get_headers()
    project_id = get_project_id(category)
    
    task_data = {
        'title': title,
        'projectId': project_id,
        'priority': priority
    }
    
    if due_date:
        if isinstance(due_date, str):
            due_date = datetime.strptime(due_date, '%Y-%m-%d')
        task_data['dueDate'] = due_date.strftime('%Y-%m-%dT%H:%M:%S+0000')
    
    resp = requests.post(
        'https://api.ticktick.com/open/v1/task',
        headers=headers,
        json=task_data
    )
    
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"Error creating task: {resp.status_code} {resp.text}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python add_task.py 'Task title' [work|life] [YYYY-MM-DD]")
        sys.exit(1)
    
    title = sys.argv[1]
    category = sys.argv[2] if len(sys.argv) > 2 else "work"
    due_date = sys.argv[3] if len(sys.argv) > 3 else None
    
    task = add_task(title, category, due_date)
    if task:
        print(f"✅ Created: {title}")
        print(f"   Project: {category}")
        if due_date:
            print(f"   Due: {due_date}")
    else:
        print("❌ Failed to create task")
