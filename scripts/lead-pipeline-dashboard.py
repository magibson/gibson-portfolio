#!/usr/bin/env python3
"""
Lead Pipeline Dashboard — Matt Gibson | New York Life
Unified prospect management, call scripts, and NYL CRM export.
Port: 8094
"""

import os
import sys
import csv
import json
import sqlite3
import subprocess
from datetime import datetime, timedelta
from io import StringIO, BytesIO

from flask import (
    Flask, render_template_string, request, redirect,
    url_for, flash, jsonify, send_file, g
)

# ── Paths ──────────────────────────────────────────────────────────────────────
HOME = os.path.expanduser("~")
CLAWD = os.path.join(HOME, "clawd")
DB_PATH = os.path.join(CLAWD, "leads", "pipeline.db")
LEADS_DIR = os.path.join(CLAWD, "leads")
LINKEDIN_DB = os.path.join(CLAWD, "projects", "linkedin-prospector", "server", "prospector.db")
DOSSIER_SCRIPT = os.path.join(CLAWD, "scripts", "prospect-dossier.py")
VENV_PYTHON = os.path.join(CLAWD, ".venv", "bin", "python3")

app = Flask(__name__)
app.secret_key = "nyl-pipeline-2026-matt"

# ── Call Scripts ───────────────────────────────────────────────────────────────
CALL_SCRIPTS = {
    "Annuity Owner": {
        "opening": 'Hi [First Name], this is Matt Gibson calling. You recently requested some information on annuities and we sent you a booklet — did you get a chance to look at it?',
        "discovery": [
            "How long have you had your annuity?",
            "Is it still in the surrender period?",
            "Are you currently taking income from it?",
            "How do you feel about the current rate you're earning?",
        ],
        "appointment": "I'd love to do a quick review — 30-45 min, no cost, no obligation. Does [day] work for you?",
        "objection": "A lot has changed with annuity rates — would it be worth 30 minutes just to compare what's available now?",
    },
    "Annuity Prospect": {
        "opening": "Hi [First Name], this is Matt Gibson calling. You recently requested some information on annuities — how can I help you?",
        "discovery": [
            "What made you start looking into annuities?",
            "Do you have money sitting in CDs, savings, or an old 401k?",
            "How important is it to you to protect your money from market risk?",
            "Are you looking for income now or in the future?",
        ],
        "appointment": "I'd love to do a quick review — 30-45 min, no cost, no obligation. Does [day] work for you?",
        "objection": "It takes just 30 minutes to see if an annuity fits your situation — no pressure at all.",
    },
    "IRA/401k Rollover": {
        "opening": "Hi [First Name], this is Matt Gibson calling. You recently requested some information on IRA and 401k rollovers — do you have a quick minute?",
        "discovery": [
            "What got you thinking about rolling over your retirement account?",
            "Are you still with the company, or have you already left?",
            "Is your money actively managed right now, or just sitting there?",
            "When are you planning to retire?",
            "What do you want this money to do for you going forward?",
        ],
        "appointment": "Let's make sure nothing gets left on the table — I can walk you through your options in 30 minutes, no cost, no obligation.",
        "objection": "A lot of people don't realize they have options until it's too late — 30 minutes could save you thousands.",
    },
    "Retiree": {
        "opening": "Hi [First Name], this is Matt Gibson calling. I specialize in working with retirees in New Jersey to make sure their income lasts and they're protected — do you have a quick minute?",
        "discovery": [
            "Are you currently drawing from Social Security, a pension, or both?",
            "Do you have any old IRAs or 401ks you're not actively managing?",
            "How are you feeling about your current income in retirement?",
            "Are you concerned at all about outliving your savings?",
        ],
        "appointment": "I'd love to do a complimentary review — 30-45 minutes, no cost, no obligation. When works best for you?",
        "objection": "Many retirees I work with find one or two tweaks that make a big difference — it's worth a quick look.",
    },
    "LinkedIn-JobChange": {
        "opening": "Hi [First Name], this is Matt Gibson — I came across your profile on LinkedIn and wanted to reach out. I work with professionals in NJ on retirement and wealth protection strategies. Do you have a quick minute?",
        "discovery": [
            "Congrats on the new role — how's the transition going?",
            "Did your previous employer have a 401k you might be looking to roll over?",
            "Are you thinking at all about protecting your income during this change?",
            "What does your financial planning look like right now?",
        ],
        "appointment": "I'd love to connect for 20-30 minutes just to walk through your options — no pressure, just a conversation.",
        "objection": "Job transitions are actually one of the best times to review your financial picture — happy to make it quick.",
    },
    "LinkedIn-FederalEmployee": {
        "opening": "Hi [First Name], this is Matt Gibson — I saw your profile on LinkedIn and noticed you work with the federal government. I specialize in helping federal employees understand their FEGLI, TSP, and FERS benefits — do you have a quick minute?",
        "discovery": [
            "How long have you been a federal employee?",
            "Have you had a chance to review your FEGLI life insurance coverage recently?",
            "Are you familiar with how your TSP fits into your overall retirement picture?",
            "Are you approaching retirement or still years out?",
        ],
        "appointment": "I'd love to do a complimentary federal benefits review — 30 minutes, no cost, completely confidential.",
        "objection": "Federal benefits can be complicated — most employees I meet have coverage gaps they didn't know about.",
    },
    "Propwire": {
        "opening": "Hi [First Name], this is Matt Gibson calling. I work with homeowners in [City] on protecting their home and family — do you have a quick minute?",
        "discovery": [
            "How long have you been in your home?",
            "Do you currently have life insurance coverage?",
            "Have you looked into mortgage protection insurance?",
            "What does your current financial protection look like for your family?",
        ],
        "appointment": "I can put together a quick quote — no cost, no obligation. Takes about 20 minutes. When works for you?",
        "objection": "Even if you have coverage through work, it usually doesn't follow you if you leave — worth a quick look.",
    },
    "Default": {
        "opening": "Hi [First Name], this is Matt Gibson calling from New York Life. Do you have a quick minute?",
        "discovery": [
            "How are you currently set up for life insurance and retirement?",
            "Do you have any coverage through your employer?",
            "What's most important to you financially right now?",
        ],
        "appointment": "I'd love to do a quick review — 30 minutes, no cost, no obligation. When works best?",
        "objection": "It's just a conversation — no pressure, and you might find something useful.",
    },
}

def get_script(sub_source):
    return CALL_SCRIPTS.get(sub_source, CALL_SCRIPTS["Default"])

# ── Database ───────────────────────────────────────────────────────────────────
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop("db", None)
    if db:
        db.close()

