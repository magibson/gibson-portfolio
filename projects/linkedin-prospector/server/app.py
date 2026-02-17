"""
Jarvis Prospector — Server API
Flask API for storing and managing LinkedIn Sales Navigator leads.
Runs on port 8089.
"""

import os
import json
import sqlite3
import requests
from datetime import datetime, date
from flask import Flask, request, jsonify, render_template, g
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow extension cross-origin requests

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prospector.db')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'AIzaSyCcuSJULuk7MFemZtUrzS0x0WtEJGR2IGM')
GEMINI_URL = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}'

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA journal_mode=WAL')
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop('db', None)
    if db:
        db.close()

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript('''
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            linkedin_url TEXT UNIQUE,
            name TEXT,
            title TEXT,
            company TEXT,
            location TEXT,
            connection_degree TEXT,
            time_in_role TEXT,
            profile_image_url TEXT,
            search_name TEXT,
            score INTEGER DEFAULT 0,
            score_reason TEXT DEFAULT '',
            message_draft TEXT DEFAULT '',
            message_draft_2 TEXT DEFAULT '',
            status TEXT DEFAULT 'new',
            notes TEXT DEFAULT '',
            scraped_at TEXT,
            contacted_at TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            filters_json TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
        CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(score);
        CREATE INDEX IF NOT EXISTS idx_leads_search ON leads(search_name);
    ''')
    db.close()

init_db()

def row_to_dict(row):
    return dict(row) if row else None

# ---------------------------------------------------------------------------
# AI Message Drafting via Gemini
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are writing a LinkedIn message for Matt Gibson, a financial advisor at "
    "New York Life in Monmouth County, NJ. Be casual, genuine, not salesy. "
    "Goal is to start a conversation, not pitch. No emojis. No hashtags. "
    "Keep it natural — like a real person reaching out, not a template."
)

# Search-specific instructions for message tailoring
SEARCH_CONTEXT = {
    'local job changes': (
        "This prospect recently changed jobs. Congratulate them on the new role. "
        "Mention that career transitions are a great time to review financial plans "
        "(benefits, retirement rollover, etc.) but do NOT pitch — just open the door. "
        "Keep it warm and congratulatory first."
    ),
    'job change': (
        "This prospect recently changed jobs. Congratulate them on the new role. "
        "Mention that career transitions are a great time to review financial plans "
        "but do NOT pitch — just open the door."
    ),
    'federal employee': (
        "This prospect works for a federal agency. With current government uncertainty, "
        "many federal employees are reviewing their benefits. Reference FEGLI, TSP, or "
        "FERS naturally. Be empathetic, not fear-mongering."
    ),
    'young families': (
        "This prospect likely has a growing family. Reference the juggle of financial "
        "priorities — protecting the family, saving for college, building wealth. "
        "Be relatable and genuine."
    ),
    'high earner': (
        "This prospect is a senior professional. Reference the complexity of financial "
        "planning at their level — tax optimization, estate planning, retirement timeline. "
        "Be peer-level, not salesy."
    ),
    'default': (
        "Reference something specific about the prospect — their role, company, or location. "
        "Find common ground. Keep it conversational."
    )
}

def get_search_context(search_name):
    """Match a search name to the appropriate messaging context."""
    if not search_name:
        return SEARCH_CONTEXT['default']
    name_lower = search_name.lower()
    for key, context in SEARCH_CONTEXT.items():
        if key in name_lower:
            return context
    return SEARCH_CONTEXT['default']

def generate_drafts(lead):
    """Generate connection request + follow-up DM for a lead using Gemini."""
    lead_info = (
        f"Name: {lead['name']}\n"
        f"Title: {lead['title']}\n"
        f"Company: {lead['company']}\n"
        f"Location: {lead['location']}\n"
        f"Time in role: {lead['time_in_role']}\n"
        f"Found via search: {lead['search_name']}\n"
        f"Connection: {lead['connection_degree']}"
    )

    search_context = get_search_context(lead['search_name'])
    
    drafts = {}
    for draft_type, max_chars in [('connection_request', 300), ('follow_up_dm', 500)]:
        if draft_type == 'connection_request':
            label = "LinkedIn connection request message (MUST be under 300 characters — this is a hard limit)"
        else:
            label = "follow-up DM to send after they accept the connection (under 500 characters)"
        prompt = f"Context about this search: {search_context}\n\nWrite a {label} for this prospect:\n\n{lead_info}"

        try:
            resp = requests.post(GEMINI_URL, json={
                'contents': [{'parts': [{'text': prompt}]}],
                'systemInstruction': {'parts': [{'text': SYSTEM_PROMPT}]},
                'generationConfig': {'maxOutputTokens': 256, 'temperature': 0.8}
            }, timeout=15)
            data = resp.json()
            text = data['candidates'][0]['content']['parts'][0]['text'].strip()
            # Trim to max chars
            if len(text) > max_chars:
                text = text[:max_chars].rsplit(' ', 1)[0]
            drafts[draft_type] = text
        except Exception as e:
            drafts[draft_type] = f'[Draft generation failed: {e}]'

    return drafts

