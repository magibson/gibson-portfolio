# Lead Scorer — Build Spec

Build a Python script at `~/clawd/scripts/lead_scorer.py` that scores and prioritizes mortgage protection leads.

## What it does

1. **Loads** the Propwire CSV: `~/clawd/leads/propwire_leads_2026-02-23.csv`
   - Key columns: Address, City, State, Zip, Bedrooms, Bathrooms, Living Square Feet, Year Built, Ownership Length (Months), Owner Type, Owner Occupied, Owner 1 First Name, Owner 1 Last Name, Owner 2 First Name, Owner 2 Last Name

2. **Loads** the dial-ready CSV: `~/clawd/leads/dial_ready_2026-02-23.csv`
   - Key columns: Name, Phone 1, Phone 2, Phone 3, Property Address, City, State, Zip, Email

3. **Joins** them by matching property address (fuzzy match ok — normalize to uppercase, strip punctuation)

4. **Scores** each lead 1-100 based on these weighted factors:
   - **Ownership Length (Months)**: 0-6 months = +35 pts (brand new homeowner — hottest lead), 7-12 = +25 pts, 13-24 = +15 pts, 25-48 = +5 pts, 48+ = 0 pts
   - **Owner Occupied**: Yes = +15 pts (they live there, they have a mortgage to protect)
   - **Bedrooms**: 3+ beds = +10 pts (family, more to protect), 2 beds = +5 pts
   - **Living Sq Ft**: 2000+ sqft = +10 pts (bigger home = bigger mortgage), 1500+ = +5 pts
   - **Owner Type**: INDIVIDUAL = +10 pts (LLC/Corp/Trust = skip or deprioritize)
   - **Phone Count**: Has Phone 1 AND Phone 2 = +10 pts (more ways to reach them), just Phone 1 = +5 pts
   - **Has email**: +5 pts
   - **Two named owners** (Owner 2 exists): +5 pts (couple = higher protection need)

5. **Filters out** leads where Name contains: LLC, Corp, Trust, Inc, Ltd, Associates, Holdings, Realty, Foundation (business entities — not our target market). Mark them "SKIP" in output.

6. **Generates a call blurb** for each lead (1-2 sentences explaining why they're worth calling):
   - Ownership length: "Recent buyer (3 months ago)" or "New homeowner (1 year)"
   - Property size/type: "4BR/3BA in Manalapan"
   - Priority reason: "New family home, high protection need"
   - Example: "New homeowner — moved in 3 months ago. 4-bed family home in Manalapan, likely has significant mortgage to protect."

7. **Outputs** two things:
   a. `~/clawd/leads/priority_dial_2026-02-24.csv` — sorted by score descending, columns: Rank, Score, Name, Phone 1, Phone 2, Phone 3, Property Address, City, Bedrooms, Sq Ft, Ownership Months, Owner Occupied, Email, Call Blurb
   b. Console summary: total leads, leads scored, leads filtered, top 10 with scores

8. **Command line args**:
   - `--propwire PATH` — override propwire CSV path
   - `--dialready PATH` — override dial-ready CSV path  
   - `--output PATH` — override output path
   - `--top N` — show top N in console (default 10)
   - `--skip-filters` — include business entities too

## Python requirements
- Standard library only (csv, re, argparse, pathlib, datetime, sys)
- No external dependencies needed
- Works on Python 3.8+

## Important
- Handle missing/blank values gracefully (not every field will be filled)
- Normalize addresses for matching: uppercase, remove periods and commas, normalize "ST" vs "STREET" etc
- Print clear output so Matt can see at a glance what's hot
- Add `if __name__ == "__main__"` guard
