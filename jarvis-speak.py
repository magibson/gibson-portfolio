#!/usr/bin/env python3
"""
Jarvis TTS Integration - Convert Clawdbot responses to Jarvis voice
"""

import requests
import sys
import tempfile

def speak_as_jarvis(text):
    """Convert text to Jarvis voice using cloned model"""
    
    # Use the trained Qwen3-TTS model
    api_url = "https://qwen-qwen3-tts.hf.space/api/predict"
    
    data = {
        'text': text,
        'method': 'custom_voice',  # Use our cloned Jarvis voice
        'voice_id': 'jarvis_clone',  # Our saved voice profile
        'language': 'en'
    }
    
    try:
        response = requests.post(api_url, json=data)
        
        if response.status_code == 200:
            # Save to temp file and play
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                f.write(response.content)
                temp_file = f.name
            
            # Play the audio (macOS/Linux compatible)
            import subprocess
            try:
                subprocess.run(['afplay', temp_file], check=True)  # macOS
            except (FileNotFoundError, subprocess.CalledProcessError):
                try:
                    subprocess.run(['aplay', temp_file], check=True)  # Linux
                except (FileNotFoundError, subprocess.CalledProcessError):
                    print(f"Audio saved to: {temp_file}")
            
            return temp_file
        else:
            print(f"Error generating speech: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 jarvis-speak.py 'text to speak'")
        sys.exit(1)
    
    text = " ".join(sys.argv[1:])
    speak_as_jarvis(text)
