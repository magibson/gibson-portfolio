#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main scraper runner
Runs all scrapers and updates the database
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime
from config import LOCATIONS, MIN_PRICE, MAX_PRICE, MIN_BEDS, MAX_BEDS
from database import init_db, upsert_listing, log_scrape, export_json
from scrapers import CraigslistScraper, ApartmentsComScraper, ZillowScraper

def run_all_scrapers():
    """Run all scrapers and update database"""
    print(f"=" * 60)
    print(f"Apartment Finder Scraper - {datetime.now().isoformat()}")
    print(f"=" * 60)
    print(f"Criteria: ${MIN_PRICE}-${MAX_PRICE}, {MIN_BEDS}-{MAX_BEDS} beds")
    print(f"Locations: {', '.join(l['name'] for l in LOCATIONS)}")
    print()
    
    # Initialize database
    init_db()
    
    all_listings = []
    scrapers = [
        CraigslistScraper(),
        ApartmentsComScraper(),
        ZillowScraper(),
    ]
    
    for scraper in scrapers:
        print(f"\n{'=' * 40}")
        print(f"Running {scraper.name}")
        print(f"{'=' * 40}")
        
        started_at = datetime.now()
        
        try:
            listings, error = scraper.run(
                LOCATIONS, MIN_PRICE, MAX_PRICE, MIN_BEDS, MAX_BEDS
            )
            
            if error:
                print(f"Error: {error}")
                log_scrape(scraper.name, started_at, 0, 0, error)
                continue
            
            # Upsert each listing
            new_count = 0
            for listing in listings:
                listing_id, is_new = upsert_listing(listing)
                if is_new:
                    new_count += 1
            
            print(f"\nResults: {len(listings)} listings, {new_count} new")
            log_scrape(scraper.name, started_at, len(listings), new_count)
            all_listings.extend(listings)
            
        except Exception as e:
            print(f"Scraper failed: {e}")
            log_scrape(scraper.name, started_at, 0, 0, str(e))
    
    # Export to JSON for the dashboard
    print(f"\n{'=' * 40}")
    print("Exporting to JSON...")
    export_json()
    
    print(f"\n{'=' * 60}")
    print(f"Complete! Total: {len(all_listings)} listings scraped")
    print(f"{'=' * 60}")

def run_single_scraper(name: str):
    """Run a single scraper by name"""
    scrapers = {
        'craigslist': CraigslistScraper,
        'apartments_com': ApartmentsComScraper,
        'zillow': ZillowScraper,
    }
    
    if name not in scrapers:
        print(f"Unknown scraper: {name}")
        print(f"Available: {', '.join(scrapers.keys())}")
        return
    
    init_db()
    
    scraper = scrapers[name]()
    started_at = datetime.now()
    
    listings, error = scraper.run(
        LOCATIONS, MIN_PRICE, MAX_PRICE, MIN_BEDS, MAX_BEDS
    )
    
    if error:
        print(f"Error: {error}")
        return
    
    new_count = 0
    for listing in listings:
        listing_id, is_new = upsert_listing(listing)
        if is_new:
            new_count += 1
    
    print(f"Results: {len(listings)} listings, {new_count} new")
    log_scrape(scraper.name, started_at, len(listings), new_count)
    
    export_json()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        run_single_scraper(sys.argv[1])
    else:
        run_all_scrapers()
