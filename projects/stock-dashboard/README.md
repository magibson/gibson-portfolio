# 📈 Stock Research Dashboard

**360° View for Matt's $1K Trading Challenge**

A comprehensive stock research dashboard combining multiple data sources to provide sentiment analysis before making trades.

## Features

### 💹 Price Action & Fundamentals
- Real-time price from Alpaca Markets API
- Daily change percentage
- 52-week high/low range
- Trading volume

### 📰 News Sentiment
- Latest 10 headlines from Alpaca News API
- Automatic sentiment scoring (bullish/neutral/bearish)
- Clickable headlines to read full articles
- Aggregate news sentiment score

### 𝕏 X/Twitter Sentiment (via Grok)
- Real-time trader chatter analysis
- Bull/Bear ratio visualization
- Sample posts from the community
- Powered by xAI's Grok with X Search

### 🔮 Polymarket Integration
- Prediction market odds for relevant events
- Earnings beat/miss probabilities
- Where the money is flowing

### 🎯 Overall Sentiment Gauge
- Combined score from all sources
- Visual speedometer gauge
- Breakdown by source (weighted)
- Label: Very Bearish ↔ Very Bullish

## Tech Stack

- **Backend:** Flask (Python)
- **Frontend:** Vanilla JS + CSS
- **APIs:** Alpaca Markets, Polymarket, xAI Grok
- **Theme:** Dark mode, mobile-friendly

## Quick Start

```bash
cd ~/clawd/projects/stock-dashboard
./start.sh
```

Dashboard runs at: **http://localhost:8084**

## Default Tickers

- AMD - Advanced Micro Devices
- NVDA - NVIDIA Corporation  
- VST - Vistra Corp

Add more tickers via the UI or update `DEFAULT_TICKERS` in `app.py`.

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Main dashboard |
| `GET /api/stock/<ticker>` | Full data for ticker |
| `GET /api/stock/<ticker>?skip_x=true` | Fast load (skip X sentiment) |
| `GET /api/stock/<ticker>/quick` | Price only |
| `GET /api/refresh/<ticker>` | Force refresh cached data |
| `GET /api/tickers` | Get watched tickers |
| `POST /api/tickers` | Update watched tickers |
| `GET /api/health` | Health check |

## Auto-Refresh

- Dashboard auto-refreshes every 5 minutes
- Countdown timer shows next refresh
- Manual refresh button available

## Data Sources

1. **Alpaca Markets** - Price data & news
2. **Polymarket** - Prediction markets
3. **Grok/xAI** - X/Twitter sentiment analysis

## Notes

- X sentiment takes ~15-30 seconds to load (Grok API)
- Fast load available (skip X sentiment)
- 5-minute cache on all data
- Polymarket may not have markets for all tickers

## For the Challenge

Current positions (AMD, NVDA, VST) are tracked. The sentiment gauge helps inform:
- When to add to positions
- When to take profits
- Market timing based on crowd sentiment

*Built by Clawd for Matt's $1K Trading Challenge* 🚀
