#!/usr/bin/env python3
"""
Portfolio monitor - checks for stop-loss breaches and significant moves.
Prints ALERT: lines for anything that needs Matt's attention.
"""
import os, sys, json
from pathlib import Path
from datetime import datetime

CLAWD = Path.home() / "clawd"
sys.path.insert(0, str(CLAWD))

try:
    from dotenv import load_dotenv
    load_dotenv(CLAWD / ".env")
    
    from alpaca.trading.client import TradingClient
    
    key = os.getenv("ALPACA_API_KEY", "PK4I3C6X562UNY7ARXWMDHIAGC")
    secret = os.getenv("ALPACA_SECRET_KEY", "3rAMANNktqkcuRRmCNDN4EfbYpL3pXyRvBNUo2Ro62uh")
    paper = os.getenv("ALPACA_PAPER", "true").lower() == "true"
    
    client = TradingClient(key, secret, paper=paper)
    positions = client.get_all_positions()
    account = client.get_account()
    
    for pos in positions:
        pct = float(pos.unrealized_plpc) * 100
        if pct <= -5.0:
            print(f"ALERT: {pos.symbol} stop-loss triggered: {pct:.1f}% loss (threshold: -5%)")
        elif abs(pct) >= 8.0:
            print(f"ALERT: {pos.symbol} big move: {pct:+.1f}%")
    
    # Portfolio-level stop
    port_val = float(account.portfolio_value)
    equity = float(account.equity)
    day_pnl = float(account.equity) - float(account.last_equity)
    day_pct = (day_pnl / float(account.last_equity)) * 100 if float(account.last_equity) else 0
    
    if day_pct <= -10.0:
        print(f"ALERT: Portfolio down {day_pct:.1f}% today — consider defensive action")

except Exception as e:
    # Silent failure - don't spam Matt with script errors
    pass
