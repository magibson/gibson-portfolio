"""
Base scraper class
"""

import requests
import time
import random
from abc import ABC, abstractmethod
from datetime import datetime
import sys
sys.path.insert(0, '..')
from config import USER_AGENT

class BaseScraper(ABC):
    """Base class for apartment scrapers"""
    
    name = "base"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        self.started_at = None
        self.listings_found = 0
        self.listings_new = 0
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """Make a GET request with rate limiting"""
        time.sleep(random.uniform(1, 3))  # Be nice to servers
        return self.session.get(url, timeout=30, **kwargs)
    
    @abstractmethod
    def scrape(self, locations: list, min_price: int, max_price: int, 
               min_beds: int, max_beds: int) -> list:
        """
        Scrape listings matching criteria.
        Returns list of listing dicts.
        """
        pass
    
    def run(self, locations: list, min_price: int, max_price: int,
            min_beds: int, max_beds: int) -> tuple:
        """Run the scraper and return (listings, stats)"""
        self.started_at = datetime.now()
        self.listings_found = 0
        self.listings_new = 0
        
        try:
            listings = self.scrape(locations, min_price, max_price, min_beds, max_beds)
            self.listings_found = len(listings)
            return listings, None
        except Exception as e:
            return [], str(e)
    
    def normalize_listing(self, raw: dict) -> dict:
        """Normalize a raw listing to standard format"""
        return {
            'source': self.name,
            'source_id': raw.get('id', ''),
            'url': raw.get('url', ''),
            'title': raw.get('title', ''),
            'address': raw.get('address', ''),
            'city': raw.get('city', ''),
            'state': raw.get('state', 'NJ'),
            'zip_code': raw.get('zip_code', ''),
            'price': self._parse_price(raw.get('price')),
            'beds': self._parse_beds(raw.get('beds')),
            'baths': self._parse_float(raw.get('baths')),
            'sqft': self._parse_int(raw.get('sqft')),
            'description': raw.get('description', ''),
            'amenities': raw.get('amenities', []),
            'images': raw.get('images', []),
            'lat': raw.get('lat'),
            'lng': raw.get('lng'),
            'raw_data': raw
        }
    
    def _parse_price(self, val) -> int:
        """Parse price string to int"""
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return int(val)
        # Remove $, commas, /mo, etc
        import re
        cleaned = re.sub(r'[^\d.]', '', str(val))
        try:
            return int(float(cleaned))
        except:
            return None
    
    def _parse_beds(self, val) -> float:
        """Parse beds, handling 'Studio' as 0"""
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        val_str = str(val).lower()
        if 'studio' in val_str:
            return 0
        try:
            import re
            match = re.search(r'(\d+)', val_str)
            return float(match.group(1)) if match else None
        except:
            return None
    
    def _parse_float(self, val) -> float:
        if val is None:
            return None
        try:
            import re
            cleaned = re.sub(r'[^\d.]', '', str(val))
            return float(cleaned)
        except:
            return None
    
    def _parse_int(self, val) -> int:
        if val is None:
            return None
        try:
            import re
            cleaned = re.sub(r'[^\d]', '', str(val))
            return int(cleaned) if cleaned else None
        except:
            return None
