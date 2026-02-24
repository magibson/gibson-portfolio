#!/usr/bin/env python3
"""
Score and prioritize mortgage protection leads.
"""
import argparse
import csv
import re
from pathlib import Path
from datetime import date

BUSINESS_KEYWORDS = [
    'LLC', 'CORP', 'TRUST', 'INC', 'LTD',
    'ASSOCIATES', 'HOLDINGS', 'REALTY', 'FOUNDATION'
]

def normalize_zip(z):
    """Normalize zip to 5-digit zero-padded string."""
    if not z:
        return ''
    try:
        return str(int(float(z))).zfill(5)
    except:
        return z.strip().zfill(5)

def normalize_address(addr, city='', state='', zip_code=''):
    """Normalize address + city + state + zip for matching."""
    if not addr:
        return ''
    s = (addr + ' ' + city + ' ' + state + ' ' + normalize_zip(zip_code)).upper()
    s = re.sub(r'[.,]', '', s)
    # Normalize common street types
    s = re.sub(r'\bSTREET\b', 'ST', s)
    s = re.sub(r'\bROAD\b', 'RD', s)
    s = re.sub(r'\bAVENUE\b', 'AVE', s)
    s = re.sub(r'\bBOULEVARD\b', 'BLVD', s)
    return re.sub(r'\s+', ' ', s).strip()

def load_propwire(path):
    props = {}
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        for r in reader:
            key = normalize_address(
                r.get('Address',''),
                r.get('City',''),
                r.get('State',''),
                r.get('Zip','')
            )
            props[key] = r
    return props

def load_dialready(path):
    with open(path, newline='') as f:
        return list(csv.DictReader(f))

def is_business(name):
    if not name:
        return False
    na = name.upper()
    return any(kw in na for kw in BUSINESS_KEYWORDS)

def score_lead(prop, dial, skip_filters=False):
    name = dial.get('Name','')
    if is_business(name) and not skip_filters:
        return {'status':'SKIP','score':0}

    score = 0
    # Ownership length
    try:
        months = int(prop.get('Ownership Length (Months)',0))
    except:
        months = 0
    if months <= 6:
        score += 35
    elif months <= 12:
        score += 25
    elif months <= 24:
        score += 15
    elif months <= 48:
        score += 5

    # Owner occupied
    oo = prop.get('Owner Occupied','')
    # Propwire stores as '1' for yes
    if oo in ('YES', '1', 'yes', 'y', 'Y', 'true', 'True', '1'):
        score += 15

    # Bedrooms
    try:
        beds = int(float(prop.get('Bedrooms',0)))
    except:
        beds = 0
    if beds >= 3:
        score += 10
    elif beds == 2:
        score += 5

    # Living square feet
    try:
        sqft = int(float(prop.get('Living Square Feet',0)))
    except:
        sqft = 0
    if sqft >= 2000:
        score += 10
    elif sqft >= 1500:
        score += 5

    # Owner type
    if prop.get('Owner Type','').strip().upper() == 'INDIVIDUAL':
        score += 10

    # Phone count
    p1, p2 = dial.get('Phone 1','').strip(), dial.get('Phone 2','').strip()
    if p1 and p2:
        score += 10
    elif p1:
        score += 5

    # Email
    if dial.get('Email','').strip():
        score += 5

    # Second owner
    if prop.get('Owner 2 First Name','').strip():
        score += 5

    return {'status':'OK','score':score,'months':months,'beds':beds,'sqft':sqft}

def make_blurb(months, beds, city):
    if months == 0:
        own = "Recent buyer (ownership date not available)."
    elif months < 12:
        own = f"New homeowner — moved in {months} months ago."
    else:
        yrs = months // 12
        rem = months % 12
        if rem > 0:
            own = f"Homeowner for {yrs}yr {rem}mo."
        else:
            own = f"Homeowner for {yrs} year{'s' if yrs != 1 else ''}."
    bed_str = f"{beds}-bed " if beds > 0 else ""
    city_str = city.title() if city else "the area"
    return f"{own} {bed_str}home in {city_str} — mortgage protection opportunity."

