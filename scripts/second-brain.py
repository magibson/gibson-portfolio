#!/usr/bin/env python3
"""
second-brain.py — Jarvis Second Brain Query Interface
------------------------------------------------------
Accepts a natural language question, searches the ChromaDB vector DB
using nomic-embed-text embeddings, and returns relevant context.

Usage:
    python3 second-brain.py "What are my top mortgage leads?"
    python3 second-brain.py "What did I work on yesterday?" --results 5
    python3 second-brain.py "Who is Carter Gibson?" --json
    python3 second-brain.py --stats
"""

import os
import sys
import json
import requests
import chromadb
from datetime import datetime

# ── Config (must match indexer) ───────────────────────────────────────────────
OLLAMA_BASE    = "http://localhost:11434"
EMBED_MODEL    = "nomic-embed-text"
CHROMA_DB_PATH = os.path.expanduser("~/clawd/data/second-brain-db")
COLLECTION_NAME = "jarvis_brain"
DEFAULT_RESULTS = 5
MAX_RESULTS     = 20


def get_embedding(text: str) -> list[float]:
    """Get embedding from Ollama nomic-embed-text."""
    resp = requests.post(
        f"{OLLAMA_BASE}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def format_result(doc: str, metadata: dict, distance: float, rank: int) -> str:
    """Format a single search result for display."""
    source = metadata.get("source_file", "unknown")
    doc_type = metadata.get("doc_type", "")
    indexed = metadata.get("indexed_at", "")[:10] if metadata.get("indexed_at") else ""
    score = round(1 - distance, 3)  # convert cosine distance to similarity

    lines = [
        f"── Result {rank} ─── {source} (score: {score}) {'[' + doc_type + ']' if doc_type else ''}",
        doc.strip(),
        "",
    ]
    return "\n".join(lines)


def query(question: str, n_results: int = DEFAULT_RESULTS,
          filter_type: str = None, as_json: bool = False,
          verbose: bool = False) -> dict:
    """
    Query the Second Brain vector database.
    Returns dict with 'results' list and 'context' string.
    """
    # Check DB exists
    if not os.path.exists(CHROMA_DB_PATH):
        return {
            "error": f"Database not found at {CHROMA_DB_PATH}. Run second-brain-index.py first.",
            "results": [],
            "context": "",
        }

    # Get embedding
    try:
        emb = get_embedding(question)
    except Exception as e:
        return {"error": f"Ollama embedding failed: {e}", "results": [], "context": ""}

    # Connect to DB
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    try:
        collection = client.get_collection(COLLECTION_NAME)
    except Exception:
        return {
            "error": f"Collection '{COLLECTION_NAME}' not found. Run second-brain-index.py first.",
            "results": [],
            "context": "",
        }

    # Build query kwargs
    query_kwargs = dict(
        query_embeddings=[emb],
        n_results=min(n_results, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    if filter_type:
        query_kwargs["where"] = {"doc_type": filter_type}

    # Query
    try:
        raw = collection.query(**query_kwargs)
    except Exception as e:
        return {"error": f"Query failed: {e}", "results": [], "context": ""}

    # Parse results
    results = []
    docs      = raw.get("documents", [[]])[0]
    metas     = raw.get("metadatas", [[]])[0]
    distances = raw.get("distances", [[]])[0]

    for i, (doc, meta, dist) in enumerate(zip(docs, metas, distances)):
        results.append({
            "rank": i + 1,
            "source": meta.get("source_file", "unknown"),
            "doc_type": meta.get("doc_type", ""),
            "score": round(1 - dist, 4),
            "distance": round(dist, 4),
            "chunk_index": meta.get("chunk_index", 0),
            "indexed_at": meta.get("indexed_at", ""),
            "text": doc.strip(),
        })

    # Build context string (for use in LLM prompts)
    context_parts = []
    for r in results:
        context_parts.append(
            f"[Source: {r['source']} | Score: {r['score']}]\n{r['text']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    return {
        "question": question,
        "timestamp": datetime.now().isoformat(),
        "total_results": len(results),
        "results": results,
        "context": context,
    }


def stats() -> dict:
    """Return stats about the database."""
    if not os.path.exists(CHROMA_DB_PATH):
        return {"error": "Database not found. Run second-brain-index.py first."}
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    try:
        collection = client.get_collection(COLLECTION_NAME)
        count = collection.count()
        # Sample metadata
        sample = collection.get(limit=1000, include=["metadatas"])
        sources = {}
        for meta in sample.get("metadatas", []):
            src = meta.get("source_file", "unknown")
            sources[src] = sources.get(src, 0) + 1
        return {
            "total_chunks": count,
            "unique_files": len(sources),
            "files": dict(sorted(sources.items())),
        }
    except Exception as e:
        return {"error": str(e)}


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Query Jarvis Second Brain",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 second-brain.py "What are my top mortgage leads?"
  python3 second-brain.py "What did I work on this week?" --results 8
  python3 second-brain.py "Carter Gibson background" --type markdown
  python3 second-brain.py "Who are the hot leads from January?" --json
  python3 second-brain.py --stats
        """,
    )
    parser.add_argument("question", nargs="?", help="Natural language question")
    parser.add_argument("-n", "--results", type=int, default=DEFAULT_RESULTS,
                        help=f"Number of results (default: {DEFAULT_RESULTS})")
    parser.add_argument("--type", choices=["markdown", "csv_summary"],
                        help="Filter by document type")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="Output raw JSON")
    parser.add_argument("--context-only", action="store_true",
                        help="Output only the context string (for LLM piping)")
    parser.add_argument("--stats", action="store_true",
                        help="Show database stats")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    if args.stats:
        s = stats()
        print(json.dumps(s, indent=2))
        return

    if not args.question:
        parser.print_help()
        sys.exit(1)

    result = query(
        question=args.question,
        n_results=args.results,
        filter_type=args.type,
        as_json=args.as_json,
        verbose=args.verbose,
    )

    if "error" in result:
        print(f"ERROR: {result['error']}", file=sys.stderr)
        sys.exit(1)

    if args.as_json:
        print(json.dumps(result, indent=2))
        return

    if args.context_only:
        print(result["context"])
        return

    # Human-readable output
    print(f"\n🧠 Second Brain Query: \"{result['question']}\"")
    print(f"   Found {result['total_results']} results\n")
    print("=" * 70)
    for r in result["results"]:
        print(f"\n{'─' * 70}")
        print(f"  [{r['rank']}] {r['source']}  |  score: {r['score']}  |  {r['doc_type']}")
        print(f"{'─' * 70}")
        # Truncate long chunks for display
        text = r["text"]
        if len(text) > 600 and not args.verbose:
            text = text[:600] + "…"
        print(text)
    print(f"\n{'=' * 70}\n")


if __name__ == "__main__":
    main()
