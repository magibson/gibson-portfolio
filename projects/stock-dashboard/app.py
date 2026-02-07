#!/usr/bin/env python3
"""
Stock Research Dashboard
Comprehensive 360° stock research view
"""

import os
import sys
import json
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, render_template, jsonify, request
from threading import Lock

# Add integrations path
sys.path.insert(0, str(Path.home() / 'clawd' / 'integrations' / 'xai'))

# Load Alpaca env
alpaca_env = Path.home() / 'clawd' / 'projects' / 'alpaca-trader' / '.env'
if alpaca_env.exists():
    with open(alpaca_env) as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, val = line.strip().split('=', 1)
                os.environ[key] = val

from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame

# Import Grok for X sentiment
try:
    from grok import search_x, ask_grok
    GROK_AVAILABLE = True
except:
    GROK_AVAILABLE = False
    print("Warning: Grok integration not available")

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
cache = {}
cache_lock = Lock()
CACHE_TTL = 300  # 5 minutes

# Alpaca clients
trading_client = TradingClient(
    os.getenv('ALPACA_API_KEY'),
    os.getenv('ALPACA_SECRET_KEY'),
    paper=True
)

data_client = StockHistoricalDataClient(
    os.getenv('ALPACA_API_KEY'),
    os.getenv('ALPACA_SECRET_KEY')
)

# Default tickers for the trading challenge
DEFAULT_TICKERS = ['AMD', 'NVDA', 'VST']

def get_cached(key, fetch_func, ttl=CACHE_TTL):
    """Simple cache with TTL"""
    with cache_lock:
        if key in cache:
            data, timestamp = cache[key]
            if time.time() - timestamp < ttl:
                return data
        
        data = fetch_func()
        cache[key] = (data, time.time())
        return data

def get_stock_data(ticker):
    """Get price data from Alpaca"""
    try:
        # Get latest quote
        request = StockLatestQuoteRequest(symbol_or_symbols=ticker)
        quotes = data_client.get_stock_latest_quote(request)
        
        # Get historical bars for 52-week range
        request = StockBarsRequest(
            symbol_or_symbols=ticker,
            timeframe=TimeFrame.Day,
            start=datetime.now() - timedelta(days=365)
        )
        bars = data_client.get_stock_bars(request)
        df = bars.df
        
        if hasattr(df.index, 'get_level_values'):
            df = df.xs(ticker) if ticker in df.index.get_level_values(0) else df
        
        current_price = float(quotes[ticker].ask_price + quotes[ticker].bid_price) / 2
        prev_close = float(df['close'].iloc[-2]) if len(df) > 1 else current_price
        daily_change = ((current_price - prev_close) / prev_close) * 100
        
        high_52w = float(df['high'].max())
        low_52w = float(df['low'].min())
        
        return {
            'ticker': ticker,
            'price': round(current_price, 2),
            'change': round(daily_change, 2),
            'high_52w': round(high_52w, 2),
            'low_52w': round(low_52w, 2),
            'volume': int(df['volume'].iloc[-1]) if len(df) > 0 else 0,
            'error': None
        }
    except Exception as e:
        return {
            'ticker': ticker,
            'price': 0,
            'change': 0,
            'high_52w': 0,
            'low_52w': 0,
            'volume': 0,
            'error': str(e)
        }

def get_fundamentals(ticker):
    """Get fundamentals data (earnings dates, analyst targets)"""
    # Using free APIs for fundamentals
    try:
        # Yahoo Finance scrape for basic info
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            meta = data.get('chart', {}).get('result', [{}])[0].get('meta', {})
            return {
                'market_cap': meta.get('regularMarketVolume', 'N/A'),
                'exchange': meta.get('exchangeName', 'Unknown'),
                'currency': meta.get('currency', 'USD')
            }
    except Exception as e:
        pass
    
    return {'market_cap': 'N/A', 'exchange': 'Unknown', 'currency': 'USD'}

