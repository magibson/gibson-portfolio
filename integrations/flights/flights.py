"""
Flight Search Client - Main Interface

Usage:
    from flights import FlightSearch
    
    fs = FlightSearch()
    results = fs.search('JFK', 'LAX', '2024-03-15')
    print(fs.format_for_telegram(results))
"""
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from providers.base import Flight, FlightSearch as SearchParams
from providers.amadeus import AmadeusProvider
from providers.kiwi import KiwiProvider
from providers.serpapi import SerpAPIProvider
from formatters import (
    format_for_telegram,
    format_cheapest_dates,
    format_price_alert,
    format_comparison
)
from alerts import AlertManager, PriceTracker

logger = logging.getLogger(__name__)


class FlightSearchClient:
    """Unified flight search client supporting multiple providers."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize with config file or environment variables."""
        self.config = self._load_config(config_path)
        self.providers = self._init_providers()
        self.default_provider = self.config.get("default_provider", "amadeus")
        
        # Initialize alert manager
        alerts_config = self.config.get("alerts", {})
        self.alerts = AlertManager(alerts_config.get("storage_path"))
        self.price_tracker = PriceTracker()
    
    def _load_config(self, config_path: Optional[str]) -> dict:
        """Load configuration from file or environment."""
        config = {}
        
        # Try config file first
        if config_path:
            path = Path(config_path)
        else:
            # Look in common locations
            candidates = [
                Path(__file__).parent / "config.yaml",
                Path(__file__).parent / "config.yml",
                Path.home() / ".config" / "flights" / "config.yaml"
            ]
            path = next((p for p in candidates if p.exists()), None)
        
        if path and path.exists():
            with open(path) as f:
                config = yaml.safe_load(f) or {}
        
        # Override with environment variables
        env_mapping = {
            "AMADEUS_API_KEY": ("amadeus", "api_key"),
            "AMADEUS_API_SECRET": ("amadeus", "api_secret"),
            "KIWI_API_KEY": ("kiwi", "api_key"),
            "SERPAPI_KEY": ("serpapi", "api_key")
        }
        
        for env_var, (section, key) in env_mapping.items():
            value = os.environ.get(env_var)
            if value:
                if section not in config:
                    config[section] = {}
                config[section][key] = value
        
        return config
    
    def _init_providers(self) -> dict:
        """Initialize available providers."""
        providers = {}
        
        # Amadeus
        amadeus_cfg = self.config.get("amadeus", {})
        if amadeus_cfg.get("api_key") and amadeus_cfg.get("api_secret"):
            providers["amadeus"] = AmadeusProvider(
                api_key=amadeus_cfg["api_key"],
                api_secret=amadeus_cfg["api_secret"],
                environment=amadeus_cfg.get("environment", "test")
            )
        
        # Kiwi
        kiwi_cfg = self.config.get("kiwi", {})
        if kiwi_cfg.get("api_key"):
            providers["kiwi"] = KiwiProvider(
                api_key=kiwi_cfg["api_key"],
                affiliate_id=kiwi_cfg.get("affiliate_id")
            )
        
        # SerpAPI
        serpapi_cfg = self.config.get("serpapi", {})
        if serpapi_cfg.get("api_key"):
            providers["serpapi"] = SerpAPIProvider(
                api_key=serpapi_cfg["api_key"]
            )
        
        return providers
    
    def get_provider(self, name: Optional[str] = None):
        """Get a provider by name or default."""
        name = name or self.default_provider
        
        if name not in self.providers:
            available = list(self.providers.keys())
            if not available:
                raise ValueError(
                    "No providers configured. Please add API keys to config.yaml "
                    "or set environment variables (AMADEUS_API_KEY, etc.)"
                )
            name = available[0]
            logger.warning(f"Provider '{self.default_provider}' not available, using '{name}'")
        
        return self.providers[name]
    
    # =========================================================================
    # Main Search Functions
    # =========================================================================
    
    def search(
        self,
        origin: str,
        destination: str,
        date: str,
        return_date: Optional[str] = None,
        passengers: int = 1,
        cabin_class: str = "economy",
        provider: Optional[str] = None,
        **kwargs
    ) -> list[Flight]:
        """Search for flights.
        
        Args:
            origin: Origin airport code (e.g., 'JFK')
            destination: Destination airport code (e.g., 'LAX')
            date: Departure date (YYYY-MM-DD)
            return_date: Return date for round trip (optional)
            passengers: Number of passengers
            cabin_class: economy, premium_economy, business, first
            provider: Specific provider to use (optional)
        
        Returns:
            List of Flight objects sorted by price
        """
        defaults = self.config.get("defaults", {})
        
        search = SearchParams(
            origin=origin.upper(),
            destination=destination.upper(),
            date=date,
            return_date=return_date,
            passengers=passengers,
            cabin_class=cabin_class,
            currency=defaults.get("currency", "USD"),
            max_results=defaults.get("max_results", 10)
        )
        
        prov = self.get_provider(provider)
        results = prov.search(search)
        
        # Track prices
        if results:
            self.price_tracker.record_price(
                origin, destination, date, 
                results[0].price,
                return_date,
                prov.name
            )
        
        return sorted(results, key=lambda f: f.price)
    
    def search_all_providers(
        self,
        origin: str,
        destination: str,
        date: str,
        return_date: Optional[str] = None,
        passengers: int = 1
    ) -> dict[str, list[Flight]]:
        """Search all configured providers and return results.
        
        Returns dict of {provider_name: [flights]}
        """
        results = {}
        
        for name, provider in self.providers.items():
            try:
                search = SearchParams(
                    origin=origin.upper(),
                    destination=destination.upper(),
                    date=date,
                    return_date=return_date,
                    passengers=passengers
                )
                results[name] = provider.search(search)
            except Exception as e:
                logger.error(f"Provider {name} failed: {e}")
                results[name] = []
        
        return results
    
    def find_cheapest_dates(
        self,
        origin: str,
        destination: str,
        month: str,
        return_days: int = 7,
        provider: Optional[str] = None
    ) -> dict:
        """Find cheapest departure dates in a month.
        
        Args:
            origin: Origin airport code
            destination: Destination airport code
            month: Month to search (YYYY-MM)
            return_days: Days to stay for round trip (0 for one-way)
            provider: Specific provider to use
        
        Returns:
            Dict of {date: lowest_price}
        """
        prov = self.get_provider(provider)
        return prov.find_cheapest_dates(origin, destination, month, return_days)
    
    # =========================================================================
    # Price Tracking & Alerts
    # =========================================================================
    
    def get_price_history(
        self,
        origin: str,
        destination: str,
        date: str,
        return_date: Optional[str] = None
    ) -> list[dict]:
        """Get price history for a route."""
        return self.price_tracker.get_history(origin, destination, date, return_date)
    
    def get_price_trend(
        self,
        origin: str,
        destination: str,
        date: str,
        return_date: Optional[str] = None
    ) -> Optional[dict]:
        """Get price trend analysis for a route."""
        return self.price_tracker.get_trend(origin, destination, date, return_date)
    
    def set_price_alert(
        self,
        origin: str,
        destination: str,
        date: str,
        target_price: float,
        return_date: Optional[str] = None
    ):
        """Set a price alert for when price drops below target.
        
        Returns the created alert.
        """
        return self.alerts.add_alert(
            origin=origin,
            destination=destination,
            date=date,
            target_price=target_price,
            return_date=return_date
        )
    
    def list_alerts(self, active_only: bool = True) -> list:
        """List all price alerts."""
        return self.alerts.list_alerts(active_only)
    
    def remove_alert(self, alert_id: str) -> bool:
        """Remove a price alert."""
        return self.alerts.remove_alert(alert_id)
    
    def check_alerts(self, notify_func=None) -> list:
        """Check all alerts and return triggered ones.
        
        Args:
            notify_func: Optional callback(alert, price) for notifications
        """
        def search_price(origin, dest, date, return_date):
            results = self.search(origin, dest, date, return_date, passengers=1)
            return results[0].price if results else None
        
        return self.alerts.check_all(search_price, notify_func)
    
    # =========================================================================
    # Formatting
    # =========================================================================
    
    def format_for_telegram(
        self,
        flights: list[Flight],
        title: Optional[str] = None,
        max_results: int = 5
    ) -> str:
        """Format flight results for Telegram."""
        return format_for_telegram(flights, title, max_results=max_results)
    
    def format_cheapest_dates(
        self,
        prices: dict,
        origin: str,
        destination: str,
        month: str
    ) -> str:
        """Format cheapest dates for Telegram."""
        return format_cheapest_dates(prices, origin, destination, month)
    
    def format_comparison(
        self,
        results: dict[str, list[Flight]],
        origin: str,
        destination: str
    ) -> str:
        """Format provider comparison for Telegram."""
        return format_comparison(results, origin, destination)
    
    # =========================================================================
    # Utilities
    # =========================================================================
    
    def available_providers(self) -> list[str]:
        """List configured providers."""
        return list(self.providers.keys())
    
    def resolve_location(self, query: str) -> list[dict]:
        """Resolve a city/airport name to IATA code.
        
        Uses Kiwi provider if available.
        """
        if "kiwi" in self.providers:
            return self.providers["kiwi"].get_locations(query)
        return []


# Convenience alias
FlightSearch = FlightSearchClient


# =========================================================================
# CLI Interface
# =========================================================================

def main():
    """Simple CLI for testing."""
    import sys
    
    if len(sys.argv) < 4:
        print("Usage: python flights.py <origin> <destination> <date> [return_date]")
        print("Example: python flights.py JFK LAX 2024-03-15 2024-03-22")
        sys.exit(1)
    
    origin = sys.argv[1]
    destination = sys.argv[2]
    date = sys.argv[3]
    return_date = sys.argv[4] if len(sys.argv) > 4 else None
    
    client = FlightSearchClient()
    
    print(f"\n🔍 Searching {origin} → {destination}...")
    print(f"   Date: {date}" + (f" - {return_date}" if return_date else ""))
    print(f"   Providers: {', '.join(client.available_providers())}")
    print()
    
    results = client.search(origin, destination, date, return_date)
    
    if results:
        print(client.format_for_telegram(results))
    else:
        print("No flights found!")


if __name__ == "__main__":
    main()
