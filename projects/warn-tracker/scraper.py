#!/usr/bin/env python3
"""
WARN Act Tracker Scraper for NJ and PA
Scrapes official labor department pages and saves to JSON for the dashboard.
Run daily via cron: 0 6 * * * /usr/bin/python3 /path/to/scraper.py
"""

import json
import os
import re
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
import requests
from bs4 import BeautifulSoup

# Optional PDF support
try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

# Configuration
SCRIPT_DIR = Path(__file__).parent
DATA_FILE = SCRIPT_DIR / "data.json"
ALERTS_FILE = SCRIPT_DIR / "alerts.json"
BIG_LAYOFF_THRESHOLD = 100

# Load .env file if it exists
ENV_FILE = SCRIPT_DIR / ".env"
if ENV_FILE.exists():
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ[key.strip()] = val.strip()

# Brave Search API (optional - set BRAVE_API_KEY env var or in .env)
BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "")

# User agent for requests
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def fetch_news_for_company(company: str, state: str) -> list:
    """Fetch news articles for a company using Brave Search API."""
    articles = []
    
    if not BRAVE_API_KEY:
        return articles
    
    try:
        query = f"{company} layoff OR layoffs OR closing"
        url = "https://api.search.brave.com/res/v1/news/search"
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": BRAVE_API_KEY
        }
        params = {
            "q": query,
            "count": 5,
            "freshness": "pm"  # Past month
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            
            for r in results[:5]:
                articles.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "source": r.get("meta_url", {}).get("hostname", ""),
                    "date": r.get("age", "")
                })
    except Exception as e:
        print(f"    Error fetching news for {company}: {e}")
    
    return articles


def generate_id(company: str, state: str, date: str, city: str = "") -> str:
    """Generate a unique ID for a WARN notice."""
    raw = f"{company}|{state}|{date}|{city}".lower().strip()
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def load_existing_data() -> dict:
    """Load existing data from JSON file."""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"notices": [], "last_updated": None, "metadata": {}}


def save_data(data: dict) -> None:
    """Save data to JSON file."""
    data["last_updated"] = datetime.now().isoformat()
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def save_alerts(alerts: list) -> None:
    """Save new big layoff alerts to alerts.json."""
    alert_data = {
        "generated_at": datetime.now().isoformat(),
        "alerts": alerts
    }
    with open(ALERTS_FILE, "w") as f:
        json.dump(alert_data, f, indent=2)


def parse_date(date_str: str) -> str:
    """Try to parse various date formats into YYYY-MM-DD."""
    if not date_str:
        return ""
    
    date_str = date_str.strip()
    
    # Handle "beginning X; ending Y" format - take the first date
    if 'beginning' in date_str.lower():
        match = re.search(r'(\d{1,2}/\d{1,2}/\d{2,4})', date_str)
        if match:
            date_str = match.group(1)
    
    # Extract just the date portion
    date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', date_str)
    if date_match:
        date_str = date_match.group(1)
    
    formats = ["%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%m-%d-%Y", "%m-%d-%y"]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    return ""


def parse_int(val: str) -> int:
    """Parse a string to int, handling commas and other chars."""
    if not val:
        return 0
    val = str(val).strip()
    if 'unknown' in val.lower() or 'tbd' in val.lower():
        return 0
    cleaned = re.sub(r'[^\d]', '', val)
    try:
        result = int(cleaned) if cleaned else 0
        # Sanity check
        if result > 50000:
            return 0
        return result
    except ValueError:
        return 0


def extract_city(text: str) -> str:
    """Extract city name from PA address text."""
    # Try to find: City, PA 12345
    match = re.search(r'([A-Za-z][A-Za-z\s\-]+),?\s*PA\s*\d{5}', text)
    if match:
        city = match.group(1).strip()
        # Clean up - get last word before PA if it looks like a city
        parts = city.split(',')
        city = parts[-1].strip() if parts else city
        # Remove street suffixes
        city = re.sub(r'\b(Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Boulevard|Blvd|Way|Lane|Ln)\s*$', '', city, flags=re.I).strip()
        if len(city) > 2:
            return city
    return ""


