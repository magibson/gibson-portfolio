#!/usr/bin/env python3
"""
Complete Integrated Free Jarvis System
Combines all functionality - TTS, conversations, integrations
Drop-in replacement for expensive systems
"""

import sys
import os
sys.path.append('/home/clawd/clawd')

from free_jarvis_complete import FreeJarvisTTS

class IntegratedFreeJarvis:
    
    def __init__(self):
        self.tts = FreeJarvisTTS()
        
    def speak(self, text, **kwargs):
        """Drop-in replacement for any TTS function"""
        return self.tts.text_to_speech(text)
    
    def daily_briefing_with_voice(self):
        """Enhanced daily briefing with voice"""
        return self.tts.daily_briefing()
    
    def drone_status_update(self):
        """Spoken drone status update"""
        
        try:
            import subprocess
            result = subprocess.run([
                'python3', 'drone-weather.py', 'quick'
            ], capture_output=True, text=True, cwd='/home/clawd/clawd')
            
            if result.returncode == 0:
                conditions = result.stdout.strip()
                message = f"Mr. Gibson, current drone assessment: {conditions}. Shall I prepare your flight equipment?"
            else:
                message = "I'm unable to access weather systems at the moment, sir."
                
        except Exception as e:
            message = f"Drone weather system offline, sir. Error details: {e}"
        
        return self.tts.text_to_speech(message)
    
    def proactive_alerts(self, alert_type, message):
        """Proactive Jarvis-style alerts"""
        
        alert_formats = {
            "email": f"Mr. Gibson, you have a new email: {message}. Shall I summarize the contents?",
            "weather": f"Weather update, sir: {message}. Adjusting recommendations accordingly.",
            "schedule": f"Calendar reminder, Mr. Gibson: {message}. Shall I prepare anything in advance?",
            "system": f"System notification: {message}. All other systems remain operational, sir.",
            "drone": f"Drone alert: {message}. Standing by for your instructions."
        }
        
        formatted_message = alert_formats.get(alert_type, f"Notification, sir: {message}")
        
        return self.tts.text_to_speech(formatted_message)
    
    def quick_responses(self, response_type):
        """Quick Jarvis responses for common situations"""
        
        responses = {
            "acknowledge": "Very good, sir.",
            "standby": "Standing by for further instructions, Mr. Gibson.",
            "online": "All systems online and operational, sir.",
            "ready": "Ready when you are, sir.",
            "completed": "Task completed successfully, Mr. Gibson.",
            "error": "I'm experiencing some difficulty with that request, sir.",
            "goodbye": "Until next time, Mr. Gibson."
        }
        
        message = responses.get(response_type, "At your service, sir.")
        return self.tts.text_to_speech(message)

# Global instance for easy integration
jarvis = IntegratedFreeJarvis()

# Drop-in replacement functions
def tts(text, channel=None):
    """Drop-in replacement for Clawdbot TTS"""
    return jarvis.speak(text)

def jarvis_tts(text):
    """Jarvis-specific TTS function"""
    return jarvis.speak(text)

def daily_briefing():
    """Generate daily briefing with voice"""
    return jarvis.daily_briefing_with_voice()

def drone_alert(message):
    """Drone-specific alert"""
    return jarvis.proactive_alerts("drone", message)

def main():
    """Demo the integrated system"""
    
    print("🤖 INTEGRATED FREE JARVIS SYSTEM")
    print("=" * 60)
    print("Complete Iron Man AI Assistant - $0 cost")
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "briefing":
            print("📊 Generating daily briefing...")
            result = daily_briefing()
            print(f"Generated: {result}")
            
        elif command == "drone":
            print("🚁 Checking drone conditions...")
            result = jarvis.drone_status_update()
            print(f"Generated: {result}")
            
        elif command == "test":
            print("🧪 Testing all integrations...")
            
            # Test basic TTS
            result1 = tts("Testing basic TTS integration, Mr. Gibson.")
            print(f"✅ Basic TTS: {result1}")
            
            # Test Jarvis-specific
            result2 = jarvis_tts("Testing Jarvis-specific voice system.")
            print(f"✅ Jarvis TTS: {result2}")
            
            # Test quick response
            result3 = jarvis.quick_responses("ready")
            print(f"✅ Quick response: {result3}")
            
            # Test alert
            result4 = jarvis.proactive_alerts("email", "New message from potential client")
            print(f"✅ Proactive alert: {result4}")
            
        elif command == "demo":
            print("🎭 Full system demonstration...")
            
            # Morning sequence
            jarvis.speak("Good morning, Mr. Gibson. Beginning system demonstration.")
            jarvis.daily_briefing_with_voice()
            jarvis.drone_status_update()
            jarvis.quick_responses("completed")
            
        else:
            print("Commands: briefing, drone, test, demo")
    else:
        print("🎯 Available Integrations:")
        print("✅ tts(text) - Drop-in TTS replacement")
        print("✅ jarvis_tts(text) - Jarvis-specific TTS")  
        print("✅ daily_briefing() - Morning briefing with voice")
        print("✅ drone_alert(msg) - Drone-specific alerts")
        print("✅ Quick responses for common situations")
        print("✅ Proactive alerts for emails, weather, etc.")
        
        print("\n🚀 Usage:")
        print("python3 integrated-free-jarvis.py briefing")
        print("python3 integrated-free-jarvis.py drone")
        print("python3 integrated-free-jarvis.py test")
        print("python3 integrated-free-jarvis.py demo")
        
        print("\n💰 Cost: $0/month (vs $5/month for ElevenLabs)")
        print("🎭 Quality: Professional British AI assistant")
        print("⚡ Performance: Fast, reliable, unlimited usage")

if __name__ == "__main__":
    main()