def main():
    parser = argparse.ArgumentParser(description='Score mortgage protection leads')
    parser.add_argument('--propwire',
        default='~/clawd/leads/propwire_leads_2026-02-23.csv')
    parser.add_argument('--dialready',
        default='~/clawd/leads/dial_ready_2026-02-23.csv')
    parser.add_argument('--output',
        default=f"~/clawd/leads/priority_dial_{date.today().isoformat()}.csv")
    parser.add_argument('--top', type=int, default=10)
    parser.add_argument('--skip-filters', action='store_true')
    args = parser.parse_args()

    propwire_path = Path(args.propwire).expanduser()
    dial_path     = Path(args.dialready).expanduser()
    out_path      = Path(args.output).expanduser()

    props = load_propwire(propwire_path)
    dials = load_dialready(dial_path)

    results = []
    filtered = 0
    matched = 0
    for d in dials:
        key  = normalize_address(
            d.get('Property Address',''),
            d.get('City',''),
            d.get('State',''),
            d.get('Zip','')
        )
        prop = props.get(key, {})
        if prop:
            matched += 1
        res  = score_lead(prop, d, args.skip_filters)
        if res['status'] == 'SKIP':
            filtered += 1

        entry = {
            'Name': d.get('Name',''),
            'Phone 1': d.get('Phone 1',''),
            'Phone 2': d.get('Phone 2',''),
            'Phone 3': d.get('Phone 3',''),
            'Property Address': d.get('Property Address',''),
            'City': d.get('City',''),
            'Bedrooms': res.get('beds',''),
            'Sq Ft': res.get('sqft',''),
            'Ownership Months': res.get('months',''),
            'Owner Occupied': prop.get('Owner Occupied',''),
            'Email': d.get('Email',''),
            'Score': res.get('score',0),
            'Status': res.get('status','OK'),
        }
        entry['Call Blurb'] = make_blurb(res['months'], res['beds'], entry['City']) \
                              if res['status']=='OK' else ''
        results.append(entry)

    # Sort scored leads descending
    scored = [r for r in results if r['Status']=='OK']
    scored.sort(key=lambda x: x['Score'], reverse=True)

    # Write CSV
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', newline='') as f:
        fieldnames = [
            'Rank','Score','Name','Phone 1','Phone 2','Phone 3',
            'Property Address','City','Bedrooms','Sq Ft',
            'Ownership Months','Owner Occupied','Email','Status','Call Blurb'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for idx, row in enumerate(scored, 1):
            row['Rank'] = idx  # add Rank to the dict in-place
            writer.writerow(row)

    # Console summary
    total = len(dials)
    print(f"\n{'='*60}")
    print(f"  LEAD SCORER RESULTS — {date.today()}")
    print(f"{'='*60}")
    print(f"  Total leads loaded:    {total}")
    print(f"  Propwire matches:      {matched} (property data enriched)")
    print(f"  Business entities:     {filtered} (filtered out)")
    print(f"  Scoreable leads:       {len(scored)}")
    print(f"  Output:                {out_path}")
    print(f"{'='*60}")
    print(f"\n  TOP {min(args.top, len(scored))} LEADS TO CALL FIRST:\n")
    for r in scored[:args.top]:
        phones = [p for p in [r['Phone 1'], r['Phone 2'], r['Phone 3']] if p]
        phone_str = phones[0] if phones else 'No phone'
        print(f"  #{r['Rank']:2d} [{r['Score']:3d}] {r['Name']}")
        print(f"       📍 {r['Property Address']}, {r['City']}")
        print(f"       📞 {phone_str}")
        print(f"       💬 {r['Call Blurb']}")
        print()

if __name__ == '__main__':
    main()
