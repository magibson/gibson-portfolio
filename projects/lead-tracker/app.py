import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from flask import Flask, render_template, request, jsonify

BASE_DIR = Path(__file__).resolve().parent
LEADS_CSV = BASE_DIR / "leads.csv"
STATUS_JSON = BASE_DIR / "leads_status.json"

STATUS_OPTIONS = [
    "Not Called",
    "Called - No Answer",
    "Called - Left VM",
    "Callback Scheduled",
    "Appointment Set",
    "Not Interested",
    "Wrong Number",
]

app = Flask(__name__)


def load_leads():
    leads = []
    with LEADS_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            row["_id"] = str(idx)
            leads.append(row)
    return leads


def load_statuses() -> Dict[str, Dict[str, Any]]:
    if not STATUS_JSON.exists():
        return {}
    try:
        with STATUS_JSON.open(encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def save_statuses(statuses: Dict[str, Dict[str, Any]]):
    temp_path = STATUS_JSON.with_suffix(".json.tmp")
    with temp_path.open("w", encoding="utf-8") as f:
        json.dump(statuses, f, indent=2)
    temp_path.replace(STATUS_JSON)


def merge_leads(leads, statuses):
    merged = []
    for lead in leads:
        status = statuses.get(lead["_id"], {})
        merged.append(
            {
                **lead,
                "status": status.get("status", "Not Called"),
                "last_contact": status.get("last_contact", ""),
                "notes": status.get("notes", ""),
            }
        )
    return merged


def compute_stats(merged):
    total = len(merged)
    calls_made = sum(1 for l in merged if l["status"] != "Not Called")
    appointments = sum(1 for l in merged if l["status"] == "Appointment Set")
    conversion = (appointments / total * 100) if total else 0
    return {
        "total": total,
        "calls_made": calls_made,
        "appointments": appointments,
        "conversion": conversion,
    }


@app.route("/")
def dashboard():
    leads = load_leads()
    statuses = load_statuses()
    merged = merge_leads(leads, statuses)
    stats = compute_stats(merged)
    return render_template(
        "index.html",
        leads=merged,
        stats=stats,
        status_options=STATUS_OPTIONS,
    )


@app.route("/update", methods=["POST"])
def update_lead():
    payload = request.get_json(force=True)
    lead_id = str(payload.get("id"))
    status = payload.get("status", "Not Called")
    notes = payload.get("notes", "")

    if status not in STATUS_OPTIONS:
        return jsonify({"ok": False, "error": "Invalid status"}), 400

    statuses = load_statuses()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    statuses[lead_id] = {
        "status": status,
        "notes": notes,
        "last_contact": now_str,
    }
    save_statuses(statuses)

    return jsonify({"ok": True, "last_contact": now_str})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081, debug=False)
