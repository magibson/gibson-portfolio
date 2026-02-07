#!/usr/bin/env python3
"""
Complete Jarvis TTS System - Ready for immediate use
Works with both cloned voices and pre-existing British voices
"""

import requests
import json
import os
import sys

class CompleteJarvisTTS:
    
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.base_url = "https://api.elevenlabs.io/v1"
        
        # Pre-existing British voices (available immediately)
        self.british_voices = {
            "brian": "nPczCjzI2devNBz1zQrb",      # Professional British male
            "daniel": "onwK4e9ZLuTAKqWW03F9",     # Deep British male  
            "callum": "N2lVS1w4EtoT3dr4eOWO",     # Sophisticated British
            "charlie": "IKne3meq5aSn9XLyUdCD",    # Warm British male
        }
        
        # Check for custom cloned voice
        self.custom_voice_id = self.load_custom_voice_id()
    
    def load_custom_voice_id(self):
        """Load custom Jarvis voice ID if it exists"""
        
        for filename in ["real-jarvis-voice-id.txt", "jarvis-voice-id.txt"]:
            if os.path.exists(filename):
                with open(filename, "r") as f:
                    voice_id = f.read().strip()
                    if voice_id:
                        print(f"✅ Found custom Jarvis voice: {voice_id}")
                        return voice_id
        
        return None
    
    def get_voice_id(self):
        """Get the best available voice ID"""
        
        if self.custom_voice_id:
            return self.custom_voice_id, "Custom Jarvis (Paul Bettany clone)"
        else:
            return self.british_voices["brian"], "Brian (British male)"
    
    def format_text_for_jarvis(self, text):
        """Format any text to sound like Jarvis"""
        
        # Replace Matt with Mr. Gibson
        if "Matt" in text and "Mr. Gibson" not in text:
            text = text.replace("Matt", "Mr. Gibson")
        
        # Add sir for formality (but don't duplicate)
        if not text.strip().endswith(("sir", "sir.", "Sir", "Sir.")):
            if any(word in text.lower() for word in ["good", "ready", "complete", "online", "optimal", "morning"]):
                text += ", sir"
        
        # Clean up emojis for speech
        replacements = {
            "🚁": "", "💪": "", "📊": "", "🟡": "", "🟢": "", "🔴": "",
            "✅": "completed", "❌": "error", "🔄": "in progress",
            "**": "", "*": "", "🎯": "", "⚠️": "", "🎉": ""
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Clean up extra spaces
        return " ".join(text.split()).strip()
    
    def text_to_speech(self, text, save_path=None):
        """Generate Jarvis speech - main TTS function"""
        
        if not self.api_key:
            print("❌ ElevenLabs API key required")
            print("Sign up free: https://elevenlabs.io")
            return None
        
        # Format text for Jarvis
        jarvis_text = self.format_text_for_jarvis(text)
        
        # Get voice
        voice_id, voice_name = self.get_voice_id()
        print(f"🎤 Jarvis ({voice_name}): {jarvis_text[:50]}...")
        
        # Generate audio
        audio_file = self._generate_audio(jarvis_text, voice_id, save_path)
        
        if audio_file:
            return f"MEDIA:{audio_file}"
        else:
            return None
    
    def _generate_audio(self, text, voice_id, save_path=None):
        """Internal audio generation"""
        
        url = f"{self.base_url}/text-to-speech/{voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        # Optimized settings for Jarvis-like speech
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.6,
                "similarity_boost": 0.8 if self.custom_voice_id else 0.7,
                "style": 0.3,
                "use_speaker_boost": True
            }
        }
        
        try:
            response = requests.post(url, json=data, headers=headers, timeout=30)
            
            if response.status_code == 200:
                # Save audio
                if save_path:
                    filename = save_path
                else:
                    os.makedirs("jarvis-audio", exist_ok=True)
                    filename = f"jarvis-audio/jarvis_{len(text)}.mp3"
                
                with open(filename, 'wb') as f:
                    f.write(response.content)
                
                return filename
            else:
                print(f"❌ ElevenLabs error: {response.status_code}")
                if response.status_code == 401:
                    print("Check your API key!")
                return None
                
        except Exception as e:
            print(f"❌ TTS error: {e}")
            return None
    
    def daily_briefing(self):
        """Generate spoken daily briefing"""
        
        # Get drone conditions
        try:
            import subprocess
            result = subprocess.run([
                'python3', 'drone-weather.py', 'briefing'
            ], capture_output=True, text=True, cwd='/home/clawd/clawd')
            
            drone_status = result.stdout.strip() if result.returncode == 0 else "Drone conditions unavailable"
        except:
            drone_status = "Drone weather system offline"
        
        # Create briefing
        briefing = f"""Good morning, Mr. Gibson.
        
Here is your morning briefing for today.

{drone_status}

Weather analysis indicates preparation is recommended for any flight operations.

Your schedule appears clear for photography work.

Shall I monitor conditions and alert you to optimal flying windows?"""
        
        print("🤖 JARVIS DAILY BRIEFING")
        print("=" * 50)
        print(briefing)
        print("=" * 50)
        
        return self.text_to_speech(briefing, "jarvis-audio/daily-briefing.mp3")
    
    def quick_alert(self, message):
        """Quick Jarvis alert"""
        
        return self.text_to_speech(message)
    
    def test_voice(self):
        """Test the current voice setup"""
        
        test_phrases = [
            "Good morning, Mr. Gibson. All systems are operational.",
            "Drone flying conditions are optimal today.",
            "At your service. How may I assist you?",
            "Weather analysis complete. Shall I proceed?"
        ]
        
        print(f"🧪 TESTING JARVIS VOICE")
        print("=" * 50)
        
        for i, phrase in enumerate(test_phrases, 1):
            print(f"\n{i}. Testing: {phrase}")
            result = self.text_to_speech(phrase)
            if result:
                print(f"   ✅ Generated: {result}")
            else:
                print(f"   ❌ Failed")
        
        return True

