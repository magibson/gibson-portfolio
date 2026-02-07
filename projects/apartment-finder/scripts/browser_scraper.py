#!/usr/bin/env python3
"""
Apartment Scraper with Browser Automation (Playwright)
Secure, local-only scraping - no external services, no data exfiltration.

Requires system deps (one-time install with sudo):
  sudo apt install -y libatk1.0-0 libatk-bridge2.0-0 libcups2 libxcomposite1 \
    libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2

Then run: python3 browser_scraper.py
"""

import json
import sqlite3
import hashlib
import time
import re
import os
from datetime import datetime
from pathlib import Path

# Configuration
CONFIG = {
    "search_areas": [
        {"name": "Shrewsbury", "zip": "07702"},
        {"name": "Red Bank", "zip": "07701"},
        {"name": "Little Silver", "zip": "07739"},
        {"name": "Tinton Falls", "zip": "07724"},
        {"name": "Eatontown", "zip": "07724"},
    ],
    "max_bedrooms": 1,
    "min_price": 0,  # No minimum - show everything affordable
    "max_price": 2800,
    "search_radius_miles": 10,
}

DB_PATH = Path(__file__).parent.parent / "data" / "apartments.db"


def init_db():
    """Initialize SQLite database"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            id TEXT PRIMARY KEY,
            source TEXT,
            title TEXT,
            price INTEGER,
            bedrooms TEXT,
            bathrooms TEXT,
            sqft INTEGER,
            address TEXT,
            city TEXT,
            state TEXT,
            zip TEXT,
            url TEXT,
            image_url TEXT,
            description TEXT,
            amenities TEXT,
            first_seen TEXT,
            last_seen TEXT,
            is_new INTEGER DEFAULT 1
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            listing_id TEXT,
            price INTEGER,
            seen_at TEXT,
            FOREIGN KEY (listing_id) REFERENCES listings(id)
        )
    """)
    conn.commit()
    return conn


def generate_listing_id(source, url):
    """Generate unique ID for a listing"""
    return hashlib.md5(f"{source}:{url}".encode()).hexdigest()[:16]


def parse_price(price_str):
    """Extract numeric price from string like '$2,100/mo'"""
    if not price_str:
        return None
    match = re.search(r'[\$]?([\d,]+)', price_str.replace(',', ''))
    return int(match.group(1)) if match else None


