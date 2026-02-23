#!/usr/bin/env python3
"""Kalshi position sync - saves snapshot to data/kalshi/snapshots/"""
import os, sys, json
from pathlib import Path
from datetime import datetime

# Try to use the kalshi integration
CLAWD = Path.home() / "clawd"
sys.path.insert(0, str(CLAWD / "integrations" / "kalshi"))

try:
    from dotenv import load_dotenv
    load_dotenv(CLAWD / ".env")
    
    import kalshi_python
    from kalshi_python.rest import ApiException
    
    config = kalshi_python.Configuration()
    config.host = "https://trading-api.kalshi.com/trade-api/v2"
    
    api_key = os.getenv("KALSHI_API_KEY")
    private_key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH", str(Path.home() / ".kalshi" / "kalshi-key.pem"))
    
    if not api_key:
        print("KALSHI_API_KEY not set — skipping sync")
        sys.exit(0)
    
    client = kalshi_python.ApiClient(config)
    kalshi_python.authenticate(client, api_key=api_key, private_key_path=private_key_path)
    
    portfolio_api = kalshi_python.PortfolioApi(client)
    positions = portfolio_api.get_positions()
    balance = portfolio_api.get_balance()
    
    snapshot = {
        "timestamp": datetime.utcnow().isoformat(),
        "balance": balance.to_dict() if hasattr(balance, 'to_dict') else str(balance),
        "positions": positions.to_dict() if hasattr(positions, 'to_dict') else str(positions),
    }
    
    snap_dir = CLAWD / "data" / "kalshi" / "snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    snap_file = snap_dir / f"snapshot_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(snap_file, 'w') as f:
        json.dump(snapshot, f, indent=2)
    print(f"✅ Kalshi snapshot saved: {snap_file.name}")

except ImportError as e:
    print(f"kalshi_python not installed: {e}")
except Exception as e:
    print(f"Kalshi sync error: {e}")
    sys.exit(1)
