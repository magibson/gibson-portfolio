#!/bin/bash
# One-time setup for browser automation
# Run with: sudo ./setup_browser.sh

echo "Installing Chromium dependencies for Playwright..."

apt-get update -qq

apt-get install -y --no-install-recommends \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libxshmfence1 \
    libxkbcommon0 \
    fonts-liberation \
    libnss3 \
    libnspr4

echo ""
echo "✅ Browser dependencies installed!"
echo ""
echo "Now run the scraper:"
echo "  cd /home/clawd/clawd/projects/apartment-finder"
echo "  python3 scripts/browser_scraper.py"
