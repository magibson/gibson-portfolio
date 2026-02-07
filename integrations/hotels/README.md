# Hotel Search Integration

Search and compare hotel prices across multiple platforms.

## API Comparison & Recommendation

### 🏆 Recommended: SerpAPI (Google Hotels)

| Feature | SerpAPI | Amadeus | Booking.com | Expedia Rapid |
|---------|---------|---------|-------------|---------------|
| **Setup** | API key only | OAuth + API key | Affiliate partnership | Partnership required |
| **Free Tier** | 100 searches/month | 2000 calls/month (test) | None | None |
| **Price Comparison** | ✅ Built-in | ❌ Single source | ❌ Single source | ❌ Single source |
| **Data Quality** | Excellent | Good | Excellent | Excellent |
| **Time to Integrate** | 1 hour | 2-3 hours | 1-2 weeks | 1-2 weeks |
| **Best For** | Search & compare | Booking integration | High volume affiliate | Enterprise |

### Why SerpAPI?
1. **Aggregates prices** from Booking.com, Hotels.com, Expedia, and more
2. **No partnership required** - just sign up and get API key
3. **Rich data**: ratings, amenities, photos, nearby places
4. **Simple REST API** with JSON responses
5. **Reasonable pricing**: Free tier → $50/mo for 5000 searches

### API Details

#### SerpAPI Google Hotels
- **Sign up**: https://serpapi.com/users/sign_up
- **Pricing**: Free (100/mo) → Developer ($50, 5K/mo) → Business ($250, 30K/mo)
- **Docs**: https://serpapi.com/google-hotels-api
- **Features**:
  - Hotel search by location
  - Property details
  - Price comparison across booking sites
  - Reviews, amenities, photos
  - Filters (star rating, amenities, price range)

#### Amadeus (Alternative for Direct Booking)
- **Sign up**: https://developers.amadeus.com/register
- **Pricing**: Free test (2000 calls) → Pay-as-you-go ($0.10-0.50/call)
- **APIs Needed**:
  - Hotel List API (find hotels by city)
  - Hotel Search API (check availability)
  - Hotel Booking API (create reservations)
- **Best for**: If you need actual booking capabilities

#### Booking.com Demand API (Enterprise)
- **Requirements**: Apply for affiliate partnership
- **URL**: https://partnerships.booking.com
- **Timeline**: 1-4 weeks approval
- **Best for**: High-volume affiliate sites

#### Expedia Rapid API (Enterprise)
- **Requirements**: Partner agreement
- **URL**: https://developers.expediagroup.com/rapid
- **Inventory**: 700K+ properties
- **Best for**: Enterprise travel platforms

## Quick Start

```bash
# 1. Set up API key
cp config.template.json config.json
# Edit config.json with your SerpAPI key

# 2. Test the client
python3 hotels_client.py --test
```

## Usage Examples

```python
from hotels_client import HotelSearchClient

client = HotelSearchClient()

# Search hotels
results = client.search_hotels(
    city="Paris",
    checkin="2024-06-01",
    checkout="2024-06-05",
    guests=2,
    rooms=1
)

# Get hotel details
details = client.get_hotel_details("property_token_here")

# Compare prices across platforms
comparison = client.compare_prices("Marriott Paris", "2024-06-01", "2024-06-05")

# Find deals under a price
deals = client.find_deals("Barcelona", "2024-07-01", "2024-07-03", max_price=150)
```

## Configuration

See `config.template.json` for all options:
- `serpapi_key`: Your SerpAPI key (required)
- `amadeus_key/secret`: Optional Amadeus credentials for booking
- `default_currency`: USD, EUR, GBP, etc.
- `default_adults`: Default guest count

## Credential Setup

### SerpAPI (5 minutes)
1. Go to https://serpapi.com/users/sign_up
2. Create account (Google/GitHub sign-in available)
3. Copy API key from dashboard
4. Paste in `config.json`

### Amadeus (10 minutes, optional)
1. Go to https://developers.amadeus.com/register
2. Create account
3. Create a new "Self-Service" app
4. Copy API Key and API Secret
5. Add to `config.json`

## Files

- `hotels_client.py` - Main client with all search functions
- `telegram_formatter.py` - Format results for Telegram
- `config.template.json` - Configuration template
- `README.md` - This file