def get_news_sentiment(ticker):
    """Scrape news and analyze sentiment"""
    headlines = []
    try:
        # Use Alpaca's built-in news API
        url = f"https://data.alpaca.markets/v1beta1/news?symbols={ticker}&limit=10"
        headers = {
            'APCA-API-KEY-ID': os.getenv('ALPACA_API_KEY'),
            'APCA-API-SECRET-KEY': os.getenv('ALPACA_SECRET_KEY')
        }
        resp = requests.get(url, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            news = resp.json().get('news', [])
            for item in news[:10]:
                headline = item.get('headline', '')
                # Simple sentiment scoring
                sentiment = analyze_sentiment(headline)
                headlines.append({
                    'headline': headline,
                    'source': item.get('source', 'Unknown'),
                    'time': item.get('created_at', ''),
                    'sentiment': sentiment,
                    'url': item.get('url', '#')
                })
    except Exception as e:
        print(f"News error for {ticker}: {e}")
    
    # Calculate overall sentiment
    if headlines:
        sentiments = [h['sentiment'] for h in headlines]
        bullish = sentiments.count('bullish')
        bearish = sentiments.count('bearish')
        total = len(sentiments)
        score = ((bullish - bearish) / total) * 100 if total > 0 else 0
    else:
        score = 0
    
    return {
        'headlines': headlines,
        'score': round(score, 1),
        'bullish_count': bullish if headlines else 0,
        'bearish_count': bearish if headlines else 0,
        'neutral_count': (total - bullish - bearish) if headlines else 0
    }

def analyze_sentiment(text):
    """Simple keyword-based sentiment analysis"""
    text_lower = text.lower()
    
    bullish_words = ['surge', 'soar', 'rally', 'gain', 'up', 'beat', 'exceed', 'strong', 
                     'growth', 'upgrade', 'buy', 'bullish', 'positive', 'record', 'high',
                     'outperform', 'jump', 'climb', 'rise', 'boost']
    bearish_words = ['fall', 'drop', 'sink', 'decline', 'down', 'miss', 'weak', 'cut',
                     'downgrade', 'sell', 'bearish', 'negative', 'low', 'concern', 'risk',
                     'plunge', 'crash', 'tumble', 'slide', 'loss', 'warn']
    
    bullish_score = sum(1 for word in bullish_words if word in text_lower)
    bearish_score = sum(1 for word in bearish_words if word in text_lower)
    
    if bullish_score > bearish_score:
        return 'bullish'
    elif bearish_score > bullish_score:
        return 'bearish'
    return 'neutral'

def get_x_sentiment(ticker):
    """Get X/Twitter sentiment via Grok - with timeout"""
    if not GROK_AVAILABLE:
        return {
            'summary': 'Grok integration not available',
            'sample_posts': [],
            'bull_bear_ratio': 50,
            'score': 0,
            'error': True
        }
    
    try:
        import concurrent.futures
        
        def fetch_x():
            query = f"${ticker} stock trading sentiment"
            context = f"""You are analyzing X/Twitter posts about ${ticker} stock.
            
Provide a brief JSON response:
{{"summary": "2-3 sentence summary", "sample_posts": ["post1", "post2"], "bull_percent": 65, "score": 30}}

Keep it concise. Score: -100 (bearish) to +100 (bullish)."""
            return search_x(query, context)
        
        # Use ThreadPoolExecutor with timeout
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(fetch_x)
            try:
                result = future.result(timeout=30)  # 30 second timeout
            except concurrent.futures.TimeoutError:
                return {
                    'summary': 'X sentiment request timed out. Try refreshing.',
                    'sample_posts': [],
                    'bull_bear_ratio': 50,
                    'score': 0,
                    'error': True
                }
        
        # Try to parse JSON from response
        try:
            import re
            json_match = re.search(r'\{[\s\S]*?\}', result)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    'summary': data.get('summary', result[:300]),
                    'sample_posts': data.get('sample_posts', []),
                    'bull_bear_ratio': data.get('bull_percent', 50),
                    'score': data.get('score', 0),
                    'error': False
                }
        except:
            pass
        
        # Fallback: return raw summary
        return {
            'summary': result[:500] if result else 'No data',
            'sample_posts': [],
            'bull_bear_ratio': 50,
            'score': 0,
            'error': False
        }
        
    except Exception as e:
        return {
            'summary': f'Error fetching X sentiment: {str(e)[:100]}',
            'sample_posts': [],
            'bull_bear_ratio': 50,
            'score': 0,
            'error': True
        }

