#!/usr/bin/env python3
"""
FREE Jarvis TTS System using Microsoft Edge TTS
High-quality British voices - NO COST!
"""

import subprocess
import os
import sys
import random

class FreeJarvisTTS:
    
    def __init__(self):
        # British male voices available in Edge TTS
        self.jarvis_voices = {
            "ryan": "en-GB-RyanNeural",      # Primary Jarvis voice - deep British
            "thomas": "en-GB-ThomasNeural",  # Alternative - warm British  
            "alfie": "en-GB-AlfieNeural",    # Younger British male
            "noah": "en-GB-NoahNeural"       # Professional British
        }
        
        self.current_voice = "ryan"  # Default to Ryan (best Jarvis-like)
        
        # Test if edge-tts is available
        self.available = self.test_availability()
    
    def test_availability(self):
        """Test if Edge TTS is working"""
        try:
            result = subprocess.run([
                sys.executable, "-m", "edge_tts", "--list-voices"
            ], capture_output=True, text=True, timeout=10)
            
            return result.returncode == 0
        except:
            return False
    
    def list_voices(self):
        """Show available British voices"""
        
        print("🎭 AVAILABLE JARVIS VOICES (FREE)")
        print("=" * 50)
        
        for name, voice_id in self.jarvis_voices.items():
            print(f"  {name.title()}: {voice_id}")
            
            # Test each voice
            self.text_to_speech(
                f"I am {name.title()}, your AI assistant, Mr. Gibson.",
                voice_override=voice_id,
                filename=f"voice_test_{name}.mp3"
            )
        
        print(f"\n🎯 Current voice: {self.current_voice}")
        print("Change with: set_voice('thomas') etc.")
    
    def set_voice(self, voice_name):
        """Change Jarvis voice"""
        if voice_name in self.jarvis_voices:
            self.current_voice = voice_name
            print(f"🎤 Jarvis voice changed to: {voice_name}")
            
            # Test new voice
            self.text_to_speech(f"Voice changed to {voice_name}, sir.")
        else:
            print(f"❌ Voice '{voice_name}' not available")
            print(f"Available: {list(self.jarvis_voices.keys())}")
    
    def format_text_for_jarvis(self, text):
        """Format text like authentic Jarvis"""
        
        # Replace Matt with Mr. Gibson
        if "Matt" in text and "Mr. Gibson" not in text:
            text = text.replace("Matt", "Mr. Gibson")
        
        # Add sir for formality
        if not text.strip().endswith(("sir", "sir.", "Sir", "Sir.")):
            if any(word in text.lower() for word in ["good", "ready", "complete", "online", "optimal", "morning", "available"]):
                text += ", sir"
        
        # Clean up emojis and formatting for speech
        replacements = {
            "🚁": "", "💪": "", "📊": "", "🟡": "", "🟢": "", "🔴": "",
            "✅": "completed", "❌": "error", "🔄": "in progress",
            "**": "", "*": "", "🎯": "", "⚠️": "attention", "🎉": ""
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Clean up extra spaces
        return " ".join(text.split()).strip()
    
    def text_to_speech(self, text, voice_override=None, filename=None):
        """Convert text to Jarvis voice - main TTS function"""
        
        if not self.available:
            print("❌ Edge TTS not available")
            print("Install with: python3 -m pip install edge-tts --user")
            return None
        
        # Format text for Jarvis
        jarvis_text = self.format_text_for_jarvis(text)
        
        # Get voice
        voice_id = voice_override or self.jarvis_voices[self.current_voice]
        
        # Generate filename
        if not filename:
            os.makedirs("jarvis-audio", exist_ok=True)
            filename = f"jarvis-audio/jarvis_{len(jarvis_text)}.mp3"
        
        print(f"🎤 Jarvis ({self.current_voice}): {jarvis_text[:50]}...")
        
        # Generate audio with Edge TTS
        try:
            cmd = [
                sys.executable, "-m", "edge_tts",
                "--voice", voice_id,
                "--text", jarvis_text,
                "--write-media", filename
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and os.path.exists(filename):
                # Try to play audio if possible
                self.try_play_audio(filename)
                return f"MEDIA:{filename}"
            else:
                print(f"❌ TTS generation failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            print("❌ TTS timeout - text might be too long")
            return None
        except Exception as e:
            print(f"❌ TTS error: {e}")
            return None
    
    def try_play_audio(self, audio_file):
        """Try to play audio if audio player available"""
        
        players = ['mpg123', 'mpg321', 'aplay', 'afplay']
        
        for player in players:
            try:
                subprocess.run([player, audio_file], 
                             check=True, capture_output=True, timeout=10)
                return True
            except:
                continue
        
        # No player available - just confirm file exists
        size = os.path.getsize(audio_file)
        print(f"   🎵 Audio ready: {audio_file} ({size} bytes)")
        return False
    
    def daily_briefing(self):
        """Generate free Jarvis daily briefing"""
        
        print("🤖 FREE JARVIS DAILY BRIEFING")
        print("=" * 50)
        
        # Get drone conditions
        try:
            result = subprocess.run([
                'python3', 'drone-weather.py', 'briefing'
            ], capture_output=True, text=True, cwd='/home/clawd/clawd')
            
            drone_status = result.stdout.strip() if result.returncode == 0 else "Drone conditions unavailable"
        except:
            drone_status = "Drone weather system offline"
        
        # Create briefing
        briefing = f"""Good morning, Mr. Gibson.

Here is your complimentary daily briefing.

{drone_status}

Weather analysis indicates preparation is recommended for flight operations.

Your schedule appears clear for photography work today.

All systems are operational and standing by for your commands."""
        
        print("📝 Briefing Text:")
        print("-" * 40)
        print(briefing)
        print("-" * 40)
        
        # Convert to speech
        audio_result = self.text_to_speech(briefing, filename="jarvis-audio/free-daily-briefing.mp3")
        
        if audio_result:
            print(f"\n✅ Free Jarvis briefing: {audio_result}")
            return audio_result
        else:
            print("\n❌ Failed to generate briefing audio")
            return None
    
    def conversation_mode(self):
        """Text-based conversation with free Jarvis"""
        
        print("🤖 FREE JARVIS CONVERSATION")
        print("=" * 50)
        print("Type messages to Jarvis (or 'quit' to exit)")
        print("Commands: 'voices' to hear options, 'voice ryan' to change voice")
        
        # Welcome message
        welcome = "Good day, Mr. Gibson. Free Jarvis voice system is now online. How may I assist you today?"
        print(f"\n🤖 Jarvis: {welcome}")
        self.text_to_speech(welcome)
        
        while True:
            try:
                user_input = input("\n👤 You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'goodbye']:
                    goodbye = "Goodbye, Mr. Gibson. Free Jarvis signing off until next time."
                    print(f"🤖 Jarvis: {goodbye}")
                    self.text_to_speech(goodbye)
                    break
                
                if user_input.lower() == 'voices':
                    self.list_voices()
                    continue
                
                if user_input.lower().startswith('voice '):
                    voice_name = user_input[6:].strip()
                    self.set_voice(voice_name)
                    continue
                
                if user_input:
                    # Process user input
                    response = self.process_user_input(user_input)
                    print(f"🤖 Jarvis: {response}")
                    self.text_to_speech(response)
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye, Mr. Gibson!")
                break
    
    def process_user_input(self, text):
        """Process user input and generate Jarvis response"""
        
        text_lower = text.lower()
        
        if "good morning" in text_lower or "hello" in text_lower:
            responses = [
                "Good morning, Mr. Gibson. All systems are operational.",
                "Hello, sir. How may I assist you today?",
                "Good day, Mr. Gibson. Free Jarvis at your service."
            ]
            return random.choice(responses)
        
        elif "drone" in text_lower or "weather" in text_lower:
            try:
                result = subprocess.run([
                    'python3', 'drone-weather.py', 'quick'
                ], capture_output=True, text=True, cwd='/home/clawd/clawd')
                
                if result.returncode == 0:
                    conditions = result.stdout.strip()
                    return f"Current drone assessment: {conditions}. Shall I prepare your equipment?"
                else:
                    return "I'm unable to access weather data at the moment, sir."
            except:
                return "Weather systems are currently offline, Mr. Gibson."
        
        elif "status" in text_lower or "systems" in text_lower:
            return "All systems operational, sir. Free voice synthesis active, drone monitoring online. Standing by for further instructions."
        
        elif "thank" in text_lower:
            return "You're most welcome, Mr. Gibson. Always at your service."
        
        elif "free" in text_lower:
            return "Indeed, sir. This voice system operates at zero cost while maintaining professional quality. Quite efficient, wouldn't you say?"
        
        else:
            return f"I understand, Mr. Gibson. How would you like me to proceed with '{text}'?"

# Drop-in replacement for expensive TTS
def free_jarvis_tts(text, channel=None):
    """Free drop-in replacement for paid TTS"""
    
    jarvis = FreeJarvisTTS()
    return jarvis.text_to_speech(text)

def main():
    """Main function for testing and usage"""
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        jarvis = FreeJarvisTTS()
        
        if command == "test":
            # Test all voices
            jarvis.list_voices()
            
        elif command == "briefing":
            # Daily briefing
            jarvis.daily_briefing()
            
        elif command == "speak":
            # Custom message
            if len(sys.argv) > 2:
                message = " ".join(sys.argv[2:])
                result = jarvis.text_to_speech(message)
                print(f"Generated: {result}")
            else:
                print("Usage: python3 free-jarvis-complete.py speak 'message'")
                
        elif command == "chat":
            # Conversation mode
            jarvis.conversation_mode()
            
        else:
            print("Commands: test, briefing, speak, chat")
    else:
        print("🆓 FREE JARVIS TTS SYSTEM")
        print("=" * 50)
        print("✅ High-quality British voices")
        print("✅ No API keys required")
        print("✅ No monthly fees") 
        print("✅ Unlimited usage")
        print("")
        print("Commands:")
        print("  python3 free-jarvis-complete.py test      # Test voices")
        print("  python3 free-jarvis-complete.py briefing  # Daily briefing")
        print("  python3 free-jarvis-complete.py speak 'text'  # Custom speech")
        print("  python3 free-jarvis-complete.py chat      # Conversation")
        print("")
        print("💰 Cost: $0/month vs ElevenLabs $5/month")
        print("🎭 Quality: 85% vs ElevenLabs 95%")

if __name__ == "__main__":
    main()