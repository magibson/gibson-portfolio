#!/usr/bin/env python3
"""
Layoff Outreach Generator
Uses Gemini AI to generate empathetic, layoff-specific outreach messages for LinkedIn.
"""

import sys
import json
import urllib.parse
import requests
from pathlib import Path

GEMINI_API_KEY = "AIzaSyCcuSJULuk7MFemZtUrzS0x0WtEJGR2IGM"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"


def generate_layoff_messages(company_name: str, employee_count: int, location: str) -> dict:
    """
    Generate empathetic layoff outreach messages using Gemini.

    Returns:
        dict with keys:
          - connection_request: str (≤300 chars)
          - followup_dm: str (≤500 chars)
          - sales_nav_url: str
    """
    prompt = f"""You are Matt, an independent financial advisor helping people navigate career transitions.
A company called "{company_name}" in {location} just laid off {employee_count} employees per the WARN Act.

Generate two LinkedIn outreach messages:

1. CONNECTION_REQUEST (max 300 characters):
   - Empathetic tone, acknowledges the transition at {company_name}
   - Soft hook around financial planning during career transitions (401k, benefits, etc.)
   - NO product pitching. NO "I can help you" promises. Just a warm, human connection request.
   - Example tone: "Hi [Name], I saw {company_name} went through some changes recently. I work with people navigating career transitions on the financial side — happy to connect."

2. FOLLOWUP_DM (max 500 characters, sent after connection accepted):
   - Continues the empathetic tone
   - Gently raises the 401k rollover decision they'll need to make (time-sensitive)
   - Offers a free 30-min call, no pressure
   - Still no hard selling

Return ONLY valid JSON in this exact format, no other text:
{{
  "connection_request": "...",
  "followup_dm": "..."
}}"""

    try:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 512
            }
        }
        resp = requests.post(GEMINI_URL, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # Extract text from Gemini response
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        messages = json.loads(text)

        # Enforce character limits
        conn_req = messages.get("connection_request", "")[:300]
        followup = messages.get("followup_dm", "")[:500]

    except Exception as e:
        print(f"⚠️  Gemini API error: {e}. Using fallback templates.", file=sys.stderr)
        conn_req = (
            f"Hi [Name], I saw {company_name} recently went through some changes. "
            f"I work with people navigating career transitions on the financial side — happy to connect."
        )[:300]
        followup = (
            f"Thanks for connecting! With the transition at {company_name}, one thing that often "
            f"comes up is the 401k rollover decision — it's time-sensitive and easy to overlook. "
            f"I offer a free 30-min call to walk through options, no pressure at all. "
            f"Would that be helpful?"
        )[:500]

    # Generate Sales Navigator URL
    encoded_name = urllib.parse.quote(company_name, safe="")
    sales_nav_url = (
        f"https://www.linkedin.com/sales/search/people?"
        f"query=(filters:List((type:CURRENT_COMPANY,values:List("
        f"(text:{encoded_name},selectionType:INCLUDED)))))"
    )

    return {
        "connection_request": conn_req,
        "followup_dm": followup,
        "sales_nav_url": sales_nav_url
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate layoff outreach messages")
    parser.add_argument("--test", metavar="COMPANY", help="Test mode: pass company name")
    parser.add_argument("employee_count", nargs="?", type=int, default=100)
    parser.add_argument("location", nargs="?", default="NJ")
    args = parser.parse_args()

    company = args.test or "Test Corp"
    count = args.employee_count
    loc = args.location

    print(f"\n🏢  Company:  {company}")
    print(f"👥  Employees: {count}")
    print(f"📍  Location: {loc}")
    print("\n" + "="*60)

    result = generate_layoff_messages(company, count, loc)

    print(f"\n🔗  Sales Nav URL:\n{result['sales_nav_url']}")
    print(f"\n📬  Connection Request ({len(result['connection_request'])} chars):")
    print(result["connection_request"])
    print(f"\n💬  Follow-up DM ({len(result['followup_dm'])} chars):")
    print(result["followup_dm"])
    print()
