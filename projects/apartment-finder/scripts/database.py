"""
Database module for apartment listings
SQLite storage with deduplication
"""

import sqlite3
import os
import json
from datetime import datetime
from config import DB_PATH, DATA_DIR

def init_db():
    """Initialize the database with required tables"""
    os.makedirs(DATA_DIR, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Main listings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            source_id TEXT NOT NULL,
            url TEXT NOT NULL,
            title TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            zip_code TEXT,
            price INTEGER,
            beds REAL,
            baths REAL,
            sqft INTEGER,
            description TEXT,
            amenities TEXT,
            images TEXT,
            lat REAL,
            lng REAL,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            raw_data TEXT,
            UNIQUE(source, source_id)
        )
    ''')
    
    # Favorites table (for dashboard state)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            listing_id INTEGER PRIMARY KEY,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (listing_id) REFERENCES listings(id)
        )
    ''')
    
    # Price history for tracking changes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id INTEGER,
            price INTEGER,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (listing_id) REFERENCES listings(id)
        )
    ''')
    
    # Scrape log
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scrape_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            listings_found INTEGER,
            listings_new INTEGER,
            error TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

def upsert_listing(listing: dict) -> tuple:
    """
    Insert or update a listing. Returns (listing_id, is_new)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if exists
    cursor.execute('''
        SELECT id, price FROM listings 
        WHERE source = ? AND source_id = ?
    ''', (listing['source'], listing['source_id']))
    
    existing = cursor.fetchone()
    
    if existing:
        listing_id, old_price = existing
        is_new = False
        
        # Update last_seen and other fields
        cursor.execute('''
            UPDATE listings SET
                last_seen = CURRENT_TIMESTAMP,
                is_active = 1,
                price = ?,
                title = ?,
                address = ?,
                description = ?,
                images = ?,
                raw_data = ?
            WHERE id = ?
        ''', (
            listing.get('price'),
            listing.get('title'),
            listing.get('address'),
            listing.get('description'),
            json.dumps(listing.get('images', [])),
            json.dumps(listing.get('raw_data', {})),
            listing_id
        ))
        
        # Record price change if different
        if old_price and listing.get('price') and old_price != listing['price']:
            cursor.execute('''
                INSERT INTO price_history (listing_id, price)
                VALUES (?, ?)
            ''', (listing_id, listing['price']))
    else:
        # Insert new listing
        cursor.execute('''
            INSERT INTO listings (
                source, source_id, url, title, address, city, state, zip_code,
                price, beds, baths, sqft, description, amenities, images,
                lat, lng, raw_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            listing['source'],
            listing['source_id'],
            listing['url'],
            listing.get('title'),
            listing.get('address'),
            listing.get('city'),
            listing.get('state', 'NJ'),
            listing.get('zip_code'),
            listing.get('price'),
            listing.get('beds'),
            listing.get('baths'),
            listing.get('sqft'),
            listing.get('description'),
            json.dumps(listing.get('amenities', [])),
            json.dumps(listing.get('images', [])),
            listing.get('lat'),
            listing.get('lng'),
            json.dumps(listing.get('raw_data', {}))
        ))
        listing_id = cursor.lastrowid
        is_new = True
        
        # Record initial price
        if listing.get('price'):
            cursor.execute('''
                INSERT INTO price_history (listing_id, price)
                VALUES (?, ?)
            ''', (listing_id, listing['price']))
    
    conn.commit()
    conn.close()
    return listing_id, is_new

def get_listings(filters: dict = None) -> list:
    """Get listings with optional filters"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = "SELECT * FROM listings WHERE is_active = 1"
    params = []
    
    if filters:
        if filters.get('min_price'):
            query += " AND price >= ?"
            params.append(filters['min_price'])
        if filters.get('max_price'):
            query += " AND price <= ?"
            params.append(filters['max_price'])
        if filters.get('min_beds') is not None:
            query += " AND beds >= ?"
            params.append(filters['min_beds'])
        if filters.get('max_beds') is not None:
            query += " AND beds <= ?"
            params.append(filters['max_beds'])
        if filters.get('city'):
            query += " AND city = ?"
            params.append(filters['city'])
    
    query += " ORDER BY first_seen DESC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def mark_inactive_old_listings(source: str, active_ids: list):
    """Mark listings not in active_ids as inactive"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if active_ids:
        placeholders = ','.join(['?' for _ in active_ids])
        cursor.execute(f'''
            UPDATE listings 
            SET is_active = 0 
            WHERE source = ? AND source_id NOT IN ({placeholders})
        ''', [source] + active_ids)
    
    conn.commit()
    conn.close()

def log_scrape(source: str, started_at: datetime, listings_found: int, listings_new: int, error: str = None):
    """Log a scrape run"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO scrape_log (source, started_at, completed_at, listings_found, listings_new, error)
        VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?)
    ''', (source, started_at, listings_found, listings_new, error))
    
    conn.commit()
    conn.close()

def export_json(filepath: str = None) -> str:
    """Export all active listings to JSON"""
    if filepath is None:
        filepath = os.path.join(DATA_DIR, 'listings.json')
    
    listings = get_listings()
    
    # Add computed fields
    from config import NEW_LISTING_HOURS, UTILITY_ESTIMATES
    now = datetime.now()
    
    for listing in listings:
        # Parse first_seen
        first_seen = datetime.fromisoformat(listing['first_seen'].replace('Z', '+00:00')) if listing['first_seen'] else now
        hours_old = (now - first_seen.replace(tzinfo=None)).total_seconds() / 3600
        listing['is_new'] = hours_old <= NEW_LISTING_HOURS
        
        # Estimate true cost
        bed_key = 'studio' if listing['beds'] == 0 else '1br'
        utilities = (
            UTILITY_ESTIMATES['electric'].get(bed_key, 100) +
            UTILITY_ESTIMATES['gas'].get(bed_key, 50) +
            UTILITY_ESTIMATES['water'].get(bed_key, 35) +
            UTILITY_ESTIMATES['internet'] +
            UTILITY_ESTIMATES['renters_insurance']
        )
        listing['estimated_utilities'] = utilities
        listing['true_monthly_cost'] = (listing['price'] or 0) + utilities
        
        # Parse JSON fields
        listing['amenities'] = json.loads(listing['amenities']) if listing['amenities'] else []
        listing['images'] = json.loads(listing['images']) if listing['images'] else []
    
    with open(filepath, 'w') as f:
        json.dump({
            'generated_at': now.isoformat(),
            'total_listings': len(listings),
            'listings': listings
        }, f, indent=2, default=str)
    
    print(f"Exported {len(listings)} listings to {filepath}")
    return filepath

if __name__ == '__main__':
    init_db()
    print("Database ready!")
