from flask import Flask, render_template
import csv
import re
from pathlib import Path

app = Flask(__name__)

CSV_PATH = Path(__file__).parent / "leads.csv"


def _to_int(value, default=0):
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value)
    digits = re.sub(r"[^0-9]", "", s)
    return int(digits) if digits else default


def _format_money(value):
    return f"${value:,.0f}"


def _mortgage_estimate(value):
    # Rough estimate: assume 75-85% of home value is financed for target messaging.
    return int(value * 0.8)


def _months_owned_point(months):
    if months <= 6:
        return "New homeowner — likely still setting up protection and budgeting."
    if months <= 24:
        return "Recent purchase — protection is still top of mind."
    if months <= 60:
        return "Established owner — good time to review coverage gaps."
    return "Long-term owner — may have never revisited coverage since purchase."


def _beds_point(beds):
    if beds >= 4:
        return "4+ beds suggests a family — emphasize protecting their lifestyle."
    if beds == 3:
        return "3 beds suggests a growing family — focus on stability and peace of mind."
    if beds == 2:
        return "2 beds — talk about protecting the home and future plans."
    return "Smaller home — focus on affordability and keeping payments covered."


def _opening_line(name, city):
    first = name.split()[0] if name else "there"
    return f"Hi {first}, this is a quick call about protecting your home in {city}. Did I catch you at a bad time?"


def load_leads():
    leads = []
    if not CSV_PATH.exists():
        return leads
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            value = _to_int(row.get("Est_Value"))
            months = _to_int(row.get("Months_Owned"))
            beds = _to_int(row.get("Beds"))
            baths = row.get("Baths", "")
            sqft = _to_int(row.get("SqFt"))
            city = (row.get("City") or "").strip()

            mortgage_est = _mortgage_estimate(value) if value else 0
            talking_points = []
            if value:
                talking_points.append(
                    f"{_format_money(value)} home ≈ {_format_money(mortgage_est)}+ mortgage to protect."
                )
            if months:
                talking_points.append(_months_owned_point(months))
            if beds:
                talking_points.append(_beds_point(beds))

            lead = {
                "name": (row.get("Name") or "").strip(),
                "address": (row.get("Address") or "").strip(),
                "city": city,
                "primary_phone": (row.get("Primary_Phone") or "").strip(),
                "phone_type": (row.get("Phone_Type") or "").strip(),
                "alt_phone": (row.get("Alt_Phone") or "").strip(),
                "email": (row.get("Email") or "").strip(),
                "value": value,
                "months": months,
                "beds": beds,
                "baths": (baths or "").strip(),
                "sqft": sqft,
                "talking_points": talking_points,
                "opening_line": _opening_line((row.get("Name") or "").strip(), city or "your area"),
            }
            leads.append(lead)
    return leads


@app.route("/")
def index():
    leads = load_leads()
    cities = sorted({l["city"] for l in leads if l["city"]})
    return render_template("index.html", leads=leads, cities=cities)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8082, debug=False)
