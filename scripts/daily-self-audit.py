#!/usr/bin/env python3
"""
Daily self-audit - checks critical systems are healthy.
Only prints CRITICAL: lines if something is broken.
"""
import subprocess, os, sys
from pathlib import Path

CLAWD = Path.home() / "clawd"
issues = []

# Check critical scripts exist
critical_scripts = [
    "scripts/daily-health-log.py",
    "scripts/health-check.py", 
    "scripts/kalshi-sync.py",
    "scripts/portfolio-monitor.py",
    "scripts/world-situation-monitor.py",
    "projects/warn-tracker/scraper.py",
]
for s in critical_scripts:
    if not (CLAWD / s).exists():
        issues.append(f"Missing script: {s}")

# Check key services running
services = {
    "dashboard": 8080,
    "linkedin-prospector": 8089,
}
import socket
for name, port in services.items():
    try:
        s = socket.socket()
        s.settimeout(2)
        s.connect(("localhost", port))
        s.close()
    except:
        issues.append(f"Service down: {name} (port {port})")

if issues:
    for issue in issues:
        print(f"CRITICAL: {issue}")
    sys.exit(1)
else:
    print("All systems healthy")
    sys.exit(0)
