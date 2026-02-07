#!/bin/bash
# Stock Research Dashboard - Start Script
# Stock Research Dashboard

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Kill any existing instance on port 8084
pkill -f "python.*stock-dashboard.*app.py" 2>/dev/null || true
sleep 1

echo ""
echo "📈 ═══════════════════════════════════════════════════"
echo "   STOCK RESEARCH DASHBOARD"
echo "   360° Stock Research View"
echo "═══════════════════════════════════════════════════"
echo ""
echo "   URL: http://localhost:8084"
echo "   External: http://$(curl -s ifconfig.me 2>/dev/null || echo 'YOUR_IP'):8084"
echo ""
echo "   Default Tickers: AMD, NVDA, VST"
echo "   Auto-refresh: Every 5 minutes"
echo ""
echo "   Data Sources:"
echo "   • Alpaca Markets (price, news)"
echo "   • Polymarket (prediction markets)"
echo "   • Grok/xAI (X/Twitter sentiment)"
echo ""
echo "   Press Ctrl+C to stop"
echo "═══════════════════════════════════════════════════"
echo ""

# Run the app
exec python3 app.py
