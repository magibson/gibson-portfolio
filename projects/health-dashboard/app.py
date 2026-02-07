from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from statistics import mean

from flask import Flask, render_template_string

DATA_PATH = Path("/home/clawd/clawd/memory/health-log.json")

app = Flask(__name__)


def load_entries():
    if not DATA_PATH.exists():
        return []
    with DATA_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    entries = payload.get("entries", [])
    def parse_date(entry):
        try:
            return datetime.strptime(entry.get("date", ""), "%Y-%m-%d")
        except ValueError:
            return datetime.min
    entries = sorted(entries, key=parse_date)
    return entries


def zone_recovery(score: float) -> str:
    if score >= 67:
        return "green"
    if score >= 34:
        return "yellow"
    return "red"


def zone_sleep(hours: float) -> str:
    if hours >= 7:
        return "green"
    if hours >= 6:
        return "yellow"
    return "red"


def pearson(xs, ys):
    if len(xs) < 2:
        return None
    if len(xs) != len(ys):
        return None
    mean_x = mean(xs)
    mean_y = mean(ys)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = sum((x - mean_x) ** 2 for x in xs)
    den_y = sum((y - mean_y) ** 2 for y in ys)
    if den_x == 0 or den_y == 0:
        return None
    return num / math.sqrt(den_x * den_y)


def format_corr(value):
    if value is None:
        return "N/A"
    return f"{value:.2f}"


def streaks(entries):
    current = 0
    best = 0
    running = 0
    for entry in entries:
        if entry.get("recovery", {}).get("score", 0) >= 67:
            running += 1
            best = max(best, running)
        else:
            running = 0
    for entry in reversed(entries):
        if entry.get("recovery", {}).get("score", 0) >= 67:
            current += 1
        else:
            break
    return current, best


