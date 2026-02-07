"""Price alert system for flight tracking."""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class PriceAlert:
    """A price alert for a specific route."""
    id: str
    origin: str
    destination: str
    date: str
    return_date: Optional[str]
    target_price: float
    currency: str = "USD"
    created_at: str = ""
    last_checked: Optional[str] = None
    last_price: Optional[float] = None
    triggered: bool = False
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
        if not self.id:
            # Generate ID from route and date
            self.id = f"{self.origin}-{self.destination}-{self.date}".lower()


class AlertManager:
    """Manages price alerts with file-based storage."""
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(
            storage_path or 
            os.path.expanduser("~/.flight_alerts.json")
        )
        self.alerts: dict[str, PriceAlert] = {}
        self._load()
    
    def _load(self):
        """Load alerts from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path) as f:
                    data = json.load(f)
                    for alert_data in data.get("alerts", []):
                        alert = PriceAlert(**alert_data)
                        self.alerts[alert.id] = alert
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Failed to load alerts: {e}")
    
    def _save(self):
        """Save alerts to storage."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, "w") as f:
            json.dump({
                "alerts": [asdict(a) for a in self.alerts.values()],
                "updated_at": datetime.utcnow().isoformat()
            }, f, indent=2)
    
    def add_alert(
        self,
        origin: str,
        destination: str,
        date: str,
        target_price: float,
        return_date: Optional[str] = None,
        currency: str = "USD"
    ) -> PriceAlert:
        """Add a new price alert."""
        alert = PriceAlert(
            id="",  # Will be generated
            origin=origin.upper(),
            destination=destination.upper(),
            date=date,
            return_date=return_date,
            target_price=target_price,
            currency=currency
        )
        
        self.alerts[alert.id] = alert
        self._save()
        
        logger.info(f"Added alert: {alert.id} (target: ${target_price})")
        return alert
    
    def remove_alert(self, alert_id: str) -> bool:
        """Remove an alert by ID."""
        if alert_id in self.alerts:
            del self.alerts[alert_id]
            self._save()
            return True
        return False
    
    def get_alert(self, alert_id: str) -> Optional[PriceAlert]:
        """Get an alert by ID."""
        return self.alerts.get(alert_id)
    
    def list_alerts(self, active_only: bool = True) -> list[PriceAlert]:
        """List all alerts."""
        alerts = list(self.alerts.values())
        if active_only:
            alerts = [a for a in alerts if not a.triggered]
        return sorted(alerts, key=lambda a: a.date)
    
    def update_price(
        self, 
        alert_id: str, 
        current_price: float
    ) -> tuple[bool, Optional[PriceAlert]]:
        """Update price for an alert and check if triggered.
        
        Returns (is_triggered, alert)
        """
        alert = self.alerts.get(alert_id)
        if not alert:
            return False, None
        
        alert.last_checked = datetime.utcnow().isoformat()
        alert.last_price = current_price
        
        if current_price <= alert.target_price:
            alert.triggered = True
            self._save()
            return True, alert
        
        self._save()
        return False, alert
    
    def check_all(
        self,
        search_func: Callable,
        notify_func: Optional[Callable] = None
    ) -> list[PriceAlert]:
        """Check all active alerts and return triggered ones.
        
        Args:
            search_func: Function(origin, dest, date, return_date) -> price
            notify_func: Optional callback for triggered alerts
        
        Returns list of newly triggered alerts.
        """
        triggered = []
        
        for alert in self.list_alerts(active_only=True):
            try:
                price = search_func(
                    alert.origin,
                    alert.destination,
                    alert.date,
                    alert.return_date
                )
                
                if price is None:
                    continue
                
                is_triggered, updated_alert = self.update_price(alert.id, price)
                
                if is_triggered and updated_alert:
                    triggered.append(updated_alert)
                    if notify_func:
                        notify_func(updated_alert, price)
                        
            except Exception as e:
                logger.error(f"Failed to check alert {alert.id}: {e}")
        
        return triggered
    
    def get_price_history(self, alert_id: str) -> list[dict]:
        """Get price history for an alert.
        
        Note: Currently only stores last price.
        For full history, would need to extend storage.
        """
        alert = self.alerts.get(alert_id)
        if not alert or not alert.last_price:
            return []
        
        return [{
            "timestamp": alert.last_checked,
            "price": alert.last_price
        }]


class PriceTracker:
    """Extended price tracking with history."""
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(
            storage_path or
            os.path.expanduser("~/.flight_price_history.json")
        )
        self.history: dict[str, list[dict]] = {}
        self._load()
    
    def _load(self):
        """Load history from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path) as f:
                    self.history = json.load(f)
            except json.JSONDecodeError:
                self.history = {}
    
    def _save(self):
        """Save history to storage."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, "w") as f:
            json.dump(self.history, f, indent=2)
    
    def _route_key(
        self, 
        origin: str, 
        destination: str, 
        date: str,
        return_date: Optional[str] = None
    ) -> str:
        """Generate a unique key for a route."""
        key = f"{origin.upper()}-{destination.upper()}-{date}"
        if return_date:
            key += f"-{return_date}"
        return key
    
    def record_price(
        self,
        origin: str,
        destination: str,
        date: str,
        price: float,
        return_date: Optional[str] = None,
        provider: str = ""
    ):
        """Record a price point."""
        key = self._route_key(origin, destination, date, return_date)
        
        if key not in self.history:
            self.history[key] = []
        
        self.history[key].append({
            "timestamp": datetime.utcnow().isoformat(),
            "price": price,
            "provider": provider
        })
        
        # Keep only last 100 price points per route
        self.history[key] = self.history[key][-100:]
        
        self._save()
    
    def get_history(
        self,
        origin: str,
        destination: str,
        date: str,
        return_date: Optional[str] = None
    ) -> list[dict]:
        """Get price history for a route."""
        key = self._route_key(origin, destination, date, return_date)
        return self.history.get(key, [])
    
    def get_trend(
        self,
        origin: str,
        destination: str,
        date: str,
        return_date: Optional[str] = None
    ) -> Optional[dict]:
        """Analyze price trend for a route.
        
        Returns dict with trend analysis.
        """
        history = self.get_history(origin, destination, date, return_date)
        
        if len(history) < 2:
            return None
        
        prices = [h["price"] for h in history]
        
        current = prices[-1]
        previous = prices[-2]
        lowest = min(prices)
        highest = max(prices)
        average = sum(prices) / len(prices)
        
        # Determine trend
        if current < previous:
            trend = "falling"
        elif current > previous:
            trend = "rising"
        else:
            trend = "stable"
        
        # Price position
        if current <= lowest * 1.05:
            position = "near_low"
        elif current >= highest * 0.95:
            position = "near_high"
        else:
            position = "middle"
        
        return {
            "current": current,
            "previous": previous,
            "lowest": lowest,
            "highest": highest,
            "average": average,
            "trend": trend,
            "position": position,
            "change": current - previous,
            "change_pct": ((current - previous) / previous) * 100 if previous else 0,
            "data_points": len(prices)
        }
