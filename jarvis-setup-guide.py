#!/usr/bin/env python3
"""
Step-by-Step Jarvis Conversational AI Setup Guide
Complete Iron Man AI Assistant
"""

import os
import subprocess

class JarvisSetupGuide:
    
    def __init__(self):
        self.steps_completed = self.load_progress()
        
    def load_progress(self):
        """Load setup progress"""
        if os.path.exists('.jarvis_setup_progress'):
            with open('.jarvis_setup_progress', 'r') as f:
                return set(line.strip() for line in f)
        return set()
    
    def save_progress(self, step):
        """Save completed step"""
        self.steps_completed.add(step)
        with open('.jarvis_setup_progress', 'w') as f:
            for completed_step in self.steps_completed:
                f.write(f"{completed_step}\n")
    
    def check_step(self, step_name):
        """Check if step is completed"""
        return step_name in self.steps_completed
    
    def step_1_voice_cloning(self):
        """Step 1: Clone Paul Bettany's voice"""
        
        print("🎭 STEP 1: CLONE PAUL BETTANY VOICE")
        print("=" * 50)
        
        if self.check_step("voice_cloning"):
            print("✅ Voice cloning already completed!")
            if os.path.exists("real-jarvis-voice-id.txt"):
                with open("real-jarvis-voice-id.txt", "r") as f:
                    voice_id = f.read().strip()
                    print(f"Voice ID: {voice_id}")
            return True
        
        print("🎬 Audio Collection Methods:")
        print("1. YouTube: Search 'Iron Man Jarvis compilation'")
        print("2. Movie clips: Download from online sources") 
        print("3. Sound libraries: Pre-extracted Jarvis clips")
        
        print("\n🎯 Target Phrases (need 3-5 clean clips):")
        phrases = [
            "Good morning, sir",
            "At your service, sir", 
            "All systems online",
            "Right away, sir",
            "Shall I proceed"
        ]
        
        for i, phrase in enumerate(phrases, 1):
            print(f"   {i}. \"{phrase}\"")
        
        print("\n🛠️ Audio Editing:")
        print("• Use Audacity (free) to extract clean clips")
        print("• 2-10 seconds each, clear voice only")
        print("• Save as WAV: jarvis1.wav, jarvis2.wav, etc.")
        print("• Place in: real-jarvis-clips/")
        
        print("\n🧬 ElevenLabs Cloning:")
        print("1. Sign up: https://elevenlabs.io")
        print("2. Go to: Voices → Add Voice → Voice Cloning")
        print("3. Upload your WAV files")
        print("4. Name: 'Paul_Bettany_Jarvis'")
        print("5. Copy the Voice ID")
        print("6. Save to: real-jarvis-voice-id.txt")
        
        # Check if user has completed this step
        voice_id_file = input("\nHave you completed voice cloning? (y/n): ").lower()
        
        if voice_id_file == 'y':
            voice_id = input("Enter your Jarvis Voice ID: ").strip()
            if voice_id:
                with open("real-jarvis-voice-id.txt", "w") as f:
                    f.write(voice_id)
                print("✅ Voice ID saved!")
                self.save_progress("voice_cloning")
                return True
        
        print("⏳ Complete voice cloning first, then run this step again")
        return False
    
    def step_2_api_keys(self):
        """Step 2: Set up API keys"""
        
        print("\n🔑 STEP 2: API KEYS SETUP")
        print("=" * 50)
        
        if self.check_step("api_keys"):
            print("✅ API keys already configured!")
            return True
        
        # ElevenLabs API key
        if not os.path.exists('.elevenlabs_key'):
            print("🎵 ElevenLabs API Key:")
            print("1. Go to: https://elevenlabs.io/speech-synthesis")
            print("2. Click Profile → API Keys")
            print("3. Copy your key")
            
            api_key = input("Paste ElevenLabs API key: ").strip()
            if api_key:
                with open('.elevenlabs_key', 'w') as f:
                    f.write(api_key)
                print("✅ ElevenLabs API key saved!")
        else:
            print("✅ ElevenLabs API key already set")
        
        # OpenAI API key (optional, for better STT)
        if not os.path.exists('.openai_key'):
            print("\n🎤 OpenAI API Key (optional, for best speech recognition):")
            print("1. Go to: https://platform.openai.com/api-keys")
            print("2. Create new key")
            print("3. Copy key")
            
            openai_key = input("Paste OpenAI API key (or press Enter to skip): ").strip()
            if openai_key:
                with open('.openai_key', 'w') as f:
                    f.write(openai_key)
                print("✅ OpenAI API key saved!")
            else:
                print("⏳ Will use free Google STT instead")
        else:
            print("✅ OpenAI API key already set")
        
        self.save_progress("api_keys")
        return True
    
    def step_3_dependencies(self):
        """Step 3: Install dependencies"""
        
        print("\n📦 STEP 3: INSTALL DEPENDENCIES")
        print("=" * 50)
        
        if self.check_step("dependencies"):
            print("✅ Dependencies already installed!")
            return True
        
        dependencies = [
            ("requests", "HTTP requests"),
            ("pyaudio", "Microphone input"),
            ("SpeechRecognition", "Speech to text"),
            ("wave", "Audio file handling"),
        ]
        
        print("Installing Python packages...")
        
        for package, description in dependencies:
            print(f"📦 Installing {package} ({description})...")
            
            try:
                # Try importing first
                if package == "SpeechRecognition":
                    import speech_recognition
                elif package == "pyaudio":
                    import pyaudio
                elif package == "wave":
                    import wave
                elif package == "requests":
                    import requests
                
                print(f"   ✅ {package} already installed")
                
            except ImportError:
                print(f"   🔄 Installing {package}...")
                
                # Install command
                install_cmd = f"pip install {package}"
                if package == "pyaudio":
                    print("   ⚠️ PyAudio may need system dependencies")
                    print("   On Ubuntu: sudo apt install python3-pyaudio")
                    install_cmd += " || pip install PyAudio"
                
                print(f"   Run: {install_cmd}")
        
        print("\n🎤 Audio System Setup:")
        print("• Make sure microphone is connected")
        print("• Test with: arecord -d 3 test.wav (Linux)")
        print("• Make sure speakers work")
        
        completed = input("\nHave you installed all dependencies? (y/n): ").lower()
        if completed == 'y':
            self.save_progress("dependencies")
            return True
        
        return False
    
    def step_4_test_system(self):
        """Step 4: Test complete system"""
        
        print("\n🧪 STEP 4: TEST SYSTEM COMPONENTS")
        print("=" * 50)
        
        print("🎵 Testing Text-to-Speech...")
        try:
            result = subprocess.run([
                'python3', 'final-jarvis-complete.py', 'speak', 
                'Good morning, Mr. Gibson. System test in progress.'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ TTS working!")
            else:
                print(f"❌ TTS failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ TTS test error: {e}")
            return False
        
        print("\n🎤 Testing Speech Recognition...")
        print("This will test if microphone input works")
        
        test_stt = input("Test speech recognition? (y/n): ").lower()
        if test_stt == 'y':
            try:
                result = subprocess.run([
                    'python3', 'conversational-jarvis.py', 'test'
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    print("✅ Speech recognition setup!")
                else:
                    print(f"⚠️ STT needs audio setup: {result.stderr}")
            except Exception as e:
                print(f"❌ STT test error: {e}")
        
        self.save_progress("system_test")
        return True
    
    def step_5_conversation(self):
        """Step 5: Start conversational AI"""
        
        print("\n🗣️ STEP 5: CONVERSATIONAL AI")
        print("=" * 50)
        
        print("🚀 Ready to start conversation!")
        print("\nConversation modes:")
        print("1. Text conversation (testing)")
        print("2. Voice conversation (full experience)")
        
        print("\nCommands:")
        print("• Text: python3 conversational-jarvis.py text")
        print("• Voice: python3 conversational-jarvis.py voice")
        
        print("\n🎯 Example Conversation:")
        print("You: 'Good morning, Jarvis'")
        print("Jarvis: 'Good morning, Mr. Gibson. All systems operational.'")
        print("You: 'Check drone conditions'") 
        print("Jarvis: 'Drone conditions are optimal, sir. Shall I prepare equipment?'")
        
        print("\n✨ Integration Features:")
        print("✅ Drone weather monitoring")
        print("✅ Daily briefings")
        print("✅ Email alerts")
        print("✅ System status")
        print("✅ Natural conversation")
        
        start_now = input("\nStart conversation now? (y/n): ").lower()
        
        if start_now == 'y':
            mode = input("Text or voice? (t/v): ").lower()
            
            if mode == 'v':
                print("🎤 Starting voice conversation...")
                os.system("python3 conversational-jarvis.py voice")
            else:
                print("💬 Starting text conversation...")
                os.system("python3 conversational-jarvis.py text")
        
        self.save_progress("conversation")
        return True
    
    def show_progress(self):
        """Show setup progress"""
        
        steps = [
            ("voice_cloning", "Clone Paul Bettany Voice"),
            ("api_keys", "Set up API Keys"),
            ("dependencies", "Install Dependencies"), 
            ("system_test", "Test System Components"),
            ("conversation", "Conversational AI")
        ]
        
        print("🤖 JARVIS SETUP PROGRESS")
        print("=" * 50)
        
        for step_id, step_name in steps:
            status = "✅" if self.check_step(step_id) else "⏳"
            print(f"{status} {step_name}")
        
        completed_count = len([s for s, _ in steps if self.check_step(s)])
        print(f"\nProgress: {completed_count}/{len(steps)} steps completed")
        
        if completed_count == len(steps):
            print("\n🎉 JARVIS SETUP COMPLETE!")
            print("Your Iron Man AI assistant is ready!")
    
    def run_setup(self):
        """Run complete setup process"""
        
        print("🤖 IRON MAN JARVIS AI SETUP")
        print("=" * 60)
        print("Creating your personal AI assistant with Paul Bettany's voice")
        
        self.show_progress()
        
        # Run steps in order
        if not self.check_step("voice_cloning"):
            if not self.step_1_voice_cloning():
                return
        
        if not self.check_step("api_keys"):
            if not self.step_2_api_keys():
                return
        
        if not self.check_step("dependencies"):
            if not self.step_3_dependencies():
                return
        
        if not self.check_step("system_test"):
            if not self.step_4_test_system():
                return
        
        if not self.check_step("conversation"):
            self.step_5_conversation()
        
        self.show_progress()

if __name__ == "__main__":
    guide = JarvisSetupGuide()
    guide.run_setup()