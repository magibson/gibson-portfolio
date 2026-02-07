#!/usr/bin/env python3
"""
Jarvis Menu Bar App
- Lives in macOS menu bar
- Global hotkey (Cmd+Shift+J) to talk
- Secure connection to VPS
- Local Whisper + Local Jarvis TTS

Requirements:
    pip install rumps openai-whisper sounddevice soundfile numpy requests pynput pyobjc

Usage:
    python jarvis-menubar.py
"""

import os
import sys
import time
import tempfile
import subprocess
import threading
import json

# ===== CONFIGURATION =====
VPS_URL = "http://100.83.250.65:8765"
LOCAL_TTS_URL = "http://localhost:5001"
AUTH_TOKEN = "1fa124bc0a493b0db3dda04174bf83f9a5d3621fc51a03b916bf5784dc2f82bf"

WHISPER_MODEL = "tiny.en"
SAMPLE_RATE = 16000

# ===== CHECK DEPENDENCIES =====
def check_deps():
    required = {
        "rumps": "rumps",
        "whisper": "openai-whisper",
        "sounddevice": "sounddevice",
        "soundfile": "soundfile",
        "numpy": "numpy",
        "requests": "requests",
        "pynput": "pynput"
    }
    missing = []
    for mod, pkg in required.items():
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"Missing packages: {', '.join(missing)}")
        print(f"Install with: pip install {' '.join(missing)}")
        sys.exit(1)

check_deps()

import rumps
import whisper
import sounddevice as sd
import soundfile as sf
import numpy as np
import requests
from pynput import keyboard

# ===== GLOBALS =====
whisper_model = None
is_recording = False
app = None

def load_whisper():
    global whisper_model
    if whisper_model is None:
        whisper_model = whisper.load_model(WHISPER_MODEL)
    return whisper_model

def record_audio(duration_limit=30):
    """Record until silence or limit"""
    chunks = []
    silence_count = 0
    silence_threshold = 0.01
    silence_limit = int(1.5 * SAMPLE_RATE / 1024)  # 1.5 seconds
    
    def callback(indata, frames, time_info, status):
        nonlocal silence_count
        chunks.append(indata.copy())
        if np.abs(indata).mean() < silence_threshold:
            silence_count += 1
        else:
            silence_count = 0
    
    global is_recording
    is_recording = True
    
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=callback, blocksize=1024):
        start = time.time()
        while is_recording and time.time() - start < duration_limit:
            if silence_count > silence_limit and len(chunks) > 10:
                break
            time.sleep(0.05)
    
    is_recording = False
    
    if chunks:
        return np.concatenate(chunks)
    return None

def transcribe(audio):
    """Transcribe with Whisper"""
    model = load_whisper()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        sf.write(f.name, audio, SAMPLE_RATE)
        result = model.transcribe(f.name, language="en", fp16=False)
        os.unlink(f.name)
        return result["text"].strip()

