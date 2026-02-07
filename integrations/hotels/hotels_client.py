#!/usr/bin/env python3
"""
Hotel Search Client - Search and compare hotel prices across platforms.

Uses SerpAPI's Google Hotels API for aggregated search results.
Optionally supports Amadeus for direct booking capabilities.

Usage:
    from hotels_client import HotelSearchClient
    client = HotelSearchClient()
    results = client.search_hotels("Paris", "2024-06-01", "2024-06-05")
"""

import json
import os
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from pathlib import Path


class HotelSearchClient:
    """Client for searching hotels across multiple platforms."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize client with config file or environment variables."""
        self.config = self._load_config(config_path)
        self.serpapi_key = self.config.get("serpapi", {}).get("api_key") or os.environ.get("SERPAPI_KEY")
        self.serpapi_url = self.config.get("serpapi", {}).get("base_url", "https://serpapi.com/search.json")
        
        # Amadeus (optional)
        self.amadeus_key = self.config.get("amadeus", {}).get("api_key") or os.environ.get("AMADEUS_API_KEY")
        self.amadeus_secret = self.config.get("amadeus", {}).get("api_secret") or os.environ.get("AMADEUS_API_SECRET")
        self.amadeus_url = self.config.get("amadeus", {}).get("base_url", "https://test.api.amadeus.com")
        self.amadeus_token = None
        
        # Defaults
        defaults = self.config.get("defaults", {})
        self.default_currency = defaults.get("currency", "USD")
        self.default_language = defaults.get("language", "en")
        self.default_country = defaults.get("country", "us")
        self.default_adults = defaults.get("adults", 2)
        self.default_children = defaults.get("children", 0)
        self.default_rooms = defaults.get("rooms", 1)
        
        # Simple in-memory cache
        self._cache = {}
        self._cache_ttl = self.config.get("cache", {}).get("ttl_minutes", 30) * 60
    
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration from file."""
        if config_path is None:
            # Try default locations
            for path in ["config.json", Path(__file__).parent / "config.json"]:
                if Path(path).exists():
                    config_path = str(path)
                    break
        
        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                return json.load(f)
        return {}
    
    def _get_cache_key(self, method: str, **kwargs) -> str:
        """Generate cache key from method and params."""
        return f"{method}:{json.dumps(kwargs, sort_keys=True)}"
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in self._cache:
            entry = self._cache[key]
            if datetime.now().timestamp() < entry["expires"]:
                return entry["data"]
            del self._cache[key]
        return None
    
    def _set_cached(self, key: str, data: Any):
        """Set value in cache with TTL."""
        self._cache[key] = {
            "data": data,
            "expires": datetime.now().timestamp() + self._cache_ttl
        }
    
    # =========================================================================
    # SERPAPI (Google Hotels) Methods
    # =========================================================================
    
    def search_hotels(
        self,
        city: str,
        checkin: str,
        checkout: str,
        guests: Optional[int] = None,
        rooms: Optional[int] = None,
        currency: Optional[str] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        rating: Optional[float] = None,
        hotel_class: Optional[int] = None,
        amenities: Optional[List[str]] = None,
        sort_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search for hotels in a city.
        
        Args:
            city: City name or search query (e.g., "Paris", "NYC hotels near Times Square")
            checkin: Check-in date (YYYY-MM-DD)
            checkout: Check-out date (YYYY-MM-DD)
            guests: Number of guests (adults)
            rooms: Number of rooms
            currency: Currency code (USD, EUR, etc.)
            min_price: Minimum price filter
            max_price: Maximum price filter
            rating: Minimum rating filter (e.g., 4.0)
            hotel_class: Minimum star rating (2-5)
            amenities: List of required amenities
            sort_by: Sort order (lowest_price, highest_rating, most_reviewed)
        
        Returns:
            Dict with 'properties', 'brands', 'search_info' keys
        """
        if not self.serpapi_key:
            return {"error": "SerpAPI key not configured. Set SERPAPI_KEY or add to config.json"}
        
        # Check cache
        cache_key = self._get_cache_key("search", city=city, checkin=checkin, checkout=checkout, 
                                        guests=guests, rooms=rooms, currency=currency)
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        params = {
            "engine": "google_hotels",
            "q": city if "hotel" in city.lower() else f"{city} hotels",
            "check_in_date": checkin,
            "check_out_date": checkout,
            "adults": guests or self.default_adults,
            "children": self.default_children,
            "currency": currency or self.default_currency,
            "gl": self.default_country,
            "hl": self.default_language,
            "api_key": self.serpapi_key,
        }
        
        # Add optional filters
        if min_price:
            params["min_price"] = min_price
        if max_price:
            params["max_price"] = max_price
        if rating:
            params["rating"] = rating
        if hotel_class:
            params["hotel_class"] = hotel_class
        if sort_by:
            sort_map = {
                "lowest_price": 3,
                "highest_rating": 8,
                "most_reviewed": 5,
            }
            params["sort_by"] = sort_map.get(sort_by, sort_by)
        
        try:
            response = requests.get(self.serpapi_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            result = {
                "properties": data.get("properties", []),
                "ads": data.get("ads", []),
                "brands": data.get("brands", []),
                "search_info": data.get("search_information", {}),
                "search_params": data.get("search_parameters", {}),
            }
            
            # Apply amenity filter (client-side if needed)
            if amenities:
                result["properties"] = [
                    p for p in result["properties"]
                    if all(a.lower() in [x.lower() for x in p.get("amenities", [])] for a in amenities)
                ]
            
            self._set_cached(cache_key, result)
            return result
            
        except requests.exceptions.RequestException as e:
            return {"error": f"Search failed: {str(e)}"}
    
    def get_hotel_details(
        self,
        hotel_id: str,
        checkin: Optional[str] = None,
        checkout: Optional[str] = None,
        guests: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get detailed information about a specific hotel.
        
        Args:
            hotel_id: Property token from search results
            checkin: Check-in date for pricing (YYYY-MM-DD)
            checkout: Check-out date for pricing (YYYY-MM-DD)
            guests: Number of guests
        
        Returns:
            Dict with hotel details including prices, amenities, reviews
        """
        if not self.serpapi_key:
            return {"error": "SerpAPI key not configured"}
        
        # Default dates if not provided
        if not checkin:
            checkin = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        if not checkout:
            checkout = (datetime.now() + timedelta(days=31)).strftime("%Y-%m-%d")
        
        params = {
            "engine": "google_hotels",
            "property_token": hotel_id,
            "check_in_date": checkin,
            "check_out_date": checkout,
            "adults": guests or self.default_adults,
            "currency": self.default_currency,
            "gl": self.default_country,
            "hl": self.default_language,
            "api_key": self.serpapi_key,
        }
        
        try:
            response = requests.get(self.serpapi_url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Failed to get hotel details: {str(e)}"}
    
    def compare_prices(
        self,
        hotel_name: str,
        checkin: str,
        checkout: str,
        city: Optional[str] = None,
        guests: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Compare prices for a specific hotel across booking platforms.
        
        Args:
            hotel_name: Name of the hotel
            checkin: Check-in date (YYYY-MM-DD)
            checkout: Check-out date (YYYY-MM-DD)
            city: City name (helps narrow search)
            guests: Number of guests
        
        Returns:
            Dict with hotel info and price comparison across platforms
        """
        # Search for the hotel
        query = f"{hotel_name} {city}" if city else hotel_name
        results = self.search_hotels(query, checkin, checkout, guests)
        
        if "error" in results:
            return results
        
        # Find best match
        properties = results.get("properties", []) + results.get("ads", [])
        if not properties:
            return {"error": f"No hotels found matching '{hotel_name}'"}
        
        # Score matches by name similarity
        def name_score(prop):
            prop_name = prop.get("name", "").lower()
            search_name = hotel_name.lower()
            if search_name == prop_name:
                return 100
            if search_name in prop_name:
                return 80
            # Count matching words
            search_words = set(search_name.split())
            prop_words = set(prop_name.split())
            return len(search_words & prop_words) * 20
        
        best_match = max(properties, key=name_score)
        
        # Get detailed pricing if we have a property token
        if "property_token" in best_match:
            details = self.get_hotel_details(
                best_match["property_token"],
                checkin, checkout, guests
            )
            if "error" not in details:
                best_match = {**best_match, **details}
        
        # Extract prices from different sources
        prices = []
        
        # From direct prices array
        for price_info in best_match.get("prices", []):
            prices.append({
                "source": price_info.get("source", "Unknown"),
                "price": price_info.get("rate_per_night", {}).get("extracted_lowest") or 
                        price_info.get("extracted_price"),
                "price_display": price_info.get("rate_per_night", {}).get("lowest") or 
                               price_info.get("price"),
            })
        
        # From main result
        if best_match.get("source"):
            main_price = {
                "source": best_match.get("source"),
                "price": best_match.get("extracted_price") or 
                        best_match.get("rate_per_night", {}).get("extracted_lowest"),
                "price_display": best_match.get("price") or 
                               best_match.get("rate_per_night", {}).get("lowest"),
            }
            if main_price["price"] and main_price not in prices:
                prices.insert(0, main_price)
        
        # Sort by price
        prices = [p for p in prices if p.get("price")]
        prices.sort(key=lambda x: x["price"])
        
        return {
            "hotel": {
                "name": best_match.get("name"),
                "rating": best_match.get("overall_rating"),
                "reviews": best_match.get("reviews"),
                "hotel_class": best_match.get("hotel_class"),
                "address": best_match.get("address"),
                "amenities": best_match.get("amenities", [])[:10],
                "thumbnail": best_match.get("thumbnail"),
            },
            "dates": {
                "checkin": checkin,
                "checkout": checkout,
                "nights": self._nights_between(checkin, checkout),
            },
            "prices": prices,
            "lowest_price": prices[0] if prices else None,
            "savings": self._calc_savings(prices) if len(prices) > 1 else None,
        }
    
    def find_deals(
        self,
        city: str,
        checkin: str,
        checkout: str,
        max_price: int,
        guests: Optional[int] = None,
        min_rating: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Find hotel deals under a maximum price.
        
        Args:
            city: City name
            checkin: Check-in date (YYYY-MM-DD)
            checkout: Check-out date (YYYY-MM-DD)
            max_price: Maximum price per night
            guests: Number of guests
            min_rating: Minimum rating filter
        
        Returns:
            Dict with list of deals sorted by value (rating/price ratio)
        """
        results = self.search_hotels(
            city, checkin, checkout, guests,
            max_price=max_price,
            rating=min_rating,
            sort_by="lowest_price"
        )
        
        if "error" in results:
            return results
        
        deals = []
        for prop in results.get("properties", []):
            price = (prop.get("rate_per_night", {}).get("extracted_lowest") or 
                    prop.get("extracted_price"))
            rating = prop.get("overall_rating")
            
            if price and price <= max_price:
                # Calculate value score (rating per dollar)
                value_score = (rating or 3.0) / price * 100 if price > 0 else 0
                
                deals.append({
                    "name": prop.get("name"),
                    "price": price,
                    "price_display": prop.get("rate_per_night", {}).get("lowest") or prop.get("price"),
                    "rating": rating,
                    "reviews": prop.get("reviews"),
                    "hotel_class": prop.get("hotel_class"),
                    "amenities": prop.get("amenities", [])[:5],
                    "thumbnail": prop.get("thumbnail"),
                    "free_cancellation": prop.get("free_cancellation", False),
                    "value_score": round(value_score, 2),
                    "property_token": prop.get("property_token"),
                })
        
        # Sort by value score (best deals first)
        deals.sort(key=lambda x: x["value_score"], reverse=True)
        
        return {
            "city": city,
            "dates": {
                "checkin": checkin,
                "checkout": checkout,
                "nights": self._nights_between(checkin, checkout),
            },
            "max_price": max_price,
            "deals": deals[:20],  # Top 20 deals
            "total_found": len(deals),
        }
    
    # =========================================================================
    # Amadeus Methods (Optional - for direct booking)
    # =========================================================================
    
    def _get_amadeus_token(self) -> Optional[str]:
        """Get OAuth token for Amadeus API."""
        if not self.amadeus_key or not self.amadeus_secret:
            return None
        
        if self.amadeus_token:
            return self.amadeus_token
        
        try:
            response = requests.post(
                f"{self.amadeus_url}/v1/security/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.amadeus_key,
                    "client_secret": self.amadeus_secret,
                },
                timeout=10
            )
            response.raise_for_status()
            self.amadeus_token = response.json()["access_token"]
            return self.amadeus_token
        except Exception:
            return None
    
    def search_hotels_amadeus(
        self,
        city_code: str,
        checkin: str,
        checkout: str,
        guests: int = 2,
    ) -> Dict[str, Any]:
        """
        Search hotels using Amadeus API (alternative source).
        
        Args:
            city_code: IATA city code (e.g., PAR, NYC, LON)
            checkin: Check-in date (YYYY-MM-DD)
            checkout: Check-out date (YYYY-MM-DD)
            guests: Number of guests
        
        Returns:
            Dict with hotel search results from Amadeus
        """
        token = self._get_amadeus_token()
        if not token:
            return {"error": "Amadeus credentials not configured"}
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 1: Get hotel list by city
        try:
            list_response = requests.get(
                f"{self.amadeus_url}/v1/reference-data/locations/hotels/by-city",
                headers=headers,
                params={"cityCode": city_code},
                timeout=15
            )
            list_response.raise_for_status()
            hotels = list_response.json().get("data", [])[:50]  # Limit for search
            
            if not hotels:
                return {"error": f"No hotels found in city: {city_code}"}
            
            # Step 2: Search availability
            hotel_ids = [h["hotelId"] for h in hotels]
            search_response = requests.get(
                f"{self.amadeus_url}/v3/shopping/hotel-offers",
                headers=headers,
                params={
                    "hotelIds": ",".join(hotel_ids[:20]),
                    "checkInDate": checkin,
                    "checkOutDate": checkout,
                    "adults": guests,
                    "currency": self.default_currency,
                },
                timeout=30
            )
            search_response.raise_for_status()
            
            return search_response.json()
            
        except requests.exceptions.RequestException as e:
            return {"error": f"Amadeus search failed: {str(e)}"}
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def _nights_between(self, checkin: str, checkout: str) -> int:
        """Calculate nights between two dates."""
        try:
            d1 = datetime.strptime(checkin, "%Y-%m-%d")
            d2 = datetime.strptime(checkout, "%Y-%m-%d")
            return (d2 - d1).days
        except:
            return 1
    
    def _calc_savings(self, prices: List[Dict]) -> Dict:
        """Calculate potential savings between lowest and highest price."""
        if len(prices) < 2:
            return None
        sorted_prices = sorted(prices, key=lambda x: x["price"])
        lowest = sorted_prices[0]["price"]
        highest = sorted_prices[-1]["price"]
        return {
            "amount": highest - lowest,
            "percentage": round((highest - lowest) / highest * 100, 1),
            "best_source": sorted_prices[0]["source"],
            "worst_source": sorted_prices[-1]["source"],
        }
    
    def validate_dates(self, checkin: str, checkout: str) -> tuple[bool, str]:
        """Validate check-in and check-out dates."""
        try:
            d_in = datetime.strptime(checkin, "%Y-%m-%d")
            d_out = datetime.strptime(checkout, "%Y-%m-%d")
            
            if d_in < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
                return False, "Check-in date cannot be in the past"
            
            if d_out <= d_in:
                return False, "Check-out must be after check-in"
            
            if (d_out - d_in).days > 30:
                return False, "Maximum stay is 30 nights"
            
            return True, "Valid"
        except ValueError:
            return False, "Invalid date format. Use YYYY-MM-DD"


# CLI for testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Hotel Search Client")
    parser.add_argument("--test", action="store_true", help="Run test search")
    parser.add_argument("--city", default="Paris", help="City to search")
    parser.add_argument("--checkin", help="Check-in date (YYYY-MM-DD)")
    parser.add_argument("--checkout", help="Check-out date (YYYY-MM-DD)")
    parser.add_argument("--guests", type=int, default=2, help="Number of guests")
    parser.add_argument("--max-price", type=int, help="Max price for deals search")
    
    args = parser.parse_args()
    
    client = HotelSearchClient()
    
    # Default dates if not provided
    if not args.checkin:
        args.checkin = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    if not args.checkout:
        args.checkout = (datetime.now() + timedelta(days=32)).strftime("%Y-%m-%d")
    
    if args.test:
        print(f"Testing hotel search for {args.city}...")
        print(f"Dates: {args.checkin} to {args.checkout}")
        print()
        
        results = client.search_hotels(
            args.city, args.checkin, args.checkout, args.guests
        )
        
        if "error" in results:
            print(f"Error: {results['error']}")
        else:
            print(f"Found {len(results.get('properties', []))} hotels")
            print()
            for i, hotel in enumerate(results.get("properties", [])[:5], 1):
                price = hotel.get("rate_per_night", {}).get("lowest") or hotel.get("price", "N/A")
                rating = hotel.get("overall_rating", "N/A")
                print(f"{i}. {hotel.get('name')}")
                print(f"   Price: {price}/night | Rating: {rating}⭐")
                print()
