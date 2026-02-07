#!/usr/bin/env python3
"""
Qwen3-TTS API Client for Jarvis Voice
"""

import requests
import json
import base64
import tempfile
import os

class Qwen3TTSClient:
    def __init__(self, api_endpoint="huggingface", api_key=None):
        self.api_key = api_key
        
        if api_endpoint == "huggingface":
            self.api_url = "https://api-inference.huggingface.co/models/Qwen/Qwen3-TTS-12Hz-1.7B-Base"
        elif api_endpoint == "local":
            self.api_url = "http://localhost:7000/generate"
        else:
            self.api_url = api_endpoint
    
    def text_to_speech(self, text, voice_description="British AI assistant, warm and intelligent"):
        """Convert text to speech using Qwen3-TTS"""
        
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "inputs": {
                "text": text,
                "voice_description": voice_description
            }
        }
        
        try:
            response = requests.post(
                self.api_url, 
                headers=headers, 
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                # Save audio response
                audio_filename = f"jarvis_voice_{len(text)}.wav"
                with open(audio_filename, 'wb') as f:
                    f.write(response.content)
                
                print(f"🎵 Generated: {audio_filename}")
                return audio_filename
            else:
                print(f"❌ API Error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def jarvis_voice_clone(self, text, reference_audio_path=None):
        """Clone Jarvis voice from reference audio"""
        
        if reference_audio_path and os.path.exists(reference_audio_path):
            with open(reference_audio_path, 'rb') as f:
                reference_audio = base64.b64encode(f.read()).decode()
        else:
            reference_audio = None
        
        payload = {
            "text": text,
            "reference_audio": reference_audio,
            "language": "en"
        }
        
        # Implementation depends on specific API
        print(f"🧬 Voice cloning: {text[:50]}...")
        return self.text_to_speech(text, "Paul Bettany as Jarvis - British AI assistant")

# Test the client
if __name__ == "__main__":
    client = Qwen3TTSClient()
    
    test_phrases = [
        "Good morning, Mr. Gibson. At your service, sir.",
        "Drone flying conditions are optimal today.",
        "All systems are online and ready, sir."
    ]
    
    for phrase in test_phrases:
        result = client.text_to_speech(phrase)
        if result:
            print(f"✅ Generated: {result}")
        else:
            print("❌ Failed to generate audio")
