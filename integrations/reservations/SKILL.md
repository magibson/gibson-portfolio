# Dinner Reservations Skill

Make restaurant reservations via Resy and OpenTable.

## Quick Reference

| Platform | Method | Status |
|----------|--------|--------|
| Resy | API (direct) | ✅ Ready after setup |
| OpenTable | Chrome relay | ✅ Use browser tool |

## Setup Required

⚠️ **Before using, Matt needs to configure credentials.** See `SECURITY.md` for full instructions.

### Quick Setup (Resy)

1. Go to resy.com, log in
2. Open DevTools → Network tab
3. Find request to api.resy.com
4. Copy headers: `authorization` (api_key) and `x-resy-auth-token`
5. Create `.env` file:
   ```bash
   cp .env.example .env
   nano .env  # Add your tokens
   chmod 600 .env
   ```
6. Test: `node book.js status`

## Resy Bookings (API)

### Check Status
```bash
node book.js status
```

### Search Restaurants
```bash
node book.js resy search "Italian" 2
node book.js resy search "Don Angie"
```

### Check Availability
```bash
node book.js resy availability <venue_id> <date> [party_size]
node book.js resy availability 1505 2024-02-15 2
```

### Make Booking
```bash
node book.js resy book <venue_id> <date> <time> [party_size]
node book.js resy book 1505 2024-02-15 19:00 2
```

### List Reservations
```bash
node book.js resy reservations
```

### Cancel
```bash
node book.js resy cancel <resy_token>
```

## OpenTable Bookings (Chrome Relay)

OpenTable has aggressive bot detection. Use Matt's real browser session:

1. Matt logs into OpenTable in Chrome
2. Matt clicks Clawdbot Browser Relay toolbar button (badge → ON)
3. Use browser tool with `profile="chrome"`:
   ```javascript
   browser.navigate({ url: 'https://www.opentable.com/...' })
   browser.act({ action: 'click', selector: '...' })
   ```
4. Matt clicks toolbar button when done (badge → OFF)

**Benefits:** No bot detection, uses existing session, no credentials stored.

## Programmatic Usage

```javascript
import ResyClient from './resy-client.js';

const client = new ResyClient();

// Search
const results = await client.searchRestaurants('Italian', 'New York', 2);

// Check availability
const slots = await client.getAvailability(venueId, '2024-02-15', 2);

// Book
const result = await client.bookSlot(venueId, '2024-02-15', '19:00', 2);

// List reservations
const mine = await client.getMyReservations();

// Cancel
await client.cancelReservation(resyToken);
```

## Common NYC Venue IDs (Resy)

| Restaurant | Venue ID |
|------------|----------|
| Don Angie | 1505 |
| Carbone | 834 |
| Via Carota | 568 |
| Le Bernardin | 1387 |

*Find more by searching and checking the venue_id in results.*

## Notes for Clawd

When booking for Matt:

1. **Check status first** - Run `node book.js status` to verify credentials
2. **Confirm details** - Always confirm restaurant, date, time, party size before booking
3. **Use Resy first** - More reliable than OpenTable automation
4. **Handle 401 errors** - Token expired, tell Matt to re-extract from DevTools
5. **Don't log tokens** - Be careful about what goes in console output
6. **Rate limit** - Add delays between requests, don't spam API

## Troubleshooting

| Error | Solution |
|-------|----------|
| 401 Unauthorized | Token expired - re-extract from DevTools |
| No slots found | Check date format (YYYY-MM-DD), verify party size |
| RESY_API_KEY not configured | Create .env file with credentials |
| OpenTable timeout | Use Chrome relay instead of headless automation |

## Files

- `book.js` - Simple CLI interface
- `resy-client.js` - Resy API client
- `opentable-client.js` - OpenTable browser automation (use Chrome relay instead)
- `.env` - Credentials (gitignored)
- `.env.example` - Template for credentials
- `config.json` - Non-sensitive settings
- `SECURITY.md` - Security documentation
- `RESEARCH.md` - Technical research notes
