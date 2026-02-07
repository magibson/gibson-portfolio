#!/bin/bash
# Jarvis Mac Setup Script
# Run this in your jarvis_clips folder with mlx_env activated

set -e

echo "=========================================="
echo "🔵 Jarvis Mac Setup"
echo "=========================================="
echo

# Check if in venv
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Please activate your virtual environment first:"
    echo "   source ../mlx_env/bin/activate"
    exit 1
fi

echo "📦 Installing dependencies..."
pip install -q rumps openai-whisper sounddevice soundfile numpy requests pynput pyobjc

echo "✅ Dependencies installed"
echo

# Download files from VPS
echo "📥 Downloading Jarvis files..."
VPS="100.83.250.65"

# Check Tailscale
if ! ping -c 1 $VPS > /dev/null 2>&1; then
    echo "❌ Can't reach VPS at $VPS"
    echo "   Make sure Tailscale is connected"
    exit 1
fi

# We can't scp, so files need to be created manually or via curl
echo "✅ VPS reachable"
echo

echo "=========================================="
echo "📋 Next Steps:"
echo "=========================================="
echo
echo "1. Make sure jarvis_server_5001.py is running:"
echo "   python jarvis_server_5001.py"
echo
echo "2. In a new terminal, run the menu bar app:"
echo "   python jarvis-menubar.py"
echo
echo "3. Look for 🔵 in your menu bar"
echo
echo "4. Press Cmd+Shift+J to talk, or click the icon"
echo
echo "=========================================="
echo "🔐 Security Info:"
echo "=========================================="
echo "- All traffic encrypted via Tailscale"
echo "- Voice processed locally (Whisper)"  
echo "- TTS runs locally (your Mac)"
echo "- Auth token protects VPS endpoint"
echo "=========================================="
