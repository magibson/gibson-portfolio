#!/usr/bin/env python3
"""
Trading Challenge Dashboard Updater
Fetches data from Alpaca and updates the dashboard
"""

import os
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Load env from alpaca-trader project
alpaca_dir = Path(__file__).parent.parent / 'alpaca-trader'
from dotenv import load_dotenv
load_dotenv(alpaca_dir / '.env')

from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

# Initialize clients
trading_client = TradingClient(
    os.getenv('ALPACA_API_KEY'),
    os.getenv('ALPACA_SECRET_KEY'),
    paper=True
)

data_client = StockHistoricalDataClient(
    os.getenv('ALPACA_API_KEY'),
    os.getenv('ALPACA_SECRET_KEY')
)

# Challenge parameters
CHALLENGE_START = datetime(2026, 1, 31)
CHALLENGE_END = datetime(2026, 2, 28)
STARTING_CAPITAL = 1000
VOO_START_PRICE = 636.22
SCALE_FACTOR = 100  # Paper account has $100K, we simulate $1K

def get_account():
    account = trading_client.get_account()
    return {
        'cash': float(account.cash) / SCALE_FACTOR,
        'portfolio_value': float(account.portfolio_value) / SCALE_FACTOR,
        'equity': float(account.equity) / SCALE_FACTOR
    }

def get_positions():
    positions = trading_client.get_all_positions()
    return [{
        'ticker': p.symbol,
        'shares': int(float(p.qty) / SCALE_FACTOR * SCALE_FACTOR),  # Keep actual shares
        'avgCost': float(p.avg_entry_price),
        'current': float(p.current_price),
        'marketValue': float(p.market_value) / SCALE_FACTOR,
        'pl': float(p.unrealized_pl) / SCALE_FACTOR,
        'plPercent': float(p.unrealized_plpc) * 100
    } for p in positions]

def get_voo_price():
    try:
        request = StockBarsRequest(
            symbol_or_symbols='VOO',
            timeframe=TimeFrame.Day,
            start=datetime.now() - timedelta(days=5)
        )
        bars = data_client.get_stock_bars(request)
        df = bars.df
        if hasattr(df.index, 'get_level_values'):
            return float(df['close'].iloc[-1])
        return float(df.xs('VOO')['close'].iloc[-1])
    except Exception as e:
        print(f"Error getting VOO price: {e}")
        return VOO_START_PRICE

def calculate_returns(portfolio_value, voo_current):
    our_return = ((portfolio_value - STARTING_CAPITAL) / STARTING_CAPITAL) * 100
    voo_return = ((voo_current - VOO_START_PRICE) / VOO_START_PRICE) * 100
    return our_return, voo_return

def days_remaining():
    today = datetime.now()
    if today > CHALLENGE_END:
        return 0
    return (CHALLENGE_END - today).days

def update_dashboard():
    print("📊 Updating trading dashboard...")
    
    try:
        account = get_account()
        positions = get_positions()
        voo_price = get_voo_price()
        our_return, voo_return = calculate_returns(account['portfolio_value'], voo_price)
        
        data = {
            'portfolioValue': round(account['portfolio_value'], 2),
            'totalReturn': round(our_return, 2),
            'cash': round(account['cash'], 2),
            'daysRemaining': days_remaining(),
            'ourReturn': round(our_return, 2),
            'vooReturn': round(voo_return, 2),
            'vooStart': VOO_START_PRICE,
            'vooCurrent': round(voo_price, 2),
            'positions': positions,
            'lastUpdated': datetime.now().isoformat()
        }
        
        # Save to JSON
        output_path = Path(__file__).parent / 'data.json'
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✅ Dashboard updated!")
        print(f"   Portfolio: ${data['portfolioValue']}")
        print(f"   Our Return: {data['ourReturn']:+.2f}%")
        print(f"   VOO Return: {data['vooReturn']:+.2f}%")
        print(f"   Beating Market: {'YES! 🏆' if data['ourReturn'] > data['vooReturn'] else 'Not yet'}")
        
        return data
        
    except Exception as e:
        print(f"❌ Error updating dashboard: {e}")
        return None

if __name__ == "__main__":
    update_dashboard()
