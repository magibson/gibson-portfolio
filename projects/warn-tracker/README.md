# WARN Act Tracker - NJ/PA

A local dashboard for tracking WARN Act layoff notices in New Jersey and Pennsylvania. Built for Matt's prospecting workflow.

## Features

- **NJ & PA only** - Focused on states where Matt is registered
- **Daily auto-scrape** - Python script fetches fresh data from official sources
- **NEW badges** - Notices added in last 24 hours are highlighted
- **BIG badges** - Layoffs with 100+ employees are flagged
- **News search** - Quick links to Google/Bing news for each company
- **LinkedIn integration** - One-click search for company employees
- **Alerts** - Big layoffs (100+) are saved to `alerts.json` for notification

## Files

```
warn-tracker/
├── index.html      # Dashboard UI
├── scraper.py      # Python scraper for NJ/PA WARN data
├── data.json       # Scraped data (read by dashboard)
├── alerts.json     # Big layoff alerts for notification
├── requirements.txt
└── README.md
```

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the scraper manually

```bash
python scraper.py
```

### 3. Open the dashboard

Open `index.html` in your browser, or serve it:

```bash
python -m http.server 8080
# Then visit http://localhost:8080
```

## Daily Auto-Scrape (Cron)

Add to crontab to run daily at 6 AM:

```bash
crontab -e
```

Add this line:
```
0 6 * * * cd /home/clawd/clawd/projects/warn-tracker && /usr/bin/python3 scraper.py >> /var/log/warn-scraper.log 2>&1
```

## Alert Notifications

The scraper writes big layoffs (100+ employees) to `alerts.json`. To get notified via Telegram:

1. Create a simple check script:
```bash
#!/bin/bash
ALERTS=$(cat /home/clawd/clawd/projects/warn-tracker/alerts.json)
COUNT=$(echo "$ALERTS" | jq '.alerts | length')
if [ "$COUNT" -gt 0 ]; then
    # Send via Clawdbot or Telegram API
    echo "New big layoffs found!"
fi
```

2. Add to crontab after scraper runs:
```
5 6 * * * /path/to/check-alerts.sh
```

## Workflow

1. **Morning**: Dashboard shows NEW and BIG layoffs from overnight scrape
2. **Research**: Click "News" to check for articles about the company
3. **LinkedIn**: Click "in Search" to find employees at that company
4. **Target**: Look for "Open to Work" badges on profiles
5. **Outreach**: Use your CRM for contact management (not this tool!)

## Data Sources

- **NJ**: https://www.nj.gov/labor/employer-services/warn/
- **PA**: https://www.pa.gov/agencies/dli/programs-services/workforce-development-home/warn-requirements/warn-notices.html

## Compliance

This tool only displays publicly available WARN Act data. It does NOT store:
- Contact information
- Prospect/client data
- CRM features

Use your work CRM for all contact management.

## Troubleshooting

**Scraper not finding data?**
- The NJ WARN PDF format changes periodically. Check the PDF URL is current.
- PA page structure may change. Update the scraper's parsing logic if needed.

**Dashboard shows old data?**
- Make sure scraper.py ran successfully
- Check `data.json` was updated (check `last_updated` field)
- Hard refresh the browser (Ctrl+Shift+R)

**News links not working?**
- News links go to Google/Bing search. If blocked, try a different network.
