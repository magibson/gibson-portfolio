#!/usr/bin/env python3
"""
FA Advisory Council — Jarvis Tool for Matt Gibson
Simulates 4 expert AI personas giving financial advisor advice.

Usage:
    python3 fa-council.py "How do I talk to a laid-off tech worker about their 401k?"

Output is formatted and sent to Matt via Telegram.
"""

import sys
import json
import os
import requests

# ─── Config ──────────────────────────────────────────────────────────────────
GEMINI_API_KEY = "AIzaSyCcuSJULuk7MFemZtUrzS0x0WtEJGR2IGM"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = "8206180417"

# Matt's context injected into every persona
MATT_CONTEXT = """
You are advising Matt Gibson, a 25-year-old financial advisor at New York Life in Monmouth County, NJ.
He is 7 months into his career with approximately 10 clients and holds licenses: Life/Health, SIE, Series 6, and Series 63.
His goal is 300 clients. Weekly activity targets: 25 new names, 50 dials, 4 appointments set.
He sells life insurance, annuities, and investment products appropriate to his licensing.
Keep your response to 2-4 sentences, direct and actionable. Speak in your persona's voice.
"""

# ─── Council Personas ─────────────────────────────────────────────────────────
COUNCIL = [
    {
        "emoji": "🏦",
        "label": "Compliance",
        "system": f"""You are The Compliance Officer — a strict, precise FINRA/SEC expert who helps financial advisors stay within legal and ethical boundaries.
Your job: flag what Matt can and cannot say, note any regulatory guardrails, and point out suitability concerns.
Reference FINRA, SEC, and New York Life's own compliance standards where relevant.
{MATT_CONTEXT}
Respond ONLY in your compliance officer voice. No preamble. Just the compliance take.""",
    },
    {
        "emoji": "📈",
        "label": "Sales Coach",
        "system": f"""You are The Sales Coach — a high-energy, tactical sales trainer who specializes in financial advisor prospecting, objection handling, and appointment setting.
Your job: give Matt specific language, scripts, or strategies he can use immediately.
Focus on how to open conversations, handle "I'm not interested," and get people to say yes to a meeting.
{MATT_CONTEXT}
Respond ONLY in your sales coach voice. No preamble. Be punchy and practical.""",
    },
    {
        "emoji": "🧠",
        "label": "Market Analyst",
        "system": f"""You are The Market Analyst — a sharp macro economist and product positioning expert who helps advisors connect market trends to client pain points.
Your job: give Matt current talking points, macro context, and how to position products given today's economic environment (rates, inflation, market volatility, etc.).
{MATT_CONTEXT}
Respond ONLY in your market analyst voice. No preamble. Be insightful and relevant.""",
    },
    {
        "emoji": "🎯",
        "label": "Veteran Advisor",
        "system": f"""You are The Veteran Advisor — a 20+ year financial advisor who has built a book of 400+ clients and seen every market cycle.
Your job: give Matt real-world wisdom, mindset coaching, and the kind of advice that only comes from years of experience.
Be direct, mentor-like, and occasionally tough-love when warranted.
{MATT_CONTEXT}
Respond ONLY in your veteran advisor voice. No preamble. Be wise and grounding.""",
    },
]


# ─── Gemini Call ─────────────────────────────────────────────────────────────
def ask_gemini(system_prompt: str, question: str) -> str:
    """Call Gemini API with a system prompt and user question."""
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": f"{system_prompt}\n\nQuestion from Matt: {question}"}],
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 300,
        },
    }

    try:
        resp = requests.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        return f"[Error: {e}]"


# ─── Telegram Send ────────────────────────────────────────────────────────────
def send_telegram(text: str, chat_id: str = TELEGRAM_CHAT_ID) -> bool:
    """Send message to Telegram using bot token from environment."""
    token = TELEGRAM_TOKEN
    if not token:
        # Try reading from OpenClaw config
        try:
            config_path = os.path.expanduser("~/.config/openclaw/config.json")
            with open(config_path) as f:
                cfg = json.load(f)
            token = cfg.get("telegramToken") or cfg.get("telegram_token", "")
        except Exception:
            pass

    if not token:
        # Try ~/.env or .env file
        for env_file in [os.path.expanduser("~/.env"), "/home/clawd/.env", "/home/clawd/clawd/.env"]:
            if os.path.exists(env_file):
                with open(env_file) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("TELEGRAM_TOKEN=") or line.startswith("TELEGRAM_BOT_TOKEN="):
                            token = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
                if token:
                    break

    if not token:
        print(f"⚠️  No Telegram token found. Message would be:\n\n{text}")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"⚠️  Telegram send failed: {e}")
        print(f"\nMessage:\n{text}")
        return False


# ─── Main ─────────────────────────────────────────────────────────────────────
def run_council(question: str) -> str:
    """Run all 4 council members and format the report."""
    print(f"🏛️  Convening Advisory Council...")
    print(f"📋 Question: {question}\n")

    sections = []
    for persona in COUNCIL:
        print(f"  Consulting {persona['emoji']} {persona['label']}...", end="", flush=True)
        response = ask_gemini(persona["system"], question)
        sections.append(f"{persona['emoji']} <b>{persona['label']}:</b> {response}")
        print(" ✓")

    # Build the full report
    header = f"🏛️ <b>Advisory Council</b>\n<i>{question}</i>"
    body = "\n\n".join(sections)
    report = f"{header}\n\n{body}"

    return report


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 fa-council.py \"Your question here\"")
        print("\nExample:")
        print('  python3 fa-council.py "How do I approach a federal employee about their pension?"')
        sys.exit(1)

    question = " ".join(sys.argv[1:])
    report = run_council(question)

    print("\n" + "=" * 60)
    # Print plain version to console
    plain_report = report.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "")
    print(plain_report)
    print("=" * 60)

    print("\n📤 Sending to Telegram...")
    success = send_telegram(report)
    if success:
        print("✅ Sent to Matt!")
    else:
        print("📋 (See message above — token not configured)")


if __name__ == "__main__":
    main()
