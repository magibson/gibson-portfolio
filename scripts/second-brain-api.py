#!/usr/bin/env python3
"""
second-brain-api.py — Flask API wrapper for Jarvis Second Brain
---------------------------------------------------------------
Exposes the second-brain ChromaDB vector search over HTTP.
Runs on port 8092.

Endpoints:
    GET  /query?q=<text>&n=<int>    - Search the brain
    POST /query  body: {"q": "...", "n": 5}
    GET  /health                     - Health check
    GET  /stats                      - DB stats

Only returns results with similarity score >= 0.65.
"""

import sys
import os

# Ensure we use the right venv packages
VENV_SITE = os.path.expanduser("~/clawd/second-brain-env/lib/python3.11/site-packages")
if VENV_SITE not in sys.path:
    sys.path.insert(0, VENV_SITE)

from flask import Flask, request, jsonify
import importlib.util

# ── Config ────────────────────────────────────────────────────────────────────
PORT = 8092
SIMILARITY_THRESHOLD = 0.65
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BRAIN_SCRIPT = os.path.join(SCRIPT_DIR, "second-brain.py")

# ── Load second-brain module dynamically ─────────────────────────────────────
spec = importlib.util.spec_from_file_location("second_brain", BRAIN_SCRIPT)
brain = importlib.util.module_from_spec(spec)
spec.loader.exec_module(brain)

# ── Flask App ─────────────────────────────────────────────────────────────────
app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "port": PORT, "threshold": SIMILARITY_THRESHOLD})


@app.route("/stats", methods=["GET"])
def stats():
    result = brain.stats()
    return jsonify(result)


@app.route("/query", methods=["GET", "POST"])
def query():
    # Parse params from GET or POST JSON
    if request.method == "POST":
        data = request.get_json(force=True, silent=True) or {}
        q = data.get("q", "").strip()
        n = int(data.get("n", 5))
    else:
        q = request.args.get("q", "").strip()
        n = int(request.args.get("n", 5))

    if not q:
        return jsonify({"error": "Missing query parameter 'q'"}), 400

    # Query the brain
    result = brain.query(question=q, n_results=max(n, 20))

    if "error" in result:
        return jsonify(result), 500

    # Filter by similarity threshold
    filtered = [r for r in result["results"] if r["score"] >= SIMILARITY_THRESHOLD]

    # Trim to requested n
    filtered = filtered[:n]

    # Build filtered context string
    context_parts = []
    for r in filtered:
        context_parts.append(
            f"[Source: {r['source']} | Score: {r['score']}]\n{r['text']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    return jsonify({
        "question": q,
        "timestamp": result["timestamp"],
        "total_results": len(filtered),
        "threshold": SIMILARITY_THRESHOLD,
        "results": filtered,
        "context": context,
    })


if __name__ == "__main__":
    print(f"🧠 Second Brain API starting on port {PORT}...")
    print(f"   Similarity threshold: {SIMILARITY_THRESHOLD}")
    print(f"   Brain script: {BRAIN_SCRIPT}")
    app.run(host="127.0.0.1", port=PORT, debug=False)
