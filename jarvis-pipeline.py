#!/usr/bin/env python3
"""
Jarvis Response Pipeline - Convert text to Jarvis voice
"""

import requests
import sys
import tempfile
import subprocess

def speak_as_jarvis(text):
    """Convert text to Jarvis-like voice"""
    
    api_url = "https://qwen-qwen3-tts.hf.space/api/predict"
    
    # Use voice design for consistent Jarvis-like voice
    voice_prompt = "Create a sophisticated, warm British AI assistant voice like a high-tech butler - clear, intelligent, and slightly formal"
    
    data = {
        "data": [text, voice_prompt, "en"]
    }
    
    try:
        response = requests.post(api_url, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            # Handle the audio response
            print(f"🎵 Generated Jarvis voice for: {text[:50]}...")
            return True
        else:
            print(f"❌ TTS failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 jarvis-pipeline.py 'text to speak as jarvis'")
        sys.exit(1)
    
    text = " ".join(sys.argv[1:])
    speak_as_jarvis(text)
