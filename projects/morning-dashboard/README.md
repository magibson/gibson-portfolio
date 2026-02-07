# J.A.R.V.I.S. Dashboard

*"Good morning, Sir."*

A JARVIS-themed personal dashboard inspired by Tony Stark's lab interface from the Iron Man movies.

## ✨ Design Features

### Visual Effects
- **Animated grid background** - Pulsing holographic grid pattern
- **Scan beam** - Moving horizontal scan line across the screen
- **Holographic cards** - Glassmorphism with animated shine effects
- **Arc reactor visualization** - Shows agent status with Iron Man-style reactor
- **Glow effects** - Cyan neon glow on all interactive elements

### Typography
- **Orbitron** - Futuristic monospace font for headers
- **Rajdhani** - Clean, techy font for body text

### Colors
- Primary: `#00d4ff` (JARVIS cyan)
- Background: `#0a0e14` (near black)
- Active: `#00ff88` (green glow for active processes)

## 📊 Dashboard Sections

| Section | Status | Data Source |
|---------|--------|-------------|
| **Time & Date** | ✅ Live | System clock (Eastern TZ) |
| **Weather** | ✅ Live | Open-Meteo API |
| **Schedule** | ✅ Live | Google Calendar API |
| **Markets** | ✅ Live | Yahoo Finance (S&P 500, VIX, 10Y Treasury, TSLA) |
| **Communications** | ✅ Live | Gmail API (unread count) |
| **Agent Status** | ✅ Live | `agent-status.json` |
| **Tasks** | 🔲 Mock | Placeholder for TickTick |
| **Quick Memory** | ✅ Working | localStorage |
| **Access Nodes** | ✅ Working | localStorage |

## 🚀 Running

```bash
cd /home/clawd/clawd/projects/morning-dashboard

# Fetch real data (Gmail, Calendar, Markets)
python3 fetch_data.py

# Start the server
python3 -m http.server 8080

# Open: http://localhost:8080
```

## 📡 Data Fetcher

`fetch_data.py` pulls real data from:
- **Gmail API** - Unread email count
- **Google Calendar API** - Today's events  
- **Yahoo Finance** - S&P 500, VIX, 10Y Treasury, TSLA

Data is written to `data.json` which the dashboard reads.

**Cron job** (runs every 5 minutes):
```bash
*/5 * * * * cd /home/clawd/clawd/projects/morning-dashboard && python3 fetch_data.py >> /tmp/dashboard-fetch.log 2>&1
```

## ⚙️ Configuration

Edit the `CONFIG` object in index.html:

```javascript
const CONFIG = {
  location: { lat: 40.3471, lon: -74.0637, name: 'Red Bank, NJ' },
  refreshInterval: 5 * 60 * 1000, // 5 minutes
  timezone: 'America/New_York'
};
```

## 🔑 API Credentials

Uses Google OAuth credentials from:
- `/home/clawd/clawd/google-credentials.json`
- `/home/clawd/clawd/google-tokens.json`

Scopes: `calendar.readonly`, `gmail.readonly`

## 🤖 Agent Status Feature

The dashboard monitors `agent-status.json` for real-time sub-agent activity. When sub-agents are running, the arc reactor pulses green and shows processing indicators.

```json
{
  "main": { "lastActive": "2024-01-15T10:30:00Z" },
  "agents": [
    {
      "id": "subagent-1",
      "label": "Research Agent",
      "status": "running",
      "task": "Researching topic X",
      "startedAt": "2024-01-15T10:25:00Z"
    }
  ]
}
```

## 💾 Local Storage Keys

| Key | Purpose |
|-----|---------|
| `dashboard_notes` | Quick memory fragments |
| `dashboard_links` | Custom access nodes |
| `dashboard_tasks` | Task list (override mock) |
| `dashboard_alerts` | Active alerts with TTL |

## 🔌 Pending Integrations

- **TickTick API** - Wire up in `loadTasks()` for real task data
- **News headlines** - Could add a news feed section

---

*"I am J.A.R.V.I.S. — Just A Rather Very Intelligent System."*
