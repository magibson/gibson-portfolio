"""Kiwi.com Tequila API provider for flight search.

Docs: https://tequila.kiwi.com/portal/docs/tequila_api

Free tier: Unlimited API calls with affiliate model.
Great for budget carriers (Ryanair, EasyJet, etc.)
"""
import requests
from datetime import datetime, timedelta
from typing import Optional
import logging

from .base import FlightProvider, Flight, FlightSearch

logger = logging.getLogger(__name__)


class KiwiProvider(FlightProvider):
    """Kiwi.com Tequila API client."""
    
    name = "kiwi"
    BASE_URL = "https://api.tequila.kiwi.com"
    
    def __init__(self, api_key: str, affiliate_id: Optional[str] = None):
        self.api_key = api_key
        self.affiliate_id = affiliate_id
    
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    def _request(self, endpoint: str, params: dict) -> dict:
        """Make API request."""
        response = requests.get(
            f"{self.BASE_URL}{endpoint}",
            params=params,
            headers={"apikey": self.api_key}
        )
        response.raise_for_status()
        return response.json()
    
    def search(self, search: FlightSearch) -> list[Flight]:
        """Search for flights using Kiwi Search API."""
        # Kiwi uses DD/MM/YYYY format
        dep_date = self._format_date(search.date)
        
        params = {
            "fly_from": search.origin.upper(),
            "fly_to": search.destination.upper(),
            "date_from": dep_date,
            "date_to": dep_date,
            "adults": search.passengers,
            "curr": search.currency,
            "limit": search.max_results,
            "sort": "price",
            "vehicle_type": "aircraft"
        }
        
        if search.return_date:
            ret_date = self._format_date(search.return_date)
            params["return_from"] = ret_date
            params["return_to"] = ret_date
            params["flight_type"] = "round"
        else:
            params["flight_type"] = "oneway"
        
        # Cabin class mapping
        cabin_map = {
            "economy": "M",
            "premium_economy": "W",
            "business": "C",
            "first": "F"
        }
        params["selected_cabins"] = cabin_map.get(search.cabin_class, "M")
        
        try:
            data = self._request("/v2/search", params)
        except requests.HTTPError as e:
            logger.error(f"Kiwi search failed: {e}")
            return []
        
        return self._parse_results(data, search)
    
    def _format_date(self, date_str: str) -> str:
        """Convert YYYY-MM-DD to DD/MM/YYYY."""
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    
    def _parse_results(self, data: dict, search: FlightSearch) -> list[Flight]:
        """Parse Kiwi search response."""
        flights = []
        
        for item in data.get("data", []):
            try:
                # Parse route segments
                route = item.get("route", [])
                if not route:
                    continue
                
                # Find outbound and return segments
                outbound_segs = [r for r in route if r.get("return") == 0]
                return_segs = [r for r in route if r.get("return") == 1]
                
                if not outbound_segs:
                    continue
                
                first_seg = outbound_segs[0]
                last_seg = outbound_segs[-1]
                
                # Parse times
                departure = datetime.utcfromtimestamp(first_seg["dTime"])
                arrival = datetime.utcfromtimestamp(last_seg["aTime"])
                
                # Duration
                duration_mins = item.get("duration", {}).get("departure", 0) // 60
                
                # Stops
                stops = len(outbound_segs) - 1
                stop_airports = [seg["flyTo"] for seg in outbound_segs[:-1]]
                
                # Build booking URL with affiliate
                booking_url = item.get("deep_link", "")
                if self.affiliate_id and booking_url:
                    booking_url = f"{booking_url}&affil={self.affiliate_id}"
                
                flight = Flight(
                    origin=search.origin.upper(),
                    destination=search.destination.upper(),
                    departure_time=departure,
                    arrival_time=arrival,
                    price=float(item.get("price", 0)),
                    currency=search.currency,
                    airline=first_seg.get("airline", ""),
                    airline_code=first_seg.get("airline", ""),
                    flight_number=f"{first_seg.get('airline', '')}{first_seg.get('flight_no', '')}",
                    duration_minutes=duration_mins,
                    stops=stops,
                    stop_airports=stop_airports,
                    booking_url=booking_url,
                    deep_link=booking_url,
                    provider="kiwi",
                    cabin_class=search.cabin_class,
                    baggage_included=bool(item.get("bags_price", {}).get("1", 0) == 0)
                )
                
                # Return leg
                if return_segs:
                    ret_first = return_segs[0]
                    ret_last = return_segs[-1]
                    
                    flight.return_departure = datetime.utcfromtimestamp(ret_first["dTime"])
                    flight.return_arrival = datetime.utcfromtimestamp(ret_last["aTime"])
                    flight.return_airline = ret_first.get("airline", "")
                    flight.return_stops = len(return_segs) - 1
                
                flights.append(flight)
                
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Failed to parse Kiwi result: {e}")
                continue
        
        return flights
    
    def find_cheapest_dates(
        self, 
        origin: str, 
        destination: str, 
        month: str,
        return_days: int = 7
    ) -> dict:
        """Find cheapest dates in a month.
        
        Kiwi's range search is excellent for this.
        """
        # Parse month to get date range
        year, mon = map(int, month.split("-"))
        start = datetime(year, mon, 1)
        
        # Get end of month
        if mon == 12:
            end = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end = datetime(year, mon + 1, 1) - timedelta(days=1)
        
        params = {
            "fly_from": origin.upper(),
            "fly_to": destination.upper(),
            "date_from": start.strftime("%d/%m/%Y"),
            "date_to": end.strftime("%d/%m/%Y"),
            "adults": 1,
            "curr": "USD",
            "limit": 100,
            "sort": "price",
            "vehicle_type": "aircraft"
        }
        
        if return_days:
            params["nights_in_dst_from"] = return_days
            params["nights_in_dst_to"] = return_days
            params["flight_type"] = "round"
        else:
            params["flight_type"] = "oneway"
        
        try:
            data = self._request("/v2/search", params)
        except requests.HTTPError as e:
            logger.error(f"Kiwi cheapest dates failed: {e}")
            return {}
        
        # Group by departure date and find minimum
        results = {}
        for item in data.get("data", []):
            try:
                route = item.get("route", [])
                outbound = [r for r in route if r.get("return") == 0]
                if outbound:
                    dep_time = datetime.utcfromtimestamp(outbound[0]["dTime"])
                    date_str = dep_time.strftime("%Y-%m-%d")
                    price = float(item.get("price", 0))
                    
                    if date_str not in results or price < results[date_str]:
                        results[date_str] = price
            except (KeyError, ValueError):
                continue
        
        return dict(sorted(results.items()))
    
    def search_flexible(
        self,
        origin: str,
        destination: str,
        date: str,
        flexibility_days: int = 3,
        return_days: int = 7
    ) -> list[Flight]:
        """Search with flexible dates (±N days)."""
        dt = datetime.strptime(date, "%Y-%m-%d")
        start = dt - timedelta(days=flexibility_days)
        end = dt + timedelta(days=flexibility_days)
        
        params = {
            "fly_from": origin.upper(),
            "fly_to": destination.upper(),
            "date_from": start.strftime("%d/%m/%Y"),
            "date_to": end.strftime("%d/%m/%Y"),
            "adults": 1,
            "curr": "USD",
            "limit": 20,
            "sort": "price",
            "vehicle_type": "aircraft"
        }
        
        if return_days:
            params["nights_in_dst_from"] = return_days - 1
            params["nights_in_dst_to"] = return_days + 1
            params["flight_type"] = "round"
        
        try:
            data = self._request("/v2/search", params)
            return self._parse_results(data, FlightSearch(
                origin=origin,
                destination=destination,
                date=date,
                return_date=(dt + timedelta(days=return_days)).strftime("%Y-%m-%d") if return_days else None
            ))
        except requests.HTTPError:
            return []
    
    def get_locations(self, query: str) -> list[dict]:
        """Search for airport/city codes.
        
        Useful for resolving city names to IATA codes.
        """
        try:
            data = self._request("/locations/query", {
                "term": query,
                "location_types": "airport,city",
                "limit": 5
            })
            
            return [
                {
                    "code": loc.get("code"),
                    "name": loc.get("name"),
                    "city": loc.get("city", {}).get("name"),
                    "country": loc.get("country", {}).get("name"),
                    "type": loc.get("type")
                }
                for loc in data.get("locations", [])
            ]
        except requests.HTTPError:
            return []
