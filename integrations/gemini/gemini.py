#!/usr/bin/env python3
"""Gemini search/query integration for Jarvis."""
import os, sys, json, requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path.home() / "clawd" / ".env")
API_KEY = os.getenv("GEMINI_API_KEY")

def ask(prompt: str, model: str = "gemini-2.0-flash") -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]

def search(query: str) -> str:
    return ask(f"Search and answer this question with current, accurate information: {query}")

if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Query: ")
    print(ask(query))
