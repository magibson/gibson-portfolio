"""
cli.py — Second Brain command line interface

Commands:
  python cli.py save <url|text|file> [--tags tag1,tag2]
  python cli.py search <query>
  python cli.py list [--limit 20]
  python cli.py stats
"""
import sys
import os
from pathlib import Path

env_path = Path.home() / "clawd" / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

from ingest import ingest
from search import format_results
from storage import semantic_search, list_recent, get_stats


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    cmd = args[0]

    if cmd == "save":
        if len(args) < 2:
            print("Usage: python cli.py save <url|text|file> [--tags tag1,tag2]")
            sys.exit(1)
        content = args[1]
        tags = []
        if "--tags" in args:
            idx = args.index("--tags")
            if idx + 1 < len(args):
                tags = args[idx + 1].split(",")
        doc_id = ingest(content, tags=tags)
        print(f"✅ Saved → ID: {doc_id[:8]}")

    elif cmd == "search":
        if len(args) < 2:
            print("Usage: python cli.py search <query>")
            sys.exit(1)
        query = " ".join(args[1:])
        results = semantic_search(query, n_results=5)
        print(format_results(results))

    elif cmd == "list":
        limit = 20
        if "--limit" in args:
            idx = args.index("--limit")
            if idx + 1 < len(args):
                limit = int(args[idx + 1])
        docs = list_recent(limit)
        if not docs:
            print("Brain is empty. Use: python cli.py save <content>")
        for d in docs:
            emoji = {"url": "🌐", "text": "📝", "pdf": "📄", "audio": "🎙️", "image": "🖼️"}.get(d["content_type"], "📌")
            print(f"[{d['date_added'][:16]}] {emoji} {d['title'][:60]}")

    elif cmd == "stats":
        stats = get_stats()
        print(f"🧠 Second Brain — {stats['total']} items total")
        for t, n in stats["by_type"].items():
            print(f"   {t}: {n}")

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
