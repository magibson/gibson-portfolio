#!/usr/bin/env python3
"""
Telegram Output Formatter for Hotel Search Results.

Formats hotel search results for clean display in Telegram messages.
Handles markdown escaping, emoji, and message length limits.

Usage:
    from telegram_formatter import format_hotel_results, format_price_comparison
"""

from typing import Dict, List, Any, Optional
import re


def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    if not text:
        return ""
    # Characters to escape: _ * [ ] ( ) ~ ` > # + - = | { } . !
    special_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(special_chars)}])', r'\\\1', str(text))


def format_rating(rating: Optional[float]) -> str:
    """Format rating with star emoji."""
    if not rating:
        return "No rating"
    stars = "⭐" * min(int(rating), 5)
    return f"{rating} {stars}"


def format_price(price: Any, currency: str = "USD") -> str:
    """Format price with currency symbol."""
    if not price:
        return "Price unavailable"
    
    symbols = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥"}
    symbol = symbols.get(currency, currency + " ")
    
    if isinstance(price, str):
        return price
    return f"{symbol}{price:,.0f}"


def format_amenities(amenities: List[str], max_items: int = 5) -> str:
    """Format amenities list with emojis."""
    if not amenities:
        return ""
    
    emoji_map = {
        "wifi": "📶", "free wifi": "📶", "pool": "🏊", "spa": "💆",
        "gym": "🏋️", "fitness": "🏋️", "parking": "🅿️", "free parking": "🅿️",
        "breakfast": "🍳", "free breakfast": "🍳", "restaurant": "🍽️",
        "bar": "🍸", "air conditioning": "❄️", "pet": "🐾", "beach": "🏖️",
        "kitchen": "🍳", "hot tub": "♨️", "kid": "👶", "airport shuttle": "🚐",
    }
    
    formatted = []
    for amenity in amenities[:max_items]:
        emoji = "✓"
        for key, value in emoji_map.items():
            if key in amenity.lower():
                emoji = value
                break
        formatted.append(f"{emoji} {amenity}")
    
    return " • ".join(formatted)


def format_hotel_card(hotel: Dict, index: int = 0, compact: bool = False) -> str:
    """
    Format a single hotel as a card.
    
    Args:
        hotel: Hotel data dict
        index: Position number (0 = no number)
        compact: Use compact format
    
    Returns:
        Formatted string for Telegram
    """
    name = hotel.get("name", "Unknown Hotel")
    price = hotel.get("rate_per_night", {}).get("lowest") or hotel.get("price") or hotel.get("price_display")
    rating = hotel.get("overall_rating") or hotel.get("rating")
    reviews = hotel.get("reviews")
    hotel_class = hotel.get("hotel_class")
    amenities = hotel.get("amenities", [])
    free_cancel = hotel.get("free_cancellation", False)
    
    # Header
    num = f"{index}. " if index else ""
    stars = "⭐" * hotel_class if hotel_class else ""
    header = f"🏨 *{num}{escape_markdown(name)}* {stars}"
    
    if compact:
        # Compact: single line
        rating_str = f"⭐{rating}" if rating else ""
        return f"{header}\n💰 {escape_markdown(str(price))} {rating_str}"
    
    # Full format
    lines = [header, ""]
    
    # Price
    if price:
        price_line = f"💰 *{escape_markdown(str(price))}*/night"
        if free_cancel:
            price_line += " ✅ Free cancellation"
        lines.append(price_line)
    
    # Rating
    if rating:
        review_str = f" ({reviews:,} reviews)" if reviews else ""
        lines.append(f"⭐ {rating}{review_str}")
    
    # Amenities
    if amenities:
        lines.append(format_amenities(amenities))
    
    return "\n".join(lines)


def format_hotel_results(
    results: Dict[str, Any],
    max_results: int = 5,
    compact: bool = False,
    show_summary: bool = True,
) -> str:
    """
    Format hotel search results for Telegram.
    
    Args:
        results: Results from HotelSearchClient.search_hotels()
        max_results: Maximum hotels to show
        compact: Use compact format
        show_summary: Show search summary header
    
    Returns:
        Formatted message string
    """
    if "error" in results:
        return f"❌ {escape_markdown(results['error'])}"
    
    properties = results.get("properties", [])
    
    if not properties:
        return "🔍 No hotels found matching your criteria\\."
    
    lines = []
    
    # Header
    if show_summary:
        params = results.get("search_params", {})
        city = params.get("q", "").replace(" hotels", "")
        checkin = params.get("check_in_date", "")
        checkout = params.get("check_out_date", "")
        adults = params.get("adults", 2)
        
        lines.append(f"🏨 *Hotels in {escape_markdown(city)}*")
        lines.append(f"📅 {escape_markdown(checkin)} → {escape_markdown(checkout)} • {adults} guests")
        lines.append(f"📊 Found {len(properties)} hotels")
        lines.append("")
    
    # Hotels
    for i, hotel in enumerate(properties[:max_results], 1):
        lines.append(format_hotel_card(hotel, index=i, compact=compact))
        lines.append("")
    
    # Footer
    remaining = len(properties) - max_results
    if remaining > 0:
        lines.append(f"_\\+{remaining} more hotels available_")
    
    return "\n".join(lines)


