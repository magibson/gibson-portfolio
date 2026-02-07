# Flight Search Integration

A flight search client supporting multiple providers. Designed for price comparison and alerts - actual booking happens on airline/OTA sites.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and configure
cp config.template.yaml config.yaml
# Edit config.yaml with your API keys

# Test it
python -c "from flights import FlightSearch; fs = FlightSearch(); print(fs.search('JFK', 'LAX', '2024-03-15'))"
```

## API Comparison

| Provider | Free Tier | Best For | Sign Up Time |
|----------|-----------|----------|--------------|
| **Amadeus** ⭐ | 2,000 calls/month | Most reliable, full-featured | ~5 min |
| **Kiwi (Tequila)** | Unlimited (affiliate) | Budget carriers, flexible dates | ~2 min |
| **SerpAPI** | 100 searches/month | Google Flights data | ~1 min |
| **Skyscanner** | Partner only | Not recommended for personal use | Requires approval |

### Recommended: Amadeus + Kiwi combo
- **Amadeus** for mainstream routes and reliable data
- **Kiwi** for budget carriers (Ryanair, EasyJet, etc.) and flexible date searches

## Getting API Keys

### Amadeus (Primary - Recommended)
1. Go to https://developers.amadeus.com
2. Create free account
3. Go to "My Self-Service Workspace" → "My Apps"
4. Create new app → get API Key + API Secret
5. Free tier: 2,000 API calls/month (test environment)

**Pros:** Well-documented, reliable, includes price prediction  
**Cons:** Limited to test environment on free tier (real prices, but can't book)

### Kiwi.com Tequila (Secondary - Great for budget)
1. Go to https://tequila.kiwi.com
2. Register for Tequila API
3. Create a "Solution" in dashboard
4. Get API key from solution settings

**Pros:** Unlimited free API calls, great for budget carriers, affiliate revenue  
**Cons:** Less mainstream carriers, slightly different data format

### SerpAPI (Google Flights scraping)
1. Go to https://serpapi.com
2. Create account (verify email)
3. Get API key from dashboard
4. Free: 100 searches/month

**Pros:** Actual Google Flights data  
**Cons:** Limited free tier, scraping can be fragile

## Features

- **search_flights()** - Search one-way or round-trip flights
- **find_cheapest_dates()** - Find cheapest days in a month
- **get_price_history()** - Track price changes over time
- **set_price_alert()** - Alert when price drops below target
- **format_for_telegram()** - Clean output for messaging

## Usage Examples

```python
from flights import FlightSearch

fs = FlightSearch()

# Basic search
results = fs.search(
    origin='JFK',
    destination='LAX', 
    date='2024-03-15',
    return_date='2024-03-22',  # Optional
    passengers=1
)

# Find cheapest dates in March
cheapest = fs.find_cheapest_dates('JFK', 'LAX', '2024-03')

# Track a route
fs.set_price_alert('JFK', 'LAX', '2024-03-15', target_price=250)

# Get Telegram-friendly output
print(fs.format_for_telegram(results))
```

## File Structure

```
flights/
├── README.md           # This file
├── requirements.txt    # Python dependencies
├── config.template.yaml # Copy to config.yaml
├── flights.py          # Main client
├── providers/
│   ├── __init__.py
│   ├── amadeus.py      # Amadeus API client
│   ├── kiwi.py         # Kiwi/Tequila client
│   └── serpapi.py      # SerpAPI/Google Flights
├── formatters.py       # Output formatting
└── alerts.py           # Price alert system
```

## Notes

- All prices in USD unless specified
- IATA codes required (JFK, LAX, LHR, etc.)
- Dates in YYYY-MM-DD format
- Price alerts stored in `~/.flight_alerts.json`
