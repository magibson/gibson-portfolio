"""
storage.py — SQLite + Ollama embeddings for semantic search
No external vector DB — Python 3.14 compatible
"""
import sqlite3
import json
import uuid
import struct
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
import requests

DB_DIR = Path.home() / "clawd" / "data" / "brain"
SQLITE_PATH = DB_DIR / "brain.db"
OLLAMA_BASE = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"   # pulled on first use if missing; tiny 274MB
FALLBACK_MODEL = "llama3.2:3b"     # already installed

# ── DB SETUP ───────────────────────────────────────────────────────────────────

def _get_db():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(SQLITE_PATH))
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            content_type TEXT NOT NULL,
            title TEXT,
            body_text TEXT,
            source TEXT,
            tags TEXT DEFAULT '[]',
            date_added TEXT,
            metadata TEXT DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS embeddings (
            id TEXT PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE,
            model TEXT,
            vector BLOB
        );
        CREATE INDEX IF NOT EXISTS idx_date ON documents(date_added);
        CREATE INDEX IF NOT EXISTS idx_type ON documents(content_type);
    """)
    conn.commit()
    return conn


# ── EMBEDDINGS ────────────────────────────────────────────────────────────────

def _ensure_embed_model() -> str:
    """Return the best available embedding model."""
    try:
        r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=3)
        models = [m["name"] for m in r.json().get("models", [])]
        if any(EMBED_MODEL in m for m in models):
            return EMBED_MODEL
        # Pull nomic-embed-text if not present (small 274MB model)
        if not any(FALLBACK_MODEL in m for m in models):
            return FALLBACK_MODEL
        # Pull nomic-embed-text in background
        print(f"[brain] Pulling {EMBED_MODEL} for better embeddings (274MB)...")
        requests.post(f"{OLLAMA_BASE}/api/pull", json={"name": EMBED_MODEL}, timeout=5)
        return FALLBACK_MODEL
    except Exception:
        return FALLBACK_MODEL


def _get_embedding(text: str) -> Optional[list]:
    """Get embedding vector from Ollama."""
    model = _ensure_embed_model()
    try:
        r = requests.post(
            f"{OLLAMA_BASE}/api/embeddings",
            json={"model": model, "prompt": text[:2000]},
            timeout=30
        )
        r.raise_for_status()
        vec = r.json().get("embedding")
        return vec
    except Exception as e:
        print(f"[brain] Embedding error: {e}")
        return None


def _vec_to_blob(vec: list) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)

def _blob_to_vec(blob: bytes) -> list:
    n = len(blob) // 4
    return list(struct.unpack(f"{n}f", blob))

def _cosine(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


# ── PUBLIC API ────────────────────────────────────────────────────────────────

def save_document(
    content_type: str,
    body_text: str,
    title: str = "",
    source: str = "",
    tags: list = None,
    metadata: dict = None
) -> str:
    """Save a document and its embedding. Returns doc id."""
    doc_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    tags = tags or []
    metadata = metadata or {}

    conn = _get_db()
    try:
        conn.execute(
            "INSERT INTO documents VALUES (?,?,?,?,?,?,?,?)",
            (doc_id, content_type, title, body_text, source,
             json.dumps(tags), now, json.dumps(metadata))
        )
        conn.commit()
    except Exception as e:
        print(f"[brain] SQLite save error: {e}")
        conn.close()
        return doc_id

    # Embed in background (don't block ingest on slow Ollama)
    embed_text = f"{title}\n\n{body_text}" if title else body_text
    vec = _get_embedding(embed_text[:3000])
    if vec:
        try:
            model = _ensure_embed_model()
            conn.execute(
                "INSERT OR REPLACE INTO embeddings VALUES (?,?,?)",
                (doc_id, model, _vec_to_blob(vec))
            )
            conn.commit()
        except Exception as e:
            print(f"[brain] Embedding save error: {e}")

    conn.close()
    return doc_id


def semantic_search(query: str, n_results: int = 5) -> list:
    """Semantic search using cosine similarity."""
    query_vec = _get_embedding(query)
    if not query_vec:
        return []

    conn = _get_db()
    try:
        rows = conn.execute("""
            SELECT d.id, d.content_type, d.title, d.body_text, d.source,
                   d.date_added, e.vector
            FROM documents d
            JOIN embeddings e ON d.id = e.id
        """).fetchall()
    except Exception as e:
        print(f"[brain] Search DB error: {e}")
        conn.close()
        return []
    conn.close()

    scored = []
    for row in rows:
        vec = _blob_to_vec(row["vector"])
        score = _cosine(query_vec, vec)
        scored.append({
            "id": row["id"],
            "content_type": row["content_type"],
            "title": row["title"] or "Untitled",
            "snippet": (row["body_text"] or "")[:250].replace("\n", " "),
            "source": row["source"] or "",
            "date_added": row["date_added"] or "",
            "score": round(score, 3)
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:n_results]


def list_recent(limit: int = 20) -> list:
    conn = _get_db()
    rows = conn.execute(
        "SELECT * FROM documents ORDER BY date_added DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats() -> dict:
    conn = _get_db()
    total = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    by_type = conn.execute(
        "SELECT content_type, COUNT(*) as n FROM documents GROUP BY content_type"
    ).fetchall()
    conn.close()
    return {"total": total, "by_type": {r[0]: r[1] for r in by_type}}
