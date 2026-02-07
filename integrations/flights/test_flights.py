#!/usr/bin/env python3
"""Quick test script for flight search integration.

Run: python test_flights.py

Tests each provider individually to verify configuration.
"""
import os
import sys
from datetime import datetime, timedelta

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_config():
    """Test configuration loading."""
    print("=" * 50)
    print("Testing Configuration")
    print("=" * 50)
    
    from flights import FlightSearchClient
    
    client = FlightSearchClient()
    providers = client.available_providers()
    
    print(f"\n✅ Config loaded successfully")
    print(f"   Available providers: {providers or 'None configured'}")
    
    if not providers:
        print("\n⚠️  No providers configured!")
        print("   Please copy config.template.yaml to config.yaml")
        print("   and add your API keys.")
        print("\n   Or set environment variables:")
        print("   - AMADEUS_API_KEY + AMADEUS_API_SECRET")
        print("   - KIWI_API_KEY")
        print("   - SERPAPI_KEY")
        return False
    
    return True


def test_amadeus():
    """Test Amadeus provider."""
    print("\n" + "=" * 50)
    print("Testing Amadeus Provider")
    print("=" * 50)
    
    from providers.amadeus import AmadeusProvider
    
    api_key = os.environ.get("AMADEUS_API_KEY")
    api_secret = os.environ.get("AMADEUS_API_SECRET")
    
    if not api_key or not api_secret:
        print("⏭️  Skipped - AMADEUS_API_KEY/SECRET not set")
        return
    
    provider = AmadeusProvider(api_key, api_secret, environment="test")
    
    # Test search
    from providers.base import FlightSearch
    search = FlightSearch(
        origin="JFK",
        destination="LAX",
        date=(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        passengers=1,
        max_results=3
    )
    
    print("\n🔍 Searching JFK → LAX...")
    results = provider.search(search)
    
    if results:
        print(f"✅ Found {len(results)} flights")
        for f in results[:3]:
            print(f"   ${f.price:.0f} - {f.airline} ({f.stops_str})")
    else:
        print("❌ No results returned")


def test_kiwi():
    """Test Kiwi provider."""
    print("\n" + "=" * 50)
    print("Testing Kiwi Provider")
    print("=" * 50)
    
    from providers.kiwi import KiwiProvider
    
    api_key = os.environ.get("KIWI_API_KEY")
    
    if not api_key:
        print("⏭️  Skipped - KIWI_API_KEY not set")
        return
    
    provider = KiwiProvider(api_key)
    
    # Test location search
    print("\n🔍 Testing location search for 'London'...")
    locations = provider.get_locations("London")
    if locations:
        print(f"✅ Found {len(locations)} locations")
        for loc in locations[:3]:
            print(f"   {loc['code']}: {loc['name']}, {loc['country']}")
    
    # Test flight search
    from providers.base import FlightSearch
    search = FlightSearch(
        origin="NYC",
        destination="LON",
        date=(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        passengers=1,
        max_results=3
    )
    
    print("\n🔍 Searching NYC → LON...")
    results = provider.search(search)
    
    if results:
        print(f"✅ Found {len(results)} flights")
        for f in results[:3]:
            print(f"   ${f.price:.0f} - {f.airline} ({f.stops_str})")
    else:
        print("❌ No results returned")


def test_serpapi():
    """Test SerpAPI provider."""
    print("\n" + "=" * 50)
    print("Testing SerpAPI Provider")
    print("=" * 50)
    
    from providers.serpapi import SerpAPIProvider
    
    api_key = os.environ.get("SERPAPI_KEY")
    
    if not api_key:
        print("⏭️  Skipped - SERPAPI_KEY not set")
        return
    
    provider = SerpAPIProvider(api_key)
    
    from providers.base import FlightSearch
    search = FlightSearch(
        origin="SFO",
        destination="NYC",
        date=(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        passengers=1,
        max_results=3
    )
    
    print("\n🔍 Searching SFO → NYC...")
    results = provider.search(search)
    
    if results:
        print(f"✅ Found {len(results)} flights")
        for f in results[:3]:
            print(f"   ${f.price:.0f} - {f.airline} ({f.stops_str})")
    else:
        print("❌ No results returned")


def test_alerts():
    """Test alert system."""
    print("\n" + "=" * 50)
    print("Testing Alert System")
    print("=" * 50)
    
    from alerts import AlertManager
    import tempfile
    
    # Use temp file for test
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        temp_path = f.name
    
    try:
        manager = AlertManager(temp_path)
        
        # Add alert
        alert = manager.add_alert(
            origin="JFK",
            destination="LAX",
            date="2024-06-15",
            target_price=200
        )
        print(f"✅ Created alert: {alert.id}")
        
        # List alerts
        alerts = manager.list_alerts()
        print(f"✅ Listed alerts: {len(alerts)} active")
        
        # Update price
        triggered, _ = manager.update_price(alert.id, 180)
        print(f"✅ Price update: triggered={triggered}")
        
        # Cleanup
        manager.remove_alert(alert.id)
        print(f"✅ Alert removed")
        
    finally:
        os.unlink(temp_path)


def test_formatters():
    """Test output formatters."""
    print("\n" + "=" * 50)
    print("Testing Formatters")
    print("=" * 50)
    
    from providers.base import Flight
    from datetime import datetime, timedelta
    from formatters import format_for_telegram, format_cheapest_dates
    
    # Create mock flights
    flights = [
        Flight(
            origin="JFK",
            destination="LAX",
            departure_time=datetime.now() + timedelta(days=30, hours=8),
            arrival_time=datetime.now() + timedelta(days=30, hours=14),
            price=299,
            airline="Delta",
            airline_code="DL",
            duration_minutes=360,
            stops=0,
            provider="test"
        ),
        Flight(
            origin="JFK",
            destination="LAX",
            departure_time=datetime.now() + timedelta(days=30, hours=10),
            arrival_time=datetime.now() + timedelta(days=30, hours=17),
            price=249,
            airline="United",
            airline_code="UA",
            duration_minutes=420,
            stops=1,
            stop_airports=["ORD"],
            provider="test"
        )
    ]
    
    output = format_for_telegram(flights)
    print("\n📱 Telegram format preview:")
    print("-" * 40)
    print(output)
    print("-" * 40)
    print("✅ Formatter working")


def main():
    print("\n🛫 Flight Search Integration Test Suite\n")
    
    # Test config
    if not test_config():
        print("\n❌ Configuration test failed. Exiting.")
        return
    
    # Test providers
    test_amadeus()
    test_kiwi()
    test_serpapi()
    
    # Test utilities
    test_alerts()
    test_formatters()
    
    print("\n" + "=" * 50)
    print("✅ All tests completed!")
    print("=" * 50)


if __name__ == "__main__":
    main()
