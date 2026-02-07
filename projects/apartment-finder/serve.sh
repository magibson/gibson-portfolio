#!/bin/bash
# Quick server for the apartment finder dashboard
cd "$(dirname "$0")"
echo "🏠 Starting Apartment Finder dashboard..."
echo "   Open http://localhost:8080/static/"
echo "   Press Ctrl+C to stop"
python3 -m http.server 8080
