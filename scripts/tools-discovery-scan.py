#!/usr/bin/env python3
"""
Tools & APIs Discovery Scan
Searches X for new free tools, APIs, integrations that could boost productivity.
Run nightly via cron.
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

# Add integrations to path
sys.path.insert(0, str(Path(__file__).parent.parent / "integrations" / "xai"))

EASTERN = ZoneInfo("America/New_York")

SEARCH_QUERIES = [
    # Free tools and APIs
    "free API launch OR released OR announcing developer",
    "open source tool launch productivity automation",
    "new free tier API developer",
    
    # AI/automation specific
    "AI agent tool free OR open source",
    "automation workflow free tool",
    "no-code tool launch free",
    
    # Integrations and skills
    "API integration new free developer",
    "Claude OR GPT plugin OR extension free",
    
    # Clawdbot/AI assistant ecosystem
    "AI assistant integration free API",
    "personal AI automation tool",
]

CONTEXT = """Looking for new free tools, APIs, or integrations that could help:
1. A personal AI assistant (like Clawdbot/Claude)
2. A financial advisor with lead generation needs
3. A photographer wanting to grow social presence
4. General productivity and automation

Focus on: genuinely free tools, open source, new API launches, useful integrations.
Ignore: paid tools, enterprise-only, crypto/NFT spam."""


def run_scan():
    """Run the discovery scan"""
    try:
        from grok import search_x
    except ImportError:
        print("❌ Grok module not available")
        return None
    
    results = []
    now = datetime.now(EASTERN)
    
    print(f"🔍 Tools Discovery Scan - {now.strftime('%Y-%m-%d %I:%M %p ET')}", flush=True)
    print("=" * 60, flush=True)
    
    for i, query in enumerate(SEARCH_QUERIES[:3]):  # Reduced to 3 to save time/tokens
        print(f"\n[{i+1}/3] Searching: {query[:50]}...", flush=True)
        try:
            result = search_x(query, context=CONTEXT)
            if result and "error" not in result.lower():
                results.append({
                    "query": query,
                    "result": result,
                    "timestamp": now.isoformat()
                })
                # Print preview
                lines = result.split('\n')[:3]
                for line in lines:
                    if line.strip():
                        print(f"    {line[:80]}", flush=True)
            else:
                print(f"    ⚠️ {result[:100] if result else 'Empty result'}", flush=True)
        except Exception as e:
            print(f"    ❌ Error: {e}", flush=True)
    
    # Save results
    output_dir = Path(__file__).parent.parent / "data" / "tools-discovery"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"scan_{now.strftime('%Y-%m-%d')}.json"
    
    with open(output_file, 'w') as f:
        json.dump({
            "scan_date": now.isoformat(),
            "queries_run": len(results),
            "results": results
        }, f, indent=2)
    
    print(f"\n✅ Results saved to {output_file}")
    return results


def format_summary(results):
    """Format findings for messaging"""
    if not results:
        return "No new tools found in tonight's scan."
    
    summary = ["🔧 **Nightly Tools Discovery**\n"]
    
    for r in results:
        if r.get("result"):
            # Extract key points
            lines = r["result"].split('\n')
            preview = '\n'.join(lines[:3])
            summary.append(f"**{r['query'][:40]}...**\n{preview}\n")
    
    return '\n'.join(summary)


if __name__ == "__main__":
    results = run_scan()
    if results:
        print("\n" + "=" * 60)
        print(format_summary(results))
