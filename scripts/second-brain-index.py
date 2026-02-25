#!/usr/bin/env python3
"""
second-brain-index.py — Jarvis Second Brain Indexer
----------------------------------------------------
Indexes all memory/reference/lead files into a ChromaDB vector database
using Ollama's nomic-embed-text model for embeddings.

Run manually or via launchd cron at 2 AM to keep the index fresh.
"""

import os
import sys
import json
import glob
import hashlib
import logging
import requests
import chromadb
from pathlib import Path
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
OLLAMA_BASE      = "http://localhost:11434"
EMBED_MODEL      = "nomic-embed-text"
CHROMA_DB_PATH   = os.path.expanduser("~/clawd/data/second-brain-db")
COLLECTION_NAME  = "jarvis_brain"
HASH_CACHE_PATH  = os.path.expanduser("~/clawd/data/second-brain-hashes.json")
LOG_PATH         = os.path.expanduser("~/clawd/data/second-brain-index.log")
CLAWD            = os.path.expanduser("~/clawd")

# ── Files to index ────────────────────────────────────────────────────────────
GLOB_PATTERNS = [
    "memory/*.md",
    "MEMORY.md",
    "NIGHTLY-BUILDS.md",
    "reference/*.md",
    "leads/*.csv",
]

# Chunk settings
CHUNK_SIZE    = 800   # characters
CHUNK_OVERLAP = 150

# ── Logging ───────────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("second-brain-index")


# ── Helpers ───────────────────────────────────────────────────────────────────

def file_hash(path: str) -> str:
    """SHA256 of file contents."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_hash_cache() -> dict:
    if os.path.exists(HASH_CACHE_PATH):
        with open(HASH_CACHE_PATH) as f:
            return json.load(f)
    return {}


def save_hash_cache(cache: dict):
    os.makedirs(os.path.dirname(HASH_CACHE_PATH), exist_ok=True)
    with open(HASH_CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)


def get_embedding(text: str) -> list[float]:
    """Get embedding from Ollama nomic-embed-text."""
    resp = requests.post(
        f"{OLLAMA_BASE}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def chunk_text(text: str, source: str) -> list[dict]:
    """Split text into overlapping chunks. Returns list of {text, chunk_id}."""
    chunks = []
    start = 0
    idx = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end]
        if chunk.strip():
            chunks.append({
                "text": chunk,
                "chunk_id": f"{source}::chunk{idx}",
                "chunk_index": idx,
            })
        start += CHUNK_SIZE - CHUNK_OVERLAP
        idx += 1
    return chunks


def read_md_file(path: str) -> str:
    """Read a markdown file and return its content."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def read_csv_summary(path: str) -> str:
    """
    Generate a summary of a CSV file suitable for vector indexing.
    Reads header + first 20 rows, formats as structured text.
    """
    import csv
    lines = []
    fname = os.path.basename(path)
    lines.append(f"CSV File: {fname}")
    lines.append(f"Path: {path}")
    lines.append("")
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            rows = []
            for i, row in enumerate(reader):
                if i >= 50:
                    break
                rows.append(row)
            if not rows:
                return "\n".join(lines)
            headers = list(rows[0].keys())
            lines.append(f"Columns: {', '.join(headers)}")
            lines.append(f"Total rows shown: {len(rows)}")
            lines.append("")
            # Summarize key fields if this looks like a leads file
            lead_name_cols = [c for c in headers if any(
                k in c.lower() for k in ["name", "first", "last", "owner"]
            )]
            addr_cols = [c for c in headers if any(
                k in c.lower() for k in ["address", "city", "state", "zip"]
            )]
            for row in rows[:20]:
                parts = []
                for col in headers[:8]:  # first 8 columns
                    val = row.get(col, "").strip()
                    if val:
                        parts.append(f"{col}: {val}")
                if parts:
                    lines.append("  " + " | ".join(parts))
    except Exception as e:
        lines.append(f"Error reading CSV: {e}")
    return "\n".join(lines)


