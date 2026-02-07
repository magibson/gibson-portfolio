"""Output formatters for flight search results."""
from datetime import datetime
from typing import Optional
from providers.base import Flight


def format_for_telegram(
    flights: list[Flight],
    title: Optional[str] = None,
    show_booking_link: bool = True,
    max_results: int = 5
) -> str:
    """Format flight results for Telegram.
    
    Clean, readable format without markdown tables (not supported well).
    """
    if not flights:
        return "✈️ No flights found for this search."
    
    lines = []
    
    # Title
    if title:
        lines.append(f"✈️ **{title}**")
    else:
        f = flights[0]
        route = f"{f.origin} → {f.destination}"
        if f.return_departure:
            route = f"{f.origin} ↔ {f.destination}"
        lines.append(f"✈️ **Flights: {route}**")
    
    lines.append("")
    
    # Flight results
    for i, flight in enumerate(flights[:max_results], 1):
        lines.append(_format_single_flight(flight, i, show_booking_link))
        lines.append("")
    
    # Summary
    prices = [f.price for f in flights[:max_results]]
    if len(prices) > 1:
        lines.append(f"💰 Range: ${min(prices):.0f} - ${max(prices):.0f}")
    
    return "\n".join(lines)


def _format_single_flight(flight: Flight, index: int, show_link: bool) -> str:
    """Format a single flight."""
    lines = []
    
    # Price and airline header
    emoji = "🥇" if index == 1 else "🥈" if index == 2 else "🥉" if index == 3 else f"{index}."
    header = f"{emoji} **${flight.price:.0f}** - {flight.airline}"
    if flight.baggage_included:
        header += " 🧳"
    lines.append(header)
    
    # Outbound
    dep_time = flight.departure_time.strftime("%H:%M")
    arr_time = flight.arrival_time.strftime("%H:%M")
    dep_date = flight.departure_time.strftime("%b %d")
    
    outbound = f"   ↗️ {dep_date}: {dep_time} → {arr_time} ({flight.duration_str})"
    if flight.stops > 0:
        stops_info = f", {flight.stops_str}"
        if flight.stop_airports:
            stops_info += f" via {', '.join(flight.stop_airports)}"
        outbound += stops_info
    else:
        outbound += ", Direct"
    lines.append(outbound)
    
    # Return flight if round trip
    if flight.return_departure:
        ret_dep = flight.return_departure.strftime("%H:%M")
        ret_arr = flight.return_arrival.strftime("%H:%M") if flight.return_arrival else "?"
        ret_date = flight.return_departure.strftime("%b %d")
        
        ret_line = f"   ↙️ {ret_date}: {ret_dep} → {ret_arr}"
        if flight.return_stops > 0:
            ret_line += f", {flight.return_stops} stop{'s' if flight.return_stops > 1 else ''}"
        else:
            ret_line += ", Direct"
        lines.append(ret_line)
    
    # Booking link
    if show_link and flight.booking_url:
        lines.append(f"   🔗 [Book]({flight.booking_url})")
    
    return "\n".join(lines)


def format_cheapest_dates(
    prices: dict,
    origin: str,
    destination: str,
    month: str
) -> str:
    """Format cheapest dates results for Telegram."""
    if not prices:
        return f"✈️ No price data found for {origin} → {destination} in {month}"
    
    lines = [
        f"📅 **Cheapest dates: {origin} → {destination}**",
        f"Month: {month}",
        ""
    ]
    
    # Sort by price
    sorted_prices = sorted(prices.items(), key=lambda x: x[1])
    
    # Show top 5 cheapest
    lines.append("**Best deals:**")
    for date_str, price in sorted_prices[:5]:
        # Parse date for better formatting
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        day_name = dt.strftime("%a")
        day_num = dt.strftime("%d")
        lines.append(f"  • {day_name} {day_num}: **${price:.0f}**")
    
    lines.append("")
    
    # Price range
    all_prices = list(prices.values())
    lines.append(f"💰 Range: ${min(all_prices):.0f} - ${max(all_prices):.0f}")
    
    # Tip
    cheapest_date = sorted_prices[0][0]
    dt = datetime.strptime(cheapest_date, "%Y-%m-%d")
    if dt.weekday() in [1, 2]:  # Tue, Wed
        lines.append("💡 Tip: Midweek flights are often cheapest!")
    
    return "\n".join(lines)


def format_price_alert(
    route: str,
    current_price: float,
    target_price: float,
    triggered: bool = False
) -> str:
    """Format price alert notification."""
    if triggered:
        return (
            f"🚨 **Price Alert Triggered!**\n\n"
            f"Route: {route}\n"
            f"Current: **${current_price:.0f}**\n"
            f"Target: ${target_price:.0f}\n\n"
            f"🎯 Price is at or below your target!"
        )
    else:
        diff = current_price - target_price
        pct = (diff / target_price) * 100
        return (
            f"📊 **Price Update**\n\n"
            f"Route: {route}\n"
            f"Current: ${current_price:.0f}\n"
            f"Target: ${target_price:.0f}\n"
            f"Gap: ${diff:.0f} ({pct:.0f}% above target)"
        )


def format_comparison(
    results: dict[str, list[Flight]],
    origin: str,
    destination: str
) -> str:
    """Format comparison across multiple providers."""
    lines = [
        f"🔄 **Price Comparison: {origin} → {destination}**",
        ""
    ]
    
    # Get best price from each provider
    provider_best = {}
    for provider, flights in results.items():
        if flights:
            best = min(flights, key=lambda f: f.price)
            provider_best[provider] = best
    
    if not provider_best:
        return f"No results found for {origin} → {destination}"
    
    # Sort by price
    sorted_providers = sorted(
        provider_best.items(), 
        key=lambda x: x[1].price
    )
    
    for provider, flight in sorted_providers:
        emoji = "✅" if flight == sorted_providers[0][1] else "  "
        lines.append(
            f"{emoji} **{provider.title()}**: ${flight.price:.0f} "
            f"({flight.airline}, {flight.stops_str})"
        )
    
    # Winner
    lines.append("")
    winner = sorted_providers[0]
    savings = sorted_providers[-1][1].price - winner[1].price if len(sorted_providers) > 1 else 0
    lines.append(f"🏆 Best: **{winner[0].title()}** saves ${savings:.0f}")
    
    return "\n".join(lines)


def format_flight_simple(flight: Flight) -> str:
    """Simple one-line format for a flight."""
    dep = flight.departure_time.strftime("%b %d %H:%M")
    stops = f"({flight.stops_str})" if flight.stops else "(Direct)"
    return f"${flight.price:.0f} | {flight.airline} | {dep} | {flight.duration_str} {stops}"
