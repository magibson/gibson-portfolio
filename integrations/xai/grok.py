#!/usr/bin/env python3
"""
Grok/xAI Integration - X Search and Research
"""

import os
import json
import requests
from pathlib import Path

# Load API key from .env file
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, val = line.strip().split("=", 1)
                os.environ[key] = val

API_KEY = os.getenv("XAI_API_KEY")
BASE_URL = "https://api.x.ai/v1"

def chat(messages, model="grok-3-fast", tools=None, temperature=0.7, timeout=30):
    """Send a chat completion request to Grok"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature
    }
    
    if tools:
        payload["tools"] = tools
    
    try:
        response = requests.post(
            f"{BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout
        )
        return response.json()
    except requests.Timeout:
        return {"error": f"Request timed out after {timeout}s"}
    except Exception as e:
        return {"error": str(e)}

def responses_api(messages, model="grok-4", tools=None, timeout=240):
    """Use the responses API for agentic tool calling"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Convert messages to responses API format
    input_msgs = []
    for msg in messages:
        input_msgs.append({
            "role": msg["role"],
            "content": msg["content"]
        })
    
    payload = {
        "model": model,
        "input": input_msgs
    }
    
    if tools:
        payload["tools"] = tools
    
    try:
        response = requests.post(
            f"{BASE_URL}/responses",
            headers=headers,
            json=payload,
            timeout=timeout
        )
        
        if response.status_code != 200:
            return {"error": f"HTTP {response.status_code}: {response.text}"}
        
        return response.json()
    except requests.Timeout:
        return {"error": f"Request timed out after {timeout}s"}
    except Exception as e:
        return {"error": str(e)}

def search_x(query, context=None):
    """
    Search X (Twitter) using Grok's native X Search tool
    NOTE: Server-side tools require grok-4 family models.
    """
    messages = []
    
    if context:
        messages.append({"role": "system", "content": context})
    
    messages.append({
        "role": "user", 
        "content": f"Search X for: {query}\n\nProvide a summary of what you find, including relevant posts, users, and trends."
    })
    
    # Enable X Search tool — requires grok-4
    tools = [{"type": "x_search"}]
    
    result = responses_api(messages, model="grok-4", tools=tools)
    
    return parse_response(result)

def fetch_x_article(url, question=None):
    """
    Fetch and read the full content of an X article or post using Grok's live search.
    Uses grok-3 which has better web/X browsing capability.
    """
    prompt = question or "Read the full content of this article and summarize every tip, lesson, and recommendation in it."
    
    messages = [
        {
            "role": "user",
            "content": f"{prompt}\n\nURL: {url}\n\nIMPORTANT: Actually read the article at that URL. Do not hallucinate or guess the content. If you cannot access it, say so explicitly."
        }
    ]
    
    # Use both x_search and web_search to maximize chances of getting the content
    tools = [{"type": "x_search"}, {"type": "web_search"}]
    
    result = responses_api(messages, model="grok-4", tools=tools, timeout=240)
    return parse_response(result)

def web_search_grok(query, context=None):
    """
    Web search using Grok's web search tool
    NOTE: Server-side tools require grok-4 family models.
    """
    messages = []
    
    if context:
        messages.append({"role": "system", "content": context})
    
    messages.append({
        "role": "user",
        "content": f"Search the web for: {query}\n\nProvide a comprehensive summary of what you find."
    })
    
    tools = [{"type": "web_search"}]
    
    result = responses_api(messages, model="grok-4", tools=tools)
    
    return parse_response(result)

def parse_response(result):
    """Parse response from either chat or responses API"""
    if result.get("error"):
        return f"Error: {result['error']}"
    
    # Chat completions format
    if "choices" in result:
        return result["choices"][0]["message"]["content"]
    
    # Responses API format
    if "output" in result:
        for item in result.get("output", []):
            if item.get("type") == "message" and "content" in item:
                for content in item.get("content", []):
                    if content.get("type") == "output_text":
                        return content.get("text", "")
                    elif content.get("type") == "text":
                        return content.get("text", "")
    
    return f"Unexpected response format: {json.dumps(result, indent=2)[:500]}"

def ask_grok(question, system_prompt=None):
    """Simple question to Grok without tools"""
    messages = []
    
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    messages.append({"role": "user", "content": question})
    
    result = chat(messages)
    
    if "choices" in result:
        return result["choices"][0]["message"]["content"]
    else:
        return f"Error: {result}"

def test_connection():
    """Test API connection"""
    try:
        result = ask_grok("Say 'Grok online!' and nothing else.")
        return result
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python grok.py test              - Test API connection")
        print("  python grok.py ask 'question'    - Ask Grok")
        print("  python grok.py x 'query'         - Search X")
        print("  python grok.py web 'query'       - Web search")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "test":
        print(test_connection())
    elif cmd == "ask" and len(sys.argv) > 2:
        print(ask_grok(" ".join(sys.argv[2:])))
    elif cmd == "x" and len(sys.argv) > 2:
        print(search_x(" ".join(sys.argv[2:])))
    elif cmd == "web" and len(sys.argv) > 2:
        print(web_search(" ".join(sys.argv[2:])))
    else:
        print("Unknown command or missing query")
