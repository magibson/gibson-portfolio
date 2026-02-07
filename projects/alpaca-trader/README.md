# Alpaca Paper Trading Bot

Built for Matt by Jarvis - Jan 2026

## Setup

1. Sign up at [alpaca.markets](https://alpaca.markets)
2. Go to Paper Trading dashboard
3. Generate API keys
4. Copy `.env.example` to `.env` and add your keys:

```bash
cp .env.example .env
# Edit .env with your keys
```

## Usage

```bash
# Check account status
python trader.py status

# See current positions
python trader.py positions

# Analyze stocks (defaults to TSLA, VOO, NVDA)
python trader.py analyze
python trader.py analyze AAPL MSFT GOOGL

# Buy shares
python trader.py buy TSLA 5        # Buy 5 shares
python trader.py buy TSLA $500     # Buy $500 worth

# Sell shares
python trader.py sell TSLA         # Sell all
python trader.py sell TSLA 2       # Sell 2 shares
```

## Strategies

### Momentum
- BUY when price crosses above 20-day SMA
- SELL when price crosses below 20-day SMA

### Mean Reversion
- BUY when price drops >5% below SMA (oversold)
- SELL when price rises >5% above SMA (overbought)

## Risk Warning

⚠️ This is for PAPER TRADING (fake money) first!

When you go live:
- Start small
- Set stop losses
- Never risk money you can't afford to lose
- As an FA, check compliance requirements

## Files

- `trader.py` - Main trading bot
- `.env` - Your API keys (don't commit this!)
- `.env.example` - Template for .env
