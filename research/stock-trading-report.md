# AI-Assisted Stock Trading Research Report

*Prepared for Matt (25, Financial Advisor, NJ)*  
*Last Updated: January 2026*

---

## Executive Summary

AI-assisted stock trading is increasingly accessible to retail investors, but success requires careful platform selection, regulatory awareness, robust risk management, and realistic expectations. This report covers the key aspects you need to understand before deploying an AI trading agent.

---

## 1. Platforms & Brokers

### Recommended for Algorithmic Trading

#### **Alpaca** ⭐ Best for Beginners
- **Pros:**
  - Commission-free equity trading
  - Modern REST API designed for developers
  - Excellent Python SDK (`alpaca-py`)
  - Paper trading environment that mirrors live trading exactly
  - Fractional shares supported
  - Active developer community (Slack, Discord)
  - No minimum balance requirement
  
- **Cons:**
  - US equities only (no international markets)
  - Free market data is 15-min delayed (paid real-time available)
  - No options trading via API
  - Payment for order flow (PFOF) model may affect execution quality
  - Margin accounts harder to use programmatically

- **Best for:** Starting out, learning, and strategies that don't require sub-second execution

#### **Interactive Brokers (IBKR)** ⭐ Best for Serious Traders
- **Pros:**
  - Access to global markets (stocks, options, futures, forex, bonds)
  - SmartRouting for better execution quality
  - Low commissions (tiered or fixed pricing)
  - Professional-grade infrastructure
  - Options and futures supported
  - Long-standing, reliable platform

- **Cons:**
  - API feels "archaic" to many developers
  - Steeper learning curve
  - Requires IBKR Pro for API access (has fees)
  - Data subscriptions cost extra
  - Minimum ~$0.01/share profit needed to cover fixed-tier fees

- **Best for:** Serious traders who need multi-asset access, options, or global markets

#### **Charles Schwab** (Post-TD Ameritrade Merger)
- **Current Status:** TD Ameritrade API was discontinued May 10, 2024
- Schwab has released a new Trader API but it's still maturing
- Requires weekly re-authentication (OAuth2 flow)
- **Recommendation:** Wait for API to stabilize, or use alternatives

#### **Robinhood** ⚠️ Not Recommended
- **No official trading API** for stocks
- Only crypto trading API available
- Unofficial APIs exist but violate ToS and have severe rate limits (~1 request/min)
- Limited historical data access
- **Verdict:** Avoid for algorithmic trading

#### **Other Options**
| Broker | API Quality | Commission | Notes |
|--------|-------------|------------|-------|
| Tradier | Good | $0.35/contract (options) | Simpler than IBKR, growing community |
| Webull | Limited | Free | No official algo trading API |
| TradeStation | Good | Varies | Strong platform, higher learning curve |

### Platform Comparison Summary

| Feature | Alpaca | IBKR | Schwab |
|---------|--------|------|--------|
| API Quality | Excellent | Good (dated) | Developing |
| Commission | Free | Low | Free |
| Asset Classes | US Equities | Global Multi-Asset | US Multi-Asset |
| Options | ❌ | ✅ | ✅ |
| Paper Trading | ✅ Excellent | ✅ Good | ✅ |
| Minimum Balance | $0 | $0 | $0 |
| Best For | Beginners | Advanced | TBD |

---

## 2. Legality & Regulations

### Algorithmic Trading is Legal

Retail investors can legally use automated trading systems. There are no laws prohibiting automation or AI-driven trading for personal accounts.

### Pattern Day Trader (PDT) Rule

**Current Rule (still in effect as of 2026):**
- If you make **4+ day trades in 5 business days** in a margin account, you're flagged as a "Pattern Day Trader"
- Must maintain **$25,000 minimum equity** in your account
- Violations can restrict your account to closing trades only

**Workarounds:**
- Use a **cash account** (no PDT rules, but must wait for settlement T+1)
- Trade with $25,000+ in your account
- Spread day trades across multiple brokers (not recommended)
- Focus on swing trading (holding overnight) instead of day trading