def format_price_comparison(comparison: Dict[str, Any]) -> str:
    """
    Format price comparison results for Telegram.
    
    Args:
        comparison: Results from HotelSearchClient.compare_prices()
    
    Returns:
        Formatted message string
    """
    if "error" in comparison:
        return f"❌ {escape_markdown(comparison['error'])}"
    
    hotel = comparison.get("hotel", {})
    dates = comparison.get("dates", {})
    prices = comparison.get("prices", [])
    savings = comparison.get("savings")
    
    lines = []
    
    # Hotel info
    name = hotel.get("name", "Unknown")
    rating = hotel.get("rating")
    hotel_class = hotel.get("hotel_class")
    
    stars = "⭐" * hotel_class if hotel_class else ""
    lines.append(f"🏨 *{escape_markdown(name)}* {stars}")
    
    if rating:
        reviews = hotel.get("reviews")
        review_str = f" \\({reviews:,} reviews\\)" if reviews else ""
        lines.append(f"⭐ {rating}{review_str}")
    
    # Dates
    nights = dates.get("nights", 1)
    lines.append(f"📅 {escape_markdown(dates.get('checkin', ''))} → {escape_markdown(dates.get('checkout', ''))} \\({nights} night{'s' if nights != 1 else ''}\\)")
    lines.append("")
    
    # Price comparison
    lines.append("💰 *Price Comparison:*")
    lines.append("")
    
    if not prices:
        lines.append("No pricing data available")
    else:
        for i, price_info in enumerate(prices):
            source = price_info.get("source", "Unknown")
            price = price_info.get("price_display") or price_info.get("price")
            
            # First one is cheapest
            prefix = "🥇" if i == 0 else "  "
            badge = " *← BEST*" if i == 0 else ""
            
            lines.append(f"{prefix} {escape_markdown(source)}: *{escape_markdown(str(price))}*/night{badge}")
    
    # Savings
    if savings:
        lines.append("")
        lines.append(f"💡 *Save {savings['percentage']}%* by booking with {escape_markdown(savings['best_source'])} instead of {escape_markdown(savings['worst_source'])}")
    
    return "\n".join(lines)


def format_deals(deals_result: Dict[str, Any], max_deals: int = 5) -> str:
    """
    Format deal search results for Telegram.
    
    Args:
        deals_result: Results from HotelSearchClient.find_deals()
        max_deals: Maximum deals to show
    
    Returns:
        Formatted message string
    """
    if "error" in deals_result:
        return f"❌ {escape_markdown(deals_result['error'])}"
    
    city = deals_result.get("city", "")
    dates = deals_result.get("dates", {})
    max_price = deals_result.get("max_price")
    deals = deals_result.get("deals", [])
    total = deals_result.get("total_found", 0)
    
    lines = []
    
    # Header
    lines.append(f"🔥 *Hotel Deals in {escape_markdown(city)}*")
    lines.append(f"📅 {escape_markdown(dates.get('checkin', ''))} → {escape_markdown(dates.get('checkout', ''))}")
    lines.append(f"💰 Under ${max_price}/night")
    lines.append(f"📊 Found {total} deals")
    lines.append("")
    
    if not deals:
        lines.append("No deals found matching your criteria\\.")
        return "\n".join(lines)
    
    # Deals
    for i, deal in enumerate(deals[:max_deals], 1):
        name = deal.get("name", "Unknown")
        price = deal.get("price_display") or f"${deal.get('price')}"
        rating = deal.get("rating")
        value = deal.get("value_score", 0)
        free_cancel = deal.get("free_cancellation", False)
        
        # Value badge
        if value > 3:
            badge = "🔥 GREAT VALUE"
        elif value > 2:
            badge = "✨ Good deal"
        else:
            badge = ""
        
        lines.append(f"*{i}\\. {escape_markdown(name)}* {badge}")
        
        rating_str = f"⭐ {rating}" if rating else ""
        cancel_str = "✅ Free cancel" if free_cancel else ""
        
        lines.append(f"   💰 *{escape_markdown(str(price))}*/night {rating_str} {cancel_str}")
        lines.append("")
    
    remaining = total - max_deals
    if remaining > 0:
        lines.append(f"_\\+{remaining} more deals_")
    
    return "\n".join(lines)


