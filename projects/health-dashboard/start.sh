#!/usr/bin/env bash
set -euo pipefail

export FLASK_ENV=production
# Port 8087 - Health Trends Dashboard
python3 /home/clawd/clawd/projects/health-dashboard/app.py
