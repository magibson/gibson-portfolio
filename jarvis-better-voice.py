#!/usr/bin/env python3
"""
Better Jarvis Voice Options
Multiple free TTS APIs with British male voices
"""

import requests
import urllib.parse
import base64
import json
import tempfile

class BetterJarvisTTS:
    
    def __init__(self):
        self.methods = [
            "voicerss",
            "responsive_voice", 
            "azure_demo",
            "google_cloud_demo"
        ]
    
    def voicerss_tts(self, text):
        """VoiceRSS - Free API with British voices"""
        
        # VoiceRSS has a free tier with British voices
        # You need to get a free API key from https://www.voicerss.org/
        
        api_key = "YOUR_VOICERSS_KEY"  # Free - 350 requests/day
        
        if api_key == "YOUR_VOICERSS_KEY":
            print("🔑 Get free VoiceRSS API key: https://www.voicerss.org/")
            return None
            
        url = "https://api.voicerss.org/"
        
        params = {
            'key': api_key,
            'src': text,
            'hl': 'en-gb',  # British English
            'v': 'Brian',   # Male British voice
            'c': 'mp3',
            'f': '44khz_16bit_stereo'
        }
        
        try:
            response = requests.get(url, params=params)
            
            if response.status_code == 200 and response.headers.get('content-type', '').startswith('audio'):
                filename = "jarvis-audio/voicerss_jarvis.mp3"
                with open(filename, 'wb') as f:
                    f.write(response.content)
                print(f"🎵 VoiceRSS: {filename}")
                return filename
            else:
                print(f"❌ VoiceRSS error: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ VoiceRSS error: {e}")
            return None
    
    def responsive_voice_tts(self, text):
        """ResponsiveVoice - Free with British male voice"""
        
        try:
            # ResponsiveVoice has a free tier
            url = "https://responsivevoice.com/responsivevoice/getvoice.php"
            
            params = {
                't': text,
                'tl': 'en',
                'sv': 'g3',  # Try different voice numbers
                'vn': 'UK English Male',
                'pitch': 0.5,
                'rate': 0.5,
                'vol': 1
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                filename = "jarvis-audio/responsive_jarvis.mp3"
                with open(filename, 'wb') as f:
                    f.write(response.content)
                print(f"🎵 ResponsiveVoice: {filename}")
                return filename
            else:
                print(f"❌ ResponsiveVoice failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ ResponsiveVoice error: {e}")
            return None
    
    def azure_cognitive_demo(self, text):
        """Try Azure Cognitive Services demo"""
        
        # Azure has excellent British voices in their free tier
        # This is a demo endpoint that sometimes works
        
        url = "https://speech.platform.bing.com/synthesize"
        
        headers = {
            'Content-Type': 'application/ssml+xml',
            'X-Microsoft-OutputFormat': 'audio-16khz-128kbitrate-mono-mp3',
            'User-Agent': 'Mozilla/5.0'
        }
        
        # SSML with British male voice
        ssml = f'''<speak version='1.0' xmlns="http://www.w3.org/2001/10/synthesis" xml:lang='en-US'>
            <voice name='en-GB-RyanNeural'>
                {text}
            </voice>
        </speak>'''
        
        try:
            response = requests.post(url, data=ssml.encode('utf-8'), headers=headers)
            
            if response.status_code == 200:
                filename = "jarvis-audio/azure_jarvis.mp3"
                with open(filename, 'wb') as f:
                    f.write(response.content)
                print(f"🎵 Azure: {filename}")
                return filename
            else:
                print(f"❌ Azure demo failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Azure error: {e}")
            return None
    
    def google_cloud_demo(self, text):
        """Google Cloud TTS with British voice"""
        
        # This uses Google Cloud's actual TTS API in demo mode
        url = "https://texttospeech.googleapis.com/v1/text:synthesize"
        
        data = {
            "input": {"text": text},
            "voice": {
                "languageCode": "en-GB",
                "name": "en-GB-Standard-B",  # British male
                "ssmlGender": "MALE"
            },
            "audioConfig": {"audioEncoding": "MP3"}
        }
        
        try:
            response = requests.post(url, json=data)
            
            if response.status_code == 200:
                result = response.json()
                if 'audioContent' in result:
                    audio_data = base64.b64decode(result['audioContent'])
                    filename = "jarvis-audio/google_cloud_jarvis.mp3"
                    with open(filename, 'wb') as f:
                        f.write(audio_data)
                    print(f"🎵 Google Cloud: {filename}")
                    return filename
                    
        except Exception as e:
            print(f"❌ Google Cloud error: {e}")
            return None
    
    def jarvis_speak(self, text):
        """Try multiple methods to get best British male voice"""
        
        # Format text for Jarvis
        if "Matt" in text and "Mr. Gibson" not in text:
            text = text.replace("Matt", "Mr. Gibson")
        
        if not text.strip().endswith(("sir", "sir.")):
            text += ", sir"
        
        print(f"🤖 Jarvis: {text}")
        
        # Try methods in order of quality
        for method in ["google_cloud_demo", "azure_cognitive_demo", "voicerss", "responsive_voice"]:
            print(f"🔄 Trying {method}...")
            
            if method == "google_cloud_demo":
                result = self.google_cloud_demo(text)
            elif method == "azure_cognitive_demo":
                result = self.azure_cognitive_demo(text)
            elif method == "voicerss":
                result = self.voicerss_tts(text)
            elif method == "responsive_voice":
                result = self.responsive_voice_tts(text)
            
            if result:
                return f"MEDIA:{result}"
        
        print("❌ All TTS methods failed")
        return None

def test_better_voices():
    """Test the improved voice options"""
    
    import os
    os.makedirs("jarvis-audio", exist_ok=True)
    
    jarvis = BetterJarvisTTS()
    
    test_message = "Good morning, Matt. Drone flying conditions are optimal today."
    
    print("🤖 TESTING BETTER JARVIS VOICES")
    print("=" * 50)
    
    result = jarvis.jarvis_speak(test_message)
    
    if result:
        print(f"✅ Success: {result}")
    else:
        print("❌ All methods failed")
        
    print("\n🎯 RECOMMENDED SETUP:")
    print("1. Get free VoiceRSS key: https://www.voicerss.org/ (350 requests/day)")
    print("2. OR try ElevenLabs free tier (10,000 chars/month)")
    print("3. OR pay $5/month for ElevenLabs Starter (30,000 chars)")
    
    print("\n💡 COST ANALYSIS:")
    print("Daily briefing + alerts = ~2,000 characters/day")
    print("Monthly usage = ~60,000 characters")
    print("ElevenLabs Starter ($5/month) = $0.0016 per day")
    print("That's like... less than a pack of gum per month!")

if __name__ == "__main__":
    test_better_voices()