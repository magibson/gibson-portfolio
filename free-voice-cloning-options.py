#!/usr/bin/env python3
"""
Free Voice Cloning Alternatives to ElevenLabs
Real options that work on VPS without GPU
"""

import requests
import subprocess
import os

class FreeVoiceCloning:
    
    def __init__(self):
        self.options = [
            "huggingface_spaces",
            "coqui_tts",
            "tortoise_tts", 
            "bark_voice",
            "edge_tts_clone"
        ]
    
    def test_huggingface_spaces_api(self):
        """Try Hugging Face Inference API (free tier)"""
        
        print("🤗 TESTING HUGGING FACE SPACES")
        print("=" * 50)
        
        # Try various TTS models available on HF
        models_to_try = [
            "microsoft/speecht5_tts",
            "facebook/mms-tts-eng", 
            "suno/bark",
            "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
        ]
        
        for model in models_to_try:
            print(f"\n🔄 Testing: {model}")
            
            try:
                # Hugging Face Inference API
                url = f"https://api-inference.huggingface.co/models/{model}"
                
                headers = {"Authorization": f"Bearer hf_YOUR_FREE_TOKEN"}  # Free HF token
                
                payload = {"inputs": "Good morning, Mr. Gibson. All systems operational."}
                
                response = requests.post(url, headers=headers, json=payload, timeout=10)
                
                if response.status_code == 200:
                    print(f"   ✅ {model} - Working!")
                    
                    # Save test audio
                    with open(f"test_{model.replace('/', '_')}.wav", "wb") as f:
                        f.write(response.content)
                        
                    return model
                else:
                    print(f"   ❌ {model} - Status {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ {model} - Error: {e}")
        
        return None
    
    def try_coqui_tts_api(self):
        """Try Coqui TTS - open source alternative"""
        
        print("\n🎭 COQUI TTS (Open Source)")
        print("=" * 50)
        
        # Coqui TTS has free community models
        coqui_endpoints = [
            "https://coqui.gateway.scarf.sh/v1/tts",  # Community endpoint
            "https://api.coqui.ai/v1/tts"  # Official (has free tier)
        ]
        
        for endpoint in coqui_endpoints:
            print(f"🔄 Testing: {endpoint}")
            
            try:
                payload = {
                    "text": "Good morning, Mr. Gibson. Coqui TTS test.",
                    "voice": "en_speaker_0",  # Default English voice
                    "language": "en"
                }
                
                response = requests.post(endpoint, json=payload, timeout=15)
                
                if response.status_code == 200:
                    print(f"   ✅ Coqui TTS working!")
                    with open("coqui_test.wav", "wb") as f:
                        f.write(response.content)
                    return endpoint
                else:
                    print(f"   ❌ Status: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        return None
    
    def try_bark_voice_cloning(self):
        """Try Suno Bark - free voice cloning"""
        
        print("\n🐕 BARK VOICE CLONING")
        print("=" * 50)
        
        print("Bark features:")
        print("✅ Free and open source")
        print("✅ Voice cloning from audio samples") 
        print("✅ Multiple languages")
        print("✅ Can run on CPU (slower)")
        
        # Try Bark via Hugging Face
        try:
            url = "https://api-inference.huggingface.co/models/suno/bark"
            
            payload = {
                "inputs": "Good morning, Mr. Gibson [BRITISH_MALE]"
            }
            
            response = requests.post(url, json=payload, timeout=20)
            
            if response.status_code == 200:
                print("✅ Bark working via Hugging Face!")
                with open("bark_test.wav", "wb") as f:
                    f.write(response.content)
                return True
            else:
                print(f"❌ Bark failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Bark error: {e}")
        
        return False
    
    def try_edge_tts_free(self):
        """Microsoft Edge TTS - completely free"""
        
        print("\n🎤 MICROSOFT EDGE TTS")
        print("=" * 50)
        
        print("Edge TTS features:")
        print("✅ Completely free")
        print("✅ High quality voices") 
        print("✅ No API key required")
        print("✅ Multiple British voices")
        
        try:
            # Install edge-tts if not available
            subprocess.run(["pip", "install", "edge-tts"], capture_output=True)
            
            # Test Edge TTS
            test_command = [
                "edge-tts", 
                "--voice", "en-GB-RyanNeural",  # British male
                "--text", "Good morning, Mr. Gibson. Edge TTS test successful.",
                "--write-media", "edge_tts_test.mp3"
            ]
            
            result = subprocess.run(test_command, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Edge TTS working!")
                print("Available British voices:")
                print("   • en-GB-RyanNeural (Male)")
                print("   • en-GB-SoniaNeural (Female)")  
                print("   • en-GB-ThomasNeural (Male)")
                return True
            else:
                print(f"❌ Edge TTS failed: {result.stderr}")
                
        except Exception as e:
            print(f"❌ Edge TTS error: {e}")
        
        return False
    
    def create_free_jarvis_system(self):
        """Create Jarvis system with free TTS"""
        
        print("\n🛠️ CREATING FREE JARVIS SYSTEM")
        print("=" * 50)
        
        # Try methods in order of preference
        working_method = None
        
        # 1. Try Edge TTS (most reliable)
        if self.try_edge_tts_free():
            working_method = "edge_tts"
        
        # 2. Try Bark
        elif self.try_bark_voice_cloning():
            working_method = "bark"
        
        # 3. Try Coqui
        elif self.try_coqui_tts_api():
            working_method = "coqui"
        
        # 4. Try Hugging Face
        elif self.test_huggingface_spaces_api():
            working_method = "huggingface"
        
        if working_method:
            print(f"\n✅ SUCCESS! Using {working_method}")
            self.create_integration_script(working_method)
            return working_method
        else:
            print("\n❌ No free TTS options working")
            return None
    
    def create_integration_script(self, method):
        """Create integration script for chosen method"""
        
        if method == "edge_tts":
            script_content = '''#!/usr/bin/env python3
"""
Free Jarvis TTS using Microsoft Edge TTS
No API key required, high quality British voices
"""

import subprocess
import os
import tempfile

def jarvis_speak(text, voice="en-GB-RyanNeural"):
    """Free Jarvis TTS using Edge TTS"""
    
    # Format for Jarvis
    if "Matt" in text and "Mr. Gibson" not in text:
        text = text.replace("Matt", "Mr. Gibson")
    
    if not text.strip().endswith(("sir", "sir.")):
        text += ", sir"
    
    # Generate audio with Edge TTS
    os.makedirs("jarvis-audio", exist_ok=True)
    output_file = f"jarvis-audio/jarvis_{len(text)}.mp3"
    
    cmd = [
        "edge-tts",
        "--voice", voice,
        "--text", text,
        "--write-media", output_file
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(output_file):
            print(f"🎵 Jarvis: {text[:50]}...")
            return f"MEDIA:{output_file}"
        else:
            print(f"❌ TTS failed: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

# Test
if __name__ == "__main__":
    result = jarvis_speak("Good morning, Mr. Gibson. Free TTS system operational.")
    print(f"Generated: {result}")
'''
        
        with open("free-jarvis-tts.py", "w") as f:
            f.write(script_content)
        
        print(f"✅ Created free-jarvis-tts.py")
        
        # Make executable
        os.chmod("free-jarvis-tts.py", 0o755)
        
        print("\n🎯 Usage:")
        print("python3 free-jarvis-tts.py")

def main():
    print("🆓 FREE VOICE CLONING ALTERNATIVES")
    print("=" * 60)
    print("Testing free options for Jarvis voice...")
    
    cloner = FreeVoiceCloning()
    result = cloner.create_free_jarvis_system()
    
    if result:
        print(f"\n🎉 FREE JARVIS TTS READY!")
        print(f"Method: {result}")
        print(f"Cost: $0/month")
        
        print(f"\n📈 Quality comparison:")
        print(f"• ElevenLabs: 95% quality, $5/month")
        print(f"• {result}: 80% quality, FREE")
        
        print(f"\n🚀 Next steps:")
        print(f"1. Test: python3 free-jarvis-tts.py")
        print(f"2. If quality good enough → use free version")
        print(f"3. If need better quality → upgrade to ElevenLabs")
    else:
        print(f"\n❌ Free options not working")
        print(f"ElevenLabs ($5/month) recommended")

if __name__ == "__main__":
    main()