def score_lead(lead):
    """Use Gemini to score a lead 1-100 for Matt's prospecting."""
    lead_info = (
        f"Name: {lead['name']}, Title: {lead['title']}, Company: {lead['company']}, "
        f"Location: {lead['location']}, Connection: {lead['connection_degree']}, "
        f"Time in role: {lead['time_in_role']}"
    )
    prompt = (
        f"Score this prospect 1-100 for a financial advisor in Monmouth County NJ. "
        f"Higher = better fit. Consider: proximity to NJ, seniority/income potential, "
        f"life stage indicators, connection degree. Reply with ONLY a JSON object: "
        f'{{\"score\": <number>, \"reason\": \"<one sentence>\"}}\n\n{lead_info}'
    )
    try:
        resp = requests.post(GEMINI_URL, json={
            'contents': [{'parts': [{'text': prompt}]}],
            'generationConfig': {'maxOutputTokens': 100, 'temperature': 0.3}
        }, timeout=10)
        data = resp.json()
        text = data['candidates'][0]['content']['parts'][0]['text'].strip()
        # Parse JSON from response
        text = text.replace('```json', '').replace('```', '').strip()
        result = json.loads(text)
        return int(result.get('score', 50)), result.get('reason', '')
    except:
        return 50, 'Auto-scored (default)'

# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/dashboard')
def api_dashboard():
    db = get_db()
    today = date.today().isoformat()
    total = db.execute('SELECT COUNT(*) FROM leads').fetchone()[0]
    new_today = db.execute('SELECT COUNT(*) FROM leads WHERE date(created_at) = ?', (today,)).fetchone()[0]
    contacted = db.execute("SELECT COUNT(*) FROM leads WHERE status IN ('contacted','replied','meeting_set')").fetchone()[0]
    meetings = db.execute("SELECT COUNT(*) FROM leads WHERE status = 'meeting_set'").fetchone()[0]
    replied = db.execute("SELECT COUNT(*) FROM leads WHERE status = 'replied'").fetchone()[0]
    response_rate = round((replied / contacted * 100), 1) if contacted > 0 else 0
    return jsonify({
        'total': total, 'new_today': new_today, 'contacted': contacted,
        'meetings': meetings, 'replied': replied, 'response_rate': response_rate
    })

