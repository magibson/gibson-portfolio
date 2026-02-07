#!/usr/bin/env python3
"""
Test Jarvis Voice Cloning with Qwen3-TTS
"""

import requests
import json
import base64
import tempfile
import subprocess
import sys

def test_qwen3_tts_api():
    """Test the Qwen3-TTS Hugging Face Space API"""
    
    # Hugging Face Space API endpoint
    api_url = "https://qwen-qwen3-tts.hf.space/api/predict"
    
    # Test with voice design (creating a custom voice)
    test_data = {
        "data": [
            "Good morning, Matt. Drone flying conditions are optimal today, sir.",  # Text to speak
            "Create a warm, intelligent British assistant voice like a sophisticated AI butler",  # Voice description
            "en"  # Language
        ]
    }
    
    print("🧪 Testing Qwen3-TTS voice generation...")
    print(f"📝 Text: '{test_data['data'][0]}'")
    print(f"🎭 Voice: '{test_data['data'][1]}'")
    
    try:
        response = requests.post(api_url, json=test_data, timeout=60)
        
        print(f"📡 API Response: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API call successful!")
            print(f"📊 Response structure: {type(result)}")
            
            # The response should contain audio data
            if "data" in result and len(result["data"]) > 0:
                audio_data = result["data"][0]
                
                # Save the audio file
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                    if isinstance(audio_data, str):
                        # If it's base64 encoded
                        try:
                            audio_bytes = base64.b64decode(audio_data)
                            f.write(audio_bytes)
                        except:
                            # If it's a file path or URL
                            print(f"🔗 Audio URL/Path: {audio_data}")
                    else:
                        f.write(audio_data)
                    
                    temp_file = f.name
                
                print(f"🎵 Generated audio saved: {temp_file}")
                return temp_file
                
            else:
                print(f"❌ Unexpected response format: {result}")
                
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"📄 Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏰ API timeout - Qwen3-TTS might be busy")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return None

def test_voice_cloning():
    """Test voice cloning with our baseline audio"""
    
    baseline_file = "jarvis-voice-samples/baseline-jarvis.mp3"
    
    print(f"🎯 Testing voice cloning with: {baseline_file}")
    
    try:
        # Read the audio file
        with open(baseline_file, 'rb') as f:
            audio_data = base64.b64encode(f.read()).decode('utf-8')
        
        # Prepare the API request for voice cloning
        api_url = "https://qwen-qwen3-tts.hf.space/api/predict"
        
        test_data = {
            "data": [
                "Mr. Gibson, your daily briefing is ready. Weather conditions are perfect for drone photography.",  # Text
                audio_data,  # Base64 audio for cloning
                "en"  # Language
            ]
        }
        
        print("🧬 Attempting voice cloning...")
        response = requests.post(api_url, json=test_data, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Voice cloning successful!")
            # Process the cloned audio result
            return result
        else:
            print(f"❌ Voice cloning failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Voice cloning error: {e}")
    
    return None

def create_jarvis_response_pipeline():
    """Create a pipeline to convert my responses to Jarvis voice"""
    
    pipeline_script = '''#!/usr/bin/env python3
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
'''
    
    with open("jarvis-pipeline.py", "w") as f:
        f.write(pipeline_script)
    
    subprocess.run(["chmod", "+x", "jarvis-pipeline.py"])
    print("✅ Created jarvis-pipeline.py")

def main():
    print("🤖 JARVIS VOICE CLONING TEST")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == "clone":
        print("\n🧬 Testing voice cloning...")
        test_voice_cloning()
    else:
        print("\n🧪 Testing Qwen3-TTS API...")
        result = test_qwen3_tts_api()
        
        if result:
            print("\n🎯 API working! Ready for voice cloning integration.")
        
    print("\n🛠️ Creating Jarvis pipeline...")
    create_jarvis_response_pipeline()
    
    print("\n🚀 Next Steps:")
    print("1. Test basic TTS: python3 test-jarvis-clone.py")
    print("2. Test voice cloning: python3 test-jarvis-clone.py clone")
    print("3. Use pipeline: python3 jarvis-pipeline.py 'Hello Mr. Gibson'")

if __name__ == "__main__":
    main()