def init_db():
    os.makedirs(LEADS_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT,
            last_name TEXT,
            full_name TEXT,
            phone TEXT,
            phone2 TEXT,
            phone3 TEXT,
            email TEXT,
            street TEXT,
            city TEXT,
            state TEXT,
            zip TEXT,
            source TEXT,
            sub_source TEXT,
            score INTEGER DEFAULT 0,
            call_blurb TEXT,
            linkedin_url TEXT,
            title TEXT,
            company TEXT,
            notes TEXT,
            date_added TEXT,
            source_file TEXT,
            dedup_key TEXT UNIQUE,
            imported_at TEXT
        );
        CREATE TABLE IF NOT EXISTS call_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            outcome TEXT,
            notes TEXT,
            logged_at TEXT,
            FOREIGN KEY(lead_id) REFERENCES leads(id)
        );
        CREATE INDEX IF NOT EXISTS idx_leads_source ON leads(source);
        CREATE INDEX IF NOT EXISTS idx_leads_sub_source ON leads(sub_source);
        CREATE INDEX IF NOT EXISTS idx_leads_date ON leads(date_added);
        CREATE INDEX IF NOT EXISTS idx_logs_lead ON call_logs(lead_id);
    """)
    conn.commit()
    return conn

def infer_sub_source(campaign_name, search_name=""):
    name = (campaign_name or search_name or "").lower()
    if "federal" in name:
        return "LinkedIn-FederalEmployee"
    if "job" in name or "change" in name:
        return "LinkedIn-JobChange"
    if "retiree" in name or "retirement" in name or "retire" in name:
        return "Retiree"
    if "family" in name or "families" in name:
        return "LinkedIn-JobChange"
    if "high earner" in name or "approaching" in name:
        return "LinkedIn-FederalEmployee"
    return "LinkedIn-JobChange"

def import_all_leads():
    """Import all lead sources into pipeline.db. Safe to re-run (dedup by key)."""
    conn = init_db()
    imported = {"propwire": 0, "monmouth": 0, "priority": 0, "linkedin": 0, "skipped": 0}
    NOW = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def upsert(row, dedup_key):
        try:
            conn.execute("""
                INSERT OR IGNORE INTO leads
                  (first_name, last_name, full_name, phone, phone2, phone3,
                   email, street, city, state, zip, source, sub_source,
                   score, call_blurb, linkedin_url, title, company, source_file, dedup_key,
                   date_added, imported_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, row + (dedup_key, NOW, NOW))
        except Exception as e:
            print(f"  Insert error: {e}")

    # ── 1. propwire_leads_2026-02-23.csv ──────────────────────────────────────
    pw_file = os.path.join(LEADS_DIR, "propwire_leads_2026-02-23.csv")
    if os.path.exists(pw_file):
        with open(pw_file, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                fn = row.get("Owner 1 First Name", "").strip().title()
                ln = row.get("Owner 1 Last Name", "").strip().title()
                if not fn and not ln:
                    imported["skipped"] += 1
                    continue
                addr = row.get("Address", "").strip().title()
                city = row.get("City", "").strip().title()
                state = row.get("State", "NJ").strip()
                zip_ = row.get("Zip", "").strip().zfill(5)
                dedup = f"propwire:{addr}:{zip_}"
                upsert((fn, ln, f"{fn} {ln}".strip(), "", "", "",
                        "", addr, city, state, zip_,
                        "Propwire", "Propwire", 0, "", "", "", "",
                        "propwire_leads_2026-02-23.csv"), dedup)
                imported["propwire"] += 1

    # ── 2. tracerfy_raw — enriched phone/email for propwire leads ─────────────
    tr_file = os.path.join(LEADS_DIR, "tracerfy_raw_2026-02-23.csv")
    if os.path.exists(tr_file):
        with open(tr_file, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                fn = row.get("first_name", "").strip().title()
                ln = row.get("last_name", "").strip().title()
                if not fn or fn == "":
                    continue
                addr = row.get("address", "").strip().title()
                zip_ = str(row.get("zip", "")).strip().zfill(5)
                phone = row.get("primary_phone") or row.get("Mobile-1") or ""
                email = row.get("Email-1", "").strip()
                dedup = f"propwire:{addr}:{zip_}"
                # Update existing if found, else insert
                existing = conn.execute(
                    "SELECT id FROM leads WHERE dedup_key=?", (dedup,)
                ).fetchone()
                if existing:
                    conn.execute(
                        "UPDATE leads SET phone=?, phone2=?, email=? WHERE id=? AND phone=''",
                        (phone, row.get("Mobile-2", ""), email, existing[0])
                    )
                # If not found, insert as new
                else:
                    city = row.get("city", "").strip().title()
                    state = row.get("state", "NJ").strip()
                    upsert((fn, ln, f"{fn} {ln}".strip(), phone,
                            row.get("Mobile-2", ""), row.get("Mobile-3", ""),
                            email, addr, city, state, zip_,
                            "Propwire", "Propwire", 0, "", "", "", "",
                            "tracerfy_raw_2026-02-23.csv"), dedup)

    # ── 3. priority_dial_2026-02-24.csv ────────────────────────────────────────
    pd_file = os.path.join(LEADS_DIR, "priority_dial_2026-02-24.csv")
    if os.path.exists(pd_file):
        with open(pd_file, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("Name", "").strip()
                parts = name.split(" ", 1)
                fn = parts[0].title() if parts else ""
                ln = parts[1].title() if len(parts) > 1 else ""
                addr = row.get("Property Address", "").strip().title()
                city = row.get("City", "").strip().title()
                phone = row.get("Phone 1", "").strip()
                email = row.get("Email", "").strip()
                score = int(row.get("Score", 0) or 0)
                blurb = row.get("Call Blurb", "").strip()
                dedup = f"priority:{addr}:{city}".lower()
                upsert((fn, ln, name, phone,
                        row.get("Phone 2", ""), row.get("Phone 3", ""),
                        email, addr, city, "NJ", "",
                        "Propwire", "Propwire", score, blurb, "", "", "",
                        "priority_dial_2026-02-24.csv"), dedup)
                imported["priority"] += 1

    # ── 4. monmouth_ready_to_dial_20260130.csv ─────────────────────────────────
    mr_file = os.path.join(LEADS_DIR, "monmouth_ready_to_dial_20260130.csv")
    if os.path.exists(mr_file):
        with open(mr_file, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("Name", "").strip()
                parts = name.split(" ", 1)
                fn = parts[0].title() if parts else ""
                ln = parts[1].title() if len(parts) > 1 else ""
                addr = row.get("Address", "").strip().title()
                city = row.get("City", "").strip().title()
                phone = row.get("Primary_Phone", "").strip()
                email = row.get("Email", "").strip()
                dedup = f"monmouth:{addr}:{city}".lower()
                upsert((fn, ln, name.title(), phone,
                        row.get("Alt_Phone_1", ""), row.get("Alt_Phone_2", ""),
                        email, addr, city, "NJ", "",
                        "Propwire", "Annuity Owner", 0, "", "", "", "",
                        "monmouth_ready_to_dial_20260130.csv"), dedup)
                imported["monmouth"] += 1

    # ── 5. dial_ready_2026-02-23.csv ───────────────────────────────────────────
    dr_file = os.path.join(LEADS_DIR, "dial_ready_2026-02-23.csv")
    if os.path.exists(dr_file):
        with open(dr_file, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("Name", "").strip()
                parts = name.split(" ", 1)
                fn = parts[0].title() if parts else ""
                ln = parts[1].title() if len(parts) > 1 else ""
                addr = row.get("Property Address", "").strip().title()
                city = row.get("City", "").strip().title()
                phone = row.get("Phone 1", "").strip()
                email = row.get("Email", "").strip()
                dedup = f"dialready:{addr}:{city}".lower()
                upsert((fn, ln, name.title(), phone,
                        row.get("Phone 2", ""), row.get("Phone 3", ""),
                        email, addr, city, "NJ", "",
                        "Propwire", "Propwire", 0, "", "", "", "",
                        "dial_ready_2026-02-23.csv"), dedup)

    # ── 6. LinkedIn Prospector DB ──────────────────────────────────────────────
    if os.path.exists(LINKEDIN_DB):
        li_conn = sqlite3.connect(LINKEDIN_DB)
        li_conn.row_factory = sqlite3.Row
        # Get campaign names for mapping
        camps = {}
        for c in li_conn.execute("SELECT id, name FROM campaigns"):
            camps[c["id"]] = c["name"]
        leads = li_conn.execute("""
            SELECT id, name, title, company, location, search_name,
                   score, created_at, linkedin_url, campaign_id
            FROM leads
        """).fetchall()
        li_conn.close()
        for lead in leads:
            name = (lead["name"] or "").strip()
            parts = name.split(" ", 1)
            fn = parts[0] if parts else ""
            ln = parts[1] if len(parts) > 1 else ""
            campaign_name = camps.get(lead["campaign_id"], "")
            sub = infer_sub_source(campaign_name, lead["search_name"] or "")
            location = lead["location"] or ""
            city = ""
            state = "NJ"
            if "," in location:
                city = location.split(",")[0].strip()
            date_added = (lead["created_at"] or NOW)[:19]
            dedup = f"linkedin:{lead['id']}"
            try:
                conn.execute("""INSERT OR IGNORE INTO leads
                  (first_name, last_name, full_name, phone, phone2, phone3,
                   email, street, city, state, zip, source, sub_source,
                   score, call_blurb, linkedin_url, title, company, source_file, dedup_key,
                   date_added, imported_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (fn, ln, name, "", "", "", "", "", city, state, "",
                 "LinkedIn", sub, lead["score"] or 0, "",
                 lead["linkedin_url"] or "", lead["title"] or "", lead["company"] or "",
                 "linkedin-prospector.db", dedup, date_added, NOW))
            except Exception as e:
                print(f"  LI insert error: {e}")
            imported["linkedin"] += 1

    conn.commit()
    conn.close()
    total = sum(v for k, v in imported.items() if k != "skipped")
    print(f"✅ Imported: propwire={imported['propwire']} monmouth={imported['monmouth']} "
          f"priority={imported['priority']} linkedin={imported['linkedin']} "
          f"skipped={imported['skipped']} | total≈{total}")
    return imported

# ── HTML Templates ─────────────────────────────────────────────────────────────

BASE_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #0d1117; color: #c9d1d9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 14px; }
a { color: #58a6ff; text-decoration: none; }
a:hover { text-decoration: underline; }

/* Nav */
.nav { background: #161b22; border-bottom: 1px solid #30363d; padding: 12px 20px; display: flex; align-items: center; gap: 20px; flex-wrap: wrap; }
.nav .brand { font-size: 18px; font-weight: 700; color: #f0f6fc; letter-spacing: -0.5px; }
.nav .brand span { color: #3b82f6; }
.nav-links { display: flex; gap: 12px; flex-wrap: wrap; }
.nav-links a { color: #8b949e; padding: 6px 12px; border-radius: 6px; transition: all 0.2s; font-size: 13px; }
.nav-links a:hover, .nav-links a.active { background: #21262d; color: #f0f6fc; text-decoration: none; }
.nav-right { margin-left: auto; }

/* Layout */
.container { max-width: 1400px; margin: 0 auto; padding: 20px; }
.page-header { margin-bottom: 24px; }
.page-header h1 { font-size: 22px; font-weight: 600; color: #f0f6fc; }
.page-header p { color: #8b949e; margin-top: 4px; font-size: 13px; }

/* Cards */
.stats-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px; }
.stat-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; }
.stat-card .label { color: #8b949e; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
.stat-card .value { font-size: 28px; font-weight: 700; color: #f0f6fc; }
.stat-card .sub { color: #8b949e; font-size: 12px; margin-top: 4px; }
.stat-card.blue .value { color: #3b82f6; }
.stat-card.green .value { color: #22c55e; }
.stat-card.yellow .value { color: #eab308; }
.stat-card.red .value { color: #ef4444; }
.stat-card.purple .value { color: #a855f7; }

/* Table */
.card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; overflow: hidden; margin-bottom: 20px; }
.card-header { padding: 14px 18px; border-bottom: 1px solid #30363d; display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.card-header h2 { font-size: 15px; font-weight: 600; color: #f0f6fc; }
table { width: 100%; border-collapse: collapse; }
th { background: #0d1117; color: #8b949e; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; padding: 10px 14px; text-align: left; border-bottom: 1px solid #21262d; }
td { padding: 10px 14px; border-bottom: 1px solid #21262d; color: #c9d1d9; vertical-align: middle; }
tr:last-child td { border-bottom: none; }
tr:hover td { background: #1c2128; }

/* Badges */
.badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 500; }
.badge-blue { background: #1d4ed8; color: #bfdbfe; }
.badge-green { background: #14532d; color: #86efac; }
.badge-yellow { background: #713f12; color: #fde68a; }
.badge-red { background: #7f1d1d; color: #fca5a5; }
.badge-purple { background: #4c1d95; color: #d8b4fe; }
.badge-gray { background: #21262d; color: #8b949e; }
.badge-orange { background: #7c2d12; color: #fed7aa; }

/* Buttons */
.btn { display: inline-block; padding: 7px 14px; border-radius: 6px; font-size: 13px; font-weight: 500; cursor: pointer; border: none; transition: all 0.2s; text-align: center; }
.btn-primary { background: #1d4ed8; color: white; }
.btn-primary:hover { background: #2563eb; color: white; text-decoration: none; }
.btn-success { background: #15803d; color: white; }
.btn-success:hover { background: #16a34a; color: white; text-decoration: none; }
.btn-danger { background: #991b1b; color: white; }
.btn-danger:hover { background: #b91c1c; color: white; text-decoration: none; }
.btn-sm { padding: 4px 10px; font-size: 12px; }
.btn-outline { background: transparent; border: 1px solid #30363d; color: #c9d1d9; }
.btn-outline:hover { background: #21262d; color: white; text-decoration: none; }
.btn-group { display: flex; gap: 8px; flex-wrap: wrap; }

/* Forms */
.form-row { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; align-items: flex-end; }
.form-group { display: flex; flex-direction: column; gap: 4px; }
.form-group label { font-size: 12px; color: #8b949e; }
input, select, textarea { background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 7px 12px; color: #c9d1d9; font-size: 13px; outline: none; }
input:focus, select:focus, textarea:focus { border-color: #3b82f6; }
select option { background: #161b22; }

/* Script card */
.script-card { background: #0d1117; border: 1px solid #21262d; border-radius: 8px; padding: 18px; margin-top: 20px; }
.script-section { margin-bottom: 16px; }
.script-section h4 { color: #3b82f6; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
.script-section p { color: #c9d1d9; line-height: 1.6; background: #161b22; padding: 12px; border-radius: 6px; border-left: 3px solid #3b82f6; }
.script-section ul { list-style: none; }
.script-section ul li { padding: 6px 0; color: #c9d1d9; padding-left: 16px; position: relative; }
.script-section ul li::before { content: "→"; position: absolute; left: 0; color: #3b82f6; }

/* Detail page */
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
@media(max-width: 768px) { .detail-grid { grid-template-columns: 1fr; } .stats-grid { grid-template-columns: 1fr 1fr; } }
.detail-section { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 18px; }
.detail-section h3 { font-size: 14px; font-weight: 600; color: #f0f6fc; margin-bottom: 14px; border-bottom: 1px solid #30363d; padding-bottom: 10px; }
.detail-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #161b22; }
.detail-row:last-child { border-bottom: none; }
.detail-label { color: #8b949e; font-size: 12px; }
.detail-value { color: #f0f6fc; font-size: 13px; font-weight: 500; }

/* Outcome buttons */
.outcome-btn { padding: 8px 14px; border-radius: 6px; border: 1px solid #30363d; background: #161b22; color: #c9d1d9; cursor: pointer; font-size: 12px; transition: all 0.2s; }
.outcome-btn:hover, .outcome-btn.selected { border-color: transparent; }
.outcome-btn[data-outcome="Contacted"]:hover, .outcome-btn[data-outcome="Contacted"].selected { background: #14532d; color: #86efac; }
.outcome-btn[data-outcome="VM"]:hover, .outcome-btn[data-outcome="VM"].selected { background: #1d4ed8; color: #bfdbfe; }
.outcome-btn[data-outcome="No Answer"]:hover, .outcome-btn[data-outcome="No Answer"].selected { background: #374151; color: #d1d5db; }
.outcome-btn[data-outcome="Callback"]:hover, .outcome-btn[data-outcome="Callback"].selected { background: #713f12; color: #fde68a; }
.outcome-btn[data-outcome="Appointment Set"]:hover, .outcome-btn[data-outcome="Appointment Set"].selected { background: #4c1d95; color: #d8b4fe; }
.outcome-btn[data-outcome="Not Interested"]:hover, .outcome-btn[data-outcome="Not Interested"].selected { background: #7f1d1d; color: #fca5a5; }

/* Alert */
.alert { padding: 12px 16px; border-radius: 6px; margin-bottom: 16px; font-size: 13px; }
.alert-success { background: #0d2818; border: 1px solid #14532d; color: #86efac; }
.alert-error { background: #1e0a0a; border: 1px solid #7f1d1d; color: #fca5a5; }
.alert-info { background: #0c1a2e; border: 1px solid #1d4ed8; color: #bfdbfe; }

/* Pagination */
.pagination { display: flex; gap: 6px; justify-content: center; padding: 16px; flex-wrap: wrap; }
.pagination a, .pagination span { padding: 6px 12px; border: 1px solid #30363d; border-radius: 6px; font-size: 13px; color: #8b949e; }
.pagination a:hover { border-color: #3b82f6; color: #3b82f6; text-decoration: none; }
.pagination .current { background: #1d4ed8; border-color: #1d4ed8; color: white; }

/* Upload zone */
.upload-zone { border: 2px dashed #30363d; border-radius: 8px; padding: 40px; text-align: center; cursor: pointer; transition: all 0.2s; }
.upload-zone:hover { border-color: #3b82f6; background: #0c1a2e; }
.upload-zone p { color: #8b949e; margin-top: 8px; font-size: 13px; }

/* Source color map */
.src-propwire { color: #fb923c; }
.src-linkedin { color: #60a5fa; }
.src-retirement { color: #a78bfa; }

/* Score bar */
.score-bar { display: flex; align-items: center; gap: 8px; }
.score-bar .bar { height: 6px; border-radius: 3px; background: #21262d; flex: 1; }
.score-bar .fill { height: 6px; border-radius: 3px; background: #22c55e; }
"""

NAV_HTML = """
<nav class="nav">
  <div class="brand">🏦 <span>NYL</span> Pipeline</div>
  <div class="nav-links">
    <a href="/" class="{active_home}">Dashboard</a>
    <a href="/leads" class="{active_leads}">All Leads</a>
    <a href="/export" class="{active_export}">Export</a>
    <a href="/upload" class="{active_upload}">Upload</a>
  </div>
  <div class="nav-right">
    <a href="/import" class="btn btn-outline btn-sm">🔄 Re-sync</a>
  </div>
</nav>
"""

def nav(page=""):
    return NAV_HTML.format(
        active_home="active" if page == "home" else "",
        active_leads="active" if page == "leads" else "",
        active_export="active" if page == "export" else "",
        active_upload="active" if page == "upload" else "",
    )

def source_badge(source):
    m = {"Propwire": "badge-orange", "LinkedIn": "badge-blue", "RetirementProspects": "badge-purple"}
    cls = m.get(source, "badge-gray")
    return f'<span class="badge {cls}">{source}</span>'

def sub_badge(sub):
    m = {
        "Annuity Owner": "badge-yellow",
        "Annuity Prospect": "badge-orange",
        "IRA/401k Rollover": "badge-green",
        "Retiree": "badge-purple",
        "LinkedIn-JobChange": "badge-blue",
        "LinkedIn-FederalEmployee": "badge-red",
        "Propwire": "badge-gray",
        "RetirementProspects": "badge-purple",
    }
    cls = m.get(sub, "badge-gray")
    return f'<span class="badge {cls}">{sub}</span>'

def outcome_badge(outcome):
    m = {
        "Contacted": "badge-green",
        "VM": "badge-blue",
        "No Answer": "badge-gray",
        "Callback": "badge-yellow",
        "Appointment Set": "badge-purple",
        "Not Interested": "badge-red",
    }
    cls = m.get(outcome, "badge-gray")
    return f'<span class="badge {cls}">{outcome}</span>'

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    db = get_db()

    # Stats
    total = db.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    this_week = db.execute(
        "SELECT COUNT(*) FROM leads WHERE date_added >= ?", (week_ago,)
    ).fetchone()[0]

    by_source = db.execute(
        "SELECT source, COUNT(*) as cnt FROM leads GROUP BY source ORDER BY cnt DESC"
    ).fetchall()

    by_sub = db.execute(
        "SELECT sub_source, COUNT(*) as cnt FROM leads GROUP BY sub_source ORDER BY cnt DESC"
    ).fetchall()

    outcomes = db.execute(
        "SELECT outcome, COUNT(*) as cnt FROM call_logs GROUP BY outcome ORDER BY cnt DESC"
    ).fetchall()

    total_calls = db.execute("SELECT COUNT(*) FROM call_logs").fetchone()[0]
    appointments = db.execute(
        "SELECT COUNT(*) FROM call_logs WHERE outcome='Appointment Set'"
    ).fetchone()[0]

    # Recent leads
    recent = db.execute(
        "SELECT id, full_name, source, sub_source, city, phone, date_added FROM leads ORDER BY id DESC LIMIT 8"
    ).fetchall()

    # Recent activity
    activity = db.execute("""
        SELECT cl.outcome, cl.logged_at, l.full_name, l.id
        FROM call_logs cl JOIN leads l ON cl.lead_id = l.id
        ORDER BY cl.logged_at DESC LIMIT 6
    """).fetchall()

    source_rows = "".join(
        f'<tr><td>{r["source"]}</td><td><strong>{r["cnt"]}</strong></td></tr>'
        for r in by_source
    )
    sub_rows = "".join(
        f'<tr><td>{sub_badge(r["sub_source"])}</td><td><strong>{r["cnt"]}</strong></td></tr>'
        for r in by_sub
    )
    outcome_rows = "".join(
        f'<tr><td>{outcome_badge(r["outcome"])}</td><td><strong>{r["cnt"]}</strong></td></tr>'
        for r in outcomes
    ) or "<tr><td colspan=2 style='color:#8b949e;'>No calls logged yet</td></tr>"

    recent_rows = "".join(f"""
        <tr>
            <td><a href="/lead/{r['id']}">{r['full_name'] or '—'}</a></td>
            <td>{source_badge(r['source'])}</td>
            <td>{sub_badge(r['sub_source'])}</td>
            <td>{r['city'] or '—'}</td>
            <td>{r['phone'] or '—'}</td>
            <td style="color:#8b949e;font-size:11px;">{(r['date_added'] or '')[:10]}</td>
        </tr>
    """ for r in recent)

    activity_rows = "".join(f"""
        <tr>
            <td><a href="/lead/{r['id']}">{r['full_name']}</a></td>
            <td>{outcome_badge(r['outcome'])}</td>
            <td style="color:#8b949e;font-size:11px;">{(r['logged_at'] or '')[:16]}</td>
        </tr>
    """ for r in activity) or "<tr><td colspan=3 style='color:#8b949e;'>No activity yet</td></tr>"

    html = f"""<!DOCTYPE html><html><head><title>NYL Pipeline Dashboard</title>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <style>{BASE_CSS}</style></head><body>
    {nav("home")}
    <div class="container">
      <div class="page-header">
        <h1>Lead Pipeline Dashboard</h1>
        <p>Matt Gibson · New York Life · {datetime.now().strftime("%B %d, %Y")}</p>
      </div>

      <div class="stats-grid">
        <div class="stat-card blue">
          <div class="label">Total Leads</div>
          <div class="value">{total:,}</div>
          <div class="sub">All sources</div>
        </div>
        <div class="stat-card green">
          <div class="label">Added This Week</div>
          <div class="value">{this_week:,}</div>
          <div class="sub">Last 7 days</div>
        </div>
        <div class="stat-card purple">
          <div class="label">Appointments Set</div>
          <div class="value">{appointments}</div>
          <div class="sub">Total logged</div>
        </div>
        <div class="stat-card yellow">
          <div class="label">Total Calls</div>
          <div class="value">{total_calls}</div>
          <div class="sub">Outcomes logged</div>
        </div>
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px;margin-bottom:20px;">
        <div class="card">
          <div class="card-header"><h2>By Source</h2></div>
          <table>{source_rows}</table>
        </div>
        <div class="card">
          <div class="card-header"><h2>By Sub-Source</h2></div>
          <table>{sub_rows}</table>
        </div>
        <div class="card">
          <div class="card-header"><h2>Call Outcomes</h2></div>
          <table>{outcome_rows}</table>
        </div>
      </div>

      <div style="display:grid;grid-template-columns:2fr 1fr;gap:20px;">
        <div class="card">
          <div class="card-header">
            <h2>Recent Leads</h2>
            <a href="/leads" class="btn btn-outline btn-sm">View All →</a>
          </div>
          <table>
            <tr><th>Name</th><th>Source</th><th>Sub-Source</th><th>City</th><th>Phone</th><th>Added</th></tr>
            {recent_rows}
          </table>
        </div>
        <div class="card">
          <div class="card-header">
            <h2>Recent Activity</h2>
          </div>
          <table>
            <tr><th>Lead</th><th>Outcome</th><th>When</th></tr>
            {activity_rows}
          </table>
        </div>
      </div>

      <div style="margin-top:20px;display:flex;gap:12px;">
        <a href="/leads" class="btn btn-primary">📋 Browse Leads</a>
        <a href="/export" class="btn btn-success">📤 NYL Export</a>
        <a href="/upload" class="btn btn-outline">⬆️ Upload CSV</a>
        <a href="/import" class="btn btn-outline">🔄 Re-sync Sources</a>
      </div>
    </div></body></html>"""
    return html

@app.route("/leads")
def leads_list():
    db = get_db()
    page = int(request.args.get("page", 1))
    per_page = 50
    offset = (page - 1) * per_page

    source_filter = request.args.get("source", "")
    sub_filter = request.args.get("sub", "")
    search = request.args.get("q", "")

    conditions = []
    params = []
    if source_filter:
        conditions.append("source=?")
        params.append(source_filter)
    if sub_filter:
        conditions.append("sub_source=?")
        params.append(sub_filter)
    if search:
        conditions.append("(full_name LIKE ? OR phone LIKE ? OR city LIKE ? OR email LIKE ?)")
        params += [f"%{search}%"] * 4

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    total = db.execute(f"SELECT COUNT(*) FROM leads {where}", params).fetchone()[0]
    leads = db.execute(
        f"SELECT * FROM leads {where} ORDER BY id DESC LIMIT ? OFFSET ?",
        params + [per_page, offset]
    ).fetchall()

    sources = [r[0] for r in db.execute("SELECT DISTINCT source FROM leads ORDER BY source").fetchall()]
    subs = [r[0] for r in db.execute("SELECT DISTINCT sub_source FROM leads ORDER BY sub_source").fetchall()]

    source_opts = "<option value=''>All Sources</option>" + "".join(
        f"<option value='{s}' {'selected' if s == source_filter else ''}>{s}</option>"
        for s in sources
    )
    sub_opts = "<option value=''>All Sub-Sources</option>" + "".join(
        f"<option value='{s}' {'selected' if s == sub_filter else ''}>{s}</option>"
        for s in subs
    )

    rows = "".join(f"""
        <tr>
            <td><a href="/lead/{r['id']}">{r['full_name'] or '—'}</a></td>
            <td>{source_badge(r['source'])}</td>
            <td>{sub_badge(r['sub_source'])}</td>
            <td>{r['city'] or '—'}</td>
            <td>{r['phone'] or '—'}</td>
            <td>{r['email'] or '—'}</td>
            <td>{"⭐" * min(int((r['score'] or 0) / 20), 5) if r['score'] else ""}</td>
            <td style="color:#8b949e;font-size:11px;">{(r['date_added'] or '')[:10]}</td>
            <td>
              <a href="/lead/{r['id']}" class="btn btn-outline btn-sm">View</a>
            </td>
        </tr>
    """ for r in leads)

    total_pages = (total + per_page - 1) // per_page

    def page_link(p):
        args = request.args.copy()
        args["page"] = p
        qs = "&".join(f"{k}={v}" for k, v in args.items())
        if p == page:
            return f'<span class="current">{p}</span>'
        return f'<a href="/leads?{qs}">{p}</a>'

    pages = ""
    if total_pages > 1:
        plinks = []
        if page > 1:
            args = request.args.copy()
            args["page"] = page - 1
            qs = "&".join(f"{k}={v}" for k, v in args.items())
            plinks.append(f'<a href="/leads?{qs}">← Prev</a>')
        for p in range(max(1, page - 3), min(total_pages + 1, page + 4)):
            plinks.append(page_link(p))
        if page < total_pages:
            args = request.args.copy()
            args["page"] = page + 1
            qs = "&".join(f"{k}={v}" for k, v in args.items())
            plinks.append(f'<a href="/leads?{qs}">Next →</a>')
        pages = f'<div class="pagination">{"".join(plinks)}</div>'

    base_url = "/leads?" + "&".join(f"{k}={v}" for k, v in request.args.items() if k != "page")

    html = f"""<!DOCTYPE html><html><head><title>All Leads — NYL Pipeline</title>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <style>{BASE_CSS}</style></head><body>
    {nav("leads")}
    <div class="container">
      <div class="page-header">
        <h1>All Leads</h1>
        <p>{total:,} total · Page {page} of {total_pages}</p>
      </div>

      <div class="card" style="margin-bottom:20px;">
        <div class="card-header">
          <form method="get" style="display:flex;gap:10px;flex-wrap:wrap;width:100%;">
            <div class="form-group">
              <label>Search</label>
              <input name="q" value="{search}" placeholder="Name, phone, city..." style="width:220px;">
            </div>
            <div class="form-group">
              <label>Source</label>
              <select name="source">{source_opts}</select>
            </div>
            <div class="form-group">
              <label>Sub-Source</label>
              <select name="sub">{sub_opts}</select>
            </div>
            <div class="form-group">
              <label>&nbsp;</label>
              <button type="submit" class="btn btn-primary">Filter</button>
            </div>
            <div class="form-group">
              <label>&nbsp;</label>
              <a href="/leads" class="btn btn-outline">Clear</a>
            </div>
          </form>
        </div>
      </div>

      <div class="card">
        <table>
          <tr>
            <th>Name</th><th>Source</th><th>Sub-Source</th><th>City</th>
            <th>Phone</th><th>Email</th><th>Score</th><th>Added</th><th></th>
          </tr>
          {rows or "<tr><td colspan=9 style='color:#8b949e;padding:20px;'>No leads found</td></tr>"}
        </table>
        {pages}
      </div>
    </div></body></html>"""
    return html

@app.route("/lead/<int:lead_id>")
def lead_detail(lead_id):
    db = get_db()
    lead = db.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
    if not lead:
        return "Lead not found", 404

    logs = db.execute(
        "SELECT * FROM call_logs WHERE lead_id=? ORDER BY logged_at DESC", (lead_id,)
    ).fetchall()

    script = get_script(lead["sub_source"])
    first_name = lead["first_name"] or (lead["full_name"] or "").split()[0] if lead["full_name"] else "there"

    def fill_script(text):
        return text.replace("[First Name]", first_name).replace("[City]", lead["city"] or "your area").replace("[their industry]", lead["company"] or "your industry")

    script_opening = fill_script(script["opening"])
    script_appt = fill_script(script["appointment"])
    script_objection = fill_script(script.get("objection", ""))

    discovery_items = "".join(f"<li>{q}</li>" for q in script.get("discovery", []))

    log_rows = "".join(f"""
        <tr>
            <td>{outcome_badge(r['outcome'])}</td>
            <td>{r['notes'] or '—'}</td>
            <td style="color:#8b949e;font-size:11px;">{(r['logged_at'] or '')[:16]}</td>
        </tr>
    """ for r in logs) or "<tr><td colspan=3 style='color:#8b949e;'>No calls logged yet</td></tr>"

    # Score bar
    score = lead["score"] or 0
    score_bar = f"""
        <div class="score-bar">
            <span style="font-size:12px;color:#8b949e;">Score</span>
            <div class="bar"><div class="fill" style="width:{score}%"></div></div>
            <span style="font-size:13px;font-weight:600;color:#f0f6fc;">{score}</span>
        </div>
    """ if score else ""

    # LinkedIn profile link
    linkedin_btn = ""
    if lead["linkedin_url"]:
        linkedin_btn = f'<a href="{lead["linkedin_url"]}" target="_blank" class="btn btn-outline btn-sm">🔗 LinkedIn Profile</a>'

    html = f"""<!DOCTYPE html><html><head><title>{lead['full_name']} — NYL Pipeline</title>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <style>{BASE_CSS}
    .name-header {{ font-size:24px;font-weight:700;color:#f0f6fc;margin-bottom:4px; }}
    </style></head><body>
    {nav("leads")}
    <div class="container">
      <div style="margin-bottom:16px;">
        <a href="/leads" style="color:#8b949e;font-size:13px;">← Back to Leads</a>
      </div>

      <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;margin-bottom:20px;">
        <div>
          <div class="name-header">{lead['full_name'] or '—'}</div>
          <div style="display:flex;gap:8px;margin-top:6px;flex-wrap:wrap;">
            {source_badge(lead['source'])} {sub_badge(lead['sub_source'])}
            {"<span class='badge badge-gray'>#" + str(lead_id) + "</span>"}
          </div>
        </div>
        <div class="btn-group">
          {linkedin_btn}
          <a href="/lead/{lead_id}/dossier" class="btn btn-outline btn-sm">📄 Generate Dossier</a>
          <a href="/lead/{lead_id}/edit" class="btn btn-outline btn-sm">✏️ Edit</a>
        </div>
      </div>

      <div class="detail-grid" style="margin-bottom:20px;">
        <div class="detail-section">
          <h3>Contact Info</h3>
          <div class="detail-row"><span class="detail-label">Phone</span>
            <span class="detail-value">{lead['phone'] or '—'}
              {"<br><small style='color:#8b949e'>" + (lead['phone2'] or '') + "</small>" if lead['phone2'] else ""}
              {"<br><small style='color:#8b949e'>" + (lead['phone3'] or '') + "</small>" if lead['phone3'] else ""}
            </span></div>
          <div class="detail-row"><span class="detail-label">Email</span>
            <span class="detail-value">{lead['email'] or '—'}</span></div>
          <div class="detail-row"><span class="detail-label">Address</span>
            <span class="detail-value">{lead['street'] or '—'}<br>
            {(lead['city'] or '') + ', ' + (lead['state'] or '') + ' ' + (lead['zip'] or '')}
            </span></div>
          {score_bar}
        </div>

        <div class="detail-section">
          <h3>Lead Info</h3>
          <div class="detail-row"><span class="detail-label">Source</span>
            <span class="detail-value">{source_badge(lead['source'])}</span></div>
          <div class="detail-row"><span class="detail-label">Sub-Source</span>
            <span class="detail-value">{sub_badge(lead['sub_source'])}</span></div>
          {"<div class='detail-row'><span class='detail-label'>Title</span><span class='detail-value'>" + (lead['title'] or '') + "</span></div>" if lead['title'] else ""}
          {"<div class='detail-row'><span class='detail-label'>Company</span><span class='detail-value'>" + (lead['company'] or '') + "</span></div>" if lead['company'] else ""}
          <div class="detail-row"><span class="detail-label">Date Added</span>
            <span class="detail-value">{(lead['date_added'] or '')[:10]}</span></div>
          {"<div class='detail-row'><span class='detail-label'>Source File</span><span class='detail-value' style='font-size:11px;color:#8b949e'>" + (lead['source_file'] or '') + "</span></div>" if lead['source_file'] else ""}
          {"<div class='detail-row'><span class='detail-label'>Notes</span><span class='detail-value'>" + (lead['notes'] or '') + "</span></div>" if lead['notes'] else ""}
          {"<div class='detail-row'><span class='detail-label'>Opportunity</span><span class='detail-value' style='color:#fde68a'>" + (lead['call_blurb'] or '') + "</span></div>" if lead['call_blurb'] else ""}
        </div>
      </div>

      <!-- Call Script -->
      <div class="card" style="margin-bottom:20px;">
        <div class="card-header">
          <h2>📞 Call Script — {lead['sub_source']}</h2>
        </div>
        <div style="padding:18px;">
          <div class="script-section">
            <h4>Opening</h4>
            <p>"{script_opening}"</p>
          </div>
          <div class="script-section">
            <h4>Discovery Questions</h4>
            <ul>{discovery_items}</ul>
          </div>
          <div class="script-section">
            <h4>Appointment Ask</h4>
            <p>"{script_appt}"</p>
          </div>
          {"<div class='script-section'><h4>Key Objection Response</h4><p>\"" + script_objection + "\"</p></div>" if script_objection else ""}
        </div>
      </div>

      <!-- Log Outcome -->
      <div class="card" style="margin-bottom:20px;">
        <div class="card-header"><h2>📋 Log Call Outcome</h2></div>
        <div style="padding:18px;">
          <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px;">
            {''.join(f'<button class="outcome-btn" data-outcome="{o}" onclick="logOutcome(\'{o}\')">{o}</button>'
              for o in ["Contacted","VM","No Answer","Callback","Appointment Set","Not Interested"])}
          </div>
          <div id="notes-area" style="display:none;">
            <textarea id="outcome-notes" rows="3" style="width:100%;" placeholder="Optional notes..."></textarea>
            <button class="btn btn-primary btn-sm" style="margin-top:8px;" onclick="submitOutcome()">Save</button>
          </div>
          <div id="log-result"></div>
        </div>
      </div>

      <!-- Call History -->
      <div class="card">
        <div class="card-header"><h2>📅 Call History</h2></div>
        <table>
          <tr><th>Outcome</th><th>Notes</th><th>Logged</th></tr>
          {log_rows}
        </table>
      </div>

    </div>

    <script>
    let selectedOutcome = null;
    function logOutcome(outcome) {{
      selectedOutcome = outcome;
      document.querySelectorAll('.outcome-btn').forEach(b => b.classList.remove('selected'));
      document.querySelector(`[data-outcome="${{outcome}}"]`).classList.add('selected');
      document.getElementById('notes-area').style.display = 'block';
    }}
    function submitOutcome() {{
      if (!selectedOutcome) return;
      const notes = document.getElementById('outcome-notes').value;
      fetch('/lead/{lead_id}/log', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{outcome: selectedOutcome, notes: notes}})
      }}).then(r => r.json()).then(data => {{
        document.getElementById('log-result').innerHTML =
          '<div class="alert alert-success" style="margin-top:12px;">✅ ' + data.message + '</div>';
        setTimeout(() => location.reload(), 1200);
      }});
    }}
    </script>
    </body></html>"""
    return html

@app.route("/lead/<int:lead_id>/log", methods=["POST"])
def log_outcome(lead_id):
    db = get_db()
    data = request.get_json()
    outcome = data.get("outcome", "")
    notes = data.get("notes", "")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.execute(
        "INSERT INTO call_logs (lead_id, outcome, notes, logged_at) VALUES (?,?,?,?)",
        (lead_id, outcome, notes, now)
    )
    db.commit()
    return jsonify({"message": f"Outcome '{outcome}' logged successfully."})

@app.route("/lead/<int:lead_id>/dossier")
def generate_dossier(lead_id):
    db = get_db()
    lead = db.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
    if not lead:
        return "Lead not found", 404
    if not os.path.exists(DOSSIER_SCRIPT):
        return jsonify({"error": "Dossier script not found at " + DOSSIER_SCRIPT}), 404
    name = lead["full_name"] or ""
    try:
        address_parts = [lead["street"] or "", lead["city"] or "", lead["state"] or "NJ", lead["postal_code"] or ""]
        address = ", ".join(p for p in address_parts if p)
        result = subprocess.run(
            [VENV_PYTHON, DOSSIER_SCRIPT, "--name", name, "--address", address],
            capture_output=True, text=True, timeout=120
        )
        return f"""<!DOCTYPE html><html><head><title>Dossier — {name}</title>
        <style>{BASE_CSS}</style></head><body>{nav("leads")}
        <div class="container">
          <div style="margin-bottom:16px;"><a href="/lead/{lead_id}" style="color:#8b949e;">← Back</a></div>
          <div class="card"><div class="card-header"><h2>Dossier: {name}</h2></div>
          <div style="padding:18px;white-space:pre-wrap;font-family:monospace;color:#c9d1d9;">
            {result.stdout or result.stderr or "No output from dossier script."}
          </div></div>
        </div></body></html>"""
    except Exception as e:
        return f"Error running dossier: {e}", 500

@app.route("/lead/<int:lead_id>/edit", methods=["GET", "POST"])
def edit_lead(lead_id):
    db = get_db()
    lead = db.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
    if not lead:
        return "Lead not found", 404

    if request.method == "POST":
        fields = ["first_name","last_name","full_name","phone","phone2","phone3",
                  "email","street","city","state","zip","source","sub_source","notes"]
        updates = {f: request.form.get(f, "") for f in fields}
        db.execute("""UPDATE leads SET first_name=?,last_name=?,full_name=?,
            phone=?,phone2=?,phone3=?,email=?,street=?,city=?,state=?,zip=?,
            source=?,sub_source=?,notes=? WHERE id=?""",
            [updates[f] for f in fields] + [lead_id])
        db.commit()
        return redirect(url_for("lead_detail", lead_id=lead_id))

    sub_sources = list(CALL_SCRIPTS.keys())
    sub_opts = "".join(
        f"<option value='{s}' {'selected' if s == lead['sub_source'] else ''}>{s}</option>"
        for s in sub_sources
    )
    sources = ["Propwire", "LinkedIn", "RetirementProspects"]
    src_opts = "".join(
        f"<option value='{s}' {'selected' if s == lead['source'] else ''}>{s}</option>"
        for s in sources
    )

    def v(key):
        return lead[key] or ""

    html = f"""<!DOCTYPE html><html><head><title>Edit — {lead['full_name']}</title>
    <style>{BASE_CSS}</style></head><body>
    {nav("leads")}
    <div class="container">
      <div style="margin-bottom:16px;"><a href="/lead/{lead_id}" style="color:#8b949e;">← Back</a></div>
      <div class="page-header"><h1>Edit Lead</h1></div>
      <div class="card">
        <div class="card-header"><h2>{lead['full_name']}</h2></div>
        <div style="padding:20px;">
          <form method="post">
            <div class="form-row">
              <div class="form-group"><label>First Name</label><input name="first_name" value="{v('first_name')}"></div>
              <div class="form-group"><label>Last Name</label><input name="last_name" value="{v('last_name')}"></div>
              <div class="form-group" style="flex:1;"><label>Full Name</label><input name="full_name" value="{v('full_name')}" style="width:100%;"></div>
            </div>
            <div class="form-row">
              <div class="form-group"><label>Phone 1</label><input name="phone" value="{v('phone')}"></div>
              <div class="form-group"><label>Phone 2</label><input name="phone2" value="{v('phone2')}"></div>
              <div class="form-group"><label>Phone 3</label><input name="phone3" value="{v('phone3')}"></div>
            </div>
            <div class="form-row">
              <div class="form-group" style="flex:1;"><label>Email</label><input name="email" value="{v('email')}" style="width:100%;"></div>
            </div>
            <div class="form-row">
              <div class="form-group" style="flex:2;"><label>Street</label><input name="street" value="{v('street')}" style="width:100%;"></div>
              <div class="form-group"><label>City</label><input name="city" value="{v('city')}"></div>
              <div class="form-group"><label>State</label><input name="state" value="{v('state')}" style="width:60px;"></div>
              <div class="form-group"><label>Zip</label><input name="zip" value="{v('zip')}" style="width:80px;"></div>
            </div>
            <div class="form-row">
              <div class="form-group"><label>Source</label><select name="source">{src_opts}</select></div>
              <div class="form-group"><label>Sub-Source</label><select name="sub_source">{sub_opts}</select></div>
            </div>
            <div class="form-group" style="margin-bottom:16px;">
              <label>Notes</label>
              <textarea name="notes" rows="3" style="width:100%;">{v('notes')}</textarea>
            </div>
            <div class="btn-group">
              <button type="submit" class="btn btn-primary">Save Changes</button>
              <a href="/lead/{lead_id}" class="btn btn-outline">Cancel</a>
            </div>
          </form>
        </div>
      </div>
    </div></body></html>"""
    return html

@app.route("/export", methods=["GET", "POST"])
def export_page():
    db = get_db()

    sources = [r[0] for r in db.execute("SELECT DISTINCT source FROM leads ORDER BY source")]
    subs = [r[0] for r in db.execute("SELECT DISTINCT sub_source FROM leads ORDER BY sub_source")]

    if request.method == "POST":
        source_f = request.form.get("source", "")
        sub_f = request.form.get("sub", "")
        date_from = request.form.get("date_from", "")
        date_to = request.form.get("date_to", "")

        conditions = []
        params = []
        if source_f:
            conditions.append("source=?")
            params.append(source_f)
        if sub_f:
            conditions.append("sub_source=?")
            params.append(sub_f)
        if date_from:
            conditions.append("date_added >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("date_added <= ?")
            params.append(date_to + " 23:59:59")

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        leads = db.execute(
            f"SELECT * FROM leads {where} ORDER BY id DESC", params
        ).fetchall()

        # NYL Import Template columns
        nyl_cols = [
            "First Name", "Middle Name", "Last Name", "Source", "Sub-Source",
            "Target Segment", "Home Phone", "Mobile Phone", "Work Phone",
            "Personal Email", "Work Email", "Other Email",
            "Date Of Birth", "Gender", "Street", "City", "State", "Postal Code"
        ]

        # Sub-source → Target Segment mapping
        segment_map = {
            "Annuity Owner": "Annuity Review",
            "Annuity Prospect": "Annuity New Business",
            "IRA/401k Rollover": "Rollover",
            "Retiree": "Retirement Income",
            "LinkedIn-JobChange": "Life Event",
            "LinkedIn-FederalEmployee": "Federal Benefits",
            "Propwire": "Mortgage Protection",
            "Default": "General",
        }

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(nyl_cols)
        for lead in leads:
            sub = lead["sub_source"] or ""
            segment = segment_map.get(sub, "General")
            writer.writerow([
                lead["first_name"] or "",
                "",  # Middle Name — not available
                lead["last_name"] or "",
                lead["source"] or "",
                sub,
                segment,
                "",  # Home Phone
                lead["phone"] or "",  # Mobile Phone
                "",  # Work Phone
                lead["email"] or "",  # Personal Email
                "",  # Work Email
                "",  # Other Email
                "",  # Date Of Birth
                "",  # Gender
                lead["street"] or "",
                lead["city"] or "",
                lead["state"] or "",
                lead["zip"] or "",
            ])

        output.seek(0)
        filename = f"nyl-import-{datetime.now().strftime('%Y-%m-%d')}.csv"
        return send_file(
            BytesIO(output.getvalue().encode("utf-8")),
            mimetype="text/csv",
            as_attachment=True,
            download_name=filename
        )

    src_opts = "<option value=''>All Sources</option>" + "".join(
        f"<option value='{s}'>{s}</option>" for s in sources
    )
    sub_opts = "<option value=''>All Sub-Sources</option>" + "".join(
        f"<option value='{s}'>{s}</option>" for s in subs
    )

    total = db.execute("SELECT COUNT(*) FROM leads").fetchone()[0]

    html = f"""<!DOCTYPE html><html><head><title>NYL Export — Pipeline</title>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <style>{BASE_CSS}</style></head><body>
    {nav("export")}
    <div class="container">
      <div class="page-header">
        <h1>📤 NYL CRM Export</h1>
        <p>Export leads formatted for New York Life CRM import template</p>
      </div>

      <div class="card" style="max-width:600px;">
        <div class="card-header"><h2>Export Options</h2></div>
        <div style="padding:20px;">
          <div class="alert alert-info">
            <strong>{total:,} leads</strong> available for export. Filters below are optional — leave blank to export all.
          </div>
          <form method="post">
            <div class="form-row">
              <div class="form-group">
                <label>Source</label>
                <select name="source">{src_opts}</select>
              </div>
              <div class="form-group">
                <label>Sub-Source</label>
                <select name="sub">{sub_opts}</select>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Date Added — From</label>
                <input type="date" name="date_from">
              </div>
              <div class="form-group">
                <label>Date Added — To</label>
                <input type="date" name="date_to">
              </div>
            </div>
            <button type="submit" class="btn btn-success">⬇️ Download NYL CSV</button>
          </form>
        </div>
      </div>

      <div class="card" style="max-width:600px;margin-top:20px;">
        <div class="card-header"><h2>Column Mapping</h2></div>
        <div style="padding:16px;">
          <table>
            <tr><th>NYL Column</th><th>Mapped From</th></tr>
            <tr><td>First Name</td><td>first_name</td></tr>
            <tr><td>Last Name</td><td>last_name</td></tr>
            <tr><td>Source</td><td>source (Propwire / LinkedIn)</td></tr>
            <tr><td>Sub-Source</td><td>sub_source</td></tr>
            <tr><td>Target Segment</td><td>Auto from sub-source</td></tr>
            <tr><td>Mobile Phone</td><td>phone (primary)</td></tr>
            <tr><td>Personal Email</td><td>email</td></tr>
            <tr><td>Street / City / State / Postal Code</td><td>address fields</td></tr>
            <tr><td>Date Of Birth</td><td>Omitted (not available)</td></tr>
          </table>
        </div>
      </div>
    </div></body></html>"""
    return html

@app.route("/upload", methods=["GET", "POST"])
def upload_page():
    message = ""
    if request.method == "POST":
        f = request.files.get("csv_file")
        source = request.form.get("source", "RetirementProspects")
        sub_source = request.form.get("sub_source", "Retiree")
        if not f or not f.filename.endswith(".csv"):
            message = '<div class="alert alert-error">Please upload a valid CSV file.</div>'
        else:
            try:
                content = f.read().decode("utf-8-sig")
                reader = csv.DictReader(StringIO(content))
                headers = reader.fieldnames or []
                db = get_db()
                count = 0

                def find_col(names):
                    for n in names:
                        for h in headers:
                            if n.lower() in h.lower():
                                return h
                    return None

                fn_col = find_col(["first_name","first name","fname"])
                ln_col = find_col(["last_name","last name","lname"])
                name_col = find_col(["name","full name"])
                phone_col = find_col(["phone","mobile","cell"])
                email_col = find_col(["email"])
                addr_col = find_col(["address","street","addr"])
                city_col = find_col(["city"])
                state_col = find_col(["state"])
                zip_col = find_col(["zip","postal"])

                for row in reader:
                    fn = row.get(fn_col, "") if fn_col else ""
                    ln = row.get(ln_col, "") if ln_col else ""
                    full = row.get(name_col, "") if name_col else f"{fn} {ln}".strip()
                    if not fn and not ln and not full:
                        continue
                    if not fn and full:
                        parts = full.split(" ", 1)
                        fn = parts[0]
                        ln = parts[1] if len(parts) > 1 else ""
                    phone = row.get(phone_col, "") if phone_col else ""
                    email = row.get(email_col, "") if email_col else ""
                    addr = row.get(addr_col, "") if addr_col else ""
                    city = row.get(city_col, "") if city_col else ""
                    state = row.get(state_col, "NJ") if state_col else "NJ"
                    zip_ = row.get(zip_col, "") if zip_col else ""
                    dedup = f"upload:{source}:{full}:{phone}:{email}"
                    try:
                        db.execute("""INSERT OR IGNORE INTO leads
                            (first_name, last_name, full_name, phone, email,
                             street, city, state, zip, source, sub_source, source_file, dedup_key)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (fn.strip().title(), ln.strip().title(), full.strip().title(),
                             phone.strip(), email.strip(),
                             addr.strip().title(), city.strip().title(), state.strip(), zip_.strip(),
                             source, sub_source, f.filename, dedup))
                        count += 1
                    except Exception:
                        pass
                db.commit()
                message = f'<div class="alert alert-success">✅ Imported {count} leads from <strong>{f.filename}</strong> as {source} / {sub_source}.</div>'
            except Exception as e:
                message = f'<div class="alert alert-error">Error: {e}</div>'

    sub_sources = list(CALL_SCRIPTS.keys())
    sub_opts = "".join(f"<option value='{s}'>{s}</option>" for s in sub_sources)

    html = f"""<!DOCTYPE html><html><head><title>Upload Leads — NYL Pipeline</title>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <style>{BASE_CSS}</style></head><body>
    {nav("upload")}
    <div class="container">
      <div class="page-header">
        <h1>⬆️ Upload CSV</h1>
        <p>Upload retirement prospects or any additional lead source</p>
      </div>
      {message}
      <div class="card" style="max-width:600px;">
        <div class="card-header"><h2>Upload Lead CSV</h2></div>
        <div style="padding:20px;">
          <form method="post" enctype="multipart/form-data">
            <div class="form-group" style="margin-bottom:16px;">
              <label>CSV File</label>
              <div class="upload-zone" onclick="document.getElementById('csv-input').click()">
                <div style="font-size:32px;">📂</div>
                <div style="color:#f0f6fc;margin-top:8px;">Click to select CSV file</div>
                <p>Supports any CSV with name/phone/email/address columns</p>
                <input type="file" id="csv-input" name="csv_file" accept=".csv" style="display:none;" onchange="this.closest('.upload-zone').querySelector('p').textContent=this.files[0].name">
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Source</label>
                <select name="source">
                  <option value="RetirementProspects">RetirementProspects</option>
                  <option value="Propwire">Propwire</option>
                  <option value="LinkedIn">LinkedIn</option>
                  <option value="Other">Other</option>
                </select>
              </div>
              <div class="form-group">
                <label>Sub-Source</label>
                <select name="sub_source">{sub_opts}</select>
              </div>
            </div>
            <button type="submit" class="btn btn-primary">Upload & Import</button>
          </form>
        </div>
      </div>

      <div class="card" style="max-width:600px;margin-top:20px;">
        <div class="card-header"><h2>Supported Column Names</h2></div>
        <div style="padding:16px;color:#8b949e;font-size:13px;">
          <p>The importer auto-detects columns. Supported names:</p>
          <ul style="margin-top:10px;list-style:disc;padding-left:20px;line-height:2;">
            <li><strong>Name:</strong> Name, First Name, Last Name, Full Name</li>
            <li><strong>Phone:</strong> Phone, Mobile, Cell</li>
            <li><strong>Email:</strong> Email</li>
            <li><strong>Address:</strong> Address, Street, Addr</li>
            <li><strong>City/State/Zip:</strong> City, State, Zip, Postal</li>
          </ul>
        </div>
      </div>
    </div></body></html>"""
    return html

@app.route("/import")
def trigger_import():
    try:
        result = import_all_leads()
        total = sum(v for k, v in result.items() if k != "skipped")
        flash(f"Re-sync complete. Processed ~{total} lead records.", "success")
    except Exception as e:
        flash(f"Import error: {e}", "error")
    return redirect("/")

@app.route("/api/stats")
def api_stats():
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    by_source = dict(db.execute("SELECT source, COUNT(*) FROM leads GROUP BY source").fetchall())
    by_sub = dict(db.execute("SELECT sub_source, COUNT(*) FROM leads GROUP BY sub_source").fetchall())
    outcomes = dict(db.execute("SELECT outcome, COUNT(*) FROM call_logs GROUP BY outcome").fetchall())
    return jsonify({"total": total, "by_source": by_source, "by_sub_source": by_sub, "outcomes": outcomes})

# ── Startup ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🚀 NYL Lead Pipeline Dashboard starting...")
    print("📦 Initializing database and importing leads...")
    import_all_leads()
    print(f"🌐 Listening on http://0.0.0.0:8094")
    app.run(host="0.0.0.0", port=8094, debug=False)