@app.route("/")
def dashboard():
    entries = load_entries()
    latest = entries[-1] if entries else {}

    def safe_get(path, default=0):
        cur = latest
        for key in path:
            if not isinstance(cur, dict):
                return default
            cur = cur.get(key)
        return cur if cur is not None else default

    recovery_score = safe_get(["recovery", "score"])
    sleep_hours = safe_get(["sleep", "hours"])
    sleep_perf = safe_get(["sleep", "performance"])
    strain_score = safe_get(["strain", "score"])

    recent_7 = entries[-7:]
    trend_30 = entries[-30:]

    labels_7 = [e.get("date", "") for e in recent_7]
    labels_30 = [e.get("date", "") for e in trend_30]

    recovery_7 = [e.get("recovery", {}).get("score", 0) for e in recent_7]
    sleep_7 = [e.get("sleep", {}).get("hours", 0) for e in recent_7]
    strain_7 = [e.get("strain", {}).get("score", 0) for e in recent_7]

    recovery_30 = [e.get("recovery", {}).get("score", 0) for e in trend_30]
    sleep_hours_30 = [e.get("sleep", {}).get("hours", 0) for e in trend_30]
    sleep_perf_30 = [e.get("sleep", {}).get("performance", 0) for e in trend_30]
    strain_30 = [e.get("strain", {}).get("score", 0) for e in trend_30]

    avg_recovery = mean(recovery_30) if recovery_30 else 0
    avg_sleep = mean(sleep_hours_30) if sleep_hours_30 else 0
    avg_strain = mean(strain_30) if strain_30 else 0

    def best_worst(metric):
        if not trend_30:
            return None, None
        best_entry = max(trend_30, key=lambda e: e.get(metric[0], {}).get(metric[1], 0))
        worst_entry = min(trend_30, key=lambda e: e.get(metric[0], {}).get(metric[1], 0))
        return best_entry, worst_entry

    best_recovery, worst_recovery = best_worst(("recovery", "score"))
    best_sleep, worst_sleep = best_worst(("sleep", "hours"))
    best_strain, worst_strain = best_worst(("strain", "score"))

    current_streak, best_streak = streaks(entries)

    rec_scores = [e.get("recovery", {}).get("score", 0) for e in trend_30]
    sleep_hours = [e.get("sleep", {}).get("hours", 0) for e in trend_30]
    strain_scores = [e.get("strain", {}).get("score", 0) for e in trend_30]

    corr_sleep_recovery = pearson(sleep_hours, rec_scores)
    corr_strain_recovery = pearson(strain_scores, rec_scores)

    sleep_good = [r for r, h in zip(rec_scores, sleep_hours) if h >= 7]
    sleep_low = [r for r, h in zip(rec_scores, sleep_hours) if h < 7]
    sleep_insight = "Not enough sleep data yet."
    if sleep_good and sleep_low:
        if mean(sleep_good) > mean(sleep_low):
            sleep_insight = "Better recovery on nights with 7+ hours sleep."
        else:
            sleep_insight = "Recovery not higher on 7+ hour sleep nights yet."

    template = """
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Health Trends Dashboard</title>
        <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            :root {
                --bg: #111316;
                --card: #1b1f24;
                --card-border: #2a3038;
                --text: #f5f7fb;
                --muted: #9aa3af;
                --green: #2ecc71;
                --yellow: #f5c542;
                --red: #ff5c5c;
                --accent: #5aa9ff;
            }
            * { box-sizing: border-box; }
            body {
                margin: 0;
                font-family: 'Space Grotesk', sans-serif;
                background: radial-gradient(circle at top, #1a1f26 0%, #0f1114 55%, #0b0d10 100%);
                color: var(--text);
            }
            header {
                padding: 24px clamp(16px, 4vw, 48px);
                display: flex;
                flex-wrap: wrap;
                gap: 12px;
                align-items: center;
                justify-content: space-between;
            }
            .title {
                font-size: clamp(24px, 3vw, 36px);
                font-weight: 700;
            }
            .subtitle {
                color: var(--muted);
                font-size: 14px;
            }
            nav {
                display: flex;
                gap: 12px;
            }
            nav a {
                color: var(--text);
                text-decoration: none;
                padding: 6px 12px;
                border: 1px solid var(--card-border);
                border-radius: 999px;
                font-size: 13px;
            }
            .container {
                padding: 0 clamp(16px, 4vw, 48px) 40px;
                display: grid;
                gap: 24px;
            }
            .grid {
                display: grid;
                gap: 16px;
            }
            .grid-3 {
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            }
            .grid-2 {
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            }
            .card {
                background: var(--card);
                border: 1px solid var(--card-border);
                border-radius: 16px;
                padding: 18px;
                box-shadow: 0 10px 24px rgba(0, 0, 0, 0.3);
            }
            .card h3 {
                margin: 0 0 12px;
                font-size: 16px;
                color: var(--muted);
                letter-spacing: 0.02em;
            }
            .stat {
                font-size: 36px;
                font-weight: 700;
            }
            .stat small {
                font-size: 14px;
                font-weight: 500;
                color: var(--muted);
            }
            .pill {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 4px 10px;
                border-radius: 999px;
                font-size: 12px;
                border: 1px solid var(--card-border);
            }
            .green { color: var(--green); }
            .yellow { color: var(--yellow); }
            .red { color: var(--red); }
            .sparkline {
                height: 80px;
            }
            .trend-chart {
                height: 280px;
            }
            .insight {
                display: flex;
                flex-direction: column;
                gap: 8px;
                font-size: 14px;
                color: var(--muted);
            }
            .insight strong {
                color: var(--text);
            }
            @media (max-width: 700px) {
                header {
                    flex-direction: column;
                    align-items: flex-start;
                }
                nav {
                    flex-wrap: wrap;
                }
            }
        </style>
    </head>
    <body>
        <header>
            <div>
                <div class="title">Health Trends Dashboard</div>
                <div class="subtitle">Latest data from {{ latest_date }}</div>
            </div>
            <nav>
                <a href="#overview">Overview</a>
                <a href="#trends">Trends</a>
                <a href="#insights">Insights</a>
            </nav>
        </header>

        <div class="container">
            <section id="overview" class="grid grid-3">
                <div class="card">
                    <h3>Recovery Score</h3>
                    <div class="stat {{ recovery_zone }}">{{ recovery_score|round(0) }}</div>
                    <div class="pill {{ recovery_zone }}">HRV {{ hrv|round(1) }} · RHR {{ resting_hr|round(0) }}</div>
                </div>
                <div class="card">
                    <h3>Sleep Performance</h3>
                    <div class="stat {{ sleep_zone }}">{{ sleep_perf|round(0) }}<small>/100</small></div>
                    <div class="pill {{ sleep_zone }}">{{ sleep_hours|round(1) }} hrs · Eff {{ sleep_eff|round(0) }}%</div>
                </div>
                <div class="card">
                    <h3>Strain</h3>
                    <div class="stat" style="color: var(--accent);">{{ strain_score|round(1) }}</div>
                    <div class="pill">Calories {{ calories }} · Max HR {{ max_hr }}</div>
                </div>
            </section>

            <section class="grid grid-3">
                <div class="card">
                    <h3>Recovery (7-day)</h3>
                    <canvas id="recoverySpark" class="sparkline"></canvas>
                </div>
                <div class="card">
                    <h3>Sleep Hours (7-day)</h3>
                    <canvas id="sleepSpark" class="sparkline"></canvas>
                </div>
                <div class="card">
                    <h3>Strain (7-day)</h3>
                    <canvas id="strainSpark" class="sparkline"></canvas>
                </div>
            </section>

            <section id="trends" class="grid grid-2">
                <div class="card">
                    <h3>Recovery Trend (30-day)</h3>
                    <canvas id="recoveryTrend" class="trend-chart"></canvas>
                </div>
                <div class="card">
                    <h3>Sleep Trend (30-day)</h3>
                    <canvas id="sleepTrend" class="trend-chart"></canvas>
                </div>
                <div class="card">
                    <h3>Strain Trend (30-day)</h3>
                    <canvas id="strainTrend" class="trend-chart"></canvas>
                </div>
            </section>

            <section id="insights" class="grid grid-2">
                <div class="card">
                    <h3>Insights</h3>
                    <div class="insight">
                        <div><strong>{{ sleep_insight }}</strong></div>
                        <div>Sleep vs Recovery correlation: <strong>{{ corr_sleep_recovery }}</strong></div>
                        <div>Strain vs Recovery correlation: <strong>{{ corr_strain_recovery }}</strong></div>
                        <div>Current green recovery streak: <strong>{{ current_streak }} days</strong></div>
                        <div>Best green recovery streak: <strong>{{ best_streak }} days</strong></div>
                    </div>
                </div>
                <div class="card">
                    <h3>Averages / Best / Worst</h3>
                    <div class="insight">
                        <div>Average recovery: <strong>{{ avg_recovery|round(1) }}</strong></div>
                        <div>Average sleep hours: <strong>{{ avg_sleep|round(1) }}</strong></div>
                        <div>Average strain: <strong>{{ avg_strain|round(1) }}</strong></div>
                        <div>Best recovery: <strong>{{ best_recovery_score }}</strong> on {{ best_recovery_date }}</div>
                        <div>Worst recovery: <strong>{{ worst_recovery_score }}</strong> on {{ worst_recovery_date }}</div>
                        <div>Best sleep: <strong>{{ best_sleep_score }}</strong> hrs on {{ best_sleep_date }}</div>
                        <div>Worst sleep: <strong>{{ worst_sleep_score }}</strong> hrs on {{ worst_sleep_date }}</div>
                    </div>
                </div>
            </section>
        </div>

        <script>
            const labels7 = {{ labels_7|tojson }};
            const labels30 = {{ labels_30|tojson }};
            const recovery7 = {{ recovery_7|tojson }};
            const sleep7 = {{ sleep_7|tojson }};
            const strain7 = {{ strain_7|tojson }};
            const recovery30 = {{ recovery_30|tojson }};
            const sleepHours30 = {{ sleep_hours_30|tojson }};
            const sleepPerf30 = {{ sleep_perf_30|tojson }};
            const strain30 = {{ strain_30|tojson }};

            const sparkOptions = {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { display: false },
                    y: { display: false }
                },
                elements: { line: { tension: 0.4, borderWidth: 2 }, point: { radius: 0 } }
            };

            new Chart(document.getElementById('recoverySpark'), {
                type: 'line',
                data: { labels: labels7, datasets: [{ data: recovery7, borderColor: '#2ecc71', backgroundColor: 'rgba(46,204,113,0.15)' }] },
                options: sparkOptions
            });
            new Chart(document.getElementById('sleepSpark'), {
                type: 'line',
                data: { labels: labels7, datasets: [{ data: sleep7, borderColor: '#f5c542', backgroundColor: 'rgba(245,197,66,0.15)' }] },
                options: sparkOptions
            });
            new Chart(document.getElementById('strainSpark'), {
                type: 'line',
                data: { labels: labels7, datasets: [{ data: strain7, borderColor: '#5aa9ff', backgroundColor: 'rgba(90,169,255,0.15)' }] },
                options: sparkOptions
            });

            const trendOptions = {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { labels: { color: '#f5f7fb' } } },
                scales: {
                    x: { ticks: { color: '#9aa3af' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                    y: { ticks: { color: '#9aa3af' }, grid: { color: 'rgba(255,255,255,0.05)' } }
                },
                elements: { line: { tension: 0.3, borderWidth: 2 }, point: { radius: 2 } }
            };

            new Chart(document.getElementById('recoveryTrend'), {
                type: 'line',
                data: {
                    labels: labels30,
                    datasets: [{ label: 'Recovery', data: recovery30, borderColor: '#2ecc71', backgroundColor: 'rgba(46,204,113,0.1)' }]
                },
                options: trendOptions
            });

            new Chart(document.getElementById('sleepTrend'), {
                type: 'line',
                data: {
                    labels: labels30,
                    datasets: [
                        { label: 'Sleep Hours', data: sleepHours30, borderColor: '#f5c542', backgroundColor: 'rgba(245,197,66,0.1)' },
                        { label: 'Sleep Performance', data: sleepPerf30, borderColor: '#5aa9ff', backgroundColor: 'rgba(90,169,255,0.1)' }
                    ]
                },
                options: trendOptions
            });

            new Chart(document.getElementById('strainTrend'), {
                type: 'line',
                data: {
                    labels: labels30,
                    datasets: [{ label: 'Strain', data: strain30, borderColor: '#ff8c42', backgroundColor: 'rgba(255,140,66,0.1)' }]
                },
                options: trendOptions
            });
        </script>
    </body>
    </html>
    """

    def get_entry_value(entry, path, default="--"):
        cur = entry
        for key in path:
            if not isinstance(cur, dict):
                return default
            cur = cur.get(key)
        return cur if cur is not None else default

    def fmt_entry(entry, path):
        if not entry:
            return "--", "--"
        return get_entry_value(entry, path, "--"), entry.get("date", "--")

    best_recovery_score, best_recovery_date = fmt_entry(best_recovery, ("recovery", "score"))
    worst_recovery_score, worst_recovery_date = fmt_entry(worst_recovery, ("recovery", "score"))
    best_sleep_score, best_sleep_date = fmt_entry(best_sleep, ("sleep", "hours"))
    worst_sleep_score, worst_sleep_date = fmt_entry(worst_sleep, ("sleep", "hours"))

    return render_template_string(
        template,
        latest_date=latest.get("date", "--"),
        recovery_score=recovery_score,
        recovery_zone=zone_recovery(recovery_score),
        hrv=safe_get(["recovery", "hrv"]),
        resting_hr=safe_get(["recovery", "resting_hr"]),
        sleep_perf=sleep_perf,
        sleep_eff=safe_get(["sleep", "efficiency"]),
        sleep_hours=sleep_hours if isinstance(sleep_hours, (int, float)) else safe_get(["sleep", "hours"]),
        sleep_zone=zone_sleep(safe_get(["sleep", "hours"])),
        strain_score=strain_score,
        calories=safe_get(["strain", "calories"]),
        max_hr=safe_get(["strain", "max_hr"]),
        labels_7=labels_7,
        labels_30=labels_30,
        recovery_7=recovery_7,
        sleep_7=sleep_7,
        strain_7=strain_7,
        recovery_30=recovery_30,
        sleep_hours_30=sleep_hours_30,
        sleep_perf_30=sleep_perf_30,
        strain_30=strain_30,
        sleep_insight=sleep_insight,
        corr_sleep_recovery=format_corr(corr_sleep_recovery),
        corr_strain_recovery=format_corr(corr_strain_recovery),
        current_streak=current_streak,
        best_streak=best_streak,
        avg_recovery=avg_recovery,
        avg_sleep=avg_sleep,
        avg_strain=avg_strain,
        best_recovery_score=best_recovery_score,
        best_recovery_date=best_recovery_date,
        worst_recovery_score=worst_recovery_score,
        worst_recovery_date=worst_recovery_date,
        best_sleep_score=best_sleep_score,
        best_sleep_date=best_sleep_date,
        worst_sleep_score=worst_sleep_score,
        worst_sleep_date=worst_sleep_date,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8087, debug=False)