def scrape_pa_warn() -> list:
    """Scrape Pennsylvania WARN notices from official page."""
    notices = []
    url = "https://www.pa.gov/agencies/dli/programs-services/workforce-development-home/warn-requirements/warn-notices.html"
    
    try:
        print(f"Fetching PA WARN page: {url}")
        response = requests.get(url, headers=HEADERS, timeout=30)
        
        if response.status_code != 200:
            print(f"  Could not fetch {url}: {response.status_code}")
            return notices
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all accordion items - each contains a WARN notice
        items = soup.find_all('div', class_='cmp-accordion__item')
        print(f"  Found {len(items)} accordion items")
        
        seen_ids = set()  # Dedupe within single scrape
        
        for item in items:
            h3 = item.find('h3')
            if not h3:
                continue
            
            company = h3.get_text(strip=True)
            if not company or re.match(r'^20\d{2}$', company):  # Skip year headers
                continue
            
            text = item.get_text()
            
            # Extract affected count
            affected_match = re.search(r'#?\s*AFFECTED:?\s*(\d+)', text, re.I)
            affected = int(affected_match.group(1)) if affected_match else 0
            
            if affected <= 0 or affected > 50000:
                continue
            
            # Extract effective date
            date_match = re.search(r'EFFECTIVE DATE:?\s*([^\n]+)', text, re.I)
            date_str = date_match.group(1).strip() if date_match else ""
            date = parse_date(date_str)
            
            # Extract county
            county_match = re.search(r'COUNTI?E?S?:?\s*([A-Za-z\s]+?)(?:\n|#|AFFECTED)', text, re.I)
            county = county_match.group(1).strip() if county_match else ""
            
            # Extract type
            type_match = re.search(r'CLOSURE OR LAYOFF:?\s*(\w+)', text, re.I)
            notice_type = "Closing" if type_match and 'clos' in type_match.group(1).lower() else "Layoff"
            
            # Extract city from address
            city = extract_city(text) or county
            
            notice_id = generate_id(company, "PA", date, city)
            
            # Skip duplicates
            if notice_id in seen_ids:
                continue
            seen_ids.add(notice_id)
            
            notices.append({
                "id": notice_id,
                "company": company,
                "state": "PA",
                "city": city,
                "county": county,
                "affected": affected,
                "date": date,
                "type": notice_type,
                "source": url
            })
        
        print(f"  Parsed {len(notices)} PA notices")
        
    except Exception as e:
        print(f"  Error scraping PA: {e}")
        import traceback
        traceback.print_exc()
    
    return notices


def scrape_nj_warn() -> list:
    """Scrape New Jersey WARN notices from web and PDFs."""
    notices = []
    url = "https://www.nj.gov/labor/employer-services/warn/"
    
    try:
        print(f"Fetching NJ HTML: {url}")
        response = requests.get(url, headers=HEADERS, timeout=30)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for tables on the page
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows[1:]:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 4:
                        company = cells[0].get_text(strip=True)
                        city = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                        affected = parse_int(cells[2].get_text(strip=True)) if len(cells) > 2 else 0
                        date = parse_date(cells[3].get_text(strip=True)) if len(cells) > 3 else ""
                        notice_type = cells[4].get_text(strip=True) if len(cells) > 4 else "Layoff"
                        
                        if company and affected > 0:
                            notices.append({
                                "id": generate_id(company, "NJ", date, city),
                                "company": company,
                                "state": "NJ",
                                "city": city,
                                "affected": affected,
                                "date": date,
                                "type": "Closing" if 'clos' in notice_type.lower() else "Layoff",
                                "source": url
                            })
            
            # Try PDFs if available
            if HAS_PYPDF2:
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link['href']
                    if '.pdf' in href.lower() and 'warn' in href.lower():
                        if not href.startswith('http'):
                            href = 'https://www.nj.gov' + href
                        pdf_notices = scrape_nj_pdf(href)
                        notices.extend(pdf_notices)
        
        print(f"  Found {len(notices)} NJ notices")
        
    except Exception as e:
        print(f"  Error scraping NJ: {e}")
    
    return notices


def scrape_nj_pdf(pdf_url: str) -> list:
    """Parse NJ WARN PDF."""
    notices = []
    
    if not HAS_PYPDF2:
        return notices
    
    try:
        from io import BytesIO
        
        print(f"    Fetching PDF: {pdf_url}")
        response = requests.get(pdf_url, headers=HEADERS, timeout=30)
        
        if response.status_code != 200:
            return notices
        
        pdf_reader = PyPDF2.PdfReader(BytesIO(response.content))
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 10:
                continue
            
            if any(x in line.lower() for x in ['warn notice', 'company name', 'effective date', 'archive']):
                continue
            
            parts = re.split(r'\s{2,}|\t', line)
            if len(parts) >= 4:
                company = parts[0].strip()
                affected = 0
                date = ""
                city = ""
                
                for part in parts[1:]:
                    part = part.strip()
                    if re.match(r'^\d+$', part) and not affected:
                        affected = int(part)
                    elif re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', part):
                        date = parse_date(part)
                    elif len(part) > 2 and not re.search(r'\d', part):
                        if not city:
                            city = part
                
                if company and 10 < affected < 10000:
                    notices.append({
                        "id": generate_id(company, "NJ", date, city),
                        "company": company,
                        "state": "NJ", 
                        "city": city,
                        "affected": affected,
                        "date": date,
                        "type": "Layoff",
                        "source": pdf_url
                    })
        
        print(f"      Parsed {len(notices)} from PDF")
        
    except Exception as e:
        print(f"      Error parsing PDF: {e}")
    
    return notices


