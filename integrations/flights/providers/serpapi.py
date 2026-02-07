"""SerpAPI Google Flights provider.

Docs: https://serpapi.com/google-flights-api

Free tier: 100 searches/month
Scrapes Google Flights for real-time data.
"""
import requests
from datetime import datetime, timedelta
from typing import Optional
import logging
import re

from .base import FlightProvider, Flight, FlightSearch

logger = logging.getLogger(__name__)


class SerpAPIProvider(FlightProvider):
    """SerpAPI Google Flights client."""
    
    name = "serpapi"
    BASE_URL = "https://serpapi.com/search"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    def search(self, search: FlightSearch) -> list[Flight]:
        """Search Google Flights via SerpAPI."""
        params = {
            "engine": "google_flights",
            "api_key": self.api_key,
            "departure_id": search.origin.upper(),
            "arrival_id": search.destination.upper(),
            "outbound_date": search.date,
            "currency": search.currency,
            "hl": "en",
            "adults": search.passengers
        }
        
        if search.return_date:
            params["return_date"] = search.return_date
            params["type"] = "1"  # Round trip
        else:
            params["type"] = "2"  # One way
        
        # Cabin class
        cabin_map = {
            "economy": "1",
            "premium_economy": "2", 
            "business": "3",
            "first": "4"
        }
        params["travel_class"] = cabin_map.get(search.cabin_class, "1")
        
        try:
            response = requests.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
        except requests.HTTPError as e:
            logger.error(f"SerpAPI search failed: {e}")
            return []
        
        return self._parse_results(data, search)
    
    def _parse_results(self, data: dict, search: FlightSearch) -> list[Flight]:
        """Parse SerpAPI Google Flights response."""
        flights = []
        
        # Best flights (Google's recommendations)
        best_flights = data.get("best_flights", [])
        other_flights = data.get("other_flights", [])
        
        all_flights = best_flights + other_flights
        
        for item in all_flights[:search.max_results]:
            try:
                # Get flight legs
                legs = item.get("flights", [])
                if not legs:
                    continue
                
                first_leg = legs[0]
                last_leg = legs[-1]
                
                # Parse departure/arrival
                departure = self._parse_datetime(
                    first_leg.get("departure_airport", {}).get("time")
                )
                arrival = self._parse_datetime(
                    last_leg.get("arrival_airport", {}).get("time")
                )
                
                if not departure or not arrival:
                    continue
                
                # Duration
                duration_mins = item.get("total_duration", 0)
                
                # Stops
                stops = len(legs) - 1
                stop_airports = []
                for leg in legs[:-1]:
                    arr_airport = leg.get("arrival_airport", {}).get("id", "")
                    if arr_airport:
                        stop_airports.append(arr_airport)
                
                # Price
                price = float(item.get("price", 0))
                
                # Airline
                airline = first_leg.get("airline", "")
                
                flight = Flight(
                    origin=search.origin.upper(),
                    destination=search.destination.upper(),
                    departure_time=departure,
                    arrival_time=arrival,
                    price=price,
                    currency=search.currency,
                    airline=airline,
                    airline_code=first_leg.get("airline_logo", "").split("/")[-1].split(".")[0].upper() if first_leg.get("airline_logo") else "",
                    flight_number=first_leg.get("flight_number", ""),
                    duration_minutes=duration_mins,
                    stops=stops,
                    stop_airports=stop_airports,
                    provider="serpapi",
                    cabin_class=search.cabin_class,
                    baggage_included=self._has_baggage(item)
                )
                
                # Check for return flight in layovers structure
                layovers = item.get("layovers", [])
                if search.return_date and len(legs) > 1:
                    # Try to identify return leg (this is tricky with Google's format)
                    # Usually the return is in a separate "flights" array
                    pass
                
                flights.append(flight)
                
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Failed to parse SerpAPI result: {e}")
                continue
        
        return flights
    
    def _parse_datetime(self, time_str: Optional[str]) -> Optional[datetime]:
        """Parse time string from Google Flights."""
        if not time_str:
            return None
        
        # Format is usually "2024-03-15 14:30" or similar
        formats = [
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(time_str[:len(fmt.replace("%", ""))], fmt)
            except ValueError:
                continue
        
        return None
    
    def _has_baggage(self, item: dict) -> bool:
        """Check if flight includes checked baggage."""
        # Check extensions for baggage info
        extensions = item.get("extensions", [])
        for ext in extensions:
            if isinstance(ext, str) and "bag" in ext.lower():
                return "included" in ext.lower() or "free" in ext.lower()
        return False
    
    def find_cheapest_dates(
        self, 
        origin: str, 
        destination: str, 
        month: str,
        return_days: int = 7
    ) -> dict:
        """Find cheapest dates by sampling.
        
        SerpAPI doesn't have a dedicated cheapest dates endpoint,
        so we sample specific dates.
        """
        year, mon = map(int, month.split("-"))
        
        results = {}
        current = datetime(year, mon, 1)
        
        # Sample every 4 days to conserve API calls
        while current.month == mon:
            search = FlightSearch(
                origin=origin,
                destination=destination,
                date=current.strftime("%Y-%m-%d"),
                return_date=(current + timedelta(days=return_days)).strftime("%Y-%m-%d") if return_days else None,
                passengers=1,
                max_results=1
            )
            
            flights = self.search(search)
            if flights:
                results[current.strftime("%Y-%m-%d")] = flights[0].price
            
            current += timedelta(days=4)
        
        return results
    
    def get_price_insights(
        self,
        origin: str,
        destination: str,
        date: str
    ) -> Optional[dict]:
        """Get Google's price insights if available."""
        params = {
            "engine": "google_flights",
            "api_key": self.api_key,
            "departure_id": origin.upper(),
            "arrival_id": destination.upper(),
            "outbound_date": date,
            "type": "2",
            "currency": "USD"
        }
        
        try:
            response = requests.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            insights = data.get("price_insights", {})
            if insights:
                return {
                    "lowest_price": insights.get("lowest_price"),
                    "typical_price_range": insights.get("typical_price_range"),
                    "price_level": insights.get("price_level"),  # low, typical, high
                    "raw": insights
                }
        except requests.HTTPError:
            pass
        
        return None
