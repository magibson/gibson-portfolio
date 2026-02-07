#!/usr/bin/env python3
"""
Simple Jarvis TTS using built-in system tools
Works immediately on any Linux VPS
"""

import subprocess
import tempfile
import urllib.parse
import requests
import os

class SimpleJarvisTTS:
    def __init__(self):
        self.available_methods = self.check_available_methods()
    
    def check_available_methods(self):
        """Check what TTS methods are available on the system"""
        methods = []
        
        # Check for espeak (common on Linux)
        try:
            subprocess.run(['espeak', '--version'], capture_output=True, check=True)
            methods.append('espeak')
        except:
            pass
        
        # Check for festival
        try:
            subprocess.run(['festival', '--version'], capture_output=True, check=True)
            methods.append('festival')
        except:
            pass
        
        # Check for pico2wave
        try:
            subprocess.run(['pico2wave', '--help'], capture_output=True, check=True)
            methods.append('pico2wave')
        except:
            pass
        
        # Online TTS as fallback
        methods.append('online')
        
        return methods
    
    def speak_with_espeak(self, text, voice="en+m3"):
        """Use espeak for TTS (if available)"""
        try:
            # Make voice sound more British and deeper
            cmd = [
                'espeak', 
                '-v', 'en+m3',  # British male voice 3
                '-s', '150',     # Speed: 150 wpm (slower, more formal)
                '-p', '30',      # Pitch: lower pitch (more authoritative)
                '-g', '10',      # Gap between words
                text
            ]
            
            subprocess.run(cmd, check=True)
            print(f"🎵 Spoke: {text[:50]}...")
            return True
        except Exception as e:
            print(f"❌ espeak failed: {e}")
            return False
    
    def speak_with_online_tts(self, text):
        """Use online TTS service"""
        try:
            # Use a simple TTS service
            encoded_text = urllib.parse.quote(text)
            url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=en-GB&client=tw-ob&q={encoded_text}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                # Save to temp file
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                    f.write(response.content)
                    temp_file = f.name
                
                print(f"🎵 Generated audio: {temp_file}")
                
                # Try to play it (if audio tools available)
                self.try_play_audio(temp_file)
                return temp_file
            else:
                print(f"❌ Online TTS failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Online TTS error: {e}")
            return None
    
    def try_play_audio(self, audio_file):
        """Try to play audio file if possible"""
        players = ['mpg123', 'mpg321', 'aplay', 'paplay']
        
        for player in players:
            try:
                subprocess.run([player, audio_file], check=True, capture_output=True)
                print(f"▶️ Played with {player}")
                return True
            except:
                continue
        
        print("🔇 No audio player found - file saved for download")
        return False
    
    def jarvis_speak(self, text):
        """Main Jarvis speaking function"""
        
        # Format text for Jarvis
        jarvis_text = self.format_for_jarvis(text)
        
        print(f"🤖 Jarvis: {jarvis_text}")
        
        # Try available TTS methods in order of preference
        for method in self.available_methods:
            if method == 'espeak':
                if self.speak_with_espeak(jarvis_text):
                    return True
            elif method == 'online':
                result = self.speak_with_online_tts(jarvis_text)
                if result:
                    return result
        
        print("❌ No TTS methods worked")
        return False
    
    def format_for_jarvis(self, text):
        """Format text to sound more like Jarvis"""
        
        # Replace Matt with Mr. Gibson
        if "Matt" in text and "Mr. Gibson" not in text:
            text = text.replace("Matt", "Mr. Gibson")
        
        # Add sir for formality
        if not text.strip().endswith(("sir", "sir.", "Sir", "Sir.")):
            text += ", sir"
        
        # Clean up emojis
        emoji_replacements = {
            "🚁": "",
            "💪": "",
            "📊": "",
            "🟡": "",
            "🟢": "",
            "🔴": "",
            "✅": "completed",
            "❌": "error",
            "🔄": "in progress"
        }
        
        for emoji, replacement in emoji_replacements.items():
            text = text.replace(emoji, replacement)
        
        # Add natural pauses
        text = text.replace(". ", ". ")
        
        return text.strip()

def test_simple_jarvis():
    """Test the simple Jarvis TTS system"""
    
    jarvis = SimpleJarvisTTS()
    
    print("🤖 SIMPLE JARVIS TTS TEST")
    print("=" * 50)
    print(f"Available methods: {jarvis.available_methods}")
    
    test_phrases = [
        "Good morning, Matt.",
        "Drone conditions are optimal today.",
        "All systems are online and ready.",
        "🟡 Weather update complete, sir."
    ]
    
    for phrase in test_phrases:
        print(f"\n📝 Original: {phrase}")
        jarvis.jarvis_speak(phrase)
        print("-" * 30)

if __name__ == "__main__":
    test_simple_jarvis()