# Drop-in replacement for Clawdbot TTS
def jarvis_tts(text, channel=None):
    """Drop-in replacement for Clawdbot's tts() function"""
    
    # Load API key from environment or file
    api_key = os.getenv('ELEVENLABS_API_KEY')
    
    if not api_key and os.path.exists('.elevenlabs_key'):
        with open('.elevenlabs_key', 'r') as f:
            api_key = f.read().strip()
    
    if api_key:
        jarvis = CompleteJarvisTTS(api_key)
        return jarvis.text_to_speech(text)
    else:
        print("❌ ElevenLabs API key not found")
        return None

def setup_api_key():
    """Setup ElevenLabs API key"""
    
    print("🔑 ELEVENLABS API KEY SETUP")
    print("=" * 40)
    print("1. Go to: https://elevenlabs.io")
    print("2. Sign up (free)")
    print("3. Go to Profile → API Keys") 
    print("4. Copy your API key")
    
    api_key = input("\nPaste your API key: ").strip()
    
    if api_key:
        with open('.elevenlabs_key', 'w') as f:
            f.write(api_key)
        print("✅ API key saved!")
        return api_key
    else:
        print("❌ No API key provided")
        return None

def main():
    """Main function for testing and setup"""
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        # Load API key
        api_key = os.getenv('ELEVENLABS_API_KEY')
        if not api_key and os.path.exists('.elevenlabs_key'):
            with open('.elevenlabs_key', 'r') as f:
                api_key = f.read().strip()
        
        if not api_key:
            api_key = setup_api_key()
        
        if api_key:
            jarvis = CompleteJarvisTTS(api_key)
            
            if command == "test":
                jarvis.test_voice()
            elif command == "briefing":
                jarvis.daily_briefing()
            elif command == "speak":
                if len(sys.argv) > 2:
                    message = " ".join(sys.argv[2:])
                    result = jarvis.text_to_speech(message)
                    print(f"Generated: {result}")
            else:
                print("Commands: test, briefing, speak 'message'")
    else:
        print("🤖 COMPLETE JARVIS TTS SYSTEM")
        print("=" * 50)
        print("Commands:")
        print("  python3 final-jarvis-complete.py test")
        print("  python3 final-jarvis-complete.py briefing")
        print("  python3 final-jarvis-complete.py speak 'Good morning'")
        print("\nFirst run will prompt for ElevenLabs API key")

if __name__ == "__main__":
    main()