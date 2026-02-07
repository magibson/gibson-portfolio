# X Content Manager

A lightweight Flask app for managing X (Twitter) content before connecting an API. Built for photographers who want a clean draft queue, thread composer, and idea generator.

## Features
- Draft Queue with status, schedule time, tags, and image URL
- Thread Composer with add/remove/reorder and thread preview
- Content Generator with local prompt templates
- Dashboard with draft + scheduled counts and quick-add form

## Tech Stack
- Python Flask
- SQLite
- HTML/CSS (dark theme)

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install flask
```

## Run
```bash
python app.py
```

App runs at: `http://localhost:8086`

## Notes
- Database file: `x_content.db`
- Scheduled publishing is stored locally until X API is connected.
