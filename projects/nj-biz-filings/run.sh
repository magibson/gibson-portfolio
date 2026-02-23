#!/bin/bash
# NJ Business Filings Scraper runner
cd "$(dirname "$0")"
python3 scraper.py "$@"