**Upcoming Changes:**
- FINRA filed amendments in 2024-2025 to potentially replace the PDT rule with new "intraday margin standards"
- SEC approval pending; implementation likely in 2026 at earliest
- Don't count on changes — plan around current rules

### Key Regulations to Know

1. **Regulation T (Margin Requirements):** Governs margin accounts, initial margin of 50%
2. **FINRA Rule 4210:** Specific margin requirements including day trading provisions
3. **Rule 611 (Order Protection Rule):** Trades must execute at best available price
4. **Rule 610 (Access Rule):** Equal opportunity across trading venues

### What You CAN'T Do

- **Spoofing:** Placing fake orders to manipulate prices (illegal, people go to prison)
- **Wash Trading:** Buying and selling to yourself to fake volume
- **Front-running:** Trading ahead of client orders (especially relevant given your FA role)
- **Market Manipulation:** Any scheme to artificially affect prices

### As a Financial Advisor

⚠️ **Special Considerations:**
- Trading in your personal account while advising clients creates potential conflicts
- May need to pre-clear personal trades depending on your firm's policies
- Consider establishing compliance guardrails (trading different securities than clients, documentation)
- Consult your compliance department before deploying any automated system

---

## 3. Trading Strategies

### Categories of AI/ML Trading Strategies

#### **1. Momentum Strategies**
- Follow trends: buy when prices are rising, sell when falling
- Use moving averages, RSI, MACD as signals
- ML can optimize parameters and detect regime changes
- **Risk:** Whipsaws in choppy markets

#### **2. Mean Reversion**
- Bet that prices will return to historical averages
- Works on: pairs trading, Bollinger Bands, statistical arbitrage
- **Risk:** Trends can persist longer than you can stay solvent

#### **3. Sentiment Analysis**
- Analyze news, social media, earnings calls using NLP
- LLMs have improved accuracy significantly since 2023
- Sources: Twitter/X, Reddit, SEC filings, earnings transcripts
- **Risk:** Sentiment can be manipulated, stale by the time you act

#### **4. Machine Learning Predictions**
- Deep learning for price prediction (LSTM, transformers)
- Reinforcement learning for optimal execution
- Feature engineering on technical indicators
- **Risk:** Overfitting is the #1 killer of ML strategies

#### **5. Market Making / Arbitrage** (Typically Not for Retail)
- Requires co-location, low-latency infrastructure
- Highly competitive, razor-thin margins
- Not recommended for retail unless you have significant technical edge

### Realistic Expectations

From expert consensus:
> "Retail traders should focus on refining an existing strategy with machine learning, not the other way around." — Stefan Jensen

**What works:**
- AI for risk management and position sizing
- ML for filtering low-probability trades
- Regime detection (knowing when to be in/out of market)
- Portfolio optimization

**What usually fails:**
- Pure prediction models trying to beat the market
- Over-optimized backtests that don't generalize
- Strategies that worked in research papers (alpha decays fast)

---

## 4. Risks

### Technical Risks

| Risk | Description | Mitigation |
|------|-------------|------------|
| **Bugs** | Code errors causing wrong trades | Extensive testing, paper trading first |
| **Latency** | Slow execution missing opportunities | Use limit orders, don't compete on speed |
| **Downtime** | Server/broker outages | Have manual override capability |
| **Data Quality** | Bad data = bad decisions | Multiple data sources, sanity checks |

### Market Risks

#### **Flash Crashes**
- May 2010: Dow dropped ~1,000 points in minutes
- Algorithms can amplify volatility
- Your stop-losses may execute at terrible prices
- **Circuit breakers exist** but don't fully protect

#### **Slippage**
- Difference between expected and actual execution price
- Worse in:
  - Low liquidity stocks
  - Market orders
  - Fast-moving markets
- Can eat entire strategy profits

