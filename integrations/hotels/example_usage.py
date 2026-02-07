#!/usr/bin/env python3
"""
Example usage of the Hotel Search integration.

Run: python3 example_usage.py
"""

from datetime import datetime, timedelta
from hotels_client import HotelSearchClient
from telegram_formatter import (
    format_hotel_results,
    format_price_comparison,
    format_deals,
    format_hotel_results_plain,
)


def main():
    # Initialize client
    client = HotelSearchClient()
    
    # Set up dates (30 days from now)
    checkin = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    checkout = (datetime.now() + timedelta(days=33)).strftime("%Y-%m-%d")
    
    print("=" * 60)
    print("HOTEL SEARCH INTEGRATION - EXAMPLES")
    print("=" * 60)
    
    # Example 1: Basic Search
    print("\n📍 Example 1: Search Hotels in Barcelona")
    print("-" * 40)
    
    results = client.search_hotels(
        city="Barcelona",
        checkin=checkin,
        checkout=checkout,
        guests=2,
    )
    
    if "error" in results:
        print(f"Error: {results['error']}")
        print("Note: Make sure SERPAPI_KEY is set or config.json has your API key")
    else:
        # Show count
        print(f"Found {len(results.get('properties', []))} hotels")
        
        # Show formatted for Telegram
        print("\nTelegram format:")
        print(format_hotel_results(results, max_results=3))
    
    # Example 2: Find Deals
    print("\n📍 Example 2: Find Deals Under $100")
    print("-" * 40)
    
    deals = client.find_deals(
        city="Lisbon",
        checkin=checkin,
        checkout=checkout,
        max_price=100,
        min_rating=4.0,
    )
    
    if "error" in deals:
        print(f"Error: {deals['error']}")
    else:
        print(f"Found {deals.get('total_found', 0)} deals")
        print("\nTelegram format:")
        print(format_deals(deals, max_deals=3))
    
    # Example 3: Price Comparison
    print("\n📍 Example 3: Compare Prices for Specific Hotel")
    print("-" * 40)
    
    comparison = client.compare_prices(
        hotel_name="Marriott",
        checkin=checkin,
        checkout=checkout,
        city="Paris",
    )
    
    if "error" in comparison:
        print(f"Error: {comparison['error']}")
    else:
        print("\nTelegram format:")
        print(format_price_comparison(comparison))
    
    # Example 4: With Filters
    print("\n📍 Example 4: Search with Filters")
    print("-" * 40)
    
    filtered = client.search_hotels(
        city="Rome",
        checkin=checkin,
        checkout=checkout,
        guests=2,
        max_price=200,
        rating=4.0,
        hotel_class=4,
        sort_by="highest_rating",
    )
    
    if "error" in filtered:
        print(f"Error: {filtered['error']}")
    else:
        print(f"Found {len(filtered.get('properties', []))} 4+ star hotels under $200")
        print("\nPlain text format:")
        print(format_hotel_results_plain(filtered, max_results=3))


if __name__ == "__main__":
    main()
