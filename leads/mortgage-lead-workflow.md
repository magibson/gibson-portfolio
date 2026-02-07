# Mortgage Protection Lead Workflow

## Overview
Generate phone-ready leads for Monmouth County homeowners with mortgage protection needs.

---

## The Pipeline

```
PROPWIRE (free) → TRACERFY ($0.02/lead) → DIAL LIST
   Names & Addresses     Phone Numbers        Ready to Call
```

---

## Step 1: Propwire Export

**Website:** propwire.com

**Filters to use:**
- Location: Monmouth County, NJ
- Home Value: $900K+
- Bedrooms: 3+
- Sale Date: Last 12 months (newer = hotter)

**Export as CSV** — you'll get: owner names, addresses, home values, purchase dates

---

## Step 2: Send to Jarvis

Upload the Propwire CSV to our chat. I'll:
1. Clean and format the data
2. Submit to Tracerfy API for phone numbers
3. Sort by "months owned" (newest buyers first)
4. Return a ready-to-dial CSV

**Turnaround:** Usually 5-10 minutes

---

## Step 3: Upload to CRM & Call

- Import the dial list into Salesforce
- Best times: Weekday evenings 5-7 PM, Saturday mornings
- Newest homeowners = most receptive (still setting up protection)

---

## Cost Breakdown

| Service | Cost |
|---------|------|
| Propwire | FREE |
| Tracerfy | $0.02/record |
| **Weekly batch (200 leads)** | **~$4** |

---

## Your Tracerfy Account

- Credits remaining: ~$16 (~800 traces)
- Hit rate: ~78% (not everyone has findable numbers)

---

\newpage

# First Test Results — January 30, 2026

## Input
- **Source:** Propwire export, Monmouth County
- **Filters:** $900K+ homes, 3+ beds, sold in last 12 months
- **Records submitted:** 235

## Output
- **Phone numbers found:** 184 (78% hit rate)
- **"Hot" leads (≤12 months owned):** 157
- **Cost:** $3.68

## Sample Lead

| Field | Value |
|-------|-------|
| Name | John Smith |
| Address | 123 Ocean Ave, Red Bank |
| Home Value | $950,000 |
| Months Owned | 3 |
| Phone | (732) 555-1234 |

## Files Delivered
- `monmouth_SORTED_leads_20260130.csv` — Final dial list
- `monmouth_HOT_leads_20260130.csv` — Filtered to newest buyers

## Talking Points Generated
- "$950K home = $760K+ mortgage to protect"
- "New homeowner (3 months) — still setting up coverage"
- "4 beds suggests family — protect their lifestyle"

---

## Ready for Next Batch?

Just send me a new Propwire export and I'll run it through.
