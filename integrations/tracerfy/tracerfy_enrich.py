#!/usr/bin/env python3
"""
Tracerfy skip trace enrichment for Propwire leads.
Submits CSV → polls for completion → downloads results → saves dial-ready list.
Cost: $0.02/record × 100 = $2.00
"""
import os, sys, csv, time, json, requests
from pathlib import Path
from datetime import datetime

CLAWD = Path.home() / "clawd"
API_KEY = os.getenv("TRACERFY_API_KEY") or open(CLAWD / ".env").read().split("TRACERFY_API_KEY=")[1].split("\n")[0].strip()
BASE = "https://api.tracerfy.com"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

INPUT_CSV = CLAWD / "leads" / "propwire_leads_2026-02-23.csv"
OUTPUT_CSV = CLAWD / "leads" / f"dial_ready_{datetime.now().strftime('%Y-%m-%d')}.csv"

def log(msg): print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def check_balance():
    r = requests.get(f"{BASE}/analytics/", headers=HEADERS, timeout=30)
    r.raise_for_status()
    d = r.json()
    log(f"Account: credits={d.get('credits', d.get('credit_balance', '?'))}, total_traced={d.get('total_properties', '?')}")
    return d

def submit_trace(csv_path):
    log(f"Submitting {csv_path.name} to Tracerfy...")
    with open(csv_path, "rb") as f:
        r = requests.post(
            f"{BASE}/trace/",
            headers=HEADERS,
            files={"file": (csv_path.name, f, "text/csv")},
            timeout=60
        )
    log(f"Response [{r.status_code}]: {r.text[:300]}")
    r.raise_for_status()
    return r.json()

def poll_queue(queue_id, max_wait=600):
    log(f"Polling queue {queue_id}...")
    for i in range(max_wait // 15):
        r = requests.get(f"{BASE}/queue/{queue_id}/", headers=HEADERS, timeout=30)
        r.raise_for_status()
        d = r.json()
        status = d.get("status", "unknown")
        log(f"  Status: {status} ({i*15}s elapsed)")
        if status in ("completed", "complete", "done", "finished"):
            return d
        if status in ("failed", "error"):
            log(f"  FAILED: {d}")
            return None
        time.sleep(15)
    log("Timed out waiting for queue")
    return None

def download_results(queue_data, queue_id):
    # Try download_url first, then fetch the queue data directly
    dl_url = queue_data.get("download_url") or queue_data.get("results_url")
    if dl_url:
        log(f"Downloading from: {dl_url}")
        r = requests.get(dl_url, headers=HEADERS, timeout=60)
        r.raise_for_status()
        return r.text
    
    # Fallback: results may be inline
    results = queue_data.get("results") or queue_data.get("properties")
    if results:
        return results  # list of dicts
    
    # Try fetching queue again with different endpoint
    r = requests.get(f"{BASE}/queues/{queue_id}/download/", headers=HEADERS, timeout=60)
    if r.status_code == 200:
        return r.text
    
    log(f"Queue data keys: {list(queue_data.keys())}")
    return None

def build_dial_list(raw_results, original_csv):
    """Merge trace results with original data, output dial-ready CSV."""
    # Parse original leads
    with open(original_csv) as f:
        originals = {row['Id']: row for row in csv.DictReader(f)}
    
    dial_rows = []
    
    if isinstance(raw_results, str):
        # CSV string
        import io
        reader = csv.DictReader(io.StringIO(raw_results))
        traced = list(reader)
    else:
        traced = raw_results  # list of dicts
    
    log(f"Traced records: {len(traced)}")
    if traced:
        log(f"Trace columns: {list(traced[0].keys())[:15]}")
    
    for row in traced:
        # Find phone numbers - Tracerfy returns Phone1..Phone8
        phones = []
        for i in range(1, 9):
            p = row.get(f"Phone{i}", row.get(f"phone_{i}", row.get(f"phone{i}", ""))).strip()
            if p and p not in ("", "None", "null"):
                phones.append(p)
        
        if not phones:
            continue  # Skip leads with no phones
        
        # Get owner name
        first = row.get("Owner 1 First Name", row.get("FirstName", row.get("first_name", ""))).strip().title()
        last = row.get("Owner 1 Last Name", row.get("LastName", row.get("last_name", ""))).strip().title()
        name = f"{first} {last}".strip()
        
        addr = row.get("Address", row.get("address", "")).strip().title()
        city = row.get("City", row.get("city", "")).strip().title()
        state = row.get("State", row.get("state", "NJ")).strip()
        zip_ = row.get("Zip", row.get("zip", "")).strip()
        
        # Primary phone first
        dial_rows.append({
            "Name": name,
            "Phone 1": phones[0],
            "Phone 2": phones[1] if len(phones) > 1 else "",
            "Phone 3": phones[2] if len(phones) > 2 else "",
            "Property Address": addr,
            "City": city,
            "State": state,
            "Zip": zip_,
            "Email": row.get("Email1", row.get("email_1", row.get("email", ""))).strip(),
            "All Phones": " | ".join(phones),
        })
    
    log(f"Dial-ready leads (with phones): {len(dial_rows)} / {len(traced)}")
    
    with open(OUTPUT_CSV, "w", newline="") as f:
        if dial_rows:
            w = csv.DictWriter(f, fieldnames=list(dial_rows[0].keys()))
            w.writeheader()
            w.writerows(dial_rows)
    
    log(f"✅ Saved: {OUTPUT_CSV}")
    return len(dial_rows)

def main():
    log("=== Tracerfy Enrichment ===")
    
    # Check balance first
    try:
        check_balance()
    except Exception as e:
        log(f"Balance check failed: {e} — continuing anyway")
    
    # Submit trace job
    try:
        result = submit_trace(INPUT_CSV)
        log(f"Submitted: {result}")
    except Exception as e:
        log(f"Submit failed: {e}")
        sys.exit(1)
    
    queue_id = result.get("id") or result.get("queue_id") or result.get("job_id")
    if not queue_id:
        log(f"No queue ID in response: {result}")
        sys.exit(1)
    
    log(f"Queue ID: {queue_id}")
    
    # Poll for completion
    queue_data = poll_queue(queue_id)
    if not queue_data:
        log("❌ Job failed or timed out")
        sys.exit(1)
    
    # Download and process results
    raw = download_results(queue_data, queue_id)
    if not raw:
        log("❌ Could not get results")
        log(f"Full queue data: {json.dumps(queue_data, indent=2)[:1000]}")
        sys.exit(1)
    
    count = build_dial_list(raw, INPUT_CSV)
    log(f"✅ Done — {count} dial-ready leads")

if __name__ == "__main__":
    main()
