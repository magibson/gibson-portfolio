#!/usr/bin/env python3
"""
X Research Scanner - Runs targeted X searches for Matt's goals
Usage: python x-research-scan.py [morning|noon|evening]
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add integrations to path
sys.path.insert(0, str(Path(__file__).parent.parent / "integrations" / "xai"))
from grok import search_x

SCANS = {
    "morning": {
        "name": "🌅 Morning Prospect Scan",
        "queries": [
            "new job announcement New Jersey OR got promoted New Jersey OR starting new position",
            "just engaged OR getting married New Jersey 2026",
            "just bought a house OR new homeowner New Jersey"
        ],
        "context": "Looking for life event triggers that indicate someone may need financial planning help."
    },
    "noon": {
        "name": "📊 Midday FA Industry Intel", 
        "queries": [
            "financial advisor tips OR financial planner advice client acquisition",
            "life insurance sales tips OR retirement planning prospecting"
        ],
        "context": "Looking for actionable tips and strategies for financial advisors to grow their practice."
    },
    "evening": {
        "name": "📸 Evening Photography Trends",
        "queries": [
            "portrait photography tips 2026 OR photography business growth",
            "photographer needed New Jersey OR looking for photographer NJ"
        ],
        "context": "Looking for photography trends, business tips, and potential client opportunities."
    }
}

def run_scan(scan_type):
    if scan_type not in SCANS:
        print(f"Unknown scan type: {scan_type}")
        print(f"Available: {', '.join(SCANS.keys())}")
        return None
    
    scan = SCANS[scan_type]
    results = []
    
    print(f"\n{scan['name']}", flush=True)
    print("=" * 50, flush=True)
    
    for query in scan["queries"]:
        print(f"\n🔍 Searching: {query[:50]}...", flush=True)
        try:
            result = search_x(query, context=scan["context"])
            results.append({
                "query": query,
                "result": result
            })
            # Print condensed result
            lines = result.split('\n')[:10]
            print('\n'.join(lines), flush=True)
            if len(result.split('\n')) > 10:
                print("... [truncated]", flush=True)
        except Exception as e:
            print(f"Error: {e}", flush=True)
            results.append({
                "query": query,
                "error": str(e)
            })
    
    # Save results
    output_dir = Path(__file__).parent.parent / "data" / "x-research"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    output_file = output_dir / f"{scan_type}_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump({
            "scan_type": scan_type,
            "name": scan["name"],
            "timestamp": datetime.now().isoformat(),
            "results": results
        }, f, indent=2)
    
    print(f"\n✅ Results saved to {output_file}")
    return results

def format_summary(scan_type, results):
    """Format a brief summary for messaging"""
    scan = SCANS[scan_type]
    summary = [f"{scan['name']}\n"]
    
    for r in results:
        if "error" not in r:
            # Extract first few meaningful lines
            lines = r["result"].split('\n')
            preview = '\n'.join(lines[:5])
            summary.append(f"**{r['query'][:40]}...**\n{preview}\n")
    
    return '\n'.join(summary)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python x-research-scan.py [morning|noon|evening|all]")
        sys.exit(1)
    
    scan_type = sys.argv[1]
    
    if scan_type == "all":
        for st in SCANS:
            run_scan(st)
    else:
        run_scan(scan_type)
