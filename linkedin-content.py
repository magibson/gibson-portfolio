#!/usr/bin/env python3
"""
LinkedIn Content Generator for Financial Advisors
Generates weekly post ideas targeting young professionals
"""

import os
import json
import requests
from datetime import datetime, timedelta

# ===== CONFIGURATION =====
BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "")
ANTHROPIC_API_KEY = None

# Topics relevant to young professionals + finance
SEARCH_TOPICS = [
    "financial planning millennials gen z 2026",
    "building wealth in your 20s 30s",
    "first time home buyer tips 2026",
    "retirement savings young professionals",
    "budgeting money management tips",
    "investing basics beginners 2026",
    "career money decisions young adults",
    "student loan strategies 2026",
    "emergency fund savings tips",
    "life insurance young families"
]

def load_api_keys():
    """Load API keys from clawdbot config"""
    global ANTHROPIC_API_KEY, BRAVE_API_KEY
    
    # Anthropic key
    try:
        auth_file = os.path.expanduser("~/.clawdbot/agents/main/agent/auth-profiles.json")
        with open(auth_file) as f:
            data = json.load(f)
            for profile in data.get("profiles", {}).values():
                if profile.get("key"):
                    ANTHROPIC_API_KEY = profile["key"]
                    break
    except:
        pass
    
    # Brave key from config
    try:
        config_file = os.path.expanduser("~/.clawdbot/clawdbot.json")
        with open(config_file) as f:
            config = json.load(f)
            BRAVE_API_KEY = config.get("braveSearch", {}).get("apiKey", BRAVE_API_KEY)
    except:
        pass


def search_articles(query, count=3):
    """Search for articles using Brave Search"""
    if not BRAVE_API_KEY:
        return []
    
    try:
        headers = {"X-Subscription-Token": BRAVE_API_KEY}
        params = {
            "q": query,
            "count": count,
            "freshness": "pw"  # Past week
        }
        r = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers=headers,
            params=params,
            timeout=10
        )
        if r.status_code == 200:
            results = r.json().get("web", {}).get("results", [])
            return [{
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "description": r.get("description", "")
            } for r in results[:count]]
    except Exception as e:
        print(f"Search error: {e}")
    return []


def generate_post(article, topic_context):
    """Generate a LinkedIn post based on an article"""
    if not ANTHROPIC_API_KEY:
        return None
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        prompt = f"""Write a LinkedIn post for a young financial advisor targeting young professionals (20s-30s).

ARTICLE TO REFERENCE:
Title: {article['title']}
Description: {article['description']}
URL: {article['url']}

GUIDELINES:
- Casual, friendly tone - like a helpful friend, not a salesman
- NO product pitches or company mentions
- NO guarantees or promises about returns
- Keep it relatable to young professionals
- Add value with a genuine insight or tip
- End with a soft engagement question (not salesy)
- 100-150 words max
- Include 2-3 relevant hashtags

Write ONLY the post text, ready to copy-paste to LinkedIn."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content[0].text.strip()
    except Exception as e:
        print(f"Generation error: {e}")
        return None


def generate_weekly_content():
    """Generate 5 LinkedIn post options for the week"""
    load_api_keys()
    
    if not ANTHROPIC_API_KEY:
        return {"error": "No Anthropic API key found"}
    
    print("🔍 Searching for relevant articles...")
    
    # Gather articles from different topics
    all_articles = []
    for topic in SEARCH_TOPICS[:5]:  # Use 5 topics
        articles = search_articles(topic, count=2)
        for article in articles:
            article['topic'] = topic
        all_articles.extend(articles)
    
    if not all_articles:
        return {"error": "No articles found"}
    
    # Pick the 5 best/most diverse articles
    selected = all_articles[:5] if len(all_articles) >= 5 else all_articles
    
    print(f"📝 Generating {len(selected)} post drafts...")
    
    posts = []
    for i, article in enumerate(selected, 1):
        print(f"  Post {i}/{len(selected)}...")
        post_text = generate_post(article, article.get('topic', ''))
        if post_text:
            posts.append({
                "number": i,
                "article_title": article['title'],
                "article_url": article['url'],
                "post": post_text
            })
    
    return {
        "generated_at": datetime.now().isoformat(),
        "post_count": len(posts),
        "posts": posts
    }


def format_for_telegram(content):
    """Format the content for Telegram delivery"""
    if "error" in content:
        return f"❌ LinkedIn Content Error: {content['error']}"
    
    msg = f"📱 **LinkedIn Content for This Week**\n"
    msg += f"Generated: {datetime.now().strftime('%A, %B %d')}\n"
    msg += f"Posts: {content['post_count']} options (pick 3)\n"
    msg += "=" * 40 + "\n\n"
    
    for post in content['posts']:
        msg += f"**POST {post['number']}**\n"
        msg += f"📰 Article: {post['article_title']}\n"
        msg += f"🔗 {post['article_url']}\n\n"
        msg += f"✏️ **Draft:**\n{post['post']}\n"
        msg += "\n" + "-" * 40 + "\n\n"
    
    msg += "Pick your favorites and schedule them! 🚀"
    return msg


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("🧪 Running test generation...")
        content = generate_weekly_content()
        print(format_for_telegram(content))
    else:
        print("Usage: python linkedin-content.py test")
        print("       Or run via cron for weekly delivery")
