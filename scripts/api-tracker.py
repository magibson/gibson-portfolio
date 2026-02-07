#!/usr/bin/env python3
"""
API Tracker - Monitor all connected APIs and their status
"""

import os
import json
from pathlib import Path
from datetime import datetime

DATA_FILE = Path(__file__).parent.parent / "data" / "api-tracker.json"

# Define all APIs we're using
APIS = {
    "whoop": {
        "name": "Whoop",
        "purpose": "Fitness/recovery data",
        "token_file": "/home/clawd/clawd/.whoop_tokens.json",
        "cost": "Free (with subscription)",
        "docs": "https://developer.whoop.com"
    },
    "withings": {
        "name": "Withings",
        "purpose": "Weight/body composition",
        "token_file": "/home/clawd/clawd/.withings_tokens.json",
        "cost": "Free",
        "docs": "https://developer.withings.com"
    },
    "xai": {
        "name": "xAI/Grok",
        "purpose": "X (Twitter) search, AI queries",
        "env_file": "/home/clawd/clawd/integrations/xai/.env",
        "cost": "~$0.20-0.50/1M tokens + $5/1k X searches",
        "docs": "https://docs.x.ai"
    },
    "telegram": {
        "name": "Telegram",
        "purpose": "Primary communication channel",
        "env_var": "TELEGRAM_BOT_TOKEN",
        "cost": "Free",
        "docs": "https://core.telegram.org/bots/api"
    },
    "gmail": {
        "name": "Gmail",
        "purpose": "Email monitoring/alerts",
        "token_file": "/home/clawd/clawd/.gmail_tokens.json",
        "cost": "Free",
        "docs": "https://developers.google.com/gmail/api"
    },
    "ticktick": {
        "name": "TickTick",
        "purpose": "Task management",
        "env_file": "/home/clawd/clawd/integrations/.personal-config.json",
        "cost": "Free",
        "docs": "https://developer.ticktick.com"
    },
    "anthropic": {
        "name": "Anthropic (Claude)",
        "purpose": "Primary AI brain",
        "env_var": "ANTHROPIC_API_KEY",
        "cost": "~$15/1M input, $75/1M output (Opus)",
        "docs": "https://docs.anthropic.com"
    },
    "github": {
        "name": "GitHub",
        "purpose": "Code deployments",
        "token_file": "/home/clawd/.config/gh/hosts.yml",
        "cost": "Free",
        "docs": "https://docs.github.com/en/rest"
    },
    "brave": {
        "name": "Brave Search",
        "purpose": "Web search",
        "env_var": "BRAVE_API_KEY",
        "cost": "Free tier available",
        "docs": "https://brave.com/search/api"
    }
}

def check_api_status(api_id, api_info):
    """Check if an API appears to be configured"""
    status = {
        "configured": False,
        "last_checked": datetime.now().isoformat(),
        "notes": ""
    }
    
    # Check token file
    if "token_file" in api_info:
        token_path = Path(api_info["token_file"])
        if token_path.exists():
            status["configured"] = True
            # Check token age
            mtime = datetime.fromtimestamp(token_path.stat().st_mtime)
            status["notes"] = f"Token file updated: {mtime.strftime('%Y-%m-%d %H:%M')}"
        else:
            status["notes"] = "Token file not found"
    
    # Check env file
    elif "env_file" in api_info:
        env_path = Path(api_info["env_file"])
        if env_path.exists():
            status["configured"] = True
            status["notes"] = "Config file exists"
        else:
            status["notes"] = "Config file not found"
    
    # Check env var
    elif "env_var" in api_info:
        if os.environ.get(api_info["env_var"]):
            status["configured"] = True
            status["notes"] = "Environment variable set"
        else:
            status["notes"] = "Environment variable not found"
    
    return status

def get_full_status():
    """Get status of all APIs"""
    results = {}
    for api_id, api_info in APIS.items():
        status = check_api_status(api_id, api_info)
        results[api_id] = {
            **api_info,
            **status
        }
    return results

def print_status():
    """Print formatted status report"""
    status = get_full_status()
    
    print("\n📡 API TRACKER")
    print("=" * 60)
    
    configured = []
    not_configured = []
    
    for api_id, info in status.items():
        if info["configured"]:
            configured.append((api_id, info))
        else:
            not_configured.append((api_id, info))
    
    print(f"\n✅ CONNECTED ({len(configured)})")
    print("-" * 40)
    for api_id, info in configured:
        print(f"  {info['name']}")
        print(f"    Purpose: {info['purpose']}")
        print(f"    Cost: {info['cost']}")
        print(f"    Status: {info['notes']}")
        print()
    
    if not_configured:
        print(f"\n❌ NOT CONFIGURED ({len(not_configured)})")
        print("-" * 40)
        for api_id, info in not_configured:
            print(f"  {info['name']}")
            print(f"    Purpose: {info['purpose']}")
            print(f"    Issue: {info['notes']}")
            print()
    
    print(f"\n💰 ESTIMATED MONTHLY COST")
    print("-" * 40)
    print("  Claude API: $15-30 (depends on usage)")
    print("  xAI/Grok: $5-10 (X searches)")
    print("  Everything else: Free")
    print("  TOTAL: ~$20-40/month")
    
    return status

def save_status():
    """Save status to JSON file"""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    status = get_full_status()
    status["_updated"] = datetime.now().isoformat()
    with open(DATA_FILE, 'w') as f:
        json.dump(status, f, indent=2)
    print(f"\n💾 Status saved to {DATA_FILE}")

def summary_for_message():
    """Generate a compact summary for messaging"""
    status = get_full_status()
    
    lines = ["📡 **Your Connected APIs:**\n"]
    
    configured = [(k, v) for k, v in status.items() if v["configured"]]
    not_configured = [(k, v) for k, v in status.items() if not v["configured"]]
    
    for api_id, info in configured:
        lines.append(f"✅ **{info['name']}** — {info['purpose']}")
    
    if not_configured:
        lines.append("\n❌ **Not configured:**")
        for api_id, info in not_configured:
            lines.append(f"  • {info['name']}")
    
    lines.append(f"\n💰 **Est. monthly cost:** $20-40")
    
    return "\n".join(lines)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "json":
            print(json.dumps(get_full_status(), indent=2))
        elif cmd == "save":
            print_status()
            save_status()
        elif cmd == "summary":
            print(summary_for_message())
    else:
        print_status()
