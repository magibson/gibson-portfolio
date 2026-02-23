"""
app.py — Second Brain Flask web UI
Port 8091 | Dashboard + Search + Ingest
"""
import os
import json
from pathlib import Path
from flask import Flask, request, jsonify, render_template_string

# Load env
env_path = Path.home() / "clawd" / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

from storage import semantic_search, list_recent, get_stats, save_document
from ingest import ingest, ingest_url, ingest_text

app = Flask(__name__)

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🧠 Second Brain</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0f172a; color: #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
  .header { background: #1e293b; border-bottom: 1px solid #334155; padding: 16px 24px; display: flex; align-items: center; justify-content: space-between; }
  .header h1 { font-size: 1.2rem; font-weight: 600; }
  .header .stats { font-size: 0.8rem; color: #94a3b8; }
  .container { max-width: 900px; margin: 0 auto; padding: 24px; }
  .search-bar { display: flex; gap: 8px; margin-bottom: 24px; }
  .search-bar input { flex: 1; background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 12px 16px; color: #e2e8f0; font-size: 0.95rem; outline: none; }
  .search-bar input:focus { border-color: #3b82f6; }
  .search-bar button { background: #3b82f6; border: none; border-radius: 8px; padding: 12px 20px; color: white; cursor: pointer; font-size: 0.9rem; white-space: nowrap; }
  .search-bar button:hover { background: #2563eb; }
  .save-bar { display: flex; gap: 8px; margin-bottom: 28px; }
  .save-bar input { flex: 1; background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 10px 16px; color: #e2e8f0; font-size: 0.9rem; outline: none; }
  .save-bar input:focus { border-color: #10b981; }
  .save-bar button { background: #10b981; border: none; border-radius: 8px; padding: 10px 16px; color: white; cursor: pointer; font-size: 0.85rem; }
  .save-bar button:hover { background: #059669; }
  .section-title { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; color: #64748b; margin-bottom: 12px; font-weight: 600; }
  .card { background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 16px; margin-bottom: 10px; transition: border-color 0.15s; }
  .card:hover { border-color: #475569; }
  .card-title { font-size: 0.95rem; font-weight: 500; color: #e2e8f0; margin-bottom: 6px; }
  .card-snippet { font-size: 0.82rem; color: #94a3b8; line-height: 1.5; margin-bottom: 8px; }
  .card-meta { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .badge { font-size: 0.7rem; padding: 2px 8px; border-radius: 99px; background: #334155; color: #94a3b8; }
  .badge.url { background: #1e3a5f; color: #60a5fa; }
  .badge.text { background: #1e3a2f; color: #4ade80; }
  .badge.pdf { background: #3a1e1e; color: #f87171; }
  .badge.audio { background: #2a1e3a; color: #c084fc; }
  .score { font-size: 0.7rem; color: #3b82f6; font-weight: 600; }
  .empty { color: #475569; text-align: center; padding: 40px; font-size: 0.9rem; }
  .toast { position: fixed; bottom: 24px; right: 24px; background: #10b981; color: white; padding: 10px 18px; border-radius: 8px; font-size: 0.85rem; display: none; z-index: 999; }
</style>
</head>
<body>
<div class="header">
  <h1>🧠 Second Brain</h1>
  <div class="stats" id="stats-bar">Loading...</div>
</div>
<div class="container">
  <div class="search-bar">
    <input type="text" id="search-input" placeholder="Search your brain... (press Enter)" onkeydown="if(event.key==='Enter') doSearch()">
    <button onclick="doSearch()">Search</button>
  </div>
  <div class="save-bar">
    <input type="text" id="save-input" placeholder="Save anything: paste a URL, type a note, or drop a file path..." onkeydown="if(event.key==='Enter') doSave()">
    <button onclick="doSave()">+ Save</button>
  </div>
  <div class="section-title" id="results-title">Recent Saves</div>
  <div id="results"></div>
</div>
<div class="toast" id="toast"></div>
<script>
async function loadRecent() {
  const r = await fetch('/api/recent');
  const data = await r.json();
  renderDocs(data.docs, 'Recent Saves');
  document.getElementById('stats-bar').textContent = data.stats.total + ' items saved';
}

async function doSearch() {
  const q = document.getElementById('search-input').value.trim();
  if (!q) { loadRecent(); return; }
  document.getElementById('results-title').textContent = 'Search: "' + q + '"';
  document.getElementById('results').innerHTML = '<div class="empty">Searching...</div>';
  const r = await fetch('/api/search?q=' + encodeURIComponent(q));
  const data = await r.json();
  renderResults(data.results);
}

async function doSave() {
  const content = document.getElementById('save-input').value.trim();
  if (!content) return;
  const btn = document.querySelector('.save-bar button');
  btn.textContent = 'Saving...'; btn.disabled = true;
  const r = await fetch('/api/ingest', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({content})
  });
  const data = await r.json();
  btn.textContent = '+ Save'; btn.disabled = false;
  if (data.id) {
    document.getElementById('save-input').value = '';
    showToast('Saved! (' + data.type + ')');
    loadRecent();
  } else {
    showToast('Error: ' + (data.error || 'unknown'), true);
  }
}

function renderDocs(docs, title) {
  document.getElementById('results-title').textContent = title;
  const el = document.getElementById('results');
  if (!docs.length) { el.innerHTML = '<div class="empty">Nothing saved yet. Drop a URL or note above ↑</div>'; return; }
  el.innerHTML = docs.map(d => cardHtml(d)).join('');
}

function renderResults(results) {
  const el = document.getElementById('results');
  if (!results.length) { el.innerHTML = '<div class="empty">No matches found.</div>'; return; }
  el.innerHTML = results.map(r => `
    <div class="card">
      <div class="card-title">${esc(r.title || 'Untitled')}</div>
      <div class="card-snippet">${esc(r.snippet)}</div>
      <div class="card-meta">
        <span class="badge ${r.content_type}">${typeEmoji(r.content_type)} ${r.content_type}</span>
        <span class="score">${Math.round(r.score*100)}% match</span>
        <span class="badge">${(r.date_added||'').slice(0,10)}</span>
        ${r.source ? '<span class="badge" title="'+esc(r.source)+'">'+esc(r.source.slice(-40))+'</span>' : ''}
      </div>
    </div>`).join('');
}

function cardHtml(d) {
  const snippet = (d.body_text||'').slice(0,200).replace(/\n/g,' ');
  return `<div class="card">
    <div class="card-title">${esc(d.title || 'Untitled')}</div>
    <div class="card-snippet">${esc(snippet)}${snippet.length>=200?'...':''}</div>
    <div class="card-meta">
      <span class="badge ${d.content_type}">${typeEmoji(d.content_type)} ${d.content_type}</span>
      <span class="badge">${(d.date_added||'').slice(0,10)}</span>
      ${d.source ? '<span class="badge" title="'+esc(d.source)+'">'+esc(d.source.slice(-40))+'</span>' : ''}
    </div>
  </div>`;
}

function typeEmoji(t) { return {url:'🌐',text:'📝',pdf:'📄',audio:'🎙️',image:'🖼️'}[t]||'📌'; }
function esc(s) { return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function showToast(msg, err) {
  const t = document.getElementById('toast');
  t.textContent = msg; t.style.background = err ? '#ef4444' : '#10b981';
  t.style.display = 'block'; setTimeout(()=>{ t.style.display='none'; }, 3000);
}

loadRecent();
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/api/recent")
def api_recent():
    docs = list_recent(20)
    stats = get_stats()
    return jsonify({"docs": docs, "stats": stats})

@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"results": []})
    results = semantic_search(q, n_results=5)
    return jsonify({"results": results})

@app.route("/api/ingest", methods=["POST"])
def api_ingest():
    data = request.get_json(force=True)
    content = data.get("content", "").strip()
    tags = data.get("tags", [])
    if not content:
        return jsonify({"error": "content required"}), 400
    try:
        doc_id = ingest(content, tags=tags)
        # Determine type
        content_type = "text"
        if content.startswith("http"):
            content_type = "url"
        elif Path(content).exists():
            ext = Path(content).suffix.lower()
            if ext == ".pdf": content_type = "pdf"
            elif ext in {".mp3",".m4a",".wav",".ogg"}: content_type = "audio"
            elif ext in {".jpg",".jpeg",".png",".gif"}: content_type = "image"
        return jsonify({"id": doc_id, "type": content_type})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("BRAIN_PORT", 8091))
    print(f"[brain] Starting Second Brain on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
