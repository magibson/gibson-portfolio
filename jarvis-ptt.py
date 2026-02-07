#!/usr/bin/env python3
"""
Jarvis Push-to-Talk - Fast conversational voice interface
Hold SPACE to talk, release to send. Jarvis responds instantly.

Requirements:
    pip install openai-whisper sounddevice soundfile numpy requests pynput

Usage:
    python jarvis-ptt.py
    
    Hold SPACEBAR to talk
    Release to send
    Press ESC to quit
"""

import os
import sys
import time
import tempfile
import subprocess
import threading
import queue

# ===== CONFIGURATION =====
VPS_URL = "http://100.83.250.65:8765"  # Tailscale IP

# Whisper - use "tiny" or "base" for speed
WHISPER_MODEL = "tiny.en"  # Fastest English-only model

# Audio
SAMPLE_RATE = 16000

# TTS - using macOS say for instant response
VOICE = "Daniel"  # British voice, closest to Jarvis vibe
SPEECH_RATE = 190  # Words per minute

# ===== STATE =====
is_recording = False
audio_queue = queue.Queue()
whisper_model = None


def install_deps():
    """Install missing dependencies"""
    deps = {
        "whisper": "openai-whisper",
        "sounddevice": "sounddevice",
        "soundfile": "soundfile",
        "numpy": "numpy",
        "requests": "requests",
        "pynput": "pynput"
    }
    
    missing = []
    for module, package in deps.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"Installing: {', '.join(missing)}")
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing + ["-q"])
        print("✅ Dependencies installed. Please restart the script.")
        sys.exit(0)


def load_whisper():
    """Load Whisper model"""
    global whisper_model
    if whisper_model is None:
        import whisper
        print(f"Loading Whisper ({WHISPER_MODEL})...", end=" ", flush=True)
        whisper_model = whisper.load_model(WHISPER_MODEL)
        print("✅")
    return whisper_model


def record_audio():
    """Record audio while is_recording is True"""
    import sounddevice as sd
    import numpy as np
    
    chunks = []
    
    def callback(indata, frames, time_info, status):
        if is_recording:
            chunks.append(indata.copy())
    
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=callback):
        while is_recording:
            time.sleep(0.05)
    
    if chunks:
        return np.concatenate(chunks)
    return None


def transcribe(audio):
    """Transcribe audio with Whisper"""
    import soundfile as sf
    
    model = load_whisper()
    
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        sf.write(f.name, audio, SAMPLE_RATE)
        temp_path = f.name
    
    try:
        result = model.transcribe(temp_path, language="en", fp16=False)
        return result["text"].strip()
    finally:
        os.unlink(temp_path)


def send_to_jarvis(text):
    """Send to VPS and get response"""
    import requests
    
    try:
        start = time.time()
        response = requests.post(
            f"{VPS_URL}/chat",
            json={"text": text},
            timeout=30
        )
        elapsed = int((time.time() - start) * 1000)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("response"), elapsed
        return None, 0
    except requests.exceptions.ConnectionError:
        return "I can't reach the server. Make sure the voice server is running on the VPS.", 0
    except Exception as e:
        return f"Error: {e}", 0


def speak(text):
    """Speak using macOS say"""
    # Clean text for speech
    text = text.replace('"', '\\"')
    subprocess.run(["say", "-v", VOICE, "-r", str(SPEECH_RATE), text])


def test_connection():
    """Test VPS connection"""
    import requests
    try:
        r = requests.get(f"{VPS_URL}/health", timeout=3)
        return r.status_code == 200
    except:
        return False


def main():
    install_deps()
    
    from pynput import keyboard
    import numpy as np
    
    global is_recording
    
    print("=" * 50)
    print("🔵 JARVIS Push-to-Talk")
    print("=" * 50)
    
    # Test connection
    print(f"Connecting to {VPS_URL}...", end=" ", flush=True)
    if test_connection():
        print("✅")
    else:
        print("❌")
        print("\n⚠️  Can't reach VPS!")
        print("   1. Make sure Tailscale is connected")
        print("   2. Start voice server: python jarvis-voice-server.py")
        sys.exit(1)
    
    # Preload Whisper
    load_whisper()
    
    print("\n" + "=" * 50)
    print("Hold SPACE to talk | Release to send | ESC to quit")
    print("=" * 50 + "\n")
    
    recording_thread = None
    recorded_audio = None
    
    def on_press(key):
        global is_recording
        nonlocal recording_thread, recorded_audio
        
        if key == keyboard.Key.space and not is_recording:
            is_recording = True
            recorded_audio = None
            print("🎤 Recording...", end=" ", flush=True)
            
            def record():
                nonlocal recorded_audio
                recorded_audio = record_audio()
            
            recording_thread = threading.Thread(target=record)
            recording_thread.start()
        
        elif key == keyboard.Key.esc:
            print("\n👋 Goodbye!")
            return False  # Stop listener
    
    def on_release(key):
        global is_recording
        nonlocal recording_thread, recorded_audio
        
        if key == keyboard.Key.space and is_recording:
            is_recording = False
            print("Processing...")
            
            if recording_thread:
                recording_thread.join()
            
            if recorded_audio is not None and len(recorded_audio) > SAMPLE_RATE * 0.3:
                # Transcribe
                text = transcribe(recorded_audio)
                
                if text and len(text.strip()) > 1:
                    print(f"🗣️  You: {text}")
                    
                    # Check for exit
                    if any(x in text.lower() for x in ["goodbye", "exit", "quit"]):
                        speak("Goodbye, sir.")
                        return False
                    
                    # Get response
                    response, latency = send_to_jarvis(text)
                    
                    if response:
                        print(f"🤖 Jarvis ({latency}ms): {response}")
                        speak(response)
                    else:
                        print("❌ No response")
                else:
                    print("(no speech detected)")
            else:
                print("(too short)")
            
            print()  # Blank line
    
    # Start keyboard listener
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()


if __name__ == "__main__":
    main()
