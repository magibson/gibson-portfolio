#!/usr/bin/env python3
"""
Jarvis Voice Setup - Clone Paul Bettany's voice from Iron Man
"""

import requests
import json
import subprocess
import os
import sys
from pathlib import Path

# Create samples directory
samples_dir = Path("jarvis-voice-samples")
samples_dir.mkdir(exist_ok=True)

def download_sample_clips():
    """Download some Jarvis audio samples for voice cloning"""
    clips = {
        "jarvis_greeting.wav": "https://www.101soundboards.com/storage/board_sounds/...",  # Need actual URLs
        "jarvis_status.wav": "https://movie-sounds.org/...",  # Need actual URLs
        "jarvis_sir.wav": "https://www.wavsource.com/..."  # Need actual URLs
    }
    
    print("🎬 Downloading Jarvis voice samples...")
    
    # For now, let's create a manual download list
    print("\n📥 Manual Download Required:")
    print("1. Visit: https://www.101soundboards.com/boards/26207-jarvis-soundboard")
    print("2. Download these key phrases:")
    print("   - 'Good morning, sir'")
    print("   - 'At your service, sir'")
    print("   - 'Right away, sir'")
    print("   - 'Shall I render using the Mark'")
    print("   - 'Systems online'")
    print(f"3. Save as MP3/WAV files in: {samples_dir.absolute()}")
    print("\n4. Visit: https://movie-sounds.org/superhero-movie-sound-clips/quotes-with-sound-clips-from-iron-man-2008")
    print("   - Download clean dialogue clips")

def test_qwen3_voice_clone(audio_file, test_text):
    """Test voice cloning with Qwen3-TTS API"""
    
    # Qwen3-TTS API endpoint (Hugging Face Space)
    api_url = "https://qwen-qwen3-tts.hf.space/api/predict"
    
    try:
        # Prepare the request
        files = {'audio_file': open(audio_file, 'rb')}
        data = {
            'text': test_text,
            'method': 'voice_clone',  # Use voice cloning method
            'language': 'en'
        }
        
        print(f"🔄 Cloning voice from {audio_file}...")
        print(f"📝 Test text: '{test_text}'")
        
        response = requests.post(api_url, files=files, data=data)
        
        if response.status_code == 200:
            # Save the generated audio
            output_file = f"jarvis_clone_test.wav"
            with open(output_file, 'wb') as f:
                f.write(response.content)
            print(f"✅ Voice clone saved: {output_file}")
            return output_file
        else:
            print(f"❌ Error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error testing voice clone: {e}")
        return None

def create_jarvis_tts_integration():
    """Create integration script for daily use"""
    
    script_content = '''#!/usr/bin/env python3
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
'''
    
    with open("jarvis-speak.py", "w") as f:
        f.write(script_content)
    
    # Make executable
    os.chmod("jarvis-speak.py", 0o755)
    print("✅ Created jarvis-speak.py integration script")

def main():
    print("🤖 JARVIS VOICE SETUP")
    print("=" * 50)
    
    print("\n🎬 Step 1: Download voice samples")
    download_sample_clips()
    
    print("\n⏳ After downloading samples, run:")
    print("python3 setup-jarvis-voice.py test")
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test voice cloning with downloaded samples
        sample_files = list(samples_dir.glob("*.wav")) + list(samples_dir.glob("*.mp3"))
        
        if not sample_files:
            print("❌ No audio samples found! Please download some first.")
            return
            
        print(f"\n🧪 Testing voice clone with {len(sample_files)} samples...")
        
        test_phrases = [
            "Good morning, Matt. Drone conditions are optimal for photography today.",
            "Sir, you have three unread emails requiring attention.",
            "Weather update: Sunny skies, eleven mile per hour winds. Perfect for landscape photography.",
            "Systems online. How may I assist you today, Mr. Gibson?"
        ]
        
        for i, sample_file in enumerate(sample_files[:1]):  # Test with first sample
            for phrase in test_phrases[:1]:  # Test with first phrase
                result = test_qwen3_voice_clone(sample_file, phrase)
                if result:
                    print(f"🎵 Test successful! Audio: {result}")
                    break
    
    print("\n🛠️ Step 2: Create integration script")
    create_jarvis_tts_integration()
    
    print("\n🎯 Next Steps:")
    print("1. Test the voice clone quality")
    print("2. Adjust voice model if needed")
    print("3. Integrate with Clawdbot responses")
    print("4. Set up daily briefing audio")

if __name__ == "__main__":
    main()