@app.route('/api/leads', methods=['POST'])
def receive_leads():
    """Receive scraped leads from the Chrome extension."""
    data = request.json
    leads = data.get('leads', [])
    search_name = data.get('search_name', '')
    db = get_db()
    new_count = 0
    dupe_count = 0

    for lead in leads:
        url = lead.get('linkedin_url', '').strip()
        if not url:
            continue
        try:
            db.execute('''
                INSERT INTO leads (linkedin_url, name, title, company, location,
                    connection_degree, time_in_role, profile_image_url, search_name, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                url, lead.get('name', ''), lead.get('title', ''),
                lead.get('company', ''), lead.get('location', ''),
                lead.get('connection_degree', ''), lead.get('time_in_role', ''),
                lead.get('profile_image_url', ''),
                lead.get('search_name', search_name),
                lead.get('scraped_at', datetime.utcnow().isoformat())
            ))
            new_count += 1
        except sqlite3.IntegrityError:
            dupe_count += 1

    db.commit()
    return jsonify({'status': 'ok', 'new': new_count, 'duplicates': dupe_count, 'total_received': len(leads)})

@app.route('/api/leads', methods=['GET'])
def list_leads():
    db = get_db()
    query = 'SELECT * FROM leads WHERE 1=1'
    params = []

    status = request.args.get('status')
    if status:
        query += ' AND status = ?'
        params.append(status)

    search = request.args.get('search_name')
    if search:
        query += ' AND search_name = ?'
        params.append(search)

    min_score = request.args.get('min_score')
    if min_score:
        query += ' AND score >= ?'
        params.append(int(min_score))

    max_score = request.args.get('max_score')
    if max_score:
        query += ' AND score <= ?'
        params.append(int(max_score))

    date_from = request.args.get('date_from')
    if date_from:
        query += ' AND date(created_at) >= ?'
        params.append(date_from)

    date_to = request.args.get('date_to')
    if date_to:
        query += ' AND date(created_at) <= ?'
        params.append(date_to)

    sort = request.args.get('sort', 'created_at')
    order = request.args.get('order', 'desc')
    allowed_sorts = {'score', 'created_at', 'name', 'status', 'company'}
    if sort in allowed_sorts:
        query += f' ORDER BY {sort} {"ASC" if order == "asc" else "DESC"}'

    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))
    query += ' LIMIT ? OFFSET ?'
    params.extend([limit, offset])

    rows = db.execute(query, params).fetchall()
    total = db.execute('SELECT COUNT(*) FROM leads').fetchone()[0]
    return jsonify({'leads': [row_to_dict(r) for r in rows], 'total': total})

@app.route('/api/leads/<int:lead_id>', methods=['GET'])
def get_lead(lead_id):
    db = get_db()
    row = db.execute('SELECT * FROM leads WHERE id = ?', (lead_id,)).fetchone()
    if not row:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(row_to_dict(row))

@app.route('/api/leads/<int:lead_id>', methods=['PUT'])
def update_lead(lead_id):
    db = get_db()
    data = request.json
    allowed = {'status', 'notes', 'contacted_at', 'score', 'score_reason',
               'message_draft', 'message_draft_2', 'search_name'}
    sets = []
    params = []
    for key, val in data.items():
        if key in allowed:
            sets.append(f'{key} = ?')
            params.append(val)
    if not sets:
        return jsonify({'error': 'No valid fields'}), 400

    sets.append("updated_at = datetime('now')")
    params.append(lead_id)
    db.execute(f"UPDATE leads SET {', '.join(sets)} WHERE id = ?", params)
    db.commit()
    return jsonify({'status': 'ok'})

@app.route('/api/leads/<int:lead_id>/draft', methods=['POST'])
def draft_lead(lead_id):
    db = get_db()
    row = db.execute('SELECT * FROM leads WHERE id = ?', (lead_id,)).fetchone()
    if not row:
        return jsonify({'error': 'Not found'}), 404

    lead = row_to_dict(row)
    drafts = generate_drafts(lead)
    score, reason = score_lead(lead)

    db.execute('''UPDATE leads SET message_draft = ?, message_draft_2 = ?,
        score = ?, score_reason = ?, updated_at = datetime('now') WHERE id = ?''',
        (drafts['connection_request'], drafts['follow_up_dm'], score, reason, lead_id))
    db.commit()

    return jsonify({
        'connection_request': drafts['connection_request'],
        'follow_up_dm': drafts['follow_up_dm'],
        'score': score, 'score_reason': reason
    })

@app.route('/api/generate-drafts', methods=['POST'])
def batch_generate_drafts():
    db = get_db()
    rows = db.execute("SELECT * FROM leads WHERE message_draft = '' OR message_draft IS NULL").fetchall()
    generated = 0
    for row in rows:
        lead = row_to_dict(row)
        try:
            drafts = generate_drafts(lead)
            score, reason = score_lead(lead)
            db.execute('''UPDATE leads SET message_draft = ?, message_draft_2 = ?,
                score = ?, score_reason = ?, updated_at = datetime('now') WHERE id = ?''',
                (drafts['connection_request'], drafts['follow_up_dm'], score, reason, lead['id']))
            generated += 1
        except Exception as e:
            print(f"Error drafting for {lead['name']}: {e}")
    db.commit()
    return jsonify({'status': 'ok', 'generated': generated, 'total_undrafted': len(rows)})

@app.route('/api/searches', methods=['GET'])
def list_searches():
    db = get_db()
    rows = db.execute('SELECT * FROM searches ORDER BY created_at DESC').fetchall()
    return jsonify({'searches': [row_to_dict(r) for r in rows]})

@app.route('/api/searches', methods=['POST'])
def create_search():
    data = request.json
    db = get_db()
    db.execute('INSERT INTO searches (name, description, filters_json) VALUES (?, ?, ?)',
        (data.get('name', ''), data.get('description', ''), json.dumps(data.get('filters', {}))))
    db.commit()
    return jsonify({'status': 'ok'})

# Bulk update
@app.route('/api/leads/bulk', methods=['PUT'])
def bulk_update():
    data = request.json
    ids = data.get('ids', [])
    updates = data.get('updates', {})
    if not ids or not updates:
        return jsonify({'error': 'Need ids and updates'}), 400

    db = get_db()
    allowed = {'status', 'contacted_at', 'notes'}
    sets = []
    params = []
    for key, val in updates.items():
        if key in allowed:
            sets.append(f'{key} = ?')
            params.append(val)
    if not sets:
        return jsonify({'error': 'No valid fields'}), 400

    sets.append("updated_at = datetime('now')")
    placeholders = ','.join('?' * len(ids))
    params.extend(ids)
    db.execute(f"UPDATE leads SET {', '.join(sets)} WHERE id IN ({placeholders})", params)
    db.commit()
    return jsonify({'status': 'ok', 'updated': len(ids)})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8089, debug=False)
