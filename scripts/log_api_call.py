"""
log_api_call.py - Lightweight API usage tracker
Logs actual API calls to SQLite for real cost/usage tracking in the morning dashboard.
"""

import sqlite3
import time
from pathlib import Path

DB_PATH = Path("/Users/jarvis/clawd/data/api_usage.db")


def _get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS api_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            tokens_in INTEGER DEFAULT 0,
            tokens_out INTEGER DEFAULT 0,
            cost_usd REAL DEFAULT 0.0,
            metadata TEXT DEFAULT ''
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_service_ts ON api_calls(service, timestamp)")
    conn.commit()
    return conn


def log_call(service: str, tokens_in: int = 0, tokens_out: int = 0, cost: float = 0.0, metadata: str = ""):
    """Log a single API call to the tracking DB."""
    try:
        conn = _get_conn()
        conn.execute(
            "INSERT INTO api_calls (service, timestamp, tokens_in, tokens_out, cost_usd, metadata) VALUES (?,?,?,?,?,?)",
            (service, int(time.time()), tokens_in, tokens_out, cost, metadata)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass  # Never crash the caller


def get_monthly_stats(service: str) -> dict:
    """Return {calls, cost, tokens_in, tokens_out} for the current calendar month."""
    try:
        import datetime
        now = datetime.datetime.now()
        # First second of current month (UTC approximation — good enough for display)
        month_start = int(datetime.datetime(now.year, now.month, 1).timestamp())
        conn = _get_conn()
        row = conn.execute(
            """SELECT COUNT(*), COALESCE(SUM(cost_usd),0), COALESCE(SUM(tokens_in),0), COALESCE(SUM(tokens_out),0)
               FROM api_calls WHERE service=? AND timestamp >= ?""",
            (service, month_start)
        ).fetchone()
        conn.close()
        return {
            "calls": row[0] or 0,
            "cost": round(row[1] or 0.0, 4),
            "tokens_in": row[2] or 0,
            "tokens_out": row[3] or 0,
        }
    except Exception:
        return {"calls": 0, "cost": 0.0, "tokens_in": 0, "tokens_out": 0}


def get_all_monthly_stats() -> dict:
    """Return monthly stats for ALL services as {service: {calls, cost, ...}}."""
    try:
        import datetime
        now = datetime.datetime.now()
        month_start = int(datetime.datetime(now.year, now.month, 1).timestamp())
        conn = _get_conn()
        rows = conn.execute(
            """SELECT service, COUNT(*), COALESCE(SUM(cost_usd),0), COALESCE(SUM(tokens_in),0), COALESCE(SUM(tokens_out),0)
               FROM api_calls WHERE timestamp >= ?
               GROUP BY service""",
            (month_start,)
        ).fetchall()
        conn.close()
        return {
            row[0]: {
                "calls": row[1],
                "cost": round(row[2], 4),
                "tokens_in": row[3],
                "tokens_out": row[4],
            }
            for row in rows
        }
    except Exception:
        return {}


if __name__ == "__main__":
    # Quick test / status check
    stats = get_all_monthly_stats()
    if stats:
        print("Monthly API usage:")
        for svc, s in sorted(stats.items()):
            print(f"  {svc:20s}  {s['calls']:5d} calls  ${s['cost']:.4f}")
    else:
        print("No usage data yet. DB is ready at:", DB_PATH)
