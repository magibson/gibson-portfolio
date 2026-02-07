#!/usr/bin/env python3
"""
Clone Real Paul Bettany Jarvis Voice from Iron Man
Personal use - completely legal
"""

import requests
import subprocess
import os
import urllib.request

class RealJarvisCloner:
    
    def __init__(self):
        self.clips_dir = "real-jarvis-clips"
        os.makedirs(self.clips_dir, exist_ok=True)
        
        # Direct movie audio clips (these exist online)
        self.clip_sources = {
            "at_your_service": "https://www.wavsource.com/movies/iron_man/jarvis_service.wav",
            "good_morning": "https://www.wavsource.com/movies/iron_man/jarvis_wish.wav", 
            "systems_online": "https://www.wavsource.com/movies/iron_man/jarvis_uploaded.wav",
            "calculations": "https://www.wavsource.com/movies/iron_man/jarvis_calculations.wav",
            "calibrating": "https://www.wavsource.com/movies/iron_man/jarvis_calibrating.wav"
        }
    
    def download_movie_clips(self):
        """Download actual Jarvis clips from Iron Man"""
        
        print("🎬 DOWNLOADING REAL JARVIS CLIPS")
        print("=" * 50)
        
        downloaded = []
        
        for name, url in self.clip_sources.items():
            print(f"📥 Downloading {name}...")
            
            try:
                file_path = os.path.join(self.clips_dir, f"{name}.wav")
                urllib.request.urlretrieve(url, file_path)
                
                if os.path.exists(file_path) and os.path.getsize(file_path) > 1000:
                    print(f"   ✅ Success: {file_path}")
                    downloaded.append(file_path)
                else:
                    print(f"   ❌ Failed or empty file")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        if downloaded:
            print(f"\n🎉 Downloaded {len(downloaded)} clips!")
            return downloaded
        else:
            print("\n⚠️ Direct download failed. Using alternative method...")
            return self.alternative_collection_method()
    
    def alternative_collection_method(self):
        """Alternative ways to get Jarvis clips"""
        
        print("\n🔄 ALTERNATIVE COLLECTION METHODS:")
        print("=" * 50)
        
        methods = [
            {
                "name": "YouTube Audio Extraction",
                "command": "yt-dlp -x --audio-format wav 'https://www.youtube.com/watch?v=StTqXEQ2l-Y'",
                "description": "Extract audio from Iron Man Jarvis compilations"
            },
            {
                "name": "Online Sound Libraries", 
                "url": "https://freesound.org/search/?q=jarvis+iron+man",
                "description": "User-uploaded clean Jarvis clips"
            },
            {
                "name": "Movie Scene Audio",
                "url": "https://movie-sounds.org/superhero-movie-sound-clips/quotes-with-sound-clips-from-iron-man-2008/",
                "description": "Direct movie dialogue clips"
            }
        ]
        
        for method in methods:
            print(f"\n🎯 {method['name']}:")
            if 'command' in method:
                print(f"   Command: {method['command']}")
            if 'url' in method:
                print(f"   URL: {method['url']}")
            print(f"   {method['description']}")
        
        return self.create_sample_clips()
    
    def create_sample_clips(self):
        """Create some sample clips for testing"""
        
        # Create text files with the exact phrases we need
        jarvis_phrases = [
            "At your service, sir",
            "Good morning, Mr. Gibson", 
            "All systems online",
            "Shall I render using the Mark",
            "Right away, sir"
        ]
        
        for i, phrase in enumerate(jarvis_phrases):
            filename = f"{self.clips_dir}/sample_{i+1}.txt"
            with open(filename, "w") as f:
                f.write(phrase)
        
        print(f"\n📝 Created sample phrases in {self.clips_dir}/")
        print("🎯 Next: Record these phrases or find audio clips")
        
        return []
    
    def clone_with_elevenlabs(self, audio_files, api_key):
        """Clone Jarvis voice using real audio clips"""
        
        if not audio_files:
            print("❌ No audio files to clone from")
            return None
        
        print(f"\n🧬 CLONING REAL JARVIS VOICE")
        print("=" * 50)
        print(f"Using {len(audio_files)} audio samples")
        
        url = "https://api.elevenlabs.io/v1/voices/add"
        headers = {"xi-api-key": api_key}
        
        # Prepare audio files for upload
        files = []
        for i, file_path in enumerate(audio_files):
            if os.path.exists(file_path):
                files.append(('files', (f'jarvis_{i}.wav', open(file_path, 'rb'), 'audio/wav')))
        
        data = {
            'name': 'Real_Jarvis_Paul_Bettany',
            'description': 'Authentic Paul Bettany Jarvis voice from Iron Man films'
        }
        
        try:
            print("📤 Uploading to ElevenLabs...")
            response = requests.post(url, headers=headers, files=files, data=data)
            
            # Close file handles
            for _, (_, file_handle, _) in files:
                file_handle.close()
            
            if response.status_code == 200:
                result = response.json()
                voice_id = result.get('voice_id')
                
                print(f"✅ REAL JARVIS VOICE CREATED!")
                print(f"   Voice ID: {voice_id}")
                
                # Save for future use
                with open("real-jarvis-voice-id.txt", "w") as f:
                    f.write(voice_id)
                
                # Test it immediately
                self.test_cloned_voice(voice_id, api_key)
                
                return voice_id
            else:
                print(f"❌ Voice cloning failed: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Cloning error: {e}")
            return None
    
    def test_cloned_voice(self, voice_id, api_key):
        """Test the cloned Jarvis voice"""
        
        test_phrases = [
            "Good morning, Mr. Gibson. All systems are operational.",
            "Drone flying conditions are optimal today, sir.", 
            "At your service. How may I assist you today?",
            "Weather analysis complete. Shall I proceed with the briefing?"
        ]
        
        print(f"\n🎤 TESTING CLONED JARVIS VOICE")
        print("=" * 50)
        
        for i, phrase in enumerate(test_phrases, 1):
            print(f"\n{i}. Testing: '{phrase}'")
            
            audio_file = self.generate_with_cloned_voice(phrase, voice_id, api_key)
            if audio_file:
                print(f"   ✅ Generated: {audio_file}")
            else:
                print(f"   ❌ Failed")
    
    def generate_with_cloned_voice(self, text, voice_id, api_key):
        """Generate speech with cloned voice"""
        
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json", 
            "xi-api-key": api_key
        }
        
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.7,        # Higher stability for consistency
                "similarity_boost": 0.9,  # Maximum similarity to original
                "style": 0.2,            # Minimal style variation
                "use_speaker_boost": True
            }
        }
        
        try:
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                filename = f"real-jarvis-audio/cloned_jarvis_{len(text)}.mp3"
                os.makedirs("real-jarvis-audio", exist_ok=True)
                
                with open(filename, 'wb') as f:
                    f.write(response.content)
                
                return filename
            else:
                print(f"❌ Generation failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Generation error: {e}")
            return None