#### **Overfitting**
- Strategy performs amazingly on historical data
- Fails miserably in live trading
- **Red flags:**
  - Too many parameters
  - Performance too good to be true
  - Only works on specific time periods

#### **Regime Changes**
- What worked in 2020-2021 (low rates, bull market) may not work in 2025+
- COVID volatility was an anomaly
- Interest rate environment matters

### Psychological Risks

- Overconfidence from backtests
- Temptation to override the algorithm
- Difficulty accepting losses even when statistically normal
- Letting winners run vs. taking profits too early

### The Sobering Reality

From research:
> "Most retail algorithmic traders do not outperform the market after costs."

This doesn't mean you can't succeed, but approach with humility and realistic expectations.

---

## 5. Implementation

### Technical Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│  Data Sources   │────▶│  AI/Strategy │────▶│   Broker    │
│  (Market Data)  │     │    Engine    │     │    API      │
└─────────────────┘     └──────────────┘     └─────────────┘
        │                      │                     │
        ▼                      ▼                     ▼
   Real-time &            Signals &            Order
   Historical             Decisions          Execution
```

### Alpaca Python Example

```python
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# Initialize client (paper=True for testing)
client = TradingClient('api-key', 'secret-key', paper=True)

# Market order
market_order = MarketOrderRequest(
    symbol="AAPL",
    qty=10,
    side=OrderSide.BUY,
    time_in_force=TimeInForce.DAY
)
order = client.submit_order(order_data=market_order)

# Limit order (better for algorithms)
limit_order = LimitOrderRequest(
    symbol="AAPL",
    qty=10,
    side=OrderSide.BUY,
    time_in_force=TimeInForce.GTC,
    limit_price=175.00
)
order = client.submit_order(order_data=limit_order)
```

### Order Types to Know

| Order Type | Use Case | Pros | Cons |
|------------|----------|------|------|
| **Market** | Immediate execution needed | Guaranteed fill | Slippage |
| **Limit** | Precise price control | No slippage | May not fill |
| **Stop** | Loss protection | Automated risk management | Can gap through |
| **Stop-Limit** | Loss protection with price control | Price guarantee | May not fill in crash |
| **Bracket** | Entry + TP + SL in one | Complete trade management | Complex |

### Execution Best Practices

1. **Prefer limit orders** over market orders
2. **Use paper trading extensively** (months, not days)
3. **Start with small position sizes** in live trading
4. **Log everything** — every decision, every order, every fill
5. **Monitor in real-time** during initial deployment
6. **Have a kill switch** — way to stop all trading immediately

### Technology Stack Recommendations

**Beginner:**
- Python + Alpaca SDK
- Pandas for data manipulation
- Simple cron job or cloud function for scheduling

**Intermediate:**
- Interactive Brokers + ib_insync
- PostgreSQL/TimescaleDB for data storage
- Docker containers for deployment

**Advanced:**
- QuantConnect or similar backtesting platform
- Real-time streaming with WebSockets
- Cloud deployment (AWS/GCP) with redundancy

---

## 6. Safeguards

### Essential Risk Controls

#### **Position Limits**
```python
MAX_POSITION_SIZE = 0.05  # 5% of portfolio per position
MAX_TOTAL_EXPOSURE = 0.80  # 80% max invested at once

def check_position_limit(symbol, qty, portfolio_value):
    position_value = qty * get_price(symbol)
    if position_value > portfolio_value * MAX_POSITION_SIZE:
        return False, "Position too large"
    return True, "OK"
```

#### **Stop-Loss Orders**
- Hard stop: Fixed percentage (e.g., -5% from entry)
- Trailing stop: Moves with price, locks in profits
- Time-based stop: Exit if no movement in X days

#### **Daily Loss Limits**
```python
MAX_DAILY_LOSS = 0.02  # 2% of portfolio
MAX_DAILY_TRADES = 50

