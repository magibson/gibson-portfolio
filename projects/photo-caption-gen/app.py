#!/usr/bin/env python3
"""
Photo Caption & Hashtag Generator
AI-powered Instagram captions for @mattgibsonpics
Port: 8100
"""

import os
import json
import sqlite3
import requests
from datetime import datetime
from flask import Flask, request, jsonify, g

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), 'captions.db')
GEMINI_API_KEY = 'AIzaSyCcuSJULuk7MFemZtUrzS0x0WtEJGR2IGM'
GEMINI_URL = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}'

CONTENT_CALENDAR_DB = os.path.expanduser('~/clawd/projects/content-calendar/content.db')

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop('db', None)
    if db:
        db.close()

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description TEXT,
            location TEXT,
            mood TEXT,
            photo_type TEXT,
            response_json TEXT
        )
    ''')
    db.commit()
    db.close()

# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------

def call_gemini(description, location, mood, photo_type, include_location, include_cta):
    loc_str = location if location else "not specified"
    cta_instruction = "Add a natural CTA (e.g. 'Save this one 🔖', 'Drop a 🔥 below', 'Follow for more') at the end of Storytelling and Question styles." if include_cta else "No call-to-action."
    loc_instruction = f"Location: {loc_str}. Weave it in naturally." if include_location and location else ("No specific location to include." if not include_location else f"Location context: {loc_str} (optional to use).")

    prompt = f"""Generate 5 Instagram captions for this photo:
- Description: {description}
- {loc_instruction}
- Mood/Vibe: {mood}
- Photo Type: {photo_type}
- {cta_instruction}

Return EXACTLY this JSON format (no markdown, no extra text, no code blocks):
{{
  "captions": [
    {{"style": "Storytelling", "text": "caption here"}},
    {{"style": "Minimal", "text": "caption here"}},
    {{"style": "Question", "text": "caption here"}},
    {{"style": "Factual", "text": "caption here"}},
    {{"style": "Poetic", "text": "caption here"}}
  ],
  "hashtags": {{
    "niche": ["#tag1","#tag2","#tag3","#tag4","#tag5","#tag6","#tag7","#tag8","#tag9","#tag10"],
    "mid": ["#tag1","#tag2","#tag3","#tag4","#tag5","#tag6","#tag7","#tag8","#tag9","#tag10"],
    "large": ["#tag1","#tag2","#tag3","#tag4","#tag5","#tag6","#tag7","#tag8","#tag9","#tag10"]
  }}
}}

Style rules:
- Storytelling: 3-5 sentences, personal and narrative, sounds like a real person sharing their experience
- Minimal: 1-10 words max, punchy and impactful, often just the feeling
- Question: Engaging question at the end to drive comments, conversational
- Factual: Interesting fact about the location, subject, or technique — teaches something
- Poetic: Lyrical, metaphorical, 2-3 lines that paint a picture with words

Hashtag tiers:
- niche (1K-50K posts): very specific to exact location, style, or subject
- mid (50K-500K posts): photography genre specific
- large (500K+ posts): broad photography community tags

Make captions sound authentic — like a photographer sharing their work, not a brand posting content."""

    system = "You are a social media expert for @mattgibsonpics, a landscape and aerial drone photographer based in New Jersey. Write captions that feel authentic, human, and engaging — never corporate or generic. Return only valid JSON."

    payload = {
        'systemInstruction': {'parts': [{'text': system}]},
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {
            'temperature': 0.85,
            'maxOutputTokens': 1200,
            'responseMimeType': 'application/json'
        }
    }

    resp = requests.post(GEMINI_URL, json=payload, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    raw = data['candidates'][0]['content']['parts'][0]['text'].strip()

    # Clean up any markdown code blocks if present
    if raw.startswith('```'):
        raw = raw.split('```')[1]
        if raw.startswith('json'):
            raw = raw[4:]
    raw = raw.strip()

    result = json.loads(raw)

    # Build combined hashtag string
    all_tags = (result['hashtags']['niche'] +
                result['hashtags']['mid'] +
                result['hashtags']['large'])
    result['hashtag_string'] = ' '.join(all_tags)

    return result

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    return HTML_PAGE

@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json()
    description = (data.get('description') or '').strip()
    if not description:
        return jsonify({'error': 'Photo description is required'}), 400

    location = (data.get('location') or '').strip()
    mood = data.get('mood', 'Peaceful')
    photo_type = data.get('photo_type', 'Landscape')
    include_location = data.get('include_location', True)
    include_cta = data.get('include_cta', True)

    try:
        result = call_gemini(description, location, mood, photo_type, include_location, include_cta)
    except Exception as e:
        return jsonify({'error': f'Generation failed: {str(e)}'}), 500

    # Save to history
    db = get_db()
    db.execute(
        'INSERT INTO history (description, location, mood, photo_type, response_json) VALUES (?, ?, ?, ?, ?)',
        (description, location, mood, photo_type, json.dumps(result))
    )
    db.commit()

    return jsonify(result)

@app.route('/history')
def history():
    db = get_db()
    rows = db.execute(
        'SELECT id, created_at, description, location, mood, photo_type, response_json FROM history ORDER BY created_at DESC LIMIT 20'
    ).fetchall()
    items = []
    for row in rows:
        r = dict(row)
        try:
            r['result'] = json.loads(r['response_json'])
        except Exception:
            r['result'] = None
        del r['response_json']
        items.append(r)
    return jsonify(items)

@app.route('/save-to-calendar', methods=['POST'])
def save_to_calendar():
    data = request.get_json()
    caption = data.get('caption', '')
    hashtags = data.get('hashtags', '')
    date = data.get('date', datetime.now().strftime('%Y-%m-%d'))
    photo_type = data.get('photo_type', 'Landscape')

    try:
        cal_db = sqlite3.connect(CONTENT_CALENDAR_DB)
        # Check what columns exist
        cols = [r[1] for r in cal_db.execute("PRAGMA table_info(posts)").fetchall()]
        full_caption = f"{caption}\n.\n.\n.\n{hashtags}" if hashtags else caption
        if 'caption' in cols:
            cal_db.execute(
                "INSERT INTO posts (date, caption, type, status) VALUES (?, ?, ?, ?)",
                (date, full_caption, photo_type, 'draft')
            )
            cal_db.commit()
            cal_db.close()
            return jsonify({'success': True, 'message': f'Saved to content calendar for {date}'})
        else:
            cal_db.close()
            return jsonify({'success': False, 'message': 'Calendar DB schema mismatch — saved locally only'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Calendar save skipped: {str(e)}'})

# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

HTML_PAGE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Caption Generator · @mattgibsonpics</title>
<style>
  :root {
    --bg: #0f1117;
    --surface: #1a1d27;
    --border: #2a2d3a;
    --text: #e2e8f0;
    --muted: #94a3b8;
    --blue: #3b82f6;
    --blue-dark: #2563eb;
    --green: #10b981;
    --purple: #8b5cf6;
    --yellow: #f59e0b;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; min-height: 100vh; }

  .header { padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 12px; }
  .header h1 { font-size: 18px; font-weight: 700; }
  .header .handle { font-size: 13px; color: var(--blue); font-weight: 500; }
  .camera-icon { font-size: 24px; }

  .tabs { display: flex; border-bottom: 1px solid var(--border); }
  .tab { flex: 1; padding: 12px; text-align: center; font-size: 14px; font-weight: 500; cursor: pointer; color: var(--muted); border-bottom: 2px solid transparent; transition: all 0.2s; }
  .tab.active { color: var(--blue); border-bottom-color: var(--blue); }

  .page { display: none; padding: 16px 20px; max-width: 600px; margin: 0 auto; }
  .page.active { display: block; }

  .form-group { margin-bottom: 14px; }
  label { display: block; font-size: 12px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }
  textarea, input, select {
    width: 100%; background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
    color: var(--text); font-size: 15px; padding: 10px 12px; outline: none; transition: border-color 0.2s;
    -webkit-appearance: none;
  }
  textarea { resize: vertical; min-height: 80px; }
  textarea:focus, input:focus, select:focus { border-color: var(--blue); }
  textarea::placeholder, input::placeholder { color: var(--muted); }

  .row-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

  .checkrow { display: flex; gap: 20px; margin-top: 4px; }
  .check-item { display: flex; align-items: center; gap: 8px; cursor: pointer; }
  .check-item input[type=checkbox] { width: 16px; height: 16px; accent-color: var(--blue); }
  .check-item span { font-size: 14px; color: var(--text); }

  .btn { width: 100%; padding: 13px; border-radius: 10px; font-size: 16px; font-weight: 600; cursor: pointer; border: none; transition: all 0.2s; margin-top: 6px; }
  .btn-primary { background: var(--blue); color: white; }
  .btn-primary:hover { background: var(--blue-dark); }
  .btn-primary:disabled { background: var(--border); color: var(--muted); cursor: not-allowed; }

  .loading { display: none; text-align: center; padding: 30px; color: var(--muted); }
  .spinner { display: inline-block; width: 28px; height: 28px; border: 3px solid var(--border); border-top-color: var(--blue); border-radius: 50%; animation: spin 0.8s linear infinite; margin-bottom: 10px; }
  @keyframes spin { to { transform: rotate(360deg); } }

  .error-card { background: #2d1515; border: 1px solid #ef444444; border-radius: 10px; padding: 14px; color: #fca5a5; font-size: 14px; margin-top: 16px; }

  .results { margin-top: 20px; }
  .results-title { font-size: 13px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px; }

  .caption-card {
    background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
    padding: 14px; margin-bottom: 10px;
  }
  .caption-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
  .style-badge {
    font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em;
    padding: 3px 8px; border-radius: 20px;
  }
  .badge-storytelling { background: #1e3a5f; color: #93c5fd; }
  .badge-minimal { background: #1a2e1a; color: #86efac; }
  .badge-question { background: #2d1f3d; color: #c4b5fd; }
  .badge-factual { background: #2d2000; color: #fcd34d; }
  .badge-poetic { background: #2d1a1a; color: #fca5a5; }

  .caption-text { font-size: 15px; line-height: 1.6; color: var(--text); }
  .caption-actions { display: flex; gap: 8px; margin-top: 10px; }
  .btn-sm {
    padding: 7px 12px; border-radius: 7px; font-size: 13px; font-weight: 500;
    cursor: pointer; border: 1px solid var(--border); background: var(--bg); color: var(--text);
    transition: all 0.15s; white-space: nowrap;
  }
  .btn-sm:hover { border-color: var(--blue); color: var(--blue); }
  .btn-sm.copied { border-color: var(--green); color: var(--green); }
  .btn-sm.cal { border-color: var(--purple); color: var(--purple); }
  .btn-sm.cal:hover { background: #1a0f2e; }

  .hashtag-section { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 14px; margin-top: 10px; }
  .hashtag-title { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 10px; color: var(--muted); }
  .hashtag-tier { margin-bottom: 12px; }
  .tier-label { font-size: 11px; font-weight: 600; margin-bottom: 6px; }
  .tier-niche .tier-label { color: var(--purple); }
  .tier-mid .tier-label { color: var(--blue); }
  .tier-large .tier-label { color: var(--muted); }
  .tag-cloud { display: flex; flex-wrap: wrap; gap: 6px; }
  .tag { font-size: 12px; padding: 3px 8px; border-radius: 20px; cursor: pointer; transition: opacity 0.15s; }
  .tag:hover { opacity: 0.8; }
  .tier-niche .tag { background: #1e1a2e; color: #c4b5fd; }
  .tier-mid .tag { background: #1a2233; color: #93c5fd; }
  .tier-large .tag { background: #1e1e1e; color: #94a3b8; }
  .hashtag-copy-row { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }

  /* Calendar Modal */
  .modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 100; align-items: center; justify-content: center; padding: 20px; }
  .modal-overlay.open { display: flex; }
  .modal { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 20px; width: 100%; max-width: 360px; }
  .modal h3 { font-size: 16px; font-weight: 700; margin-bottom: 14px; }
  .modal-actions { display: flex; gap: 10px; margin-top: 16px; }
  .btn-cancel { flex: 1; padding: 10px; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; border: 1px solid var(--border); background: transparent; color: var(--muted); }
  .btn-save { flex: 2; padding: 10px; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; border: none; background: var(--purple); color: white; }
  .success-toast { display: none; position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); background: var(--green); color: white; padding: 10px 20px; border-radius: 8px; font-size: 14px; font-weight: 600; z-index: 200; }

  /* History */
  .history-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 14px; margin-bottom: 10px; }
  .history-meta { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
  .history-date { font-size: 12px; color: var(--muted); }
  .history-type { font-size: 11px; color: var(--blue); background: #1a2233; padding: 2px 8px; border-radius: 20px; }
  .history-desc { font-size: 14px; color: var(--text); margin-bottom: 10px; line-height: 1.4; }
  .history-caption { font-size: 13px; color: var(--muted); font-style: italic; margin-bottom: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .history-expand { font-size: 12px; color: var(--blue); cursor: pointer; }
  .history-full { display: none; margin-top: 10px; }
  .history-full.open { display: block; }
  .empty-state { text-align: center; padding: 40px 20px; color: var(--muted); }
  .empty-icon { font-size: 40px; margin-bottom: 12px; }
</style>
</head>
<body>

<div class="header">
  <span class="camera-icon">📸</span>
  <div>
    <h1>Caption Generator</h1>
    <div class="handle">@mattgibsonpics</div>
  </div>
</div>

<div class="tabs">
  <div class="tab active" onclick="switchTab('generator')">✨ Generator</div>
  <div class="tab" onclick="switchTab('history')">🕐 History</div>
</div>

<!-- Generator Page -->
<div class="page active" id="page-generator">
  <div style="height:12px"></div>

  <div class="form-group">
    <label>Describe Your Photo *</label>
    <textarea id="description" placeholder="e.g. Golden hour drone shot over Barnegat Lighthouse, NJ. Warm orange and pink sky, lighthouse silhouette, calm ocean below..." rows="4"></textarea>
  </div>

  <div class="row-2">
    <div class="form-group">
      <label>Location</label>
      <input type="text" id="location" placeholder="e.g. Barnegat Light, NJ">
    </div>
    <div class="form-group">
      <label>Photo Type</label>
      <select id="photo_type">
        <option>Landscape</option>
        <option>Drone / Aerial</option>
        <option>Cityscape</option>
        <option>Seascape</option>
        <option>Architecture</option>
        <option>Travel</option>
        <option>Portrait</option>
        <option>Wildlife</option>
        <option>Abstract</option>
        <option>Long Exposure</option>
      </select>
    </div>
  </div>

  <div class="form-group">
    <label>Mood / Vibe</label>
    <select id="mood">
      <option>Peaceful</option>
      <option>Epic</option>
      <option>Nostalgic</option>
      <option>Adventurous</option>
      <option>Minimal</option>
      <option>Moody</option>
      <option>Dramatic</option>
      <option>Serene</option>
    </select>
  </div>

  <div class="form-group">
    <label>Options</label>
    <div class="checkrow">
      <label class="check-item">
        <input type="checkbox" id="include_location" checked>
        <span>📍 Include location</span>
      </label>
      <label class="check-item">
        <input type="checkbox" id="include_cta" checked>
        <span>📢 Add CTA</span>
      </label>
    </div>
  </div>

  <button class="btn btn-primary" id="generate-btn" onclick="generate()">
    ✨ Generate Captions
  </button>

  <div class="loading" id="loading">
    <div class="spinner"></div>
    <div>Crafting your captions...</div>
  </div>

  <div id="error-area"></div>
  <div class="results" id="results" style="display:none"></div>
</div>

<!-- History Page -->
<div class="page" id="page-history">
  <div style="height:12px"></div>
  <div id="history-list"><div class="empty-state"><div class="empty-icon">📷</div><div>No history yet — generate some captions!</div></div></div>
</div>

<!-- Calendar Modal -->
<div class="modal-overlay" id="cal-modal">
  <div class="modal">
    <h3>📅 Save to Content Calendar</h3>
    <div class="form-group">
      <label>Post Date</label>
      <input type="date" id="cal-date">
    </div>
    <div class="modal-actions">
      <button class="btn-cancel" onclick="closeModal()">Cancel</button>
      <button class="btn-save" onclick="confirmSave()">Save to Calendar</button>
    </div>
  </div>
</div>

<div class="success-toast" id="toast"></div>

<script>
let currentResult = null;
let pendingSave = null;

function switchTab(tab) {
  document.querySelectorAll('.tab').forEach((t,i) => t.classList.toggle('active', (i===0 && tab==='generator') || (i===1 && tab==='history')));
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + tab).classList.add('active');
  if (tab === 'history') loadHistory();
}

function showToast(msg, color='#10b981') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.style.background = color;
  t.style.display = 'block';
  setTimeout(() => t.style.display = 'none', 2500);
}

async function copyText(text, btn) {
  try {
    await navigator.clipboard.writeText(text);
    const orig = btn.textContent;
    btn.textContent = '✓ Copied!';
    btn.classList.add('copied');
    setTimeout(() => { btn.textContent = orig; btn.classList.remove('copied'); }, 1800);
  } catch (e) {
    // fallback
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    showToast('Copied!');
  }
}

function badgeClass(style) {
  const m = {Storytelling:'storytelling', Minimal:'minimal', Question:'question', Factual:'factual', Poetic:'poetic'};
  return 'badge-' + (m[style] || 'minimal');
}

function renderResults(result, photoType) {
  currentResult = result;
  let html = `<div class="results-title">5 Captions — Pick Your Favorite</div>`;

  result.captions.forEach((cap, i) => {
    html += `
    <div class="caption-card">
      <div class="caption-header">
        <span class="style-badge ${badgeClass(cap.style)}">${cap.style}</span>
      </div>
      <div class="caption-text">${cap.text.replace(/\\n/g,'<br>').replace(/\n/g,'<br>')}</div>
      <div class="caption-actions">
        <button class="btn-sm" onclick="copyText(${JSON.stringify(cap.text)}, this)">📋 Copy</button>
        <button class="btn-sm" onclick="copyText(${JSON.stringify(cap.text + '\\n.\\n.\\n.\\n' + result.hashtag_string)}, this)">📋 Caption + Tags</button>
        <button class="btn-sm cal" onclick="openCalModal(${JSON.stringify(cap.text)}, ${JSON.stringify(result.hashtag_string)}, ${JSON.stringify(photoType)})">📅 Calendar</button>
      </div>
    </div>`;
  });

  const h = result.hashtags;
  html += `
  <div class="hashtag-section">
    <div class="hashtag-title">#️⃣ 30 Hashtags (click to copy)</div>
    <div class="hashtag-tier tier-niche">
      <div class="tier-label">🟣 Niche (1K-50K)</div>
      <div class="tag-cloud">${h.niche.map(t=>`<span class="tag" onclick="copyText('${t}', this)">${t}</span>`).join('')}</div>
    </div>
    <div class="hashtag-tier tier-mid">
      <div class="tier-label">🔵 Mid (50K-500K)</div>
      <div class="tag-cloud">${h.mid.map(t=>`<span class="tag" onclick="copyText('${t}', this)">${t}</span>`).join('')}</div>
    </div>
    <div class="hashtag-tier tier-large">
      <div class="tier-label">⚪ Large (500K+)</div>
      <div class="tag-cloud">${h.large.map(t=>`<span class="tag" onclick="copyText('${t}', this)">${t}</span>`).join('')}</div>
    </div>
    <div class="hashtag-copy-row">
      <button class="btn-sm" onclick="copyText(${JSON.stringify(result.hashtag_string)}, this)">📋 Copy All 30 Tags</button>
      <button class="btn-sm" onclick="copyText(${JSON.stringify((result.captions[0]?.text||'') + '\\n.\\n.\\n.\\n' + result.hashtag_string)}, this)">📋 Best Caption + All Tags</button>
    </div>
  </div>`;

  document.getElementById('results').innerHTML = html;
  document.getElementById('results').style.display = 'block';
  document.getElementById('results').scrollIntoView({behavior:'smooth', block:'start'});
}

async function generate() {
  const description = document.getElementById('description').value.trim();
  if (!description) { showToast('Describe your photo first!', '#ef4444'); return; }

  const btn = document.getElementById('generate-btn');
  btn.disabled = true;
  document.getElementById('loading').style.display = 'block';
  document.getElementById('results').style.display = 'none';
  document.getElementById('error-area').innerHTML = '';

  const payload = {
    description,
    location: document.getElementById('location').value.trim(),
    mood: document.getElementById('mood').value,
    photo_type: document.getElementById('photo_type').value,
    include_location: document.getElementById('include_location').checked,
    include_cta: document.getElementById('include_cta').checked
  };

  try {
    const resp = await fetch('/generate', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
    const data = await resp.json();
    if (data.error) throw new Error(data.error);
    renderResults(data, payload.photo_type);
  } catch(e) {
    document.getElementById('error-area').innerHTML = `<div class="error-card">⚠️ ${e.message || 'Generation failed. Try again.'}</div>`;
  } finally {
    btn.disabled = false;
    document.getElementById('loading').style.display = 'none';
  }
}

function openCalModal(caption, hashtags, photoType) {
  const today = new Date().toISOString().split('T')[0];
  document.getElementById('cal-date').value = today;
  pendingSave = {caption, hashtags, photoType};
  document.getElementById('cal-modal').classList.add('open');
}

function closeModal() {
  document.getElementById('cal-modal').classList.remove('open');
  pendingSave = null;
}

async function confirmSave() {
  if (!pendingSave) return;
  const date = document.getElementById('cal-date').value;
  try {
    const resp = await fetch('/save-to-calendar', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({...pendingSave, date})
    });
    const data = await resp.json();
    closeModal();
    showToast(data.message || '✅ Saved!');
  } catch(e) {
    closeModal();
    showToast('Save failed', '#ef4444');
  }
}

async function loadHistory() {
  const container = document.getElementById('history-list');
  try {
    const resp = await fetch('/history');
    const items = await resp.json();
    if (!items.length) {
      container.innerHTML = '<div class="empty-state"><div class="empty-icon">📷</div><div>No history yet</div></div>';
      return;
    }
    container.innerHTML = items.map((item, idx) => {
      const d = new Date(item.created_at).toLocaleDateString('en-US', {month:'short', day:'numeric', hour:'numeric', minute:'2-digit'});
      const firstCap = item.result?.captions?.[0]?.text || 'No caption';
      const preview = firstCap.length > 80 ? firstCap.substring(0,80)+'…' : firstCap;
      const allTags = item.result?.hashtag_string || '';
      const capsHtml = (item.result?.captions||[]).map(c => `
        <div class="caption-card" style="margin-bottom:8px">
          <div class="caption-header"><span class="style-badge ${badgeClass(c.style)}">${c.style}</span></div>
          <div class="caption-text" style="font-size:13px">${c.text.replace(/\n/g,'<br>')}</div>
          <div class="caption-actions">
            <button class="btn-sm" onclick="copyText(${JSON.stringify(c.text)}, this)">📋 Copy</button>
            <button class="btn-sm" onclick="copyText(${JSON.stringify(c.text+'\\n.\\n.\\n.\\n'+allTags)}, this)">📋 + Tags</button>
          </div>
        </div>`).join('');
      return `
      <div class="history-card">
        <div class="history-meta">
          <span class="history-date">${d}</span>
          <span class="history-type">${item.photo_type || 'Photo'}</span>
        </div>
        <div class="history-desc">${item.description}</div>
        <div class="history-caption">"${preview}"</div>
        <span class="history-expand" onclick="toggleExpand(this, 'hist-${idx}')">Show all captions ▾</span>
        <div class="history-full" id="hist-${idx}">
          ${capsHtml}
          ${allTags ? `<div style="margin-top:8px"><button class="btn-sm" onclick="copyText(${JSON.stringify(allTags)}, this)">📋 Copy All Tags</button></div>` : ''}
        </div>
      </div>`;
    }).join('');
  } catch(e) {
    container.innerHTML = '<div class="empty-state"><div class="empty-icon">⚠️</div><div>Failed to load history</div></div>';
  }
}

function toggleExpand(btn, id) {
  const el = document.getElementById(id);
  el.classList.toggle('open');
  btn.textContent = el.classList.contains('open') ? 'Hide ▴' : 'Show all captions ▾';
}

// Allow Cmd/Ctrl+Enter to generate
document.getElementById('description').addEventListener('keydown', function(e) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') generate();
});
</script>
</body>
</html>'''

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8100, debug=False)
