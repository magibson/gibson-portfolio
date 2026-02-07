# 🏠 Apartment Finder - Shrewsbury NJ Area

A tool to monitor and aggregate apartment listings in the Shrewsbury, NJ area for Matt's 2027 housing goal.

## 📍 Search Criteria

- **Locations:** Shrewsbury, Red Bank, Little Silver, Tinton Falls, Eatontown, Fair Haven, Rumson
- **Size:** Studio or 1 bedroom
- **Budget:** $1,500 - $2,800/month (based on market research showing 1BR averages $2,400-3,000 in the area)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd /home/clawd/clawd/projects/apartment-finder
pip install -r requirements.txt
```

### 2. Initialize Database

```bash
cd scripts
python database.py
```

### 3. Run Scrapers

```bash
# Run all scrapers
python scrape.py

# Or run individual scrapers
python scrape.py craigslist
python scrape.py apartments_com
python scrape.py zillow
```

### 4. View Dashboard

Open `static/index.html` in a browser, or serve it:

```bash
cd static
python -m http.server 8080
# Then visit http://localhost:8080
```

## 📁 Project Structure

```
apartment-finder/
├── data/
│   ├── apartments.db      # SQLite database
│   └── listings.json      # Exported JSON for dashboard
├── scripts/
│   ├── config.py          # Search criteria & settings
│   ├── database.py        # Database operations
│   ├── scrape.py          # Main scraper runner
│   └── scrapers/
│       ├── base.py        # Base scraper class
│       ├── craigslist.py  # Craigslist scraper
│       ├── apartments_com.py  # Apartments.com scraper
│       └── zillow.py      # Zillow scraper
├── static/
│   ├── index.html         # Dashboard UI
│   ├── styles.css         # JARVIS-style dark theme
│   └── app.js             # Dashboard JavaScript
├── requirements.txt
└── README.md
```

## 🔧 Configuration

Edit `scripts/config.py` to adjust:

- `LOCATIONS` - Towns to search
- `MIN_PRICE` / `MAX_PRICE` - Budget range
- `MIN_BEDS` / `MAX_BEDS` - Bedroom requirements
- `NEW_LISTING_HOURS` - How long listings show "NEW" badge
- `UTILITY_ESTIMATES` - For true cost calculations

## 💰 True Cost Calculator

The dashboard estimates total monthly cost including:

| Expense | Studio | 1 BR |
|---------|--------|------|
| Electric | $80 | $100 |
| Gas | $40 | $50 |
| Water | $30 | $35 |
| Internet | $70 | $70 |
| Renter's Insurance | $20 | $20 |
| **Utilities Total** | **$240** | **$275** |

So a $2,500 1BR = ~$2,775 true monthly cost.

## 🗺️ Dashboard Features

- **List View** - Detailed listing cards
- **Grid View** - Compact visual grid
- **Map View** - Leaflet map with markers (for listings with coordinates)
- **Filters** - Price, beds, location, source
- **Sort** - Newest, price, true cost
- **Favorites** - Save listings locally (localStorage)
- **NEW Badge** - Highlights listings seen in last 48 hours
- **True Cost** - Shows estimated total monthly cost
- **Export** - CSV export, favorites export

## 🕐 Automation (Cron)

To run scrapers automatically:

```bash
# Edit crontab
crontab -e

# Add line to run every 6 hours
0 */6 * * * cd /home/clawd/clawd/projects/apartment-finder/scripts && python scrape.py >> ../data/scrape.log 2>&1
```

## ⚠️ Scraper Notes

**Current Status:** Major apartment sites (Zillow, Apartments.com) actively block direct HTTP requests (403 Forbidden). The scrapers are structured to work but need enhancement.

**Options for real data:**
1. **Browser automation** - Use Playwright/Selenium to render pages
2. **Proxy rotation** - Use residential proxies to avoid blocks
3. **RSS feeds** - Some sites offer RSS (Craigslist used to)
4. **Manual monitoring** - Check sites directly, add listings manually

**For now:** Sample data is provided in `data/listings.json` to demonstrate the dashboard.

Rate limiting is built in (1-3 second delays between requests).

## 📊 Database Schema

### listings
- `id` - Primary key
- `source` - Which site (craigslist, apartments_com, zillow)
- `source_id` - ID from original site
- `url` - Link to original listing
- `title`, `address`, `city`, `state`, `zip_code`
- `price`, `beds`, `baths`, `sqft`
- `description`, `amenities`, `images`
- `lat`, `lng` - Coordinates
- `first_seen` - When we first found it
- `last_seen` - Last time it appeared in scrape
- `is_active` - Still listed or not

### price_history
Tracks price changes over time.

### favorites
Stores favorite listings (synced from dashboard).

### scrape_log
Log of each scrape run with stats.

## 🛠️ Development

### Adding a New Scraper

1. Create `scripts/scrapers/newsource.py`
2. Extend `BaseScraper` class
3. Implement `scrape()` method
4. Add to `scrapers/__init__.py`
5. Import in `scrape.py`

### Updating Criteria

Edit `scripts/config.py` then re-run scrapers.

## 📝 Market Research (2025)

Average rents in the area:
- **Shrewsbury:** ~$2,467 (1BR), $3,595 overall
- **Red Bank:** ~$2,464 average, $2,309-3,295 range
- **Studios:** ~$2,300

The area is expensive - targeting the lower end of market for "affordable but nice."

---

Built for Matt's 2027 goal 🏡
