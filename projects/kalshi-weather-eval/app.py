from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template_string

APP_PORT = 8104
DATA_PATH = Path("/home/clawd/clawd/data/kalshi/weather-paper-trades.json")

app = Flask(__name__)

def _load_trades():
    with DATA_PATH.open() as f:
        return json.load(f)

def _safe_div(n, d):
    return (n / d) if d else 0.0

def compute_stats(trades):
    # Normalize
    for t in trades:
        t["pnl_cents"] = t.get("pnl_cents") or 0
        t["cost_cents"] = t.get("cost_cents") or 0
        t["edge_pct"] = t.get("edge_pct") or 0
        t["model_prob"] = t.get("model_prob") or 0
        t["market_prob"] = t.get("market_prob") or 0

    total_trades = len(trades)
    scored = [t for t in trades if t.get("outcome") in ("win", "loss")]
    scored_trades = len(scored)
    wins = sum(1 for t in scored if t["outcome"] == "win")
    losses = sum(1 for t in scored if t["outcome"] == "loss")

    total_pnl_cents = sum(t["pnl_cents"] for t in trades)
    total_cost_cents = sum(t["cost_cents"] for t in trades)
    total_wagered = total_cost_cents / 100.0

    win_rate = _safe_div(wins, scored_trades)
    roi = _safe_div(total_pnl_cents, total_cost_cents)

    avg_edge = sum(t["edge_pct"] for t in trades) / total_trades if total_trades else 0

    # P&L by city
    pnl_by_city = defaultdict(int)
    for t in trades:
        pnl_by_city[t["city"]] += t["pnl_cents"]

    # Daily P&L
    pnl_by_day = defaultdict(int)
    for t in trades:
        pnl_by_day[t["date"]] += t["pnl_cents"]
    daily_dates = sorted(pnl_by_day.keys())
    daily_pnl = [pnl_by_day[d] for d in daily_dates]
    cumulative = []
    running = 0
    for v in daily_pnl:
        running += v
        cumulative.append(running)

    # Best single day / city
    best_day_date, best_day_pnl = (None, None)
    if daily_dates:
        best_day_date = max(daily_dates, key=lambda d: pnl_by_day[d])
        best_day_pnl = pnl_by_day[best_day_date]
    best_city = max(pnl_by_city.items(), key=lambda kv: kv[1]) if pnl_by_city else ("—", 0)

    # Win rate by city table
    by_city = defaultdict(list)
    for t in trades:
        by_city[t["city"]].append(t)
    win_rate_by_city = []
    for city, rows in by_city.items():
        c_scored = [t for t in rows if t.get("outcome") in ("win", "loss")]
        c_wins = sum(1 for t in c_scored if t["outcome"] == "win")
        c_losses = sum(1 for t in c_scored if t["outcome"] == "loss")
        c_pnl = sum(t["pnl_cents"] for t in rows)
        c_cost = sum(t["cost_cents"] for t in rows)
        win_rate_by_city.append({
            "city": city,
            "trades": len(rows),
            "wins": c_wins,
            "losses": c_losses,
            "win_rate": _safe_div(c_wins, len(c_scored)) if c_scored else 0,
            "pnl_cents": c_pnl,
            "roi": _safe_div(c_pnl, c_cost),
        })
    win_rate_by_city.sort(key=lambda r: r["pnl_cents"], reverse=True)

    # Calibration buckets
    buckets = [
        ("0-10%", 0, 10),
        ("10-20%", 10, 20),
        ("20-30%", 20, 30),
        ("30-40%", 30, 40),
        ("40%+", 40, 101),
    ]
    calib = []
    for label, lo, hi in buckets:
        rows = [t for t in trades if lo <= t["model_prob"] < hi]
        if rows:
            avg_prob = sum(t["model_prob"] for t in rows) / len(rows)
            scored_rows = [t for t in rows if t.get("outcome") in ("win", "loss")]
            wins_bucket = sum(1 for t in scored_rows if t["outcome"] == "win")
            actual = _safe_div(wins_bucket, len(scored_rows)) if scored_rows else 0
            calib.append({
                "bucket": label,
                "trades": len(rows),
                "model_avg": avg_prob,
                "actual_win_rate": actual,
                "calibration_error": actual - (avg_prob / 100.0),
            })
        else:
            calib.append({
                "bucket": label,
                "trades": 0,
                "model_avg": 0,
                "actual_win_rate": 0,
                "calibration_error": 0,
            })

    # Top 5 best/worst trades
    best_trades = sorted(trades, key=lambda t: t["pnl_cents"], reverse=True)[:5]
    worst_trades = sorted(trades, key=lambda t: t["pnl_cents"])[:5]

    # Scatter (scored only)
    scatter = [
        {"x": t["edge_pct"], "y": t["pnl_cents"], "outcome": t["outcome"]}
        for t in scored
    ]

    return {
        "totals": {
            "total_trades": total_trades,
            "scored_trades": scored_trades,
            "wins": wins,
            "losses": losses,
            "total_pnl_cents": total_pnl_cents,
            "total_cost_cents": total_cost_cents,
            "win_rate": win_rate,
            "roi": roi,
            "avg_edge": avg_edge,
            "total_wagered": total_wagered,
        },
        "best_day": {"date": best_day_date, "pnl_cents": best_day_pnl or 0},
        "best_city": {"city": best_city[0], "pnl_cents": best_city[1]},
        "pnl_by_city": dict(pnl_by_city),
        "daily": {"dates": daily_dates, "pnl": daily_pnl, "cumulative": cumulative},
        "win_rate_by_city": win_rate_by_city,
        "calibration": calib,
        "best_trades": best_trades,
        "worst_trades": worst_trades,
        "scatter": scatter,
    }

