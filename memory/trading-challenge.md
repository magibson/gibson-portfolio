# Trading Challenge - Jan 31 to Feb 28, 2026

## Overview
- **Goal:** Beat S&P 500 (VOO) over 1 month
- **Capital:** $1,000 Alpaca paper trading
- **Autonomy:** FULL — trade without approval
- **Benchmark start:** VOO @ $636.22

## Current Positions (as of Feb 6)
| Symbol | Allocation | Value | Unrealized P/L |
|--------|------------|-------|----------------|
| AMD    | ~43%       | $397  | -11.7% 🔴      |
| NVDA   | ~37%       | $347  | -1.0%          |
| VST    | ~20%       | $189  | -5.4%          |
| **Total** | 100%   | $933  | **-6.7%**      |

**vs Benchmark:** VOO -1.8% → We're trailing by ~5%

## Strategy (Updated Feb 2, 2026)

### Trading Style: SWING TRADING
**Rationale:** Research confirms swing trading outperforms day trading for:
- Non-real-time monitoring (we check in periodically)
- Fewer decisions = fewer mistakes
- Less emotional, psychologically easier
- Paper money = no urgency to minimize exposure time

### Risk Management: NO HARD STOP LOSSES
**Rationale based on research:**
1. **Backtests show stops hurt returns** - QuantifiedStrategies: "stop-loss mostly makes your strategies perform worse"
2. **X trader consensus**: Tight stops "frequently hurt by volatility" on AMD/NVDA
3. **Earnings plays**: Stops get triggered by pre-earnings noise, then stocks recover
4. **@i_manage_risk**: "No hard stops on volatile names—use alerts to avoid false lows"

**New Framework:**
- ❌ No automatic stop losses (removed -5% rule)
- ⚠️ -10% position: Review thesis, consider trimming
- 🔴 -20% position: Serious reassessment required  
- 🚨 -25% portfolio: Catastrophic stop - full exit, capital preservation only

### Position Strategy

**AMD (45% → Hold)**
- Earnings Feb 3 (tomorrow) - key catalyst
- Already +6% = roughly 1x implied move
- X sentiment: 60-70% bullish, "breakout potential to $350"
- @Mr_Derivatives: "AMD chart outperforming NVDA—like AMD for 2026"
- Decision: **HOLD through earnings** - we need alpha to beat VOO

**NVDA (35% → Hold)**  
- Earnings Feb 25 - late in challenge
- Expected to "skull fuck earnings" per @Citrini7
- 65% revenue growth potential (Gene Munster)
- Watch AMD reaction for NVDA sentiment spillover
- Decision: **HOLD** - reassess after AMD earnings

**VST (20% → Monitor)**
- Energy/nuclear diversification play
- Slightly down (-1.3%)
- If AMD/NVDA rally hard, consider trimming VST to add
- Decision: **HOLD for now** - provides sector diversification

## Key Learnings from Research

### Why No Stop Losses for This Challenge:
1. Paper money = no real capital at risk
2. 1-month timeframe = need to capture full moves
3. Volatile stocks (AMD/NVDA) = stops trigger on noise
4. Goal is to beat benchmark, not preserve capital
5. Concentrated bets need room to work

### What X Traders Say:
- "Only hold through earnings if profit >2x implied move" (@TraderLion)
- "Short strangles for IV crush edge" (options strategy)
- "Exit without cushion" lesson from stopped-out AMD trades
- AMD expected to outperform NVDA near-term

## Key Dates
- **Feb 3: AMD earnings** ← CRITICAL - hold position
- Feb 12: CPI data
- **Feb 25: NVDA earnings** ← Second catalyst
- Feb 28: Challenge ends

## Weekly Check-ins
- Week 1 (Feb 3-7): AMD earnings reaction - adjust if blowout or disaster
- Week 2 (Feb 10-14): CPI impact, momentum check
- Week 3 (Feb 17-21): Pre-NVDA positioning, consider adding if dip
- Week 4 (Feb 24-28): NVDA earnings, final sprint

## Decision Log
| Date | Action | Rationale |
|------|--------|-----------|
| Jan 31 | Initial: AMD 45%, NVDA 35%, VST 20% | Earnings catalysts + momentum |
| Feb 2 | Removed -5% stop losses | Research: stops hurt returns on volatile stocks |
| Feb 2 | Kept positions unchanged | AMD +6% into earnings, sentiment bullish |
| Feb 6 | HOLD all positions | AMD -17% post-earnings but recovering (-11.7% now). Selling locks in loss. Wait for NVDA catalyst Feb 25. |

## Tools
- Alpaca keys: `~/clawd/projects/alpaca-trader/.env`
- Positions: `python3 ~/clawd/projects/alpaca-trader/trader.py positions`
- Trade: `python3 ~/clawd/projects/alpaca-trader/trader.py [buy/sell] [symbol] [amount]`

## Cron
- Fridays 4pm ET: Send Matt performance update
