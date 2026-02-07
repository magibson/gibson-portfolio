#!/usr/bin/env python3
"""Grok Imagine - Image Generation"""

import os
import requests
from pathlib import Path

# Load API key
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, val = line.strip().split("=", 1)
                os.environ[key] = val

API_KEY = os.getenv("XAI_API_KEY")

def generate_image(prompt, n=1, response_format="url"):
    """Generate image(s) from a text prompt"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "grok-imagine-image",
        "prompt": prompt,
        "n": n,
        "response_format": response_format
    }
    
    response = requests.post(
        "https://api.x.ai/v1/images/generations",
        headers=headers,
        json=payload
    )
    
    return response.json()

if __name__ == "__main__":
    import sys
    prompt = sys.argv[1] if len(sys.argv) > 1 else "A test image"
    result = generate_image(prompt)
    print(result)


def generate_video(prompt, duration=10, aspect_ratio="16:9", image_url=None):
    """Start video generation and poll for result"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "grok-imagine-video",
        "prompt": prompt,
        "duration": duration,
        "aspect_ratio": aspect_ratio
    }
    
    if image_url:
        payload["image_url"] = image_url
    
    # Start generation
    response = requests.post(
        "https://api.x.ai/v1/videos/generations",
        headers=headers,
        json=payload
    )
    
    result = response.json()
    if "request_id" not in result:
        return result  # Error case
    
    request_id = result["request_id"]
    print(f"Video generation started: {request_id}")
    
    # Poll for result
    import time
    for _ in range(120):  # Max 2 min wait
        time.sleep(2)
        check = requests.get(
            f"https://api.x.ai/v1/videos/{request_id}",
            headers=headers
        )
        status = check.json()
        if status.get("status") == "completed":
            return status
        elif status.get("status") == "failed":
            return status
        print(f"Status: {status.get('status', 'processing')}...")
    
    return {"error": "timeout", "request_id": request_id}