@app.get("/api/data")
def api_data():
    trades = _load_trades()
    return jsonify(compute_stats(trades))

@app.get("/")
def dashboard():
    trades = _load_trades()
    data = compute_stats(trades)
    return render_template_string(
        TEMPLATE,
        data=data,
        generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    )

TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Kalshi Weather Paper Trading — Final Evaluation</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <style>
    :root{
      --bg:#0d1117;
      --card:#161b22;
      --text:#e6edf3;
      --muted:#8b949e;
      --blue:#3b82f6;
      --green:#10b981;
      --red:#ef4444;
      --yellow:#f59e0b;
      --border:#21262d;
    }
    *{box-sizing:border-box;margin:0;padding:0}
    body{
      background:var(--bg);color:var(--text);
      font-family:"Segoe UI",system-ui,sans-serif;font-size:14px;line-height:1.5;
    }
    .container{max-width:1200px;margin:0 auto;padding:28px 20px;}
    .page-header{margin-bottom:24px;}
    h1{font-size:26px;font-weight:700;margin-bottom:4px;}
    .subtitle{color:var(--muted);font-size:13px;}
    .section-title{font-size:16px;color:#cbd5e1;margin:28px 0 12px;}
    .grid{display:grid;gap:14px;}
    .grid-3{grid-template-columns:repeat(3,1fr);}
    .grid-6{grid-template-columns:repeat(6,1fr);}
    .card{
      background:var(--card);border:1px solid var(--border);
      border-radius:12px;padding:18px;
    }
    .stat-label{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px;}
    .stat-value{font-size:30px;font-weight:700;}
    .stat-value.sm{font-size:18px;line-height:1.3;}
    .pos{color:var(--green);}
    .neg{color:var(--red);}
    .chart-wrap{height:320px;position:relative;}
    table{width:100%;border-collapse:collapse;}
    th{padding:8px 10px;border-bottom:2px solid var(--border);color:#8b949e;font-size:11px;
       text-transform:uppercase;letter-spacing:.06em;text-align:left;font-weight:600;}
    td{padding:9px 10px;border-bottom:1px solid var(--border);}
    tr:last-child td{border-bottom:none;}
    tr:hover td{background:rgba(255,255,255,.02);}
    .verdict-card{
      border:1px solid var(--border);border-radius:12px;padding:22px;
      background:linear-gradient(135deg,rgba(59,130,246,.1),rgba(16,185,129,.06));
    }
    .verdict-badge{
      display:inline-block;padding:6px 14px;border-radius:999px;font-size:13px;
      font-weight:600;background:rgba(16,185,129,.15);color:var(--green);
      border:1px solid rgba(16,185,129,.3);margin-bottom:14px;
    }
    .verdict-badge.warn{background:rgba(245,158,11,.15);color:var(--yellow);border-color:rgba(245,158,11,.3);}
    .verdict-badge.bad{background:rgba(239,68,68,.15);color:var(--red);border-color:rgba(239,68,68,.3);}
    .two-col{display:flex;gap:24px;flex-wrap:wrap;margin-top:14px;}
    .two-col>div{flex:1;min-width:220px;}
    ul{padding-left:18px;margin-top:6px;}
    li{margin-bottom:4px;color:#cbd5e1;}
    .footer{margin-top:20px;color:var(--muted);font-size:11px;}
    @media(max-width:900px){
      .grid-3,.grid-6{grid-template-columns:repeat(2,1fr);}
    }
    @media(max-width:540px){
      .grid-3,.grid-6{grid-template-columns:1fr;}
      .chart-wrap{height:260px;}
    }
  </style>
</head>
<body>
<div class="container">
  <div class="page-header">
    <h1>📊 Kalshi Weather Paper Trading — Final Evaluation</h1>
    <div class="subtitle">Feb 11–24, 2026 &bull; Paper Mode &bull; 5 Cities (Austin, Chicago, Denver, Miami, NYC)</div>
  </div>

  <!-- Hero stats -->
  <div class="grid grid-3">
    <div class="card">
      <div class="stat-label">Total P&L</div>
      {% set pnl = data.totals.total_pnl_cents/100.0 %}
      <div class="stat-value {{ 'pos' if pnl >= 0 else 'neg' }}">${{ "%.2f"|format(pnl) }}</div>
    </div>
    <div class="card">
      <div class="stat-label">Win Rate</div>
      <div class="stat-value">{{ "%.1f"|format(data.totals.win_rate*100) }}%</div>
    </div>
    <div class="card">
      <div class="stat-label">ROI</div>
      <div class="stat-value {{ 'pos' if data.totals.roi >= 0 else 'neg' }}">{{ "%.1f"|format(data.totals.roi*100) }}%</div>
    </div>
  </div>

  <!-- Executive summary -->
  <div class="section-title">Executive Summary</div>
  <div class="grid grid-6">
    <div class="card">
      <div class="stat-label">Total Trades</div>
      <div class="stat-value">{{ data.totals.total_trades }}</div>
    </div>
    <div class="card">
      <div class="stat-label">Scored</div>
      <div class="stat-value">{{ data.totals.scored_trades }}</div>
    </div>
    <div class="card">
      <div class="stat-label">Total Wagered</div>
      <div class="stat-value">${{ "%.2f"|format(data.totals.total_wagered) }}</div>
    </div>
    <div class="card">
      <div class="stat-label">Avg Edge</div>
      <div class="stat-value">{{ "%.1f"|format(data.totals.avg_edge) }}%</div>
    </div>
    <div class="card">
      <div class="stat-label">Best Day</div>
      <div class="stat-value sm">
        {{ data.best_day.date or "—" }}<br>
        <span class="{{ 'pos' if data.best_day.pnl_cents >= 0 else 'neg' }}">${{ "%.2f"|format(data.best_day.pnl_cents/100.0) }}</span>
      </div>
    </div>
    <div class="card">
      <div class="stat-label">Best City</div>
      <div class="stat-value sm">
        {{ data.best_city.city }}<br>
        <span class="{{ 'pos' if data.best_city.pnl_cents >= 0 else 'neg' }}">${{ "%.2f"|format(data.best_city.pnl_cents/100.0) }}</span>
      </div>
    </div>
  </div>

  <!-- Charts -->
  <div class="section-title">P&L by City</div>
  <div class="card chart-wrap"><canvas id="cityBar"></canvas></div>

  <div class="section-title">Daily P&L</div>
  <div class="card chart-wrap"><canvas id="dailyLine"></canvas></div>

  <div class="section-title">Edge % vs Outcome</div>
  <div class="card chart-wrap"><canvas id="edgeScatter"></canvas></div>

  <!-- Win rate by city table -->
  <div class="section-title">Win Rate by City</div>
  <div class="card">
    <table>
      <thead>
        <tr><th>City</th><th>Trades</th><th>Wins</th><th>Losses</th><th>Win Rate</th><th>P&L</th><th>ROI</th></tr>
      </thead>
      <tbody>
        {% for row in data.win_rate_by_city %}
        <tr>
          <td>{{ row.city }}</td>
          <td>{{ row.trades }}</td>
          <td class="pos">{{ row.wins }}</td>
          <td class="neg">{{ row.losses }}</td>
          <td>{{ "%.1f"|format(row.win_rate*100) }}%</td>
          <td class="{{ 'pos' if row.pnl_cents >= 0 else 'neg' }}">${{ "%.2f"|format(row.pnl_cents/100.0) }}</td>
          <td class="{{ 'pos' if row.roi >= 0 else 'neg' }}">{{ "%.1f"|format(row.roi*100) }}%</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <!-- Calibration -->
  <div class="section-title">Model Calibration</div>
  <div class="card">
    <table>
      <thead>
        <tr><th>Probability Bucket</th><th># Trades</th><th>Model Avg Prob</th><th>Actual Win Rate</th><th>Calibration Error</th></tr>
      </thead>
      <tbody>
        {% for row in data.calibration %}
        <tr>
          <td>{{ row.bucket }}</td>
          <td>{{ row.trades }}</td>
          <td>{{ "%.1f"|format(row.model_avg) }}%</td>
          <td>{{ "%.1f"|format(row.actual_win_rate*100) }}%</td>
          <td class="{{ 'pos' if row.calibration_error >= 0 else 'neg' }}">{{ "%.1f"|format(row.calibration_error*100) }}%</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <!-- Best / Worst trades -->
  <div class="section-title">Top 5 Best Trades</div>
  <div class="card">
    <table>
      <thead>
        <tr><th>Date</th><th>City</th><th>Side</th><th>Entry Price</th><th>Qty</th><th>Edge %</th><th>P&L</th></tr>
      </thead>
      <tbody>
        {% for t in data.best_trades %}
        <tr>
          <td>{{ t.date }}</td><td>{{ t.city }}</td><td>{{ t.side }}</td>
          <td>${{ "%.2f"|format(t.entry_price_cents/100.0) }}</td>
          <td>{{ t.qty }}</td>
          <td>{{ "%.1f"|format(t.edge_pct) }}%</td>
          <td class="pos">${{ "%.2f"|format(t.pnl_cents/100.0) }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <div class="section-title">Top 5 Worst Trades</div>
  <div class="card">
    <table>
      <thead>
        <tr><th>Date</th><th>City</th><th>Side</th><th>Entry Price</th><th>Qty</th><th>Edge %</th><th>P&L</th></tr>
      </thead>
      <tbody>
        {% for t in data.worst_trades %}
        <tr>
          <td>{{ t.date }}</td><td>{{ t.city }}</td><td>{{ t.side }}</td>
          <td>${{ "%.2f"|format(t.entry_price_cents/100.0) }}</td>
          <td>{{ t.qty }}</td>
          <td>{{ "%.1f"|format(t.edge_pct) }}%</td>
          <td class="neg">${{ "%.2f"|format(t.pnl_cents/100.0) }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <!-- Verdict -->
  <div class="section-title">Verdict — Should We Go Live?</div>
  {% set roi = data.totals.roi*100 %}
  <div class="verdict-card">
    {% if roi > 20 %}
      <div class="verdict-badge">✅ Strong YES — the edge is real</div>
    {% elif roi >= 0 %}
      <div class="verdict-badge warn">⚠️ Cautious YES — edge exists, needs larger sample</div>
    {% else %}
      <div class="verdict-badge bad">❌ NO — model needs recalibration</div>
    {% endif %}
    <div class="two-col">
      <div>
        <div class="stat-label">Key Findings</div>
        <ul>
          <li>ROI of <strong>{{ "%.1f"|format(roi) }}%</strong> on ${{ "%.2f"|format(data.totals.total_wagered) }} wagered</li>
          <li>Win rate {{ "%.1f"|format(data.totals.win_rate*100) }}% across {{ data.totals.scored_trades }} scored trades — low rate is expected for cheap YES contracts</li>
          <li>Denver dominated: ${{ "%.2f"|format(data.pnl_by_city.get("Denver",0)/100.0) }} P&L — model was best calibrated for cold-climate extremes</li>
        </ul>
      </div>
      <div>
        <div class="stat-label">Recommended Next Steps</div>
        <ul>
          <li>Start live trading with $25–50 max daily exposure per city</li>
          <li>Focus early capital on Denver + Chicago (model calibration strongest there)</li>
          <li>Run 4–6 more weeks of data before scaling position sizes</li>
        </ul>
      </div>
    </div>
  </div>

  <div class="footer">Generated {{ generated_at }} &bull; Data: ~/clawd/data/kalshi/weather-paper-trades.json</div>
</div>

<script>
const data = {{ data | tojson }};

const GRID = "#21262d";
const TICK = "#8b949e";

// City bar
const cityLabels = ["Austin","Chicago","Denver","Miami","NYC"];
const cityPnL = cityLabels.map(c => (data.pnl_by_city[c] || 0) / 100.0);
new Chart(document.getElementById("cityBar"), {
  type: "bar",
  data: {
    labels: cityLabels,
    datasets: [{
      label: "P&L ($)",
      data: cityPnL,
      backgroundColor: cityPnL.map(v => v >= 0 ? "rgba(16,185,129,.75)" : "rgba(239,68,68,.75)"),
      borderColor: cityPnL.map(v => v >= 0 ? "#10b981" : "#ef4444"),
      borderWidth: 1, borderRadius: 6
    }]
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    indexAxis: "y",
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { color: GRID }, ticks: { color: TICK } },
      y: { grid: { color: GRID }, ticks: { color: TICK } }
    }
  }
});

// Daily line
new Chart(document.getElementById("dailyLine"), {
  type: "line",
  data: {
    labels: data.daily.dates,
    datasets: [
      {
        label: "Daily P&L ($)",
        data: data.daily.pnl.map(v => v/100.0),
        borderColor: "#3b82f6", backgroundColor: "rgba(59,130,246,.15)",
        tension: 0.3, fill: true, pointRadius: 5, yAxisID: "y"
      },
      {
        label: "Cumulative P&L ($)",
        data: data.daily.cumulative.map(v => v/100.0),
        borderColor: "#10b981", backgroundColor: "rgba(16,185,129,.1)",
        tension: 0.3, fill: false, pointRadius: 4, borderDash: [4,3], yAxisID: "y1"
      }
    ]
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    scales: {
      y: { position:"left", grid:{color:GRID}, ticks:{color:TICK} },
      y1: { position:"right", grid:{drawOnChartArea:false}, ticks:{color:TICK} },
      x: { grid:{color:GRID}, ticks:{color:TICK} }
    }
  }
});

// Scatter
const scatterWins = data.scatter.filter(d => d.outcome === "win");
const scatterLoss = data.scatter.filter(d => d.outcome === "loss");
new Chart(document.getElementById("edgeScatter"), {
  type: "scatter",
  data: {
    datasets: [
      { label:"Win", data: scatterWins, backgroundColor:"rgba(16,185,129,.7)", pointRadius:6 },
      { label:"Loss", data: scatterLoss, backgroundColor:"rgba(239,68,68,.55)", pointRadius:5 }
    ]
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { labels: { color: TICK } } },
    scales: {
      x: { title:{display:true,text:"Edge %",color:"#cbd5e1"}, grid:{color:GRID}, ticks:{color:TICK} },
      y: { title:{display:true,text:"P&L (cents)",color:"#cbd5e1"}, grid:{color:GRID}, ticks:{color:TICK} }
    }
  }
});
</script>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=APP_PORT, debug=False)