def format_hotel_details(details: Dict[str, Any]) -> str:
    """
    Format detailed hotel information for Telegram.
    
    Args:
        details: Hotel details dict
    
    Returns:
        Formatted message string
    """
    if "error" in details:
        return f"❌ {escape_markdown(details['error'])}"
    
    # Handle different response structures
    hotel = details.get("hotel_data") or details
    
    name = hotel.get("name", "Unknown Hotel")
    rating = hotel.get("overall_rating")
    reviews = hotel.get("reviews")
    address = hotel.get("address")
    hotel_class = hotel.get("hotel_class")
    amenities = hotel.get("amenities", [])
    check_in = hotel.get("check_in_time")
    check_out = hotel.get("check_out_time")
    nearby = hotel.get("nearby_places", [])
    
    lines = []
    
    # Header
    stars = "⭐" * hotel_class if hotel_class else ""
    lines.append(f"🏨 *{escape_markdown(name)}* {stars}")
    lines.append("")
    
    # Rating
    if rating:
        review_str = f" \\({reviews:,} reviews\\)" if reviews else ""
        lines.append(f"⭐ *{rating}*{review_str}")
    
    # Address
    if address:
        lines.append(f"📍 {escape_markdown(address)}")
    
    # Check-in/out times
    if check_in or check_out:
        lines.append(f"🕐 Check\\-in: {escape_markdown(check_in or 'N/A')} • Check\\-out: {escape_markdown(check_out or 'N/A')}")
    
    lines.append("")
    
    # Amenities
    if amenities:
        lines.append("*Amenities:*")
        lines.append(format_amenities(amenities, max_items=10))
    
    # Nearby places
    if nearby:
        lines.append("")
        lines.append("*Nearby:*")
        for place in nearby[:3]:
            place_name = place.get("name", "")
            transports = place.get("transportations", [])
            if transports:
                transport = transports[0]
                duration = transport.get("duration", "")
                lines.append(f"  • {escape_markdown(place_name)}: {escape_markdown(duration)}")
    
    return "\n".join(lines)


# Plain text versions (no markdown)
def format_hotel_results_plain(results: Dict[str, Any], max_results: int = 5) -> str:
    """Format results as plain text (for platforms without markdown)."""
    if "error" in results:
        return f"❌ {results['error']}"
    
    properties = results.get("properties", [])
    if not properties:
        return "🔍 No hotels found."
    
    params = results.get("search_params", {})
    city = params.get("q", "").replace(" hotels", "")
    
    lines = [f"🏨 Hotels in {city}", f"Found {len(properties)} hotels", ""]
    
    for i, hotel in enumerate(properties[:max_results], 1):
        name = hotel.get("name", "Unknown")
        price = hotel.get("rate_per_night", {}).get("lowest") or hotel.get("price", "N/A")
        rating = hotel.get("overall_rating", "")
        
        rating_str = f"⭐{rating}" if rating else ""
        lines.append(f"{i}. {name}")
        lines.append(f"   💰 {price}/night {rating_str}")
        lines.append("")
    
    return "\n".join(lines)


# Test
if __name__ == "__main__":
    # Test data
    test_results = {
        "search_params": {
            "q": "Paris hotels",
            "check_in_date": "2024-06-01",
            "check_out_date": "2024-06-05",
            "adults": 2,
        },
        "properties": [
            {
                "name": "Hotel Le Bristol Paris",
                "rate_per_night": {"lowest": "$850"},
                "overall_rating": 4.8,
                "reviews": 1234,
                "hotel_class": 5,
                "amenities": ["Free WiFi", "Pool", "Spa", "Restaurant", "Bar"],
                "free_cancellation": True,
            },
            {
                "name": "Mercure Paris Centre Tour Eiffel",
                "rate_per_night": {"lowest": "$195"},
                "overall_rating": 4.2,
                "reviews": 892,
                "hotel_class": 4,
                "amenities": ["Free WiFi", "Restaurant", "Bar"],
                "free_cancellation": False,
            },
        ]
    }
    
    print("=== Hotel Results ===")
    print(format_hotel_results(test_results))
    print()
    
    test_comparison = {
        "hotel": {
            "name": "The Ritz Paris",
            "rating": 4.9,
            "reviews": 2345,
            "hotel_class": 5,
        },
        "dates": {
            "checkin": "2024-06-01",
            "checkout": "2024-06-05",
            "nights": 4,
        },
        "prices": [
            {"source": "Booking.com", "price": 850, "price_display": "$850"},
            {"source": "Hotels.com", "price": 875, "price_display": "$875"},
            {"source": "Expedia", "price": 920, "price_display": "$920"},
        ],
        "savings": {
            "amount": 70,
            "percentage": 7.6,
            "best_source": "Booking.com",
            "worst_source": "Expedia",
        },
    }
    
    print("=== Price Comparison ===")
    print(format_price_comparison(test_comparison))