def merge_notices(existing: list, new: list) -> tuple:
    """Merge new notices with existing ones. Returns (merged, truly_new)."""
    existing_ids = {n.get("id") for n in existing}
    existing_by_id = {n.get("id"): n for n in existing}
    
    new_notices = []
    now = datetime.now().isoformat()
    
    for notice in new:
        notice_id = notice.get("id")
        
        if notice_id not in existing_ids:
            notice["first_seen"] = now
            notice["is_new"] = True
            new_notices.append(notice)
            existing_by_id[notice_id] = notice
        else:
            old = existing_by_id[notice_id]
            notice["first_seen"] = old.get("first_seen", now)
            try:
                first_seen = datetime.fromisoformat(notice["first_seen"])
                notice["is_new"] = (datetime.now() - first_seen) < timedelta(hours=24)
            except:
                notice["is_new"] = False
            existing_by_id[notice_id] = notice
    
    return list(existing_by_id.values()), new_notices


def check_big_layoffs(notices: list) -> list:
    """Check for big layoffs (100+ employees) that are new."""
    alerts = []
    
    for notice in notices:
        if notice.get("is_new") and notice.get("affected", 0) >= BIG_LAYOFF_THRESHOLD:
            alerts.append({
                "company": notice.get("company"),
                "state": notice.get("state"),
                "city": notice.get("city"),
                "affected": notice.get("affected"),
                "date": notice.get("date"),
                "type": notice.get("type"),
                "first_seen": notice.get("first_seen")
            })
    
    return alerts


def main():
    """Main scraper function."""
    print(f"=== WARN Act Scraper - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    
    data = load_existing_data()
    existing_notices = data.get("notices", [])
    print(f"Loaded {len(existing_notices)} existing notices")
    
    all_new = []
    
    pa_notices = scrape_pa_warn()
    all_new.extend(pa_notices)
    
    nj_notices = scrape_nj_warn()
    all_new.extend(nj_notices)
    
    print(f"Scraped {len(all_new)} total notices ({len(nj_notices)} NJ, {len(pa_notices)} PA)")
    
    if len(all_new) == 0:
        print("Warning: No new data scraped. Keeping existing data.")
        now = datetime.now()
        for notice in existing_notices:
            try:
                first_seen = datetime.fromisoformat(notice.get("first_seen", now.isoformat()))
                notice["is_new"] = (now - first_seen) < timedelta(hours=24)
            except:
                notice["is_new"] = False
        data["notices"] = existing_notices
        save_data(data)
        save_alerts([])
        return
    
    merged, truly_new = merge_notices(existing_notices, all_new)
    print(f"After merge: {len(merged)} total notices, {len(truly_new)} brand new")
    
    # Fetch news for big layoffs (100+ employees)
    if BRAVE_API_KEY:
        print("Fetching news articles for big layoffs...")
        big_layoffs = [n for n in merged if n.get("affected", 0) >= BIG_LAYOFF_THRESHOLD]
        for i, notice in enumerate(big_layoffs[:20]):  # Limit to 20 to avoid rate limits
            if not notice.get("news"):  # Only fetch if we don't have news already
                company = notice.get("company", "")
                state = notice.get("state", "")
                print(f"  [{i+1}/{min(len(big_layoffs), 20)}] Fetching news for {company}...")
                articles = fetch_news_for_company(company, state)
                notice["news"] = articles
                if articles:
                    print(f"    Found {len(articles)} articles")
    else:
        print("Skipping news fetch (BRAVE_API_KEY not set)")
    
    alerts = check_big_layoffs(truly_new)
    if alerts:
        print(f"🚨 {len(alerts)} new BIG layoffs (100+ employees):")
        for a in alerts[:10]:
            print(f"   - {a['company']} ({a['state']}): {a['affected']} employees")
        if len(alerts) > 10:
            print(f"   ... and {len(alerts) - 10} more")
        save_alerts(alerts)
    else:
        save_alerts([])
    
    data["notices"] = merged
    data["metadata"] = {
        "nj_count": len([n for n in merged if n.get("state") == "NJ"]),
        "pa_count": len([n for n in merged if n.get("state") == "PA"]),
        "total_affected": sum(n.get("affected", 0) for n in merged),
        "new_count": len(truly_new)
    }
    save_data(data)
    
    print(f"✅ Saved to {DATA_FILE}")
    print(f"✅ Alerts saved to {ALERTS_FILE}")


if __name__ == "__main__":
    main()
