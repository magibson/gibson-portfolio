"""
Zillow scraper
Uses search pages (Zillow's API requires partnership)
"""

import re
import json
from bs4 import BeautifulSoup
from urllib.parse import quote
from .base import BaseScraper

class ZillowScraper(BaseScraper):
    """Scrape Zillow rentals"""
    
    name = "zillow"
    base_url = "https://www.zillow.com"
    
    def __init__(self):
        super().__init__()
        # Zillow needs extra headers
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.zillow.com/',
        })
    
    def scrape(self, locations: list, min_price: int, max_price: int,
               min_beds: int, max_beds: int) -> list:
        """Scrape Zillow for rentals"""
        listings = []
        
        for loc in locations:
            # Build URL: zillow.com/shrewsbury-nj/rentals/
            city_slug = loc['name'].lower().replace(' ', '-')
            
            # Build filter string
            filters = []
            if min_beds == 0:
                filters.append("0-_beds")
            if max_beds and max_beds <= 1:
                filters.append(f"0-{max_beds}_beds")
            if min_price:
                filters.append(f"{min_price}-_price")
            if max_price:
                filters.append(f"-{max_price}_price")
            
            search_url = f"{self.base_url}/{city_slug}-nj/rentals/"
            
            print(f"[Zillow] Searching: {loc['name']}")
            
            try:
                resp = self.get(search_url)
                
                # Zillow often blocks scrapers - handle gracefully
                if resp.status_code == 403:
                    print(f"  Blocked (403) - Zillow requires browser")
                    continue
                if resp.status_code != 200:
                    print(f"  Warning: Got status {resp.status_code}")
                    continue
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Try to extract data from script tags
                script_listings = self._extract_script_data(soup)
                if script_listings:
                    for item in script_listings:
                        listing = self._parse_script_listing(item, loc, min_price, max_price, min_beds, max_beds)
                        if listing:
                            listings.append(listing)
                    print(f"  Found {len(script_listings)} from scripts")
                else:
                    # Fallback to HTML parsing
                    cards = soup.select('article[data-test="property-card"], div[class*="ListItem"]')
                    for card in cards:
                        try:
                            listing = self._parse_card(card, loc)
                            if listing:
                                listings.append(listing)
                        except:
                            continue
                    print(f"  Found {len(cards)} cards")
                
            except Exception as e:
                print(f"  Error: {e}")
                continue
        
        return listings
    
    def _extract_script_data(self, soup) -> list:
        """Extract listing data from Zillow's embedded JSON"""
        try:
            # Look for the main data script
            for script in soup.select('script'):
                if not script.string:
                    continue
                
                # Look for search results data
                if '"listResults"' in script.string or '"searchResults"' in script.string:
                    # Try to find the JSON object
                    match = re.search(r'"listResults"\s*:\s*(\[.+?\])\s*[,}]', script.string, re.DOTALL)
                    if match:
                        return json.loads(match.group(1))
                
                # Alternative format
                if '"cat1"' in script.string and '"searchResults"' in script.string:
                    match = re.search(r'"cat1"\s*:\s*(\{.+?\})\s*[,}]', script.string, re.DOTALL)
                    if match:
                        try:
                            data = json.loads(match.group(1))
                            return data.get('searchResults', {}).get('listResults', [])
                        except:
                            pass
        except Exception as e:
            print(f"  Script parsing error: {e}")
        return []
    
    def _parse_script_listing(self, item: dict, location: dict, 
                              min_price: int, max_price: int,
                              min_beds: int, max_beds: int) -> dict:
        """Parse a listing from Zillow's script data"""
        try:
            # Extract price
            price = item.get('price') or item.get('unformattedPrice')
            if isinstance(price, str):
                price = re.sub(r'[^\d]', '', price)
                price = int(price) if price else None
            
            # Filter by price
            if price:
                if min_price and price < min_price:
                    return None
                if max_price and price > max_price:
                    return None
            
            # Extract beds
            beds = item.get('beds')
            if beds is None:
                beds_match = re.search(r'(\d+)\s*bd', str(item.get('statusText', '')).lower())
                if beds_match:
                    beds = int(beds_match.group(1))
                elif 'studio' in str(item).lower():
                    beds = 0
            
            # Filter by beds
            if beds is not None:
                if min_beds is not None and beds < min_beds:
                    return None
                if max_beds is not None and beds > max_beds:
                    return None
            
            zpid = item.get('zpid') or item.get('id', '')
            detail_url = item.get('detailUrl', '')
            if detail_url and not detail_url.startswith('http'):
                detail_url = f"{self.base_url}{detail_url}"
            
            return self.normalize_listing({
                'id': str(zpid),
                'url': detail_url,
                'title': item.get('statusText', '') or item.get('address', ''),
                'address': item.get('address', ''),
                'city': location['name'],
                'zip_code': item.get('addressZipcode', '') or location.get('zip', ''),
                'price': price,
                'beds': beds,
                'baths': item.get('baths'),
                'sqft': item.get('area'),
                'lat': item.get('latLong', {}).get('latitude') if isinstance(item.get('latLong'), dict) else None,
                'lng': item.get('latLong', {}).get('longitude') if isinstance(item.get('latLong'), dict) else None,
                'images': [item.get('imgSrc')] if item.get('imgSrc') else [],
            })
        except Exception as e:
            return None
    
    def _parse_card(self, card, location: dict) -> dict:
        """Parse an HTML listing card"""
        link = card.select_one('a[data-test="property-card-link"], a[href*="/homedetails/"]')
        if not link:
            return None
        
        url = link.get('href', '')
        if not url.startswith('http'):
            url = f"{self.base_url}{url}"
        
        # Extract zpid from URL
        zpid_match = re.search(r'(\d+)_zpid', url)
        listing_id = zpid_match.group(1) if zpid_match else url
        
        address_el = card.select_one('[data-test="property-card-addr"], address')
        address = address_el.get_text(strip=True) if address_el else ''
        
        price_el = card.select_one('[data-test="property-card-price"], span[class*="Price"]')
        price = price_el.get_text(strip=True) if price_el else None
        
        details_el = card.select_one('[data-test="property-card-details"]')
        details = details_el.get_text(strip=True) if details_el else ''
        
        beds = None
        beds_match = re.search(r'(\d+)\s*bd', details.lower())
        if beds_match:
            beds = int(beds_match.group(1))
        elif 'studio' in details.lower():
            beds = 0
        
        baths_match = re.search(r'(\d+\.?\d*)\s*ba', details.lower())
        baths = float(baths_match.group(1)) if baths_match else None
        
        sqft_match = re.search(r'(\d+,?\d*)\s*sqft', details.lower())
        sqft = int(sqft_match.group(1).replace(',', '')) if sqft_match else None
        
        img_el = card.select_one('img')
        images = [img_el.get('src', '')] if img_el else []
        
        return self.normalize_listing({
            'id': listing_id,
            'url': url,
            'title': address,
            'address': address,
            'city': location['name'],
            'zip_code': location.get('zip', ''),
            'price': price,
            'beds': beds,
            'baths': baths,
            'sqft': sqft,
            'images': images,
        })