def send_to_jarvis(text):
    """Send to VPS with auth"""
    try:
        response = requests.post(
            f"{VPS_URL}/chat",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            json={"text": text},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("response"), data.get("latency_ms", 0)
        elif response.status_code == 401:
            return "Authentication failed. Check your token.", 0
        else:
            return f"Server error: {response.status_code}", 0
    except requests.exceptions.ConnectionError:
        return "Can't connect to VPS. Is Tailscale running?", 0
    except Exception as e:
        return f"Error: {e}", 0

def speak_jarvis(text):
    """Use local Jarvis TTS"""
    try:
        r = requests.post(f"{LOCAL_TTS_URL}/speak", json={"text": text}, timeout=60)
        if r.status_code == 200:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(r.content)
                subprocess.run(["afplay", f.name])
                os.unlink(f.name)
                return True
    except:
        pass
    # Fallback to macOS say
    subprocess.run(["say", "-v", "Daniel", "-r", "180", text])
    return True

def test_connections():
    """Test VPS and TTS connections"""
    vps_ok = False
    tts_ok = False
    
    try:
        r = requests.get(f"{VPS_URL}/health", timeout=5)
        vps_ok = r.status_code == 200
    except:
        pass
    
    try:
        r = requests.get(f"{LOCAL_TTS_URL}/test", timeout=5)
        tts_ok = r.status_code == 200
    except:
        pass
    
    return vps_ok, tts_ok


class JarvisApp(rumps.App):
    def __init__(self):
        super(JarvisApp, self).__init__(
            "Jarvis",
            icon=None,  # Will use emoji
            title="🔵",
            quit_button=None
        )
        
        self.menu = [
            rumps.MenuItem("🎤 Talk to Jarvis (⌘⇧J)", callback=self.talk),
            None,  # Separator
            rumps.MenuItem("Status", callback=self.show_status),
            rumps.MenuItem("Clear History", callback=self.clear_history),
            None,
            rumps.MenuItem("Quit Jarvis", callback=self.quit_app)
        ]
        
        self.is_talking = False
        
        # Start hotkey listener in background
        self.start_hotkey_listener()
        
        # Preload Whisper in background
        threading.Thread(target=load_whisper, daemon=True).start()
    
    def start_hotkey_listener(self):
        """Listen for Cmd+Shift+J"""
        pressed_keys = set()
        
        def on_press(key):
            try:
                pressed_keys.add(key)
                # Check for Cmd+Shift+J
                if (keyboard.Key.cmd in pressed_keys and 
                    keyboard.Key.shift in pressed_keys and
                    hasattr(key, 'char') and key.char == 'j'):
                    if not self.is_talking:
                        threading.Thread(target=lambda: self.talk(None), daemon=True).start()
            except:
                pass
        
        def on_release(key):
            try:
                pressed_keys.discard(key)
            except:
                pass
        
        def listen():
            with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
                listener.join()
        
        threading.Thread(target=listen, daemon=True).start()
    
    @rumps.clicked("🎤 Talk to Jarvis (⌘⇧J)")
    def talk(self, _):
        if self.is_talking:
            return
        
        self.is_talking = True
        self.title = "🔴"  # Recording indicator
        
        def do_talk():
            try:
                # Record
                audio = record_audio()
                
                if audio is None or len(audio) < SAMPLE_RATE * 0.3:
                    rumps.notification("Jarvis", "", "No speech detected")
                    return
                
                self.title = "🟡"  # Processing
                
                # Transcribe
                text = transcribe(audio)
                if not text or len(text) < 2:
                    rumps.notification("Jarvis", "", "Couldn't understand that")
                    return
                
                print(f"You: {text}")
                
                # Check for quit commands
                if any(x in text.lower() for x in ["goodbye jarvis", "quit jarvis", "exit jarvis"]):
                    speak_jarvis("Goodbye, sir.")
                    rumps.quit_application()
                    return
                
                self.title = "🧠"  # Thinking
                
                # Get response
                response, latency = send_to_jarvis(text)
                print(f"Jarvis ({latency}ms): {response}")
                
                self.title = "🔊"  # Speaking
                
                # Speak
                speak_jarvis(response)
                
            except Exception as e:
                print(f"Error: {e}")
                rumps.notification("Jarvis", "Error", str(e)[:50])
            finally:
                self.is_talking = False
                self.title = "🔵"  # Ready
        
        threading.Thread(target=do_talk, daemon=True).start()
    
    @rumps.clicked("Status")
    def show_status(self, _):
        vps_ok, tts_ok = test_connections()
        status = []
        status.append(f"VPS: {'✅' if vps_ok else '❌'}")
        status.append(f"TTS: {'✅' if tts_ok else '❌'}")
        rumps.notification("Jarvis Status", "", "\n".join(status))
    
    @rumps.clicked("Clear History")
    def clear_history(self, _):
        try:
            requests.get(
                f"{VPS_URL}/clear",
                headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
                timeout=5
            )
            rumps.notification("Jarvis", "", "Conversation cleared")
        except:
            rumps.notification("Jarvis", "", "Failed to clear")
    
    @rumps.clicked("Quit Jarvis")
    def quit_app(self, _):
        rumps.quit_application()


def main():
    print("=" * 50)
    print("🔵 Jarvis Menu Bar App")
    print("=" * 50)
    
    # Test connections
    print("Testing connections...")
    vps_ok, tts_ok = test_connections()
    print(f"  VPS: {'✅' if vps_ok else '❌'}")
    print(f"  TTS: {'✅' if tts_ok else '❌'}")
    
    if not vps_ok:
        print("\n⚠️  Can't reach VPS!")
        print("  Make sure Tailscale is connected")
    
    if not tts_ok:
        print("\n⚠️  TTS server not running")
        print("  Start it: python jarvis_server_5001.py")
    
    print("\n🎤 Press Cmd+Shift+J to talk")
    print("   Or click the 🔵 in menu bar")
    print("=" * 50)
    
    global app
    app = JarvisApp()
    app.run()


if __name__ == "__main__":
    main()
