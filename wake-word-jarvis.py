#!/usr/bin/env python3
"""
Wake Word Detection for Jarvis
"Hey Jarvis" or "Jarvis" triggers conversation
Like real Iron Man experience
"""

import threading
import time
import os
import subprocess
import speech_recognition as sr
from conversational_jarvis import ConversationalJarvis

class WakeWordJarvis:
    
    def __init__(self):
        self.wake_words = ["jarvis", "hey jarvis", "ok jarvis"]
        self.listening = True
        self.conversation_active = False
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Load Jarvis system
        api_key = self.load_api_key()
        self.jarvis = ConversationalJarvis(api_key)
        
        print("🎤 Calibrating microphone...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
    
    def load_api_key(self):
        """Load ElevenLabs API key"""
        if os.path.exists('.elevenlabs_key'):
            with open('.elevenlabs_key', 'r') as f:
                return f.read().strip()
        return None
    
    def listen_for_wake_word(self):
        """Continuously listen for wake word"""
        
        print("👂 Listening for wake word...")
        print("Say: 'Hey Jarvis' or 'Jarvis' to activate")
        
        while self.listening:
            try:
                # Listen for audio
                with self.microphone as source:
                    # Short timeout to check for wake word
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=3)
                
                # Recognize speech
                try:
                    text = self.recognizer.recognize_google(audio).lower()
                    print(f"🔍 Heard: {text}")
                    
                    # Check for wake word
                    if any(wake_word in text for wake_word in self.wake_words):
                        print("🎯 Wake word detected!")
                        self.wake_up_jarvis()
                        
                except sr.UnknownValueError:
                    # No speech detected, continue listening
                    pass
                except sr.RequestError as e:
                    print(f"❌ Speech recognition error: {e}")
                    time.sleep(1)
                    
            except sr.WaitTimeoutError:
                # No audio detected, continue
                pass
            except Exception as e:
                print(f"❌ Error: {e}")
                time.sleep(1)
    
    def wake_up_jarvis(self):
        """Jarvis wakes up and starts conversation"""
        
        if self.conversation_active:
            return
        
        self.conversation_active = True
        
        # Jarvis acknowledgment
        wake_responses = [
            "At your service, Mr. Gibson.",
            "Good to hear from you, sir. How may I assist?",
            "Systems online. What can I do for you today?",
            "Yes, Mr. Gibson?"
        ]
        
        import random
        response = random.choice(wake_responses)
        
        print(f"🤖 Jarvis: {response}")
        
        # Speak response
        if self.jarvis.elevenlabs_key:
            self.jarvis.text_to_jarvis_speech(response)
        
        # Start conversation mode
        self.start_conversation()
    
    def start_conversation(self):
        """Start active conversation"""
        
        print("\n💬 Conversation mode active")
        print("Say 'goodbye' or 'that's all' to return to standby")
        
        conversation_timeout = 30  # seconds of silence before auto-standby
        last_activity = time.time()
        
        while self.conversation_active:
            try:
                with self.microphone as source:
                    # Listen for conversation input
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                
                try:
                    text = self.recognizer.recognize_google(audio)
                    last_activity = time.time()
                    
                    print(f"👤 You: {text}")
                    
                    # Check for end conversation
                    if any(phrase in text.lower() for phrase in ["goodbye", "that's all", "standby", "stop listening"]):
                        self.end_conversation()
                        break
                    
                    # Process with AI
                    response = self.jarvis.process_with_ai(text)
                    print(f"🤖 Jarvis: {response}")
                    
                    # Speak response
                    if self.jarvis.elevenlabs_key:
                        self.jarvis.text_to_jarvis_speech(response)
                    
                except sr.UnknownValueError:
                    # No clear speech, continue listening
                    pass
                except sr.RequestError as e:
                    print(f"❌ Speech error: {e}")
                    
            except sr.WaitTimeoutError:
                # Check for timeout
                if time.time() - last_activity > conversation_timeout:
                    print("⏱️ Conversation timeout - returning to standby")
                    self.end_conversation()
                    break
    
    def end_conversation(self):
        """End conversation and return to wake word listening"""
        
        self.conversation_active = False
        
        goodbye_responses = [
            "Until next time, Mr. Gibson.",
            "Returning to standby mode, sir.",
            "I'll be here when you need me.",
            "Standby mode activated."
        ]
        
        import random
        response = random.choice(goodbye_responses)
        
        print(f"🤖 Jarvis: {response}")
        
        if self.jarvis.elevenlabs_key:
            self.jarvis.text_to_jarvis_speech(response)
        
        print("\n👂 Returning to wake word listening...")
    
    def run_continuous(self):
        """Run continuous wake word detection"""
        
        print("🤖 JARVIS WAKE WORD SYSTEM")
        print("=" * 50)
        print("Iron Man-style AI assistant")
        print("Voice cloned from Paul Bettany")
        
        if not self.jarvis.elevenlabs_key:
            print("⚠️ No ElevenLabs API key - text responses only")
        else:
            print("✅ Voice synthesis ready")
        
        print("\nWake words: 'Hey Jarvis' or 'Jarvis'")
        print("Conversation: Say 'goodbye' to return to standby")
        print("Exit: Ctrl+C\n")
        
        # Initial greeting
        greeting = "Good day, Mr. Gibson. Jarvis AI assistant is now online and listening."
        print(f"🤖 {greeting}")
        
        if self.jarvis.elevenlabs_key:
            self.jarvis.text_to_jarvis_speech(greeting)
        
        try:
            # Start wake word detection
            self.listen_for_wake_word()
            
        except KeyboardInterrupt:
            print("\n👋 Shutting down Jarvis...")
            self.listening = False
            
            shutdown_msg = "Goodbye, Mr. Gibson. Jarvis signing off."
            print(f"🤖 {shutdown_msg}")
            
            if self.jarvis.elevenlabs_key:
                self.jarvis.text_to_jarvis_speech(shutdown_msg)

def test_microphone():
    """Test microphone setup"""
    
    print("🎤 MICROPHONE TEST")
    print("=" * 30)
    
    try:
        r = sr.Recognizer()
        mic = sr.Microphone()
        
        print("Available microphones:")
        for i, name in enumerate(sr.Microphone.list_microphone_names()):
            print(f"  {i}: {name}")
        
        print("\nTesting default microphone...")
        print("Say something in the next 5 seconds:")
        
        with mic as source:
            r.adjust_for_ambient_noise(source)
            audio = r.listen(source, timeout=5)
        
        text = r.recognize_google(audio)
        print(f"✅ Heard: '{text}'")
        print("Microphone working properly!")
        
    except Exception as e:
        print(f"❌ Microphone test failed: {e}")
        print("Check microphone connection and permissions")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_microphone()
    else:
        # Check dependencies
        try:
            import speech_recognition
        except ImportError:
            print("📦 Install: pip install SpeechRecognition")
            sys.exit(1)
        
        try:
            import pyaudio
        except ImportError:
            print("📦 Install: pip install pyaudio")
            print("On Ubuntu: sudo apt install python3-pyaudio")
            sys.exit(1)
        
        # Start wake word system
        jarvis_system = WakeWordJarvis()
        jarvis_system.run_continuous()