# NJ Business Filings Monitor

Scrapes recently-formed NJ LLCs and corporations from the NJ Division of Revenue & Enterprise Services. 
Outputs a lead list of new business owners — prime prospects for life insurance, key-person coverage, and retirement planning.

## Why this works

New business owners are underserved. They just made a major financial decision (starting a company), they have employees or partners to protect, and they're actively thinking about their financial future. Finding them **within 30 days of filing** is an edge no one else has.

## Setup

```bash
cd ~/clawd/projects/nj-biz-filings
pip3 install playwright flask --break-system-packages
python3 -m playwright install chromium
```

## Usage

### Run the scraper
```bash
python3 scraper.py                # LLCs formed in last 30 days (default)
python3 scraper.py --type CORP    # Corporations
python3 scraper.py --type ALL     # Both
python3 scraper.py --days 60      # Look back 60 days
python3 scraper.py --max 100      # Scrape more detail pages
```

### View the dashboard
```bash
python3 dashboard.py
# Opens at http://localhost:8107
```

## Data files
- `~/clawd/data/biz-filings/YYYY-MM-DD.json` — daily scrape output
- `~/clawd/data/biz-filings/master.json` — all-time deduplicated records
- `~/clawd/data/biz-filings/tracking.db` — SQLite: contacted status, notes
- `~/clawd/data/biz-filings/scraper.log` — scraper logs

## Cron (nightly 2am)
```
0 2 * * * cd ~/clawd/projects/nj-biz-filings && python3 scraper.py --type ALL >> ~/clawd/data/biz-filings/cron.log 2>&1
```

## Notes
- The NJ portal may block scraping if too many requests. Max 50 detail pages per run.
- Portal requires no auth for the public name search.
- Filter by Monmouth County in the dashboard notes field to focus on local leads.
- Pair with Tracerfy for phone number skip-tracing on the best leads.
