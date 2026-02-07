#!/usr/bin/env python3
"""
Jarvis Voice Client for Mac
Records your voice, transcribes with Whisper, sends to VPS, speaks response with Jarvis voice

Requirements:
    pip install openai-whisper sounddevice soundfile numpy requests pyobjc-framework-AVFoundation

Setup:
    1. Start the voice server on VPS: python jarvis-voice-server.py
    2. Set your Jarvis voice reference path below (or use macOS voice fallback)
    3. Run this script: python jarvis-mac-client.py

Usage:
    - Press Enter to start recording (or just start talking with voice activity detection)
    - Speak your message
    - Stop speaking for 1.5s to auto-stop recording
    - Wait for Jarvis to respond
    - Say "goodbye" or "exit" to quit
"""

import os
import sys
import time
import tempfile
import subprocess
import json

# ===== CONFIGURATION =====
VPS_URL = "http://100.83.250.65:8765"  # Tailscale IP of VPS voice server

# Whisper settings
WHISPER_MODEL = "base"  # tiny/base/small for speed, medium/large for accuracy

# Audio settings  
SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.01  # Adjust based on your mic
SILENCE_DURATION = 1.5    # Seconds of silence to stop
MAX_RECORD_TIME = 30      # Max seconds to record

# TTS Settings - Update this path to your Jarvis voice setup
JARVIS_VOICE_REF = os.path.expanduser("~/jarvis-voice/reference.mp3")
USE_QWEN_TTS = True  # Set False to use macOS say as fallback

# ===== LAZY IMPORTS =====
whisper_model = None

def check_dependencies():
    """Check and install missing dependencies"""
    required = ["whisper", "sounddevice", "soundfile", "numpy", "requests"]
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg if pkg != "whisper" else "openai-whisper")
    
    if missing:
        print(f"Installing missing packages: {', '.join(missing)}")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", *missing, "-q"
        ])


def load_whisper():
    """Load Whisper model (lazy, cached)"""
    global whisper_model
    if whisper_model is None:
        import whisper
        print(f"🧠 Loading Whisper ({WHISPER_MODEL})...")
        whisper_model = whisper.load_model(WHISPER_MODEL)
        print("✅ Whisper ready")
    return whisper_model


def record_audio():
    """Record audio until silence detected"""
    import sounddevice as sd
    import numpy as np
    
    print("\n🎤 Listening... (speak now)")
    
    chunks = []
    silence_samples = 0
    silence_limit = int(SILENCE_DURATION * SAMPLE_RATE)
    started_speaking = False
    
    def callback(indata, frames, time_info, status):
        nonlocal silence_samples, started_speaking
        chunks.append(indata.copy())
        
        volume = np.abs(indata).mean()
        if volume > SILENCE_THRESHOLD:
            started_speaking = True
            silence_samples = 0
        elif started_speaking:
            silence_samples += frames
    
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=callback):
        start = time.time()
        while True:
            time.sleep(0.1)
            elapsed = time.time() - start
            
            # Stop conditions
            if started_speaking and silence_samples > silence_limit:
                break
            if elapsed > MAX_RECORD_TIME:
                print("⏱️ Max time reached")
                break
            if elapsed > 5 and not started_speaking:
                # 5 seconds with no speech
                return None
    
    if not chunks or not started_speaking:
        return None
    
    audio = np.concatenate(chunks)
    duration = len(audio) / SAMPLE_RATE
    print(f"📝 Recorded {duration:.1f}s")
    return audio


def transcribe(audio):
    """Transcribe audio with Whisper"""
    import soundfile as sf
    
    model = load_whisper()
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        sf.write(f.name, audio, SAMPLE_RATE)
        temp_path = f.name
    
    try:
        result = model.transcribe(temp_path, language="en")
        text = result["text"].strip()
        if text:
            print(f"🗣️  You: {text}")
        return text
    finally:
        os.unlink(temp_path)


def send_to_jarvis(text):
    """Send text to VPS and get Jarvis's response"""
    import requests
    
    try:
        response = requests.post(
            f"{VPS_URL}/chat",
            json={"text": text},
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            jarvis_response = data.get("response", "")
            latency = data.get("latency_ms", 0)
            print(f"🤖 Jarvis ({latency}ms): {jarvis_response}")
            return jarvis_response
        else:
            print(f"❌ Server error: {response.status_code}")
            return None
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Can't connect to {VPS_URL}")
        print("   Make sure the voice server is running on VPS")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def speak_with_jarvis_voice(text):
    """Generate speech using Jarvis voice clone"""
    
    if not USE_QWEN_TTS or not os.path.exists(JARVIS_VOICE_REF):
        # Fallback to macOS
        speak_macos(text)
        return
    
    try:
        # Using Qwen3-TTS - adjust this based on your setup
        output_file = tempfile.mktemp(suffix=".wav")
        
        # This assumes you have qwen3-tts installed and working
        # Adjust the import/API call based on your actual setup
        cmd = f'''
cd ~/Qwen3-TTS && python -c "
from qwen3_tts import Qwen3TTS
tts = Qwen3TTS()
tts.synthesize(
    text='''{text.replace("'", "\\'")}''',
    reference_audio='{JARVIS_VOICE_REF}',
    output_path='{output_file}'
)
"
'''
        result = subprocess.run(cmd, shell=True, capture_output=True, timeout=30)
        
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            subprocess.run(["afplay", output_file])
            os.unlink(output_file)
        else:
            # Fallback
            speak_macos(text)
            
    except Exception as e:
        print(f"⚠️ TTS error: {e}, using fallback")
        speak_macos(text)


def speak_macos(text):
    """Fallback: use macOS say command with Daniel voice"""
    subprocess.run(["say", "-v", "Daniel", "-r", "180", text])


def test_connection():
    """Test connection to VPS"""
    import requests
    
    try:
        r = requests.get(f"{VPS_URL}/health", timeout=5)
        return r.status_code == 200
    except:
        return False


def main():
    print("=" * 50)
    print("🔵 JARVIS Voice Interface")
    print("=" * 50)
    
    # Check dependencies
    check_dependencies()
    
    # Reload after potential installs
    import numpy as np
    import requests
    
    # Test VPS connection
    print(f"\n🔗 Connecting to VPS ({VPS_URL})...")
    if test_connection():
        print("✅ VPS connected")
    else:
        print("❌ Can't reach VPS!")
        print("   1. Make sure you're on Tailscale")
        print("   2. Run on VPS: python jarvis-voice-server.py")
        sys.exit(1)
    
    # Pre-load Whisper
    load_whisper()
    
    print("\n" + "=" * 50)
    print("Ready! Just start talking.")
    print("Say 'goodbye' or 'exit' to quit.")
    print("=" * 50 + "\n")
    
    try:
        while True:
            # Record
            audio = record_audio()
            
            if audio is None:
                print("(no speech detected)")
                continue
            
            # Transcribe
            text = transcribe(audio)
            
            if not text or len(text.strip()) < 2:
                continue
            
            # Check exit
            lower = text.lower()
            if any(x in lower for x in ["goodbye", "exit", "quit", "bye jarvis"]):
                speak_with_jarvis_voice("Goodbye, sir.")
                break
            
            # Send to Jarvis
            response = send_to_jarvis(text)
            
            if response:
                speak_with_jarvis_voice(response)
            else:
                speak_macos("Sorry, I couldn't get a response.")
            
            print()  # Blank line
            
    except KeyboardInterrupt:
        print("\n\n👋 Jarvis signing off.")


if __name__ == "__main__":
    main()
