"""
search.py — Semantic search for the Second Brain
"""
import sys
from storage import semantic_search, list_recent, get_stats


def format_results(results: list) -> str:
    if not results:
        return "No results found."
    lines = []
    for i, r in enumerate(results, 1):
        date = r["date_added"][:10] if r["date_added"] else "?"
        score_pct = int(r["score"] * 100)
        type_badge = {"url": "🌐", "text": "📝", "pdf": "📄", "audio": "🎙️", "image": "🖼️"}.get(r["content_type"], "📌")
        lines.append(f"{i}. {type_badge} {r['title'] or 'Untitled'} ({score_pct}% match)")
        lines.append(f"   {r['snippet'][:200]}...")
        if r["source"]:
            lines.append(f"   → {r['source'][:80]}")
        lines.append(f"   Saved: {date}")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python search.py <query>")
        print("       python search.py --recent")
        print("       python search.py --stats")
        sys.exit(1)

    arg = sys.argv[1]
    if arg == "--recent":
        docs = list_recent(20)
        for d in docs:
            print(f"[{d['date_added'][:16]}] {d['content_type']:6} | {d['title'][:60]}")
    elif arg == "--stats":
        stats = get_stats()
        print(f"Total items: {stats['total']}")
        for t, n in stats["by_type"].items():
            print(f"  {t}: {n}")
    else:
        query = " ".join(sys.argv[1:])
        results = semantic_search(query, n_results=5)
        print(format_results(results))
