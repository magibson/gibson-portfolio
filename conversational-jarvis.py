#!/usr/bin/env python3
"""
Full Conversational Jarvis System
Speech-to-Text → AI Processing → Jarvis Voice Response
Real Iron Man AI Assistant Experience
"""

import requests
import json
import os
import subprocess
import tempfile
import threading
import time
import wave
import pyaudio

class ConversationalJarvis:
    
    def __init__(self, elevenlabs_api_key=None):
        self.elevenlabs_key = elevenlabs_api_key
        self.jarvis_voice_id = self.load_jarvis_voice_id()
        self.listening = False
        self.conversation_active = False
        
        # Audio settings
        self.audio_format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.chunk = 1024
        
    def load_jarvis_voice_id(self):
        """Load the cloned Jarvis voice ID"""
        
        for filename in ["real-jarvis-voice-id.txt", "jarvis-voice-id.txt"]:
            if os.path.exists(filename):
                with open(filename, "r") as f:
                    return f.read().strip()
        
        # Fallback to British male voice
        return "nPczCjzI2devNBz1zQrb"  # Brian
    
    def speech_to_text(self, audio_file):
        """Convert speech to text using OpenAI Whisper API"""
        
        # For now, using OpenAI Whisper API (can be replaced with local Whisper)
        url = "https://api.openai.com/v1/audio/transcriptions"
        
        headers = {
            "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY', 'your_key_here')}"
        }
        
        try:
            with open(audio_file, 'rb') as f:
                files = {'file': f}
                data = {'model': 'whisper-1'}
                
                response = requests.post(url, headers=headers, files=files, data=data)
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get('text', '').strip()
                else:
                    print(f"❌ Speech recognition failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            print(f"❌ STT Error: {e}")
            return None
    
    def local_speech_to_text(self, audio_file):
        """Local speech recognition (fallback method)"""
        
        try:
            # Using speech_recognition library with Google (free)
            import speech_recognition as sr
            
            r = sr.Recognizer()
            with sr.AudioFile(audio_file) as source:
                audio = r.record(source)
            
            # Try multiple services
            try:
                text = r.recognize_google(audio)
                return text
            except:
                try:
                    text = r.recognize_sphinx(audio)  # Offline option
                    return text
                except:
                    return None
                    
        except ImportError:
            print("📦 Install: pip install SpeechRecognition")
            return None
        except Exception as e:
            print(f"❌ Local STT error: {e}")
            return None
    
    def process_with_ai(self, text):
        """Process user input with AI (this would integrate with Clawdbot)"""
        
        # Format as Jarvis personality
        system_prompt = """You are JARVIS, Tony Stark's AI assistant. You are:
- Sophisticated, intelligent, and helpful
- British, polite, and professional
- Address the user as "Mr. Gibson" or "sir"
- Knowledgeable about technology, weather, schedules
- Capable of managing drone operations, calendar, emails
- Concise but warm in responses
- Always maintain the dignified AI assistant personality"""
        
        # This would integrate with Clawdbot's AI processing
        # For now, simulate responses based on common queries
        
        text_lower = text.lower()
        
        if "good morning" in text_lower or "hello" in text_lower:
            return "Good morning, Mr. Gibson. All systems are online and ready. How may I assist you today?"
        
        elif "drone" in text_lower or "weather" in text_lower:
            # Get actual drone conditions
            try:
                result = subprocess.run([
                    'python3', 'drone-weather.py', 'quick'
                ], capture_output=True, text=True, cwd='/home/clawd/clawd')
                
                if result.returncode == 0:
                    conditions = result.stdout.strip()
                    return f"Current drone conditions: {conditions}. Shall I prepare your equipment, sir?"
                else:
                    return "I'm unable to access weather data at the moment. Shall I try again?"
            except:
                return "Weather systems are currently offline, Mr. Gibson."
        
        elif "time" in text_lower or "schedule" in text_lower:
            from datetime import datetime
            current_time = datetime.now().strftime("%I:%M %p")
            return f"It's currently {current_time}, sir. Your schedule appears clear for the day."
        
        elif "status" in text_lower or "systems" in text_lower:
            return "All systems are operational, sir. Drone weather monitoring is active, and I'm standing by for further instructions."
        
        elif "thank" in text_lower:
            return "You're most welcome, Mr. Gibson. At your service as always."
        
        elif "jarvis" in text_lower and "there" in text_lower:
            return "At your service, sir. How may I assist you?"
        
        else:
            return f"I understand you said '{text}'. How would you like me to proceed, sir?"
    
    def text_to_jarvis_speech(self, text):
        """Convert text to Jarvis voice"""
        
        if not self.elevenlabs_key:
            print("🎤 Jarvis would say:", text)
            return None
        
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.jarvis_voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.elevenlabs_key
        }
        
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.7,
                "similarity_boost": 0.9,
                "style": 0.2,
                "use_speaker_boost": True
            }
        }
        
        try:
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                # Save and play audio
                audio_file = f"jarvis-audio/response_{int(time.time())}.mp3"
                os.makedirs("jarvis-audio", exist_ok=True)
                
                with open(audio_file, 'wb') as f:
                    f.write(response.content)
                
                # Play audio (platform-dependent)
                self.play_audio(audio_file)
                return audio_file
            else:
                print(f"❌ TTS failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ TTS error: {e}")
            return None
    
    def play_audio(self, audio_file):
        """Play audio file"""
        
        players = ['mpg123', 'mpg321', 'afplay', 'aplay']
        
        for player in players:
            try:
                subprocess.run([player, audio_file], check=True, capture_output=True)
                return True
            except:
                continue
        
        print(f"🎵 Audio ready: {audio_file}")
        return False
    
    def record_audio(self, duration=5):
        """Record audio from microphone"""
        
        try:
            import pyaudio
            
            audio = pyaudio.PyAudio()
            
            stream = audio.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk
            )
            
            print("🎤 Listening...")
            frames = []
            
            for _ in range(0, int(self.rate / self.chunk * duration)):
                data = stream.read(self.chunk)
                frames.append(data)
            
            stream.stop_stream()
            stream.close()
            audio.terminate()
            
            # Save to file
            filename = f"temp_audio_{int(time.time())}.wav"
            
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(audio.get_sample_size(self.audio_format))
                wf.setframerate(self.rate)
                wf.writeframes(b''.join(frames))
            
            return filename
            
        except ImportError:
            print("📦 Install: pip install pyaudio")
            return None
        except Exception as e:
            print(f"❌ Recording error: {e}")
            return None
    
    def conversation_loop(self):
        """Main conversation loop"""
        
        print("🤖 JARVIS CONVERSATIONAL AI")
        print("=" * 50)
        
        # Welcome message
        self.text_to_jarvis_speech("Good morning, Mr. Gibson. I am now online and ready for conversation. How may I assist you today?")
        
        while self.conversation_active:
            print("\n🎤 Say something (or 'quit' to exit)...")
            
            # Record audio
            audio_file = self.record_audio(duration=5)
            
            if audio_file:
                # Convert to text
                text = self.speech_to_text(audio_file) or self.local_speech_to_text(audio_file)
                
                if text:
                    print(f"👤 You said: {text}")
                    
                    # Check for exit
                    if "quit" in text.lower() or "stop" in text.lower() or "goodbye" in text.lower():
                        self.text_to_jarvis_speech("Goodbye, Mr. Gibson. Until next time.")
                        break
                    
                    # Process with AI
                    response = self.process_with_ai(text)
                    print(f"🤖 Jarvis: {response}")
                    
                    # Convert to speech
                    self.text_to_jarvis_speech(response)
                else:
                    print("❌ Could not understand audio")
                
                # Clean up temp file
                try:
                    os.remove(audio_file)
                except:
                    pass
            else:
                print("❌ Recording failed")
                break
    
    def start_conversation(self):
        """Start the conversational system"""
        
        self.conversation_active = True
        self.conversation_loop()
    
    def text_conversation(self):
        """Text-based conversation for testing"""
        
        print("🤖 JARVIS TEXT CONVERSATION")
        print("=" * 50)
        print("Type messages to Jarvis (or 'quit' to exit)")
        
        while True:
            text = input("\n👤 You: ").strip()
            
            if text.lower() in ['quit', 'exit', 'stop']:
                print("🤖 Jarvis: Goodbye, Mr. Gibson.")
                break
            
            if text:
                response = self.process_with_ai(text)
                print(f"🤖 Jarvis: {response}")
                
                # Convert to speech if API available
                if self.elevenlabs_key:
                    self.text_to_jarvis_speech(response)

def main():
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
    else:
        command = "help"
    
    # Load API key
    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key and os.path.exists('.elevenlabs_key'):
        with open('.elevenlabs_key', 'r') as f:
            api_key = f.read().strip()
    
    jarvis = ConversationalJarvis(api_key)
    
    if command == "voice":
        print("🎤 Starting voice conversation...")
        jarvis.start_conversation()
    elif command == "text":
        jarvis.text_conversation()
    elif command == "test":
        # Test individual components
        test_text = "Good morning, Mr. Gibson. All systems are operational."
        print(f"🧪 Testing TTS: {test_text}")
        jarvis.text_to_jarvis_speech(test_text)
    else:
        print("🤖 CONVERSATIONAL JARVIS")
        print("=" * 40)
        print("Commands:")
        print("  python3 conversational-jarvis.py voice  # Voice conversation")
        print("  python3 conversational-jarvis.py text   # Text conversation")
        print("  python3 conversational-jarvis.py test   # Test TTS")
        print("\nFirst setup ElevenLabs API key and clone Jarvis voice!")

if __name__ == "__main__":
    main()