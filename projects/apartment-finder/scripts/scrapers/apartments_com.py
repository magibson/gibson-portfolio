"""
Apartments.com scraper
Uses their search pages (they don't have a public API)
"""

import re
import json
from bs4 import BeautifulSoup
from urllib.parse import quote
from .base import BaseScraper

class ApartmentsComScraper(BaseScraper):
    """Scrape Apartments.com"""
    
    name = "apartments_com"
    base_url = "https://www.apartments.com"
    
    def scrape(self, locations: list, min_price: int, max_price: int,
               min_beds: int, max_beds: int) -> list:
        """Scrape Apartments.com for listings"""
        listings = []
        
        for loc in locations:
            # Build URL: apartments.com/shrewsbury-nj/studios-1-bedrooms/
            city_slug = loc['name'].lower().replace(' ', '-')
            
            # Beds filter
            if min_beds == 0 and max_beds == 1:
                beds_slug = "studios-1-bedrooms"
            elif min_beds == 0 and max_beds == 0:
                beds_slug = "studios"
            elif min_beds == 1 and max_beds == 1:
                beds_slug = "1-bedrooms"
            else:
                beds_slug = ""
            
            # Price filter
            price_slug = f"{min_price}-to-{max_price}" if min_price and max_price else ""
            
            search_url = f"{self.base_url}/{city_slug}-nj/{beds_slug}/"
            if price_slug:
                search_url = search_url.rstrip('/') + f"-{price_slug}/"
            
            print(f"[Apartments.com] Searching: {loc['name']}")
            
            try:
                resp = self.get(search_url)
                if resp.status_code != 200:
                    print(f"  Warning: Got status {resp.status_code}")
                    continue
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Try to find JSON data in script tags
                script_data = self._extract_json_data(soup)
                if script_data:
                    for item in script_data:
                        listing = self._parse_json_listing(item, loc)
                        if listing:
                            listings.append(listing)
                
                # Also parse HTML cards as fallback
                cards = soup.select('article.placard, li.mortar-wrapper article, div[data-listingid]')
                
                for card in cards:
                    try:
                        listing = self._parse_card(card, loc)
                        if listing and listing['source_id'] not in [l['source_id'] for l in listings]:
                            listings.append(listing)
                    except Exception as e:
                        continue
                
                print(f"  Found {len(cards)} cards")
                
            except Exception as e:
                print(f"  Error: {e}")
                continue
        
        return listings
    
    def _extract_json_data(self, soup) -> list:
        """Try to extract listing data from embedded JSON"""
        try:
            # Look for JSON-LD
            for script in soup.select('script[type="application/ld+json"]'):
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') == 'ItemList':
                    return data.get('itemListElement', [])
            
            # Look for inline JS data
            for script in soup.select('script'):
                if script.string and 'window.__PRELOADED_STATE__' in script.string:
                    match = re.search(r'window\.__PRELOADED_STATE__\s*=\s*({.+?});', script.string, re.DOTALL)
                    if match:
                        data = json.loads(match.group(1))
                        return data.get('listings', {}).get('listings', [])
        except:
            pass
        return []
    
    def _parse_json_listing(self, item: dict, location: dict) -> dict:
        """Parse a listing from JSON data"""
        try:
            prop = item.get('item', item)
            
            return self.normalize_listing({
                'id': prop.get('listingId') or prop.get('@id', ''),
                'url': prop.get('url', ''),
                'title': prop.get('name', ''),
                'address': prop.get('address', {}).get('streetAddress', '') if isinstance(prop.get('address'), dict) else '',
                'city': location['name'],
                'zip_code': prop.get('address', {}).get('postalCode', '') if isinstance(prop.get('address'), dict) else '',
                'price': prop.get('offers', {}).get('price') if isinstance(prop.get('offers'), dict) else None,
                'beds': prop.get('numberOfBedrooms'),
                'baths': prop.get('numberOfBathroomsTotal'),
                'lat': prop.get('geo', {}).get('latitude') if isinstance(prop.get('geo'), dict) else None,
                'lng': prop.get('geo', {}).get('longitude') if isinstance(prop.get('geo'), dict) else None,
                'images': [img.get('contentUrl', img) for img in prop.get('photo', [])] if isinstance(prop.get('photo'), list) else [],
            })
        except Exception as e:
            return None
    
    def _parse_card(self, card, location: dict) -> dict:
        """Parse an HTML listing card"""
        listing_id = card.get('data-listingid', '')
        
        link = card.select_one('a.property-link, a[data-tag="link"]')
        url = link.get('href', '') if link else ''
        
        if not listing_id:
            id_match = re.search(r'/([a-z0-9]+)/?$', url)
            listing_id = id_match.group(1) if id_match else url
        
        title_el = card.select_one('.property-title, h3, .placard-header')
        title = title_el.get_text(strip=True) if title_el else ''
        
        address_el = card.select_one('.property-address, address')
        address = address_el.get_text(strip=True) if address_el else ''
        
        price_el = card.select_one('.property-pricing, .price-range, [data-tag="price"]')
        price = price_el.get_text(strip=True) if price_el else None
        
        beds_el = card.select_one('.property-beds, [data-tag="beds"]')
        beds = beds_el.get_text(strip=True) if beds_el else None
        
        baths_el = card.select_one('.property-baths, [data-tag="baths"]')
        baths = baths_el.get_text(strip=True) if baths_el else None
        
        sqft_el = card.select_one('.property-sqft, [data-tag="sqft"]')
        sqft = sqft_el.get_text(strip=True) if sqft_el else None
        
        img_el = card.select_one('img.property-image, img[data-tag="image"]')
        images = [img_el.get('src', '')] if img_el else []
        
        return self.normalize_listing({
            'id': listing_id,
            'url': url if url.startswith('http') else f"{self.base_url}{url}",
            'title': title,
            'address': address,
            'city': location['name'],
            'zip_code': location.get('zip', ''),
            'price': price,
            'beds': beds,
            'baths': baths,
            'sqft': sqft,
            'images': images,
        })
