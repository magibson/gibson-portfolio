"""
Apartment Finder Configuration
Matt's search criteria for Shrewsbury, NJ area
"""

# Search locations (Shrewsbury + nearby towns)
LOCATIONS = [
    {"name": "Shrewsbury", "state": "NJ", "zip": "07702"},
    {"name": "Red Bank", "state": "NJ", "zip": "07701"},
    {"name": "Little Silver", "state": "NJ", "zip": "07739"},
    {"name": "Tinton Falls", "state": "NJ", "zip": "07724"},
    {"name": "Eatontown", "state": "NJ", "zip": "07724"},
    {"name": "Fair Haven", "state": "NJ", "zip": "07704"},
    {"name": "Rumson", "state": "NJ", "zip": "07760"},
]

# Budget range (based on market research: 1BR averages $2,400-3,000)
# Setting lower bound to catch affordable options
MIN_PRICE = 1500
MAX_PRICE = 2800

# Bedroom requirements
MIN_BEDS = 0  # Studio
MAX_BEDS = 1  # 1 bedroom

# Search radius from Red Bank (miles)
SEARCH_RADIUS = 10

# Listing age threshold for "NEW" badge (hours)
NEW_LISTING_HOURS = 48

# Database path
import os
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'apartments.db')
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

# True cost estimates for the area
UTILITY_ESTIMATES = {
    "electric": {"studio": 80, "1br": 100},
    "gas": {"studio": 40, "1br": 50},
    "water": {"studio": 30, "1br": 35},
    "internet": 70,
    "renters_insurance": 20,
}

# Commute reference points
COMMUTE_DESTINATIONS = [
    {"name": "Red Bank Train Station", "lat": 40.3487, "lng": -74.0765},
    {"name": "Downtown Red Bank", "lat": 40.3470, "lng": -74.0643},
    {"name": "Eatontown (typical office area)", "lat": 40.2965, "lng": -74.0507},
]

# User agent for scraping
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
