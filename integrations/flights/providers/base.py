"""Base provider interface for flight search."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Flight:
    """Normalized flight result."""
    # Route info
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    
    # Price
    price: float
    currency: str = "USD"
    
    # Flight details
    airline: str = ""
    airline_code: str = ""
    flight_number: str = ""
    
    # Duration & stops
    duration_minutes: int = 0
    stops: int = 0
    stop_airports: list = field(default_factory=list)
    
    # Booking
    booking_url: str = ""
    deep_link: str = ""
    
    # Return leg (for round trips)
    return_departure: Optional[datetime] = None
    return_arrival: Optional[datetime] = None
    return_airline: str = ""
    return_stops: int = 0
    
    # Meta
    provider: str = ""
    cabin_class: str = "economy"
    baggage_included: bool = False
    
    @property
    def duration_str(self) -> str:
        """Human readable duration."""
        hours = self.duration_minutes // 60
        mins = self.duration_minutes % 60
        if hours and mins:
            return f"{hours}h {mins}m"
        elif hours:
            return f"{hours}h"
        return f"{mins}m"
    
    @property
    def stops_str(self) -> str:
        """Human readable stops."""
        if self.stops == 0:
            return "Direct"
        elif self.stops == 1:
            return f"1 stop"
        return f"{self.stops} stops"


@dataclass 
class FlightSearch:
    """Search parameters."""
    origin: str
    destination: str
    date: str  # YYYY-MM-DD
    return_date: Optional[str] = None
    passengers: int = 1
    cabin_class: str = "economy"
    currency: str = "USD"
    max_results: int = 10


class FlightProvider(ABC):
    """Base class for flight search providers."""
    
    name: str = "base"
    
    @abstractmethod
    def search(self, search: FlightSearch) -> list[Flight]:
        """Search for flights."""
        pass
    
    @abstractmethod
    def find_cheapest_dates(
        self, 
        origin: str, 
        destination: str, 
        month: str,  # YYYY-MM
        return_days: int = 7
    ) -> dict:
        """Find cheapest dates in a month.
        
        Returns dict of {date: lowest_price}
        """
        pass
    
    def is_configured(self) -> bool:
        """Check if provider has valid credentials."""
        return False
