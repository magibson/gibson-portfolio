"""
Craigslist scraper for NJ apartments
Uses RSS feeds and HTML parsing
"""

import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlencode
from .base import BaseScraper

class CraigslistScraper(BaseScraper):
    """Scrape Craigslist NJ housing"""
    
    name = "craigslist"
    base_url = "https://newjersey.craigslist.org"
    
    def scrape(self, locations: list, min_price: int, max_price: int,
               min_beds: int, max_beds: int) -> list:
        """Scrape Craigslist for apartments"""
        listings = []
        
        # Build search URL
        # Craigslist uses numeric codes: 0 = no min, 1-8 = beds
        params = {
            'min_price': min_price,
            'max_price': max_price,
            'min_bedrooms': max(min_beds, 0) if min_beds is not None else '',
            'max_bedrooms': max_beds if max_beds is not None else '',
            'availabilityMode': 0,
            'sale_date': 'all+dates',
        }
        
        # Search for each location
        for loc in locations:
            query = f"{loc['name']} NJ"
            search_url = f"{self.base_url}/search/apa?query={query}&{urlencode({k:v for k,v in params.items() if v != ''})}"
            
            print(f"[Craigslist] Searching: {loc['name']}")
            
            try:
                resp = self.get(search_url)
                if resp.status_code != 200:
                    print(f"  Warning: Got status {resp.status_code}")
                    continue
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Find listing items
                items = soup.select('li.cl-static-search-result, div.result-row, li.result-row')
                
                for item in items:
                    try:
                        listing = self._parse_listing(item, loc)
                        if listing:
                            listings.append(listing)
                    except Exception as e:
                        print(f"  Error parsing item: {e}")
                        continue
                
                print(f"  Found {len(items)} items")
                
            except Exception as e:
                print(f"  Error: {e}")
                continue
        
        return listings
    
    def _parse_listing(self, item, location: dict) -> dict:
        """Parse a single Craigslist listing"""
        # Try different selectors for Craigslist's varying HTML
        link = item.select_one('a.titlestring, a.result-title, a.posting-title, a[href*="/apa/"]')
        if not link:
            return None
        
        url = link.get('href', '')
        if not url.startswith('http'):
            url = urljoin(self.base_url, url)
        
        # Extract ID from URL
        id_match = re.search(r'/(\d+)\.html', url)
        source_id = id_match.group(1) if id_match else url
        
        title = link.get_text(strip=True)
        
        # Price
        price_el = item.select_one('.price, .result-price, span.priceinfo')
        price = price_el.get_text(strip=True) if price_el else None
        
        # Location/neighborhood
        hood_el = item.select_one('.result-hood, .housing, .meta')
        hood = hood_el.get_text(strip=True) if hood_el else ''
        
        # Try to extract beds from title or meta
        beds = None
        beds_match = re.search(r'(\d+)\s*br', title.lower() + ' ' + hood.lower())
        if beds_match:
            beds = int(beds_match.group(1))
        elif 'studio' in (title.lower() + ' ' + hood.lower()):
            beds = 0
        
        # Extract sqft if present
        sqft = None
        sqft_match = re.search(r'(\d+)\s*ft', title.lower() + ' ' + hood.lower())
        if sqft_match:
            sqft = int(sqft_match.group(1))
        
        return self.normalize_listing({
            'id': source_id,
            'url': url,
            'title': title,
            'price': price,
            'beds': beds,
            'sqft': sqft,
            'city': location['name'],
            'state': 'NJ',
            'zip_code': location.get('zip', ''),
            'address': hood.strip('() ') if hood else location['name'],
        })
