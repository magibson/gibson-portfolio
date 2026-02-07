#!/usr/bin/env python3
"""
Alpaca Paper Trading Bot
Built for Matt by Jarvis - Jan 2026

Strategies:
1. Momentum - Buy when price crosses above SMA, sell when below
2. Mean Reversion - Buy dips, sell rips
3. Simple DCA - Dollar cost average on schedule
"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, GetAssetsRequest
from alpaca.trading.enums import OrderSide, TimeInForce, AssetClass
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
import pandas as pd

load_dotenv()

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


def get_account():
    """Get account info"""
    account = trading_client.get_account()
    return {
        'cash': float(account.cash),
        'portfolio_value': float(account.portfolio_value),
        'buying_power': float(account.buying_power),
        'equity': float(account.equity)
    }


def get_positions():
    """Get current positions"""
    positions = trading_client.get_all_positions()
    return [{
        'symbol': p.symbol,
        'qty': float(p.qty),
        'market_value': float(p.market_value),
        'unrealized_pl': float(p.unrealized_pl),
        'unrealized_plpc': float(p.unrealized_plpc) * 100
    } for p in positions]


def get_price_history(symbol, days=30):
    """Get historical price data"""
    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=datetime.now() - timedelta(days=days)
    )
    bars = data_client.get_stock_bars(request)
    df = bars.df
    if isinstance(df.index, pd.MultiIndex):
        df = df.xs(symbol)
    return df


def calculate_sma(symbol, period=20):
    """Calculate Simple Moving Average"""
    df = get_price_history(symbol, days=period+10)
    return df['close'].rolling(window=period).mean().iloc[-1]


def get_current_price(symbol):
    """Get current price (last close)"""
    df = get_price_history(symbol, days=5)
    return float(df['close'].iloc[-1])


def buy(symbol, qty=None, dollars=None):
    """Place a buy order"""
    if dollars:
        price = get_current_price(symbol)
        qty = int(dollars / price)
    
    if qty <= 0:
        return {'error': 'Quantity must be positive'}
    
    order = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY
    )
    result = trading_client.submit_order(order)
    return {
        'id': str(result.id),
        'symbol': result.symbol,
        'qty': result.qty,
        'side': 'buy',
        'status': str(result.status)
    }


def sell(symbol, qty=None):
    """Place a sell order"""
    if qty is None:
        # Sell all
        positions = get_positions()
        pos = next((p for p in positions if p['symbol'] == symbol), None)
        if not pos:
            return {'error': f'No position in {symbol}'}
        qty = int(pos['qty'])
    
    order = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=OrderSide.SELL,
        time_in_force=TimeInForce.DAY
    )
    result = trading_client.submit_order(order)
    return {
        'id': str(result.id),
        'symbol': result.symbol,
        'qty': result.qty,
        'side': 'sell',
        'status': str(result.status)
    }


# ============ STRATEGIES ============

def momentum_check(symbol, sma_period=20):
    """
    Momentum Strategy:
    - BUY signal if price > SMA
    - SELL signal if price < SMA
    """
    price = get_current_price(symbol)
    sma = calculate_sma(symbol, sma_period)
    
    signal = 'hold'
    if price > sma * 1.01:  # 1% above SMA
        signal = 'buy'
    elif price < sma * 0.99:  # 1% below SMA
        signal = 'sell'
    
    return {
        'symbol': symbol,
        'price': price,
        'sma': sma,
        'signal': signal,
        'strategy': 'momentum'
    }


def mean_reversion_check(symbol, period=20, threshold=0.05):
    """
    Mean Reversion Strategy:
    - BUY when price drops >5% below SMA (oversold)
    - SELL when price rises >5% above SMA (overbought)
    """
    price = get_current_price(symbol)
    sma = calculate_sma(symbol, period)
    deviation = (price - sma) / sma
    
    signal = 'hold'
    if deviation < -threshold:
        signal = 'buy'  # Oversold
    elif deviation > threshold:
        signal = 'sell'  # Overbought
    
    return {
        'symbol': symbol,
        'price': price,
        'sma': sma,
        'deviation': f"{deviation*100:.2f}%",
        'signal': signal,
        'strategy': 'mean_reversion'
    }


def analyze(symbols=['TSLA', 'VOO', 'NVDA']):
    """Run analysis on multiple symbols"""
    results = []
    for symbol in symbols:
        try:
            momentum = momentum_check(symbol)
            mean_rev = mean_reversion_check(symbol)
            results.append({
                'symbol': symbol,
                'price': momentum['price'],
                'sma_20': momentum['sma'],
                'momentum_signal': momentum['signal'],
                'mean_rev_signal': mean_rev['signal'],
                'deviation': mean_rev['deviation']
            })
        except Exception as e:
            results.append({'symbol': symbol, 'error': str(e)})
    return results


# ============ CLI ============

if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("""
Alpaca Paper Trading Bot
Usage:
  python trader.py status          - Account status
  python trader.py positions       - Current positions
  python trader.py analyze         - Analyze TSLA, VOO, NVDA
  python trader.py analyze AAPL    - Analyze specific symbol
  python trader.py buy TSLA 5      - Buy 5 shares of TSLA
  python trader.py buy TSLA $500   - Buy $500 worth of TSLA
  python trader.py sell TSLA       - Sell all TSLA
  python trader.py sell TSLA 2     - Sell 2 shares of TSLA
        """)
        sys.exit(0)
    
    cmd = sys.argv[1].lower()
    
    if cmd == 'status':
        print(json.dumps(get_account(), indent=2))
    
    elif cmd == 'positions':
        positions = get_positions()
        if positions:
            print(json.dumps(positions, indent=2))
        else:
            print("No open positions")
    
    elif cmd == 'analyze':
        symbols = sys.argv[2:] if len(sys.argv) > 2 else ['TSLA', 'VOO', 'NVDA']
        results = analyze(symbols)
        print(json.dumps(results, indent=2))
    
    elif cmd == 'buy':
        if len(sys.argv) < 3:
            print("Usage: python trader.py buy SYMBOL QTY|$DOLLARS")
            sys.exit(1)
        symbol = sys.argv[2].upper()
        if len(sys.argv) > 3:
            amt = sys.argv[3]
            if amt.startswith('$'):
                result = buy(symbol, dollars=float(amt[1:]))
            else:
                result = buy(symbol, qty=int(amt))
        else:
            result = buy(symbol, qty=1)
        print(json.dumps(result, indent=2))
    
    elif cmd == 'sell':
        if len(sys.argv) < 3:
            print("Usage: python trader.py sell SYMBOL [QTY]")
            sys.exit(1)
        symbol = sys.argv[2].upper()
        qty = int(sys.argv[3]) if len(sys.argv) > 3 else None
        result = sell(symbol, qty)
        print(json.dumps(result, indent=2))
    
    else:
        print(f"Unknown command: {cmd}")
