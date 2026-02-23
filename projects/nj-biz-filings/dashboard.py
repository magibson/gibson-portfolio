#!/usr/bin/env python3
"""
NJ Business Filings Dashboard
Flask web dashboard for viewing and tracking NJ business filing leads.

Port: 8107
Usage: python3 dashboard.py
"""

import csv
import io
import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, g, jsonify, redirect, render_template_string, request, Response, url_for

app = Flask(__name__)

DATA_DIR = Path.home() / "clawd" / "data" / "biz-filings"
DB_PATH = DATA_DIR / "tracking.db"
MASTER_JSON = DATA_DIR / "master.json"

# ──────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────

def get_db():
    if "db" not in g:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(str(DB_PATH))
        g.db.row_factory = sqlite3.Row
        _init_db(g.db)
    return g.db


@app.teardown_appcontext
def close_db(e=None):
    db = g.pop("db", None)
    if db:
        db.close()


def _init_db(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS entities (
            entity_id    TEXT PRIMARY KEY,
            name         TEXT,
            type         TEXT,
            formed_date  TEXT,
            agent_name   TEXT,
            agent_address TEXT,
            city         TEXT,
            state        TEXT DEFAULT 'NJ',
            zip          TEXT,
            notes        TEXT DEFAULT '',
            contacted    INTEGER DEFAULT 0,
            contacted_date TEXT,
            json_data    TEXT,
            imported_at  TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()


def sync_json_to_db():
    """Import any entities from master.json that aren't in the DB yet."""
    if not MASTER_JSON.exists():
        return 0
    with open(MASTER_JSON) as f:
        master = json.load(f)

    db = get_db()
    new_count = 0
    for e in master.get("entities", []):
        existing = db.execute("SELECT entity_id FROM entities WHERE entity_id=?", (e["entity_id"],)).fetchone()
        if not existing:
            db.execute(
                """INSERT OR IGNORE INTO entities
                   (entity_id, name, type, formed_date, agent_name, agent_address,
                    city, state, zip, json_data)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    e.get("entity_id"),
                    e.get("name"),
                    e.get("type"),
                    e.get("formed_date"),
                    e.get("agent_name"),
                    e.get("agent_address"),
                    e.get("agent_city"),
                    e.get("agent_state", "NJ"),
                    e.get("agent_zip"),
                    json.dumps(e),
                ),
            )
            new_count += 1
    db.commit()
    return new_count


# ──────────────────────────────────────────────
# HTML Template
# ──────────────────────────────────────────────

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NJ Business Filings Monitor</title>
<style>
  :root {
    --bg: #0f0f23;
    --card: #1a1a2e;
    --border: #2a2a4a;
    --text: #e0e0ff;
    --muted: #888aaa;
    --blue: #4fc3f7;
    --green: #4caf50;
    --yellow: #ffc107;
    --red: #ef5350;
    --purple: #ba68c8;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; font-size: 14px; }
  header { background: var(--card); border-bottom: 1px solid var(--border); padding: 16px 24px; display: flex; align-items: center; gap: 12px; }
  header h1 { font-size: 1.3rem; color: var(--blue); }
  header .sub { color: var(--muted); font-size: 0.85rem; }
  .container { padding: 20px 24px; max-width: 1400px; margin: 0 auto; }
  .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 20px; }
  .stat-card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; text-align: center; }
  .stat-card .value { font-size: 2rem; font-weight: 700; color: var(--blue); }
  .stat-card .label { font-size: 0.78rem; color: var(--muted); margin-top: 4px; text-transform: uppercase; letter-spacing: 0.05em; }
  .filters { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 14px 16px; margin-bottom: 16px; display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
  .filters select, .filters input { background: var(--bg); border: 1px solid var(--border); color: var(--text); padding: 6px 10px; border-radius: 6px; font-size: 13px; }
  .btn { padding: 7px 14px; border-radius: 6px; border: none; cursor: pointer; font-size: 13px; font-weight: 500; transition: opacity .2s; }
  .btn:hover { opacity: .85; }
  .btn-blue { background: var(--blue); color: #000; }
  .btn-green { background: var(--green); color: #fff; }
  .btn-muted { background: var(--border); color: var(--text); }
  table { width: 100%; border-collapse: collapse; background: var(--card); border-radius: 8px; overflow: hidden; border: 1px solid var(--border); }
  th { background: #141428; color: var(--muted); text-transform: uppercase; font-size: 0.72rem; letter-spacing: 0.06em; padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); }
  td { padding: 10px 12px; border-bottom: 1px solid var(--border); vertical-align: top; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: rgba(79,195,247,.05); }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.72rem; font-weight: 600; }
  .badge-new { background: rgba(76,175,80,.2); color: var(--green); }
  .badge-mid { background: rgba(255,193,7,.2); color: var(--yellow); }
  .badge-old { background: rgba(100,100,120,.3); color: var(--muted); }
  .badge-contacted { background: rgba(186,104,200,.2); color: var(--purple); }
  .badge-llc { background: rgba(79,195,247,.15); color: var(--blue); }
  .badge-corp { background: rgba(255,193,7,.15); color: var(--yellow); }
  .contact-btn { font-size: 12px; padding: 4px 8px; }
  .notes-input { background: transparent; border: 1px solid var(--border); color: var(--text); padding: 3px 6px; border-radius: 4px; font-size: 12px; width: 140px; }
  .notes-input:focus { outline: none; border-color: var(--blue); }
  .entity-name { font-weight: 600; color: var(--text); }
  .entity-id { font-size: 0.72rem; color: var(--muted); }
  .pagination { display: flex; gap: 8px; align-items: center; padding: 14px 0; justify-content: center; }
  .pagination a { color: var(--blue); text-decoration: none; padding: 4px 10px; border-radius: 4px; border: 1px solid var(--border); }
  .pagination a.active { background: var(--blue); color: #000; }
  .sync-bar { background: rgba(79,195,247,.1); border: 1px solid rgba(79,195,247,.2); border-radius: 6px; padding: 10px 14px; margin-bottom: 14px; display: flex; align-items: center; gap: 10px; font-size: 13px; }
  .empty-state { text-align: center; padding: 60px 20px; color: var(--muted); }
  .empty-state h2 { font-size: 1.2rem; margin-bottom: 8px; color: var(--text); }
</style>
</head>
<body>
<header>
  <div>🏢</div>
  <div>
    <h1>NJ Business Filings Monitor</h1>
    <div class="sub">New LLCs & Corps → Financial Advisor Leads · Auto-refresh 60s</div>
  </div>
  <div style="margin-left:auto; display:flex; gap:8px;">
    <a href="/export{{ '?' + request.query_string.decode() if request.query_string else '' }}" class="btn btn-green">⬇ Export CSV</a>
    <button class="btn btn-blue" onclick="syncJson()">🔄 Sync JSON</button>
  </div>
</header>

<div class="container">
  <!-- Stats -->
  <div class="stats-grid">
    <div class="stat-card"><div class="value">{{ stats.total }}</div><div class="label">Total Leads</div></div>
    <div class="stat-card"><div class="value">{{ stats.today }}</div><div class="label">Added Today</div></div>
    <div class="stat-card"><div class="value">{{ stats.week }}</div><div class="label">This Week</div></div>
    <div class="stat-card"><div class="value">{{ stats.new_uncontacted }}</div><div class="label">New (uncontacted)</div></div>
    <div class="stat-card"><div class="value">{{ stats.contacted }}</div><div class="label">Contacted</div></div>
    <div class="stat-card"><div class="value">{{ stats.llc }}</div><div class="label">LLCs</div></div>
    <div class="stat-card"><div class="value">{{ stats.corp }}</div><div class="label">Corps</div></div>
  </div>

  <!-- Filters -->
  <form method="get" action="/">
    <div class="filters">
      <select name="etype">
        <option value="">All Types</option>
        <option value="LLC" {{ 'selected' if filters.etype=='LLC' else '' }}>LLC</option>
        <option value="CORP" {{ 'selected' if filters.etype=='CORP' else '' }}>Corporation</option>
      </select>
      <select name="contacted">
        <option value="">All Status</option>
        <option value="0" {{ 'selected' if filters.contacted=='0' else '' }}>Not Contacted</option>
        <option value="1" {{ 'selected' if filters.contacted=='1' else '' }}>Contacted</option>
      </select>
      <select name="age">
        <option value="">Any Age</option>
        <option value="7" {{ 'selected' if filters.age=='7' else '' }}>< 7 days</option>
        <option value="14" {{ 'selected' if filters.age=='14' else '' }}>< 14 days</option>
        <option value="30" {{ 'selected' if filters.age=='30' else '' }}>< 30 days</option>
      </select>
      <input type="text" name="q" placeholder="Search name / agent..." value="{{ filters.q }}" style="width:200px;">
      <button type="submit" class="btn btn-blue">Filter</button>
      <a href="/" class="btn btn-muted">Clear</a>
      <span style="margin-left:auto; color:var(--muted); font-size:12px;">{{ total_count }} results</span>
    </div>
  </form>

  <!-- Table -->
  {% if entities %}
  <table>
    <thead>
      <tr>
        <th>Entity</th>
        <th>Type</th>
        <th>Formed</th>
        <th>Age</th>
        <th>Registered Agent</th>
        <th>Address</th>
        <th>Status</th>
        <th>Notes</th>
        <th>Action</th>
      </tr>
    </thead>
    <tbody>
      {% for e in entities %}
      <tr id="row-{{ e.entity_id }}">
        <td>
          <div class="entity-name">{{ e.name }}</div>
          <div class="entity-id">#{{ e.entity_id }}</div>
        </td>
        <td>
          <span class="badge {{ 'badge-llc' if 'LLC' in e.type else 'badge-corp' }}">{{ e.type }}</span>
        </td>
        <td>{{ e.formed_date or '—' }}</td>
        <td>
          {% if e.age_days is not none %}
            {% if e.age_days <= 7 %}
              <span class="badge badge-new">{{ e.age_days }}d</span>
            {% elif e.age_days <= 14 %}
              <span class="badge badge-mid">{{ e.age_days }}d</span>
            {% else %}
              <span class="badge badge-old">{{ e.age_days }}d</span>
            {% endif %}
          {% else %}—{% endif %}
        </td>
        <td>{{ e.agent_name or '—' }}</td>
        <td style="font-size:12px; color:var(--muted);">
          {{ e.agent_address or '' }}{% if e.city %}<br>{{ e.city }}, {{ e.state }} {{ e.zip or '' }}{% endif %}
        </td>
        <td>
          {% if e.contacted %}
            <span class="badge badge-contacted">✓ Called</span>
            {% if e.contacted_date %}<div style="font-size:11px;color:var(--muted);">{{ e.contacted_date[:10] }}</div>{% endif %}
          {% else %}
            <span class="badge badge-new">New</span>
          {% endif %}
        </td>
        <td>
          <input class="notes-input" id="notes-{{ e.entity_id }}" value="{{ e.notes or '' }}"
                 onblur="saveNotes('{{ e.entity_id }}')" placeholder="Add note...">
        </td>
        <td>
          {% if not e.contacted %}
          <button class="btn btn-green contact-btn" onclick="markContacted('{{ e.entity_id }}')">✓ Called</button>
          {% else %}
          <button class="btn btn-muted contact-btn" onclick="unmarkContacted('{{ e.entity_id }}')">Undo</button>
          {% endif %}
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>

  <!-- Pagination -->
  {% if total_pages > 1 %}
  <div class="pagination">
    {% if page > 1 %}<a href="?{{ pagination_query }}&page={{ page-1 }}">← Prev</a>{% endif %}
    {% for p in range(1, total_pages+1) %}
      <a href="?{{ pagination_query }}&page={{ p }}" class="{{ 'active' if p == page else '' }}">{{ p }}</a>
    {% endfor %}
    {% if page < total_pages %}<a href="?{{ pagination_query }}&page={{ page+1 }}">Next →</a>{% endif %}
  </div>
  {% endif %}

  {% else %}
  <div class="empty-state">
    <h2>No leads yet</h2>
    <p>Run the scraper to pull new business filings:<br><code>python3 ~/clawd/projects/nj-biz-filings/scraper.py</code></p>
    <br>
    <button class="btn btn-blue" onclick="syncJson()">🔄 Sync from JSON files</button>
  </div>
  {% endif %}
</div>

<script>
  // Auto-refresh every 60 seconds
  setTimeout(() => location.reload(), 60000);

  async function markContacted(entityId) {
    const res = await fetch('/api/contact', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({entity_id: entityId, contacted: 1})
    });
    if (res.ok) location.reload();
  }

  async function unmarkContacted(entityId) {
    const res = await fetch('/api/contact', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({entity_id: entityId, contacted: 0})
    });
    if (res.ok) location.reload();
  }

  async function saveNotes(entityId) {
    const notes = document.getElementById('notes-' + entityId).value;
    await fetch('/api/notes', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({entity_id: entityId, notes: notes})
    });
  }

  async function syncJson() {
    const btn = event.target;
    btn.textContent = '⏳ Syncing...';
    btn.disabled = true;
    const res = await fetch('/api/sync', {method: 'POST'});
    const data = await res.json();
    btn.textContent = `✅ +${data.new_count} imported`;
    setTimeout(() => location.reload(), 1500);
  }
</script>
</body>
</html>
"""


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────

@app.route("/")
def index():
    sync_json_to_db()
    db = get_db()

    # Filters
    etype = request.args.get("etype", "")
    contacted = request.args.get("contacted", "")
    age = request.args.get("age", "")
    q = request.args.get("q", "")
    page = int(request.args.get("page", 1))
    per_page = 25

    # Build query
    where = ["1=1"]
    params = []
    if etype:
        where.append("type LIKE ?")
        params.append(f"%{etype}%")
    if contacted in ("0", "1"):
        where.append("contacted=?")
        params.append(int(contacted))
    if age:
        cutoff = (datetime.now() - timedelta(days=int(age))).strftime("%Y-%m-%d")
        where.append("formed_date >= ?")
        params.append(cutoff)
    if q:
        where.append("(name LIKE ? OR agent_name LIKE ? OR agent_address LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])

    where_sql = " AND ".join(where)
    total_count = db.execute(f"SELECT COUNT(*) FROM entities WHERE {where_sql}", params).fetchone()[0]
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    offset = (page - 1) * per_page

    rows = db.execute(
        f"SELECT * FROM entities WHERE {where_sql} ORDER BY formed_date DESC, imported_at DESC LIMIT ? OFFSET ?",
        params + [per_page, offset],
    ).fetchall()

    # Calculate age_days
    entities = []
    today = datetime.now().date()
    for row in rows:
        e = dict(row)
        if e.get("formed_date"):
            try:
                fd = datetime.strptime(e["formed_date"], "%Y-%m-%d").date()
                e["age_days"] = (today - fd).days
            except Exception:
                e["age_days"] = None
        else:
            e["age_days"] = None
        entities.append(e)

    # Stats
    stats = {
        "total": db.execute("SELECT COUNT(*) FROM entities").fetchone()[0],
        "today": db.execute(
            "SELECT COUNT(*) FROM entities WHERE imported_at >= date('now')"
        ).fetchone()[0],
        "week": db.execute(
            "SELECT COUNT(*) FROM entities WHERE imported_at >= date('now', '-7 days')"
        ).fetchone()[0],
        "new_uncontacted": db.execute(
            "SELECT COUNT(*) FROM entities WHERE contacted=0 AND formed_date >= date('now', '-30 days')"
        ).fetchone()[0],
        "contacted": db.execute("SELECT COUNT(*) FROM entities WHERE contacted=1").fetchone()[0],
        "llc": db.execute("SELECT COUNT(*) FROM entities WHERE type LIKE '%LLC%'").fetchone()[0],
        "corp": db.execute("SELECT COUNT(*) FROM entities WHERE type LIKE '%Corp%'").fetchone()[0],
    }

    # Build pagination query string without page param
    pq_args = {k: v for k, v in request.args.items() if k != "page"}
    pagination_query = "&".join(f"{k}={v}" for k, v in pq_args.items())

    return render_template_string(
        TEMPLATE,
        entities=entities,
        stats=stats,
        filters={"etype": etype, "contacted": contacted, "age": age, "q": q},
        page=page,
        total_pages=total_pages,
        total_count=total_count,
        pagination_query=pagination_query,
        request=request,
    )


@app.route("/api/contact", methods=["POST"])
def api_contact():
    data = request.json
    db = get_db()
    contacted_date = datetime.now().isoformat() if data.get("contacted") else None
    db.execute(
        "UPDATE entities SET contacted=?, contacted_date=? WHERE entity_id=?",
        (data.get("contacted", 0), contacted_date, data.get("entity_id")),
    )
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/notes", methods=["POST"])
def api_notes():
    data = request.json
    db = get_db()
    db.execute("UPDATE entities SET notes=? WHERE entity_id=?", (data.get("notes", ""), data.get("entity_id")))
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/sync", methods=["POST"])
def api_sync():
    new_count = sync_json_to_db()
    return jsonify({"ok": True, "new_count": new_count})


@app.route("/export")
def export():
    db = get_db()

    # Apply same filters as index
    etype = request.args.get("etype", "")
    contacted = request.args.get("contacted", "")
    age = request.args.get("age", "")
    q = request.args.get("q", "")

    where = ["1=1"]
    params = []
    if etype:
        where.append("type LIKE ?")
        params.append(f"%{etype}%")
    if contacted in ("0", "1"):
        where.append("contacted=?")
        params.append(int(contacted))
    if age:
        cutoff = (datetime.now() - timedelta(days=int(age))).strftime("%Y-%m-%d")
        where.append("formed_date >= ?")
        params.append(cutoff)
    if q:
        where.append("(name LIKE ? OR agent_name LIKE ? OR agent_address LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])

    rows = db.execute(
        f"SELECT * FROM entities WHERE {' AND '.join(where)} ORDER BY formed_date DESC",
        params,
    ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["Entity Name", "Entity ID", "Type", "Formed Date", "Agent Name", "Agent Address", "City", "State", "ZIP",
         "Contacted", "Contacted Date", "Notes", "Imported At"]
    )
    for row in rows:
        writer.writerow([
            row["name"], row["entity_id"], row["type"], row["formed_date"],
            row["agent_name"], row["agent_address"], row["city"], row["state"], row["zip"],
            "Yes" if row["contacted"] else "No", row["contacted_date"] or "",
            row["notes"] or "", row["imported_at"] or "",
        ])

    output.seek(0)
    filename = f"nj-biz-filings-{datetime.now().strftime('%Y-%m-%d')}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


if __name__ == "__main__":
    print("🏢 NJ Business Filings Dashboard starting on http://localhost:8107")
    print(f"   Data dir: {DATA_DIR}")
    app.run(host="0.0.0.0", port=8107, debug=False)