def main():
    print("🤖 REAL JARVIS VOICE CLONING")
    print("=" * 50)
    print("Personal use - completely legal!")
    
    cloner = RealJarvisCloner()
    
    # Step 1: Get audio clips
    audio_files = cloner.download_movie_clips()
    
    # Step 2: Clone voice (if we have clips and API key)
    if audio_files:
        api_key = input("\nEnter ElevenLabs API key (free signup): ").strip()
        
        if api_key:
            voice_id = cloner.clone_with_elevenlabs(audio_files, api_key)
            
            if voice_id:
                print(f"\n🎉 SUCCESS! Real Jarvis voice cloned!")
                print(f"Voice ID saved to: real-jarvis-voice-id.txt")
                print(f"Audio samples in: real-jarvis-audio/")
                
                print(f"\n🚀 Integration ready:")
                print(f"Use voice_id '{voice_id}' in your TTS system")
            else:
                print(f"\n❌ Cloning failed - try collecting better audio samples")
    else:
        print(f"\n📋 Next steps:")
        print(f"1. Collect clean Jarvis audio clips") 
        print(f"2. Save to: {cloner.clips_dir}/")
        print(f"3. Run this script again")
    
    print(f"\n💡 Remember: This gives you the REAL Paul Bettany voice!")
    print(f"Way more authentic than any synthetic voice.")

if __name__ == "__main__":
    main()