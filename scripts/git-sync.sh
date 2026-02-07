#!/bin/bash
# Auto-commit and push changes to GitHub
# Usage: ./scripts/git-sync.sh "Commit message"

cd ~/clawd

MESSAGE="${1:-Auto-sync by Jarvis}"

# Check for changes
if git diff --quiet && git diff --cached --quiet; then
    echo "No changes to commit"
    exit 0
fi

# Add all changes
git add -A

# Commit with message
git commit -m "$MESSAGE

🤖 Auto-committed by Jarvis"

# Push to origin
git push origin main

echo "✅ Synced to GitHub"
