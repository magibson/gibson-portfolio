#!/bin/bash
set -e
echo "🧠 Setting up Second Brain..."
mkdir -p ~/clawd/data/brain/chroma
~/clawd/.venv/bin/pip install -r "$(dirname "$0")/requirements.txt" -q
echo "✅ Second Brain ready."
echo "   Save: python cli.py save <url|text|file>"
echo "   Search: python cli.py search <query>"
echo "   UI: http://100.82.133.57:8091"