def collect_files() -> list[str]:
    """Collect all target files based on GLOB_PATTERNS."""
    files = []
    for pattern in GLOB_PATTERNS:
        full_pattern = os.path.join(CLAWD, pattern)
        matched = sorted(glob.glob(full_pattern))
        files.extend(matched)
    return list(dict.fromkeys(files))  # dedupe, preserve order


def index_file(path: str, collection, hash_cache: dict, force: bool = False) -> int:
    """
    Index a single file into the ChromaDB collection.
    Returns number of chunks added/updated.
    """
    rel = os.path.relpath(path, CLAWD)
    fhash = file_hash(path)

    if not force and hash_cache.get(rel) == fhash:
        log.debug(f"  SKIP (unchanged): {rel}")
        return 0

    log.info(f"  Indexing: {rel}")

    # Read content
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        content = read_csv_summary(path)
        doc_type = "csv_summary"
    else:
        content = read_md_file(path)
        doc_type = "markdown"

    if not content.strip():
        log.warning(f"  Empty file: {rel}")
        return 0

    # Remove existing chunks for this file
    try:
        existing = collection.get(where={"source_file": rel})
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
            log.debug(f"  Removed {len(existing['ids'])} old chunks for {rel}")
    except Exception as e:
        log.warning(f"  Could not remove old chunks: {e}")

    # Chunk & embed
    chunks = chunk_text(content, rel)
    added = 0
    for chunk in chunks:
        try:
            emb = get_embedding(chunk["text"])
            collection.add(
                ids=[chunk["chunk_id"]],
                embeddings=[emb],
                documents=[chunk["text"]],
                metadatas=[{
                    "source_file": rel,
                    "chunk_index": chunk["chunk_index"],
                    "doc_type": doc_type,
                    "file_path": path,
                    "indexed_at": datetime.now().isoformat(),
                }],
            )
            added += 1
        except Exception as e:
            log.error(f"  Error embedding chunk {chunk['chunk_id']}: {e}")

    hash_cache[rel] = fhash
    log.info(f"  ✓ {rel} — {added} chunks indexed")
    return added


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Index files into Jarvis Second Brain")
    parser.add_argument("--force", action="store_true", help="Re-index all files regardless of changes")
    parser.add_argument("--file", help="Index a specific file only")
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("Jarvis Second Brain — Indexer Starting")
    log.info(f"  DB Path:     {CHROMA_DB_PATH}")
    log.info(f"  Embed Model: {EMBED_MODEL}")
    log.info(f"  Force:       {args.force}")
    log.info("=" * 60)

    # Verify Ollama is running
    try:
        resp = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        models = [m["name"] for m in resp.json().get("models", [])]
        if not any(EMBED_MODEL in m for m in models):
            log.error(f"Model '{EMBED_MODEL}' not found in Ollama. Available: {models}")
            sys.exit(1)
        log.info(f"  Ollama OK — found {EMBED_MODEL}")
    except Exception as e:
        log.error(f"Cannot reach Ollama at {OLLAMA_BASE}: {e}")
        sys.exit(1)

    # Init ChromaDB
    os.makedirs(CHROMA_DB_PATH, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    log.info(f"  ChromaDB collection '{COLLECTION_NAME}' — {collection.count()} existing chunks")

    # Load hash cache
    hash_cache = load_hash_cache()

    # Collect files
    if args.file:
        files = [os.path.expanduser(args.file)]
    else:
        files = collect_files()
    log.info(f"  Files to check: {len(files)}")

    # Index
    total_added = 0
    total_files = 0
    errors = 0
    for path in files:
        if not os.path.exists(path):
            log.warning(f"  NOT FOUND: {path}")
            continue
        try:
            added = index_file(path, collection, hash_cache, force=args.force)
            if added > 0:
                total_added += added
                total_files += 1
        except Exception as e:
            log.error(f"  FAILED {path}: {e}")
            errors += 1

    # Save hashes
    save_hash_cache(hash_cache)

    total_chunks = collection.count()
    log.info("=" * 60)
    log.info(f"  Done — {total_files} files updated, {total_added} chunks added")
    log.info(f"  Total chunks in DB: {total_chunks}")
    log.info(f"  Errors: {errors}")
    log.info("=" * 60)

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
