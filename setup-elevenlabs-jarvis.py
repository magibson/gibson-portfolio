#!/usr/bin/env python3
"""
ElevenLabs Jarvis Voice Setup
"""

import requests
import json
import os

class ElevenLabsJarvis:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.base_url = "https://api.elevenlabs.io/v1"
        
        # Pre-existing British male voices that sound Jarvis-like
        self.jarvis_like_voices = {
            "brian": "nPczCjzI2devNBz1zQrb",      # Brian - British male, professional
            "daniel": "onwK4e9ZLuTAKqWW03F9",     # Daniel - Deep British male
            "callum": "N2lVS1w4EtoT3dr4eOWO",     # Callum - Sophisticated British
            "charlie": "IKne3meq5aSn9XLyUdCD",    # Charlie - Warm British male
        }
    
    def test_connection(self):
        """Test API connection"""
        if not self.api_key or self.api_key == "your_api_key_here":
            print("🔑 Get ElevenLabs API key:")
            print("1. Go to: https://elevenlabs.io/")
            print("2. Sign up (free account)")
            print("3. Go to: https://elevenlabs.io/speech-synthesis")
            print("4. Click your profile → API Keys")
            print("5. Copy the API key")
            return False
        
        headers = {"xi-api-key": self.api_key}
        
        try:
            response = requests.get(f"{self.base_url}/voices", headers=headers)
            if response.status_code == 200:
                print("✅ ElevenLabs API connected!")
                return True
            else:
                print(f"❌ API Error: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
    
    def test_jarvis_voices(self, text="Good morning, Mr. Gibson. All systems are online."):
        """Test pre-existing British voices"""
        
        if not self.test_connection():
            return
        
        print(f"\n🎭 Testing Jarvis-like voices with: '{text}'")
        print("=" * 60)
        
        for name, voice_id in self.jarvis_like_voices.items():
            print(f"\n🔄 Testing {name.title()} voice...")
            audio_file = self.text_to_speech(text, voice_id, f"test_{name}.mp3")
            
            if audio_file:
                print(f"   ✅ Generated: {audio_file}")
            else:
                print(f"   ❌ Failed")
    
    def text_to_speech(self, text, voice_id, filename=None):
        """Generate speech with specific voice"""
        
        if not filename:
            filename = f"jarvis-audio/elevenlabs_{len(text)}.mp3"
        
        os.makedirs("jarvis-audio", exist_ok=True)
        
        url = f"{self.base_url}/text-to-speech/{voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        # Optimized for Jarvis-like speech
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.6,        # More stable/consistent
                "similarity_boost": 0.8,  # Stay close to voice character
                "style": 0.3,            # Slightly more expressive
                "use_speaker_boost": True
            }
        }
        
        try:
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                with open(filename, 'wb') as f:
                    f.write(response.content)
                return filename
            else:
                print(f"❌ TTS Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ TTS Error: {e}")
            return None
    
    def create_custom_voice(self, audio_files, voice_name="Jarvis"):
        """Create custom voice from audio samples"""
        
        if not self.test_connection():
            return None
        
        print(f"🧬 Creating custom voice: {voice_name}")
        
        # Check that audio files exist
        for file_path in audio_files:
            if not os.path.exists(file_path):
                print(f"❌ Audio file not found: {file_path}")
                return None
        
        url = f"{self.base_url}/voices/add"
        headers = {"xi-api-key": self.api_key}
        
        # Prepare files for upload
        files = []
        for i, file_path in enumerate(audio_files):
            files.append(('files', (f'sample_{i}.wav', open(file_path, 'rb'), 'audio/wav')))
        
        data = {
            'name': voice_name,
            'description': 'AI assistant voice based on sophisticated British male speaker'
        }
        
        try:
            response = requests.post(url, headers=headers, files=files, data=data)
            
            # Close file handles
            for _, (_, file_handle, _) in files:
                file_handle.close()
            
            if response.status_code == 200:
                result = response.json()
                voice_id = result.get('voice_id')
                print(f"✅ Custom voice created! ID: {voice_id}")
                
                # Save voice ID for future use
                with open("jarvis-voice-id.txt", "w") as f:
                    f.write(voice_id)
                
                return voice_id
            else:
                print(f"❌ Voice creation failed: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Voice creation error: {e}")
            return None
    
    def jarvis_speak(self, text):
        """Main Jarvis speaking function"""
        
        # Format text for Jarvis
        if "Matt" in text and "Mr. Gibson" not in text:
            text = text.replace("Matt", "Mr. Gibson")
        
        if not text.strip().endswith(("sir", "sir.")):
            text += ", sir"
        
        # Try to use custom Jarvis voice if it exists
        voice_id = None
        
        if os.path.exists("jarvis-voice-id.txt"):
            with open("jarvis-voice-id.txt", "r") as f:
                voice_id = f.read().strip()
            print("🤖 Using custom Jarvis voice")
        else:
            # Use best pre-existing British voice
            voice_id = self.jarvis_like_voices["brian"]
            print("🎭 Using Brian (British male) voice")
        
        audio_file = self.text_to_speech(text, voice_id)
        
        if audio_file:
            return f"MEDIA:{audio_file}"
        else:
            return None