def get_polymarket_odds(ticker):
    """Fetch live Polymarket odds for stocks"""
    ticker_upper = ticker.upper()
    ticker_lower = ticker.lower()
    
    # Known Polymarket event slug patterns for stocks
    # These follow patterns like: nvda-above-on-{date}, nvda-up-or-down-on-{date}
    from datetime import datetime, timedelta
    
    # Get current week's Friday date for weekly markets
    today = datetime.now()
    days_until_friday = (4 - today.weekday()) % 7
    if days_until_friday == 0 and today.hour >= 16:  # Past market close on Friday
        days_until_friday = 7
    friday = today + timedelta(days=days_until_friday)
    friday_str = friday.strftime('%B-%-d-%Y').lower().replace(' ', '-')
    
    # Try known slug patterns
    slug_patterns = [
        f"{ticker_lower}-above-on-february-6-2026",  # Current week
        f"{ticker_lower}-up-or-down-on-february-3-2026",  # Today
    ]
    
    markets_data = []
    
    for slug in slug_patterns:
        try:
            url = f"https://gamma-api.polymarket.com/events?slug={slug}"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    event = data[0]
                    for m in event.get('markets', []):
                        prices = m.get('outcomePrices', '[]')
                        try:
                            pl = json.loads(prices) if isinstance(prices, str) else prices
                            yes_pct = round(float(pl[0]) * 100) if pl else 0
                        except:
                            yes_pct = 0
                        
                        if yes_pct > 0 and yes_pct < 100:  # Skip resolved markets
                            markets_data.append({
                                'question': m.get('question', ''),
                                'yes_pct': yes_pct,
                                'url': f"https://polymarket.com/event/{event.get('slug', '')}",
                                'volume': event.get('volume', 0)
                            })
        except Exception as e:
            print(f"Polymarket API error for {slug}: {e}")
            continue
    
    # Also try gamma-api search
    try:
        search_url = f"https://gamma-api.polymarket.com/events?limit=50&active=true"
        resp = requests.get(search_url, timeout=10)
        if resp.status_code == 200:
            events = resp.json()
            for event in events:
                title = event.get('title', '').lower()
                slug = event.get('slug', '').lower()
                if ticker_lower in title or ticker_lower in slug:
                    for m in event.get('markets', [])[:3]:
                        prices = m.get('outcomePrices', '[]')
                        try:
                            pl = json.loads(prices) if isinstance(prices, str) else prices
                            yes_pct = round(float(pl[0]) * 100) if pl else 0
                        except:
                            yes_pct = 0
                        
                        if yes_pct > 0 and yes_pct < 100:
                            markets_data.append({
                                'question': m.get('question', ''),
                                'yes_pct': yes_pct,
                                'url': f"https://polymarket.com/event/{event.get('slug', '')}",
                                'volume': event.get('volume', 0)
                            })
    except:
        pass
    
    # Deduplicate by question
    seen = set()
    unique_markets = []
    for m in markets_data:
        if m['question'] not in seen:
            seen.add(m['question'])
            unique_markets.append(m)
    
    # Stocks known to have active Polymarket markets
    active_stocks = ['NVDA']  # Update this list as Polymarket adds more
    
    return {
        'markets': unique_markets[:5],
        'search_url': f"https://polymarket.com/search/{ticker_lower}",
        'earnings_url': "https://polymarket.com/earnings",
        'found': len(unique_markets) > 0,
        'note': None if unique_markets else f"No active prediction markets for {ticker_upper}. Check around earnings season or try NVDA which has weekly price targets.",
        'has_active_markets': ticker_upper in active_stocks
    }