def check_daily_limits(daily_pnl, trade_count, portfolio_value):
    if daily_pnl < -portfolio_value * MAX_DAILY_LOSS:
        return False, "Daily loss limit hit - stop trading"
    if trade_count >= MAX_DAILY_TRADES:
        return False, "Max trades reached for today"
    return True, "Continue"
```

#### **Drawdown Limits**
- Track peak portfolio value
- If current value drops X% from peak, reduce exposure or halt
- Common thresholds: 10% warning, 20% halt

### Implementation Checklist

```markdown
□ Position sizing limits (% per trade, % total)
□ Stop-loss on every position
□ Daily loss limit
□ Maximum drawdown trigger
□ Maximum number of trades per day
□ Minimum time between trades
□ Symbol diversification limits
□ Sector exposure limits
□ Kill switch / emergency stop
□ Alert system for anomalies
□ Daily reconciliation
□ Weekly strategy review
```

### Monitoring & Alerts

Set up alerts for:
- Order rejections
- Large slippage (>0.5%)
- Unusual volatility
- API errors
- Position limit approaching
- Daily/weekly loss thresholds

### The "Sleep Test"

Ask yourself: *Can I sleep at night with this system running?*

If no, your safeguards aren't strong enough.

---

## 7. Recommendations for Matt

### Starting Path

1. **Phase 1: Paper Trading (2-3 months)**
   - Open Alpaca paper trading account
   - Implement a simple strategy (e.g., RSI-based)
   - Focus on the infrastructure: logging, monitoring, error handling
   - Track performance religiously

2. **Phase 2: Small Live Trading (3-6 months)**
   - Start with $1,000-$5,000
   - Position sizes of $100-$500 max
   - Keep human oversight high
   - Document everything for potential compliance questions

3. **Phase 3: Scale If Successful**
   - Only after consistent positive results
   - Gradually increase position sizes
   - Consider IBKR if you want options/futures
   - Keep improving safeguards

### What to Study

- **Quantitative Finance:** Portfolio theory, risk metrics (Sharpe, Sortino)
- **Python for Finance:** Pandas, NumPy, backtrader/zipline
- **Machine Learning:** Start with scikit-learn, understand overfitting deeply
- **Market Microstructure:** How orders flow, market makers, liquidity

### Resources

- **Books:**
  - "Advances in Financial Machine Learning" by Marcos López de Prado
  - "Algorithmic Trading" by Ernest Chan
  - "Python for Finance" by Yves Hilpisch

- **Courses:**
  - QuantInsti's EPAT (paid but comprehensive)
  - Coursera's Machine Learning Specialization
  - AlgoTrading101 (free articles)

- **Communities:**
  - r/algotrading (Reddit)
  - Alpaca Slack/Discord
  - QuantConnect forums

### Final Advice

1. **Your FA background is an asset** — you understand markets, risk, and client psychology better than most algo traders
2. **Start simple** — complex doesn't mean profitable
3. **Respect the PDT rule** — either keep $25k+ or use a cash account
4. **Paper trade until you're bored** — then trade live
5. **The goal isn't to beat the market** — consistent, risk-adjusted returns with automation
6. **Document everything** — for your compliance, for taxes, for learning

---

## Appendix: Quick Links

- [Alpaca Documentation](https://docs.alpaca.markets/)
- [Alpaca Python SDK](https://github.com/alpacahq/alpaca-py)
- [IBKR API](https://www.interactivebrokers.com/en/trading/ib-api.php)
- [SEC Pattern Day Trading Info](https://www.sec.gov/files/daytrading.pdf)
- [FINRA Algorithmic Trading Rules](https://www.finra.org/rules-guidance/key-topics/algorithmic-trading)
- [Schwab Developer Portal](https://developer.schwab.com/)

---

*Disclaimer: This is research for educational purposes. Nothing here is financial or legal advice. Algorithmic trading involves substantial risk of loss. Past performance does not guarantee future results. Consult with qualified professionals before implementing any trading system.*