def save_listing(conn, listing):
    """Save or update a listing in the database"""
    c = conn.cursor()
    now = datetime.now().isoformat()
    
    # Check if exists
    c.execute("SELECT id, price FROM listings WHERE id = ?", (listing['id'],))
    existing = c.fetchone()
    
    if existing:
        # Update last_seen, check for price change
        c.execute("UPDATE listings SET last_seen = ?, is_new = 0 WHERE id = ?", 
                  (now, listing['id']))
        
        # Track price history if changed
        if existing[1] != listing.get('price'):
            c.execute("INSERT INTO price_history (listing_id, price, seen_at) VALUES (?, ?, ?)",
                      (listing['id'], listing.get('price'), now))
    else:
        # Insert new listing
        c.execute("""
            INSERT INTO listings (id, source, title, price, bedrooms, bathrooms, sqft,
                address, city, state, zip, url, image_url, description, amenities,
                first_seen, last_seen, is_new)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (
            listing['id'], listing.get('source'), listing.get('title'),
            listing.get('price'), listing.get('bedrooms'), listing.get('bathrooms'),
            listing.get('sqft'), listing.get('address'), listing.get('city'),
            listing.get('state'), listing.get('zip'), listing.get('url'),
            listing.get('image_url'), listing.get('description'),
            json.dumps(listing.get('amenities', [])), now, now
        ))
        
        # Initial price history
        c.execute("INSERT INTO price_history (listing_id, price, seen_at) VALUES (?, ?, ?)",
                  (listing['id'], listing.get('price'), now))
    
    conn.commit()


def scrape_apartments_com(page, zip_code, max_beds=1):
    """Scrape Apartments.com for a given zip code"""
    listings = []
    
    url = f"https://www.apartments.com/{zip_code}/?bb=gyv8z8y9mNvwlhtrM"
    if max_beds == 0:
        url = f"https://www.apartments.com/apartments/{zip_code}/?bb=gyv8z8y9mNvwlhtrM"
    elif max_beds == 1:
        url = f"https://www.apartments.com/1-bedrooms/{zip_code}/"
    
    print(f"  Fetching: {url}")
    
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        time.sleep(2)  # Let dynamic content load
        
        # Get all listing cards
        cards = page.query_selector_all("article.placard")
        print(f"  Found {len(cards)} listings")
        
        for card in cards:
            try:
                listing = {"source": "apartments.com"}
                
                # Title/Property name
                title_el = card.query_selector(".property-title")
                listing['title'] = title_el.inner_text().strip() if title_el else None
                
                # Price
                price_el = card.query_selector(".property-pricing")
                price_text = price_el.inner_text() if price_el else ""
                listing['price'] = parse_price(price_text)
                
                # Address
                addr_el = card.query_selector(".property-address")
                listing['address'] = addr_el.inner_text().strip() if addr_el else None
                
                # URL
                link_el = card.query_selector("a.property-link")
                listing['url'] = link_el.get_attribute("href") if link_el else None
                
                # Beds/Baths
                beds_el = card.query_selector(".property-beds")
                if beds_el:
                    beds_text = beds_el.inner_text()
                    bed_match = re.search(r'(\d+|Studio)', beds_text, re.I)
                    listing['bedrooms'] = bed_match.group(1) if bed_match else None
                
                # Image
                img_el = card.query_selector("img")
                listing['image_url'] = img_el.get_attribute("src") if img_el else None
                
                # Generate ID
                if listing['url']:
                    listing['id'] = generate_listing_id("apartments.com", listing['url'])
                    listings.append(listing)
                    
            except Exception as e:
                print(f"  Error parsing card: {e}")
                continue
                
    except Exception as e:
        print(f"  Error fetching apartments.com: {e}")
    
    return listings


def scrape_zillow(page, zip_code, max_beds=1):
    """Scrape Zillow rentals for a given zip code"""
    listings = []
    
    beds_param = "0-1" if max_beds <= 1 else f"0-{max_beds}"
    url = f"https://www.zillow.com/homes/for_rent/{zip_code}_rb/?searchQueryState=%7B%22pagination%22%3A%7B%7D%2C%22usersSearchTerm%22%3A%22{zip_code}%22%2C%22filterState%22%3A%7B%22beds%22%3A%7B%22max%22%3A{max_beds}%7D%2C%22fr%22%3A%7B%22value%22%3Atrue%7D%2C%22fsba%22%3A%7B%22value%22%3Afalse%7D%2C%22fsbo%22%3A%7B%22value%22%3Afalse%7D%2C%22nc%22%3A%7B%22value%22%3Afalse%7D%2C%22cmsn%22%3A%7B%22value%22%3Afalse%7D%2C%22auc%22%3A%7B%22value%22%3Afalse%7D%2C%22fore%22%3A%7B%22value%22%3Afalse%7D%7D%7D"
    
    print(f"  Fetching Zillow: {zip_code}")
    
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        time.sleep(3)
        
        # Zillow stores data in a script tag
        html = page.content()
        
        # Look for the preloaded state with listings
        match = re.search(r'"listResults":\s*(\[.*?\])(?=,"mapResults")', html)
        if match:
            try:
                results = json.loads(match.group(1))
                print(f"  Found {len(results)} Zillow listings")
                
                for item in results:
                    listing = {"source": "zillow"}
                    listing['title'] = item.get('address') or item.get('buildingName')
                    listing['price'] = item.get('price')
                    listing['address'] = item.get('address')
                    listing['url'] = "https://www.zillow.com" + item.get('detailUrl', '')
                    listing['bedrooms'] = str(item.get('beds', ''))
                    listing['bathrooms'] = str(item.get('baths', ''))
                    listing['sqft'] = item.get('area')
                    listing['image_url'] = item.get('imgSrc')
                    listing['id'] = generate_listing_id("zillow", listing['url'])
                    listings.append(listing)
            except json.JSONDecodeError:
                print("  Failed to parse Zillow JSON")
        else:
            # Try alternative selectors
            cards = page.query_selector_all("article[data-test='property-card']")
            print(f"  Found {len(cards)} Zillow cards via DOM")
            
            for card in cards:
                try:
                    listing = {"source": "zillow"}
                    
                    addr_el = card.query_selector("address")
                    listing['title'] = addr_el.inner_text().strip() if addr_el else None
                    listing['address'] = listing['title']
                    
                    price_el = card.query_selector("[data-test='property-card-price']")
                    listing['price'] = parse_price(price_el.inner_text() if price_el else "")
                    
                    link_el = card.query_selector("a[data-test='property-card-link']")
                    href = link_el.get_attribute("href") if link_el else ""
                    listing['url'] = "https://www.zillow.com" + href if href.startswith("/") else href
                    
                    if listing['url']:
                        listing['id'] = generate_listing_id("zillow", listing['url'])
                        listings.append(listing)
                except Exception as e:
                    continue
                    
    except Exception as e:
        print(f"  Error fetching Zillow: {e}")
    
    return listings


def scrape_craigslist(page, zip_code, max_beds=1):
    """Scrape Craigslist NJ housing"""
    listings = []
    
    # Central NJ craigslist
    url = f"https://newjersey.craigslist.org/search/jsy/apa?postal={zip_code}&search_distance=10&max_bedrooms={max_beds}"
    
    print(f"  Fetching Craigslist: {zip_code}")
    
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        time.sleep(2)
        
        # Get listing rows
        rows = page.query_selector_all(".cl-search-result")
        print(f"  Found {len(rows)} Craigslist listings")
        
        for row in rows:
            try:
                listing = {"source": "craigslist"}
                
                title_el = row.query_selector(".title")
                listing['title'] = title_el.inner_text().strip() if title_el else None
                
                price_el = row.query_selector(".price")
                listing['price'] = parse_price(price_el.inner_text() if price_el else "")
                
                link_el = row.query_selector("a")
                listing['url'] = link_el.get_attribute("href") if link_el else None
                
                meta_el = row.query_selector(".meta")
                if meta_el:
                    meta = meta_el.inner_text()
                    # Extract location
                    listing['city'] = meta.strip()
                
                if listing['url']:
                    listing['id'] = generate_listing_id("craigslist", listing['url'])
                    listings.append(listing)
                    
            except Exception as e:
                continue
                
    except Exception as e:
        print(f"  Error fetching Craigslist: {e}")
    
    return listings


def run_scraper():
    """Main scraper runner"""
    print("=" * 50)
    print("Apartment Scraper - Starting")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 50)
    
    # Check for playwright
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: Playwright not installed. Run: pip install playwright")
        return
    
    conn = init_db()
    total_new = 0
    total_found = 0
    
    with sync_playwright() as p:
        # Launch browser in headless mode
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        
        # Create context with realistic settings
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = context.new_page()
        
        for area in CONFIG['search_areas']:
            print(f"\n--- Searching {area['name']} ({area['zip']}) ---")
            
            # Scrape each source
            for scraper_name, scraper_func in [
                ("Apartments.com", scrape_apartments_com),
                ("Zillow", scrape_zillow),
                ("Craigslist", scrape_craigslist),
            ]:
                print(f"\n{scraper_name}:")
                try:
                    listings = scraper_func(page, area['zip'], CONFIG['max_bedrooms'])
                    
                    # Filter by price
                    filtered = [
                        l for l in listings 
                        if l.get('price') is None or 
                        (CONFIG['min_price'] <= l['price'] <= CONFIG['max_price'])
                    ]
                    
                    print(f"  Saving {len(filtered)} listings (filtered from {len(listings)})")
                    
                    for listing in filtered:
                        listing['city'] = listing.get('city') or area['name']
                        listing['state'] = 'NJ'
                        listing['zip'] = listing.get('zip') or area['zip']
                        save_listing(conn, listing)
                    
                    total_found += len(filtered)
                    
                except Exception as e:
                    print(f"  Scraper error: {e}")
                
                # Polite delay between sources
                time.sleep(2)
            
            # Delay between areas
            time.sleep(3)
        
        browser.close()
    
    # Count new listings
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM listings WHERE is_new = 1")
    total_new = c.fetchone()[0]
    
    conn.close()
    
    print("\n" + "=" * 50)
    print(f"Scraping complete!")
    print(f"Total found: {total_found}")
    print(f"New listings: {total_new}")
    print(f"Database: {DB_PATH}")
    print("=" * 50)
    
    return total_new


if __name__ == "__main__":
    run_scraper()