def calculate_overall_sentiment(news_score, x_score, polymarket_data):
    """Combine all sentiment sources into one score"""
    # Polymarket now just provides links, so weight between news and X
    weights = {
        'news': 0.4,
        'x': 0.6
    }
    
    # Normalize scores to -100 to +100 scale
    news_normalized = news_score  # Already -100 to +100
    x_normalized = x_score  # Already -100 to +100
    
    overall = (
        news_normalized * weights['news'] +
        x_normalized * weights['x']
    )
    
    return {
        'score': round(overall, 1),
        'news_weight': round(news_normalized * weights['news'], 1),
        'x_weight': round(x_normalized * weights['x'], 1),
        'poly_weight': 0,  # Polymarket now manual check via links
        'label': get_sentiment_label(overall)
    }

def get_sentiment_label(score):
    """Convert score to label"""
    if score >= 60:
        return 'Very Bullish'
    elif score >= 25:
        return 'Bullish'
    elif score >= -25:
        return 'Neutral'
    elif score >= -60:
        return 'Bearish'
    else:
        return 'Very Bearish'

@app.route('/')
def index():
    return render_template('index.html', tickers=DEFAULT_TICKERS)

@app.route('/api/stock/<ticker>')
def api_stock(ticker):
    """Get all data for a single stock"""
    ticker = ticker.upper()
    skip_x = request.args.get('skip_x', 'false').lower() == 'true'
    
    def fetch_all():
        price_data = get_stock_data(ticker)
        fundamentals = get_fundamentals(ticker)
        news_data = get_news_sentiment(ticker)
        
        # X sentiment is slow, make it optional
        if skip_x:
            x_data = {'summary': 'Click refresh for X sentiment', 'sample_posts': [], 'bull_bear_ratio': 50, 'score': 0, 'error': False, 'skipped': True}
        else:
            x_data = get_x_sentiment(ticker)
        
        poly_data = get_polymarket_odds(ticker)
        
        overall = calculate_overall_sentiment(
            news_data['score'],
            x_data['score'],
            poly_data
        )
        
        return {
            'ticker': ticker,
            'price': price_data,
            'fundamentals': fundamentals,
            'news': news_data,
            'x_sentiment': x_data,
            'polymarket': poly_data,
            'overall_sentiment': overall,
            'last_updated': datetime.now().isoformat()
        }
    
    cache_key = f'stock_{ticker}' + ('_fast' if skip_x else '')
    data = get_cached(cache_key, fetch_all, ttl=60 if skip_x else CACHE_TTL)
    return jsonify(data)

@app.route('/api/stock/<ticker>/quick')
def api_stock_quick(ticker):
    """Quick price-only data"""
    ticker = ticker.upper()
    price_data = get_stock_data(ticker)
    return jsonify({
        'ticker': ticker,
        'price': price_data,
        'last_updated': datetime.now().isoformat()
    })

@app.route('/api/refresh/<ticker>')
def api_refresh(ticker):
    """Force refresh data for a ticker"""
    ticker = ticker.upper()
    key = f'stock_{ticker}'
    with cache_lock:
        if key in cache:
            del cache[key]
    return api_stock(ticker)

@app.route('/api/tickers', methods=['GET', 'POST'])
def api_tickers():
    """Get or update watched tickers"""
    if request.method == 'POST':
        data = request.json
        global DEFAULT_TICKERS
        DEFAULT_TICKERS = [t.upper() for t in data.get('tickers', DEFAULT_TICKERS)]
        return jsonify({'tickers': DEFAULT_TICKERS})
    return jsonify({'tickers': DEFAULT_TICKERS})

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'grok_available': GROK_AVAILABLE})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8084, debug=False)
