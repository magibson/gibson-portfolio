#!/usr/bin/env python3
"""
Jarvis Voice with ElevenLabs API
Best quality option for authentic voice cloning
"""

import requests
import json
import base64

class ElevenLabsJarvis:
    def __init__(self, api_key=None):
        self.api_key = api_key or "your_api_key_here"
        self.base_url = "https://api.elevenlabs.io/v1"
        
        # Pre-made British male voices that sound Jarvis-like
        self.jarvis_voices = {
            "british_male": "21m00Tcm4TlvDq8ikWAM",  # Brian - British male
            "professional": "2EiwWnXFnvU5JabPnv8n",   # Clyde - Professional 
            "warm_british": "D38z5RcWu1voky8WS1ja",    # Ethan - English warm
            "butler": "VR6AewLTigWG4xSOukaG"          # Josh - Professional butler-like
        }
    
    def text_to_speech(self, text, voice_id="21m00Tcm4TlvDq8ikWAM"):
        """Convert text to speech using ElevenLabs"""
        
        url = f"{self.base_url}/text-to-speech/{voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
        
        try:
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                # Save audio file
                filename = f"jarvis_voice_{len(text)}.mp3"
                with open(filename, 'wb') as f:
                    f.write(response.content)
                print(f"🎵 Generated: {filename}")
                return filename
            else:
                print(f"❌ ElevenLabs Error: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def jarvis_speak(self, text):
        """Speak as Jarvis with proper formatting"""
        
        # Format text for Jarvis
        if "Matt" in text and "Mr. Gibson" not in text:
            text = text.replace("Matt", "Mr. Gibson")
        
        if not text.strip().endswith(("sir", "sir.")):
            text += ", sir."
        
        return self.text_to_speech(text, self.jarvis_voices["british_male"])
    
    def clone_voice_from_audio(self, audio_file_path, voice_name="Jarvis"):
        """Clone voice from audio sample (requires Pro plan)"""
        
        url = f"{self.base_url}/voices/add"
        
        headers = {"xi-api-key": self.api_key}
        
        with open(audio_file_path, 'rb') as audio_file:
            files = {'files': audio_file}
            data = {'name': voice_name}
            
            response = requests.post(url, headers=headers, files=files, data=data)
            
            if response.status_code == 200:
                voice_id = response.json()['voice_id']
                print(f"✅ Voice cloned! ID: {voice_id}")
                return voice_id
            else:
                print(f"❌ Voice cloning failed: {response.status_code}")
                return None

def demo_jarvis_voice():
    """Demo the Jarvis voice system"""
    
    jarvis = ElevenLabsJarvis()
    
    test_phrases = [
        "Good morning, Matt. All systems are online.",
        "Drone flying conditions are optimal today.",
        "Your daily briefing is ready, sir.",
        "Weather analysis complete. Cold temperatures detected."
    ]
    
    print("🤖 JARVIS ELEVENLABS DEMO")
    print("=" * 50)
    
    for phrase in test_phrases:
        print(f"\n📝 Text: {phrase}")
        
        # Format for Jarvis
        jarvis_text = phrase
        if "Matt" in jarvis_text and "Mr. Gibson" not in jarvis_text:
            jarvis_text = jarvis_text.replace("Matt", "Mr. Gibson")
        
        if not jarvis_text.strip().endswith(("sir", "sir.")):
            jarvis_text += ", sir."
        
        print(f"🎭 Jarvis: {jarvis_text}")
        print("🔑 Need ElevenLabs API key to generate audio")
    
    print("\n🎯 Setup Instructions:")
    print("1. Get free ElevenLabs API key: https://elevenlabs.io")
    print("2. Add API key to this script")
    print("3. Run: python3 jarvis-elevenlabs.py")

if __name__ == "__main__":
    demo_jarvis_voice()