def setup_jarvis_voice():
    """Main setup function"""
    
    print("🤖 ELEVENLABS JARVIS SETUP")
    print("=" * 50)
    
    # Get API key
    api_key = input("Enter your ElevenLabs API key (or press Enter to skip): ").strip()
    
    if not api_key:
        api_key = "your_api_key_here"
    
    jarvis = ElevenLabsJarvis(api_key)
    
    if api_key != "your_api_key_here":
        # Test existing voices
        jarvis.test_jarvis_voices()
        
        # Check for training audio
        clips_dir = "jarvis-training-clips"
        audio_files = []
        
        if os.path.exists(clips_dir):
            for file in os.listdir(clips_dir):
                if file.endswith(('.wav', '.mp3')):
                    audio_files.append(os.path.join(clips_dir, file))
        
        if len(audio_files) >= 3:
            print(f"\n🎵 Found {len(audio_files)} audio files for voice cloning")
            create_custom = input("Create custom Jarvis voice? (y/n): ").lower().startswith('y')
            
            if create_custom:
                voice_id = jarvis.create_custom_voice(audio_files[:5])  # Use max 5 files
                
                if voice_id:
                    print(f"\n🎉 Custom Jarvis voice created!")
                    test_text = "Good morning, Mr. Gibson. All systems are operational and ready for today's mission."
                    result = jarvis.jarvis_speak(test_text)
                    print(f"🎵 Test result: {result}")
        else:
            print(f"\n⚠️ Only {len(audio_files)} audio files found")
            print("Need at least 3 clean audio samples for voice cloning")
            print("Using pre-existing British voice for now")
    
    # Create integration script
    create_final_integration(api_key)

def create_final_integration(api_key):
    """Create final integration script"""
    
    integration_code = f'''#!/usr/bin/env python3
"""
Final Jarvis TTS Integration for Clawdbot
"""

import requests
import os

class JarvisTTS:
    def __init__(self):
        self.api_key = "{api_key}"
        self.voice_id = self.get_jarvis_voice_id()
    
    def get_jarvis_voice_id(self):
        """Get the Jarvis voice ID"""
        if os.path.exists("jarvis-voice-id.txt"):
            with open("jarvis-voice-id.txt", "r") as f:
                return f.read().strip()
        else:
            # Fallback to Brian (British male)
            return "nPczCjzI2devNBz1zQrb"
    
    def speak(self, text):
        """Main TTS function - drop-in replacement for Clawdbot TTS"""
        
        # Format for Jarvis
        if "Matt" in text and "Mr. Gibson" not in text:
            text = text.replace("Matt", "Mr. Gibson")
        
        if not text.strip().endswith(("sir", "sir.")):
            text += ", sir"
        
        # Generate audio
        audio_file = self.generate_audio(text)
        
        if audio_file:
            return f"MEDIA:{{audio_file}}"
        else:
            return None
    
    def generate_audio(self, text):
        """Generate audio with ElevenLabs"""
        
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{{self.voice_id}}"
        
        headers = {{
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }}
        
        data = {{
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {{
                "stability": 0.6,
                "similarity_boost": 0.8,
                "style": 0.3,
                "use_speaker_boost": True
            }}
        }}
        
        try:
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                os.makedirs("jarvis-audio", exist_ok=True)
                filename = f"jarvis-audio/jarvis_{{len(text)}}.mp3"
                
                with open(filename, 'wb') as f:
                    f.write(response.content)
                
                return filename
            else:
                print(f"❌ ElevenLabs error: {{response.status_code}}")
                return None
                
        except Exception as e:
            print(f"❌ TTS error: {{e}}")
            return None

# Usage:
# jarvis = JarvisTTS()
# audio = jarvis.speak("Good morning, Mr. Gibson")
'''
    
    with open("jarvis-final-tts.py", "w") as f:
        f.write(integration_code)
    
    print(f"\n✅ Created: jarvis-final-tts.py")
    print("\n🎯 READY FOR USE:")
    print("1. Test: python3 jarvis-final-tts.py")
    print("2. Integrate with daily briefings")
    print("3. Replace Clawdbot TTS calls with Jarvis TTS")

if __name__ == "__main__":
    setup_jarvis_voice()