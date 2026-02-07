"""Amadeus API provider for flight search.

Docs: https://developers.amadeus.com/self-service/category/flights

Free tier: 2,000 API calls/month in test environment.
"""
import requests
from datetime import datetime, timedelta
from typing import Optional
import logging

from .base import FlightProvider, Flight, FlightSearch

logger = logging.getLogger(__name__)


class AmadeusProvider(FlightProvider):
    """Amadeus Self-Service API client."""
    
    name = "amadeus"
    
    # API endpoints
    TEST_URL = "https://test.api.amadeus.com"
    PROD_URL = "https://api.amadeus.com"
    
    def __init__(
        self, 
        api_key: str, 
        api_secret: str,
        environment: str = "test"
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = self.PROD_URL if environment == "production" else self.TEST_URL
        self._token = None
        self._token_expires = None
    
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_secret)
    
    def _get_token(self) -> str:
        """Get or refresh OAuth2 token."""
        # Return cached token if still valid
        if self._token and self._token_expires and datetime.now() < self._token_expires:
            return self._token
        
        response = requests.post(
            f"{self.base_url}/v1/security/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.api_secret
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        response.raise_for_status()
        
        data = response.json()
        self._token = data["access_token"]
        # Token typically valid for 30 minutes, refresh early
        self._token_expires = datetime.now() + timedelta(seconds=data.get("expires_in", 1799) - 60)
        
        return self._token
    
    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make authenticated API request."""
        token = self._get_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        
        response = requests.request(
            method,
            f"{self.base_url}{endpoint}",
            headers=headers,
            **kwargs
        )
        
        if response.status_code == 401:
            # Token expired, refresh and retry
            self._token = None
            token = self._get_token()
            headers["Authorization"] = f"Bearer {token}"
            response = requests.request(
                method,
                f"{self.base_url}{endpoint}",
                headers=headers,
                **kwargs
            )
        
        response.raise_for_status()
        return response.json()
    
    def search(self, search: FlightSearch) -> list[Flight]:
        """Search for flights using Amadeus Flight Offers Search API."""
        params = {
            "originLocationCode": search.origin.upper(),
            "destinationLocationCode": search.destination.upper(),
            "departureDate": search.date,
            "adults": search.passengers,
            "currencyCode": search.currency,
            "max": search.max_results,
            "nonStop": "false"
        }
        
        if search.return_date:
            params["returnDate"] = search.return_date
        
        cabin_map = {
            "economy": "ECONOMY",
            "premium_economy": "PREMIUM_ECONOMY",
            "business": "BUSINESS",
            "first": "FIRST"
        }
        if search.cabin_class in cabin_map:
            params["travelClass"] = cabin_map[search.cabin_class]
        
        try:
            data = self._request("GET", "/v2/shopping/flight-offers", params=params)
        except requests.HTTPError as e:
            logger.error(f"Amadeus search failed: {e}")
            return []
        
        return self._parse_offers(data, search)
    
    def _parse_offers(self, data: dict, search: FlightSearch) -> list[Flight]:
        """Parse Amadeus flight offers response."""
        flights = []
        
        # Build carrier lookup from dictionaries
        carriers = data.get("dictionaries", {}).get("carriers", {})
        
        for offer in data.get("data", []):
            try:
                price = float(offer["price"]["total"])
                currency = offer["price"]["currency"]
                
                # Parse outbound segment
                outbound = offer["itineraries"][0]
                first_seg = outbound["segments"][0]
                last_seg = outbound["segments"][-1]
                
                departure = datetime.fromisoformat(first_seg["departure"]["at"].replace("Z", "+00:00"))
                arrival = datetime.fromisoformat(last_seg["arrival"]["at"].replace("Z", "+00:00"))
                
                # Calculate duration from ISO 8601 duration (PT2H30M)
                duration_str = outbound.get("duration", "PT0M")
                duration_mins = self._parse_duration(duration_str)
                
                # Stops
                stops = len(outbound["segments"]) - 1
                stop_airports = [
                    seg["arrival"]["iataCode"] 
                    for seg in outbound["segments"][:-1]
                ]
                
                # Airline
                airline_code = first_seg.get("carrierCode", "")
                airline_name = carriers.get(airline_code, airline_code)
                
                flight = Flight(
                    origin=search.origin.upper(),
                    destination=search.destination.upper(),
                    departure_time=departure,
                    arrival_time=arrival,
                    price=price,
                    currency=currency,
                    airline=airline_name,
                    airline_code=airline_code,
                    flight_number=f"{airline_code}{first_seg.get('number', '')}",
                    duration_minutes=duration_mins,
                    stops=stops,
                    stop_airports=stop_airports,
                    provider="amadeus",
                    cabin_class=search.cabin_class,
                    baggage_included=self._has_baggage(offer)
                )
                
                # Parse return leg if round trip
                if len(offer["itineraries"]) > 1:
                    inbound = offer["itineraries"][1]
                    ret_first = inbound["segments"][0]
                    ret_last = inbound["segments"][-1]
                    
                    flight.return_departure = datetime.fromisoformat(
                        ret_first["departure"]["at"].replace("Z", "+00:00")
                    )
                    flight.return_arrival = datetime.fromisoformat(
                        ret_last["arrival"]["at"].replace("Z", "+00:00")
                    )
                    flight.return_airline = carriers.get(
                        ret_first.get("carrierCode", ""),
                        ret_first.get("carrierCode", "")
                    )
                    flight.return_stops = len(inbound["segments"]) - 1
                
                flights.append(flight)
                
            except (KeyError, ValueError, IndexError) as e:
                logger.warning(f"Failed to parse offer: {e}")
                continue
        
        return flights
    
    def _parse_duration(self, duration: str) -> int:
        """Parse ISO 8601 duration (PT2H30M) to minutes."""
        if not duration.startswith("PT"):
            return 0
        
        duration = duration[2:]  # Remove PT
        hours = 0
        minutes = 0
        
        if "H" in duration:
            h_part, duration = duration.split("H")
            hours = int(h_part)
        
        if "M" in duration:
            m_part = duration.replace("M", "")
            if m_part:
                minutes = int(m_part)
        
        return hours * 60 + minutes
    
    def _has_baggage(self, offer: dict) -> bool:
        """Check if offer includes checked baggage."""
        try:
            for pax_seg in offer.get("travelerPricings", [{}])[0].get("fareDetailsBySegment", []):
                baggage = pax_seg.get("includedCheckedBags", {})
                if baggage.get("quantity", 0) > 0 or baggage.get("weight", 0) > 0:
                    return True
        except (KeyError, IndexError):
            pass
        return False
    
    def find_cheapest_dates(
        self, 
        origin: str, 
        destination: str, 
        month: str,
        return_days: int = 7
    ) -> dict:
        """Find cheapest dates using Flight Inspiration Search.
        
        Note: This endpoint is limited in the free tier.
        Falls back to sampling specific dates if needed.
        """
        # Try the dedicated cheapest dates endpoint first
        try:
            params = {
                "origin": origin.upper(),
                "destination": destination.upper(),
                "departureDate": f"{month}-01",
                "oneWay": "false" if return_days else "true",
                "viewBy": "DATE"
            }
            
            data = self._request("GET", "/v1/shopping/flight-dates", params=params)
            
            results = {}
            for item in data.get("data", []):
                date = item.get("departureDate")
                price = float(item.get("price", {}).get("total", 0))
                if date and price:
                    results[date] = price
            
            return results
            
        except requests.HTTPError as e:
            logger.warning(f"Flight dates endpoint failed: {e}, falling back to sampling")
            return self._sample_dates(origin, destination, month, return_days)
    
    def _sample_dates(
        self, 
        origin: str, 
        destination: str, 
        month: str,
        return_days: int
    ) -> dict:
        """Sample specific dates to find cheapest (fallback method)."""
        from datetime import date
        
        # Parse month
        year, mon = map(int, month.split("-"))
        
        # Sample every 3 days in the month
        results = {}
        current = date(year, mon, 1)
        
        while current.month == mon:
            search = FlightSearch(
                origin=origin,
                destination=destination,
                date=current.isoformat(),
                return_date=(current + timedelta(days=return_days)).isoformat() if return_days else None,
                passengers=1,
                max_results=1
            )
            
            flights = self.search(search)
            if flights:
                results[current.isoformat()] = flights[0].price
            
            current += timedelta(days=3)
        
        return results
    
    def get_price_prediction(
        self, 
        origin: str, 
        destination: str, 
        date: str
    ) -> Optional[dict]:
        """Get price prediction (will price go up or down?).
        
        Returns dict with 'recommendation' (BUY/WAIT) and confidence.
        Requires production access for full accuracy.
        """
        try:
            params = {
                "originLocationCode": origin.upper(),
                "destinationLocationCode": destination.upper(),
                "departureDate": date,
                "currencyCode": "USD"
            }
            
            data = self._request("GET", "/v1/shopping/flight-offers/prediction", params=params)
            
            # Parse prediction
            for item in data.get("data", []):
                return {
                    "recommendation": item.get("result", "UNKNOWN"),
                    "confidence": item.get("confidence", 0),
                    "raw": item
                }
                
        except requests.HTTPError:
            return None
        
        return None
