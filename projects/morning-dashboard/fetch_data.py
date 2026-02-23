#!/usr/bin/env python3
"""
JARVIS Dashboard Data Fetcher
Fetches real data from Gmail, Google Calendar, and Yahoo Finance
Updates data.json for the dashboard to consume
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_FILE = SCRIPT_DIR / "data.json"
CREDENTIALS_FILE = Path("/Users/jarvis/clawd/google-credentials.json")
TOKENS_FILE = Path("/Users/jarvis/clawd/google-tokens.json")

def load_credentials():
    """Load Google OAuth credentials"""
    with open(CREDENTIALS_FILE) as f:
        return json.load(f)["installed"]

def load_tokens():
    """Load Google OAuth tokens"""
    with open(TOKENS_FILE) as f:
        return json.load(f)

def save_tokens(tokens):
    """Save updated tokens"""
    with open(TOKENS_FILE, "w") as f:
        json.dump(tokens, f, indent=2)

def refresh_access_token():
    """Refresh the access token using refresh_token"""
    creds = load_credentials()
    tokens = load_tokens()
    
    response = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
        "refresh_token": tokens["refresh_token"],
        "grant_type": "refresh_token"
    })
    
    if response.status_code == 200:
        new_tokens = response.json()
        tokens["access_token"] = new_tokens["access_token"]
        tokens["expires_in"] = new_tokens.get("expires_in", 3600)
        tokens["created_at"] = datetime.now().isoformat()
        save_tokens(tokens)
        return tokens["access_token"]
    else:
        print(f"Token refresh failed: {response.text}", file=sys.stderr)
        return None

def get_access_token():
    """Get a valid access token, refreshing if needed"""
    tokens = load_tokens()
    
    # Check if token might be expired (refresh proactively)
    created_at = tokens.get("created_at", "")
    if created_at:
        try:
            created = datetime.fromisoformat(created_at)
            expires_in = tokens.get("expires_in", 3600)
            if datetime.now() > created + timedelta(seconds=expires_in - 300):
                return refresh_access_token()
        except ValueError:
            pass
    
    # Try current token first
    return tokens.get("access_token") or refresh_access_token()

def fetch_gmail_unread():
    """Fetch unread email count from Gmail"""
    token = get_access_token()
    if not token:
        return {"unread": 0, "error": "No token"}
    
    try:
        response = requests.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            headers={"Authorization": f"Bearer {token}"},
            params={"q": "is:unread", "maxResults": 100}
        )
        
        if response.status_code == 200:
            data = response.json()
            messages = data.get("messages", [])
            # Get estimated total
            total = data.get("resultSizeEstimate", len(messages))
            return {"unread": total, "error": None}
        elif response.status_code == 401:
            # Token expired, refresh and retry
            token = refresh_access_token()
            if token:
                response = requests.get(
                    "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"q": "is:unread", "maxResults": 100}
                )
                if response.status_code == 200:
                    data = response.json()
                    return {"unread": data.get("resultSizeEstimate", 0), "error": None}
            return {"unread": 0, "error": "Auth failed"}
        else:
            return {"unread": 0, "error": f"API error {response.status_code}"}
    except Exception as e:
        return {"unread": 0, "error": str(e)}

def fetch_calendar_events():
    """Fetch today's calendar events"""
    token = get_access_token()
    if not token:
        return {"events": [], "error": "No token"}
    
    try:
        # Get today's date range in RFC3339 format
        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day)
        today_end = today_start + timedelta(days=1)
        
        time_min = today_start.isoformat() + "Z"
        time_max = today_end.isoformat() + "Z"
        
        response = requests.get(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "timeMin": time_min,
                "timeMax": time_max,
                "singleEvents": True,
                "orderBy": "startTime",
                "maxResults": 10
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            events = []
            for item in data.get("items", []):
                start = item.get("start", {})
                # Get start time
                start_time = start.get("dateTime", start.get("date", ""))
                if "T" in start_time:
                    # Parse datetime
                    try:
                        dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                        time_str = dt.strftime("%-I:%M %p")
                    except:
                        time_str = start_time.split("T")[1][:5]
                else:
                    time_str = "All day"
                
                events.append({
                    "time": time_str,
                    "title": item.get("summary", "Untitled Event"),
                    "color": "cyan"  # Default color
                })
            return {"events": events, "error": None}
        elif response.status_code == 401:
            token = refresh_access_token()
            if token:
                # Retry with new token
                return fetch_calendar_events()
            return {"events": [], "error": "Auth failed"}
        else:
            return {"events": [], "error": f"API error {response.status_code}"}
    except Exception as e:
        return {"events": [], "error": str(e)}

def fetch_market_data():
    """Fetch market data from Yahoo Finance"""
    symbols = {
        "^GSPC": {"name": "S&P 500", "type": "index"},
        "^VIX": {"name": "VIX", "type": "volatility"},
        "^TNX": {"name": "10Y Treasury", "type": "bond"},
        "TSLA": {"name": "TSLA", "type": "stock"}
    }
    
    markets = []
    
    for symbol, info in symbols.items():
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
            response = requests.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            
            if response.status_code == 200:
                data = response.json()
                result = data.get("chart", {}).get("result", [{}])[0]
                meta = result.get("meta", {})
                
                price = meta.get("regularMarketPrice", 0)
                prev_close = meta.get("previousClose", meta.get("chartPreviousClose", price))
                
                if prev_close and prev_close > 0:
                    change = ((price - prev_close) / prev_close) * 100
                else:
                    change = 0
                
                markets.append({
                    "symbol": symbol,
                    "name": info["name"],
                    "type": info["type"],
                    "price": round(price, 2),
                    "change": round(change, 2),
                    "prevClose": round(prev_close, 2)
                })
        except Exception as e:
            print(f"Error fetching {symbol}: {e}", file=sys.stderr)
            markets.append({
                "symbol": symbol,
                "name": info["name"],
                "type": info["type"],
                "price": 0,
                "change": 0,
                "error": str(e)
            })
    
    return {"markets": markets, "error": None}

def load_agent_status():
    """Load agent status from agent-status.json"""
    status_file = SCRIPT_DIR / "agent-status.json"
    try:
        if status_file.exists():
            with open(status_file) as f:
                return json.load(f)
    except Exception as e:
        print(f"  Error loading agent status: {e}", file=sys.stderr)
    
    return {
        "main": {"name": "JARVIS", "status": "online", "lastActive": datetime.now().isoformat()},
        "agents": []
    }

def fetch_live_prices(symbols):
    """Fetch live prices from Yahoo Finance for given symbols"""
    import urllib.request
    prices = {}
    
    for symbol in symbols:
        if symbol == 'CASH':
            continue
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=2d"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                meta = data["chart"]["result"][0]["meta"]
                price = meta.get("regularMarketPrice", 0)
                prev_close = meta.get("previousClose", meta.get("chartPreviousClose", price))
                prices[symbol] = {
                    'price': round(price, 2),
                    'prev_close': round(prev_close, 2),
                    'change': round(price - prev_close, 2),
                    'change_pct': round(((price - prev_close) / prev_close * 100) if prev_close else 0, 2)
                }
        except Exception as e:
            print(f"  Error fetching {symbol}: {e}", file=sys.stderr)
    
    return prices

def load_portfolio():
    """Load portfolio from CSV with LIVE prices"""
    import csv
    csv_path = SCRIPT_DIR / "data" / "portfolio.csv"
    
    if not csv_path.exists():
        return None
    
    try:
        # First pass: get symbols and base data from CSV
        raw_holdings = []
        
        def clean_num(s):
            if not s:
                return 0
            return float(s.replace('$', '').replace(',', '').replace('+', '').replace('%', ''))
        
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                symbol = (row.get('Symbol') or '').strip()
                if not symbol or symbol.startswith('"'):
                    continue
                    
                if '**' in symbol:
                    raw_holdings.append({
                        'symbol': 'CASH',
                        'description': 'Cash',
                        'quantity': 0,
                        'cost_basis': clean_num(row.get('Current Value')),
                        'avg_cost': 0
                    })
                    continue
                
                raw_holdings.append({
                    'symbol': symbol,
                    'description': (row.get('Description') or '')[:30],
                    'quantity': clean_num(row.get('Quantity')),
                    'cost_basis': clean_num(row.get('Cost Basis Total')),
                    'avg_cost': clean_num(row.get('Average Cost Basis'))
                })
        
        # Fetch live prices for all symbols
        symbols = [h['symbol'] for h in raw_holdings if h['symbol'] != 'CASH']
        live_prices = fetch_live_prices(symbols)
        
        # Second pass: calculate values with live prices
        holdings = []
        total_value = 0
        total_gain_today = 0
        total_gain_all = 0
        total_cost_basis = 0
        
        for h in raw_holdings:
            symbol = h['symbol']
            
            if symbol == 'CASH':
                val = h['cost_basis']
                holdings.append({
                    'symbol': 'CASH', 'description': 'Cash', 'quantity': None, 'price': None,
                    'value': val, 'today_gain': 0, 'today_gain_pct': 0, 'total_gain': 0,
                    'total_gain_pct': 0, 'pct_of_account': 0
                })
                total_value += val
                continue
            
            live = live_prices.get(symbol, {})
            price = live.get('price', 0)
            prev_close = live.get('prev_close', price)
            quantity = h['quantity']
            cost_basis = h['cost_basis']
            
            if not price or not quantity:
                continue
            
            value = round(price * quantity, 2)
            today_gain = round((price - prev_close) * quantity, 2)
            today_gain_pct = live.get('change_pct', 0)
            total_gain = round(value - cost_basis, 2)
            total_gain_pct = round((total_gain / cost_basis * 100) if cost_basis else 0, 2)
            
            holdings.append({
                'symbol': symbol,
                'description': h['description'],
                'quantity': quantity,
                'price': price,
                'value': value,
                'today_gain': today_gain,
                'today_gain_pct': today_gain_pct,
                'total_gain': total_gain,
                'total_gain_pct': total_gain_pct,
                'pct_of_account': 0  # calculated after totals
            })
            
            total_value += value
            total_gain_today += today_gain
            total_gain_all += total_gain
            total_cost_basis += cost_basis
        
        # Calculate percentages
        for h in holdings:
            h['pct_of_account'] = round((h['value'] / total_value * 100) if total_value else 0, 2)
        
        holdings.sort(key=lambda x: x['value'], reverse=True)
        
        # Load history
        history_file = SCRIPT_DIR / "data" / "portfolio_history.json"
        history_values = []
        if history_file.exists():
            try:
                with open(history_file) as hf:
                    hist_data = json.load(hf)
                    history_values = [s["value"] for s in hist_data.get("snapshots", [])][-7:]
            except:
                pass
        
        return {
            'holdings': holdings,
            'total_value': round(total_value, 2),
            'today_gain': round(total_gain_today, 2),
            'today_gain_pct': round((total_gain_today / total_value * 100) if total_value else 0, 2),
            'total_gain': round(total_gain_all, 2),
            'total_gain_pct': round((total_gain_all / total_cost_basis * 100) if total_cost_basis else 0, 2),
            'cost_basis': round(total_cost_basis, 2),
            'history': history_values if len(history_values) >= 2 else None
        }
    except Exception as e:
        print(f"  Error loading portfolio: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return None

def load_ticktick_tasks():
    """Load TickTick tasks"""
    tokens_file = SCRIPT_DIR / "ticktick" / "tokens.json"
    if not tokens_file.exists():
        return None
    
    try:
        with open(tokens_file) as f:
            token = json.load(f).get("access_token")
        
        if not token:
            return None
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get projects
        projects_resp = requests.get(
            "https://api.ticktick.com/open/v1/project",
            headers=headers
        )
        if projects_resp.status_code != 200:
            return None
        
        projects = {p["id"]: p["name"] for p in projects_resp.json()}
        
        # Get tasks
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
        all_tasks.sort(key=lambda t: t.get("dueDate") or "9999")
        
        # Format for dashboard
        formatted = []
        for t in all_tasks[:20]:  # Limit to 20
            formatted.append({
                "id": t["id"],
                "projectId": t.get("projectId", ""),
                "title": t["title"],
                "project": t.get("projectName", ""),
                "dueDate": t.get("dueDate"),
                "priority": t.get("priority", 0),
                "status": t.get("status", 0)
            })
        
        return {"tasks": formatted, "total": len(all_tasks)}
    except Exception as e:
        print(f"  Error loading TickTick: {e}", file=sys.stderr)
        return None

def load_packages():
    """Load packages from packages.json"""
    packages_file = SCRIPT_DIR / "data" / "packages.json"
    try:
        if packages_file.exists():
            with open(packages_file) as f:
                return json.load(f)
    except Exception as e:
        print(f"  Error loading packages: {e}", file=sys.stderr)
    return {"packages": [], "count": 0}

def load_api_status():
    """Load API status data"""
    apis = [
        {
            "id": "anthropic",
            "name": "Claude",
            "purpose": "Primary AI brain",
            "status": "connected",
            "cost": 22.00,
            "requests": 1847
        },
        {
            "id": "xai",
            "name": "Grok",
            "purpose": "X search & research",
            "status": "connected" if Path("/Users/jarvis/clawd/integrations/xai/.env").exists() else "error",
            "cost": 4.50,
            "requests": 245
        },
        {
            "id": "whoop",
            "name": "Whoop",
            "purpose": "Fitness tracking",
            "status": "connected" if Path("/Users/jarvis/clawd/.whoop_tokens.json").exists() else "error",
            "cost": 0,
            "requests": 62
        },
        {
            "id": "withings",
            "name": "Withings",
            "purpose": "Body composition",
            "status": "connected" if Path("/Users/jarvis/clawd/.withings_tokens.json").exists() else "error",
            "cost": 0,
            "requests": 8
        },
        {
            "id": "telegram",
            "name": "Telegram",
            "purpose": "Communication",
            "status": "connected",
            "cost": 0,
            "requests": 523
        },
        {
            "id": "ticktick",
            "name": "TickTick",
            "purpose": "Task management",
            "status": "connected" if Path("/Users/jarvis/clawd/integrations/.personal-config.json").exists() else "error",
            "cost": 0,
            "requests": 31
        },
        {
            "id": "gmail",
            "name": "Gmail",
            "purpose": "Email alerts",
            "status": "connected",
            "cost": 0,
            "requests": 186
        },
        {
            "id": "github",
            "name": "GitHub",
            "purpose": "Code deploys",
            "status": "connected",
            "cost": 0,
            "requests": 14
        },
        {
            "id": "brave",
            "name": "Brave",
            "purpose": "Web search",
            "status": "connected",
            "cost": 0,
            "requests": 89
        },
        {
            "id": "tracerfy",
            "name": "Tracerfy",
            "purpose": "Skip tracing contacts",
            "status": "connected",
            "cost": 0,
            "requests": 0
        },
        {
            "id": "retell",
            "name": "Retell",
            "purpose": "Voice AI agent",
            "status": "connected",
            "cost": 0,
            "requests": 0
        }
    ]
    
    total_cost = sum(a["cost"] for a in apis)
    connected = len([a for a in apis if a["status"] == "connected"])
    
    return {
        "services": apis,
        "total_cost": total_cost,
        "connected_count": connected,
        "updated": datetime.now().isoformat()
    }

def main():
    """Fetch all data and write to data.json"""
    print(f"[{datetime.now().isoformat()}] Fetching dashboard data...")
    
    # Fetch all data
    gmail_data = fetch_gmail_unread()
    print(f"  Gmail: {gmail_data}")
    
    calendar_data = fetch_calendar_events()
    print(f"  Calendar: {len(calendar_data.get('events', []))} events")
    
    market_data = fetch_market_data()
    print(f"  Markets: {len(market_data.get('markets', []))} symbols")
    
    agent_status = load_agent_status()
    print(f"  Agents: {len(agent_status.get('agents', []))} active")
    
    portfolio_data = load_portfolio()
    print(f"  Portfolio: {'$' + str(portfolio_data['total_value']) if portfolio_data else 'not loaded'}")
    
    ticktick_data = load_ticktick_tasks()
    print(f"  TickTick: {ticktick_data['total'] if ticktick_data else 0} tasks")
    
    packages_data = load_packages()
    print(f"  Packages: {packages_data.get('count', 0)} active")
    
    api_data = load_api_status()
    print(f"  APIs: {api_data.get('connected_count', 0)} connected, ${api_data.get('total_cost', 0):.2f}/mo")
    
    # Combine into single data object
    data = {
        "updated": datetime.now().isoformat(),
        "email": gmail_data,
        "calendar": calendar_data,
        "markets": market_data,
        "agents": agent_status,
        "portfolio": portfolio_data,
        "ticktick": ticktick_data,
        "packages": packages_data,
        "apis": api_data
    }
    
    # Write to data.json
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"  Written to {DATA_FILE}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
