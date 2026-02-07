# Dinner Reservation System

A functional reservation system that can actually **book** tables at restaurants, not just search.

## 🚀 Platforms Supported

| Platform | Search | Availability | Booking | Method |
|----------|--------|--------------|---------|--------|
| **Resy** | ✅ | ✅ | ✅ | API |
| **OpenTable** | ✅ | ✅ | ✅ | Browser Automation |
| **Yelp** | ✅ | ⚠️ | ⚠️ | API + Browser |

## 📦 Setup

### 1. Install Dependencies

```bash
cd /home/clawd/clawd/integrations/reservations
npm install
```

### 2. Configure Credentials

Edit `config.json` with your actual credentials:

```json
{
  "user_preferences": {
    "name": "Matt",
    "email": "your-email@example.com",
    "phone": "+1234567890",
    "default_party_size": 2
  },
  "credentials": {
    "resy": {
      "api_key": "YOUR_RESY_API_KEY",
      "auth_token": "YOUR_RESY_AUTH_TOKEN",
      "email": "your-resy-email",
      "password": "your-resy-password"
    },
    "opentable": {
      "email": "your-opentable-email",
      "password": "your-opentable-password"
    },
    "yelp": {
      "api_key": "YOUR_YELP_FUSION_API_KEY"
    }
  }
}
```

## 🔑 Getting API Keys

### Resy (Required for Resy bookings)

1. Log into [resy.com](https://resy.com) in Chrome
2. Open Developer Tools → Network tab
3. Go to any restaurant page
4. Find requests to `api.resy.com`
5. Look for headers:
   - `authorization` → This is your `api_key` (format: `ResyAPI api_key="..."`)
   - `x-resy-auth-token` → This is your `auth_token`

**Or use password login:**
```bash
node resy-client.js login
```

### OpenTable

Just add your OpenTable account email/password. The browser automation handles the rest.

### Yelp Fusion API

1. Go to [Yelp Developer](https://www.yelp.com/developers/v3/manage_app)
2. Create an app
3. Copy your API Key

## 📖 Usage

### From Code

```javascript
import ReservationSystem from './index.js';

const system = new ReservationSystem();

// Search restaurants
const results = await system.searchRestaurants({
  location: 'New York',
  cuisine: 'Italian',
  date: '2024-02-15',
  time: '19:00',
  partySize: 2
});

// Check availability
const availability = await system.checkAvailability({
  restaurant: { platform: 'resy', id: '123' },
  date: '2024-02-15',
  time: '19:00',
  partySize: 2
});

// Make a reservation
const booking = await system.makeReservation({
  platform: 'resy',
  restaurantId: '123',
  restaurantName: 'Carbone',
  date: '2024-02-15',
  time: '19:00',
  partySize: 2
});

// Quick book (search + check + book in one call)
const result = await system.quickBook({
  restaurantName: 'Carbone',
  location: 'NYC',
  date: '2024-02-15',
  preferredTime: '19:00',
  partySize: 2,
  platform: 'resy'
});

// Get my reservations
const reservations = await system.getMyReservations({ fetchRemote: true });

// Cancel
await system.cancelReservation({
  platform: 'resy',
  confirmationId: 'abc123'
});
```

### From CLI

```bash
# Search
node index.js search --location "NYC" --cuisine "Italian" --date 2024-02-15

# Check availability
node index.js availability --platform resy --id 12345 --date 2024-02-15 --time 19:00

# Book
node index.js book --platform resy --id 12345 --date 2024-02-15 --time 19:00

# Quick book (all-in-one)
node index.js quickbook --restaurant "Carbone" --location "NYC" --date 2024-02-15 --time 19:00

# View reservations
node index.js reservations --remote true

# Cancel
node index.js cancel --platform resy --confirmation abc123
```

## 🔧 Individual Clients

### Resy Client

```bash
node resy-client.js login
node resy-client.js search "Italian"
node resy-client.js availability 12345 2024-02-15 2
node resy-client.js book 12345 2024-02-15 19:00 2
node resy-client.js reservations
node resy-client.js cancel <resy_token>
```

### OpenTable Client

```bash
node opentable-client.js login
node opentable-client.js search "NYC" 2024-02-15 19:00 2 "Italian"
node opentable-client.js availability <restaurant-id> 2024-02-15 19:00 2
node opentable-client.js book <restaurant-id> 2024-02-15 19:00 2
node opentable-client.js reservations
node opentable-client.js cancel <confirmation>
```

### Yelp Client

```bash
node yelp-client.js search "New York" "Italian restaurants"
node yelp-client.js details <business-id>
```

## 📂 Files

```
reservations/
├── config.json           # Your credentials & preferences
├── index.js              # Unified reservation system
├── resy-client.js        # Resy API client
├── opentable-client.js   # OpenTable browser automation
├── yelp-client.js        # Yelp API + browser client
├── my-reservations.json  # Local cache of your bookings
├── favorites.json        # Saved favorite restaurants
├── package.json          # Dependencies
└── README.md             # This file
```

## ⚠️ Notes

- **Resy API** is the most reliable for booking. Get your tokens from network inspector.
- **OpenTable** requires browser automation because they don't provide public booking APIs.
- **Some restaurants** require credit card on file for reservations.
- **Rate limiting**: Don't spam requests. Be reasonable.
- **Authentication tokens** may expire. Re-login if you get 401 errors.

## 🎯 Common Restaurants (NYC)

| Restaurant | Platform | Venue ID |
|------------|----------|----------|
| Carbone | Resy | 834 |
| Don Angie | Resy | 2567 |
| Via Carota | Resy | 2040 |
| Le Bernardin | Resy | 1387 |

To find a venue ID:
1. Go to the restaurant on resy.com
2. Open Network tab, filter by `api.resy.com`
3. Look for `venue_id` in any request

## 🤖 Integration with Claude

To book a table via conversation:

```
"Book me a table at Carbone for 2 on February 15th at 7pm"
```

The system will:
1. Search for the restaurant
2. Check availability
3. Find the closest available time
4. Complete the booking
5. Return confirmation
