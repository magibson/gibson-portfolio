#!/usr/bin/env python3
"""
Jarvis Push-to-Talk with Local Jarvis Voice
Hold SPACE to talk → Whisper transcribes → VPS responds → Local Jarvis TTS speaks

Requirements (run in your mlx_env):
    pip install openai-whisper sounddevice soundfile numpy requests pynput

Usage:
    1. Start your Jarvis TTS server: python jarvis_server_5001.py
    2. Run this script: python jarvis-ptt-local.py
    3. Hold SPACEBAR to talk, release to send
    4. Press ESC to quit
"""

import os
import sys
import time
import tempfile
import subprocess
import threading
import queue
import io

# ===== CONFIGURATION =====
VPS_URL = "http://100.83.250.65:8765"  # Jarvis brain (VPS over Tailscale)
LOCAL_TTS_URL = "http://localhost:5001"  # Local Jarvis voice server

WHISPER_MODEL = "tiny.en"  # Fast English model
SAMPLE_RATE = 16000

# ===== STATE =====
is_recording = False
whisper_model = None


def check_deps():
    """Check dependencies"""
    required = ["whisper", "sounddevice", "soundfile", "numpy", "requests", "pynput"]
    missing = []
    for mod in required:
        try:
            __import__(mod)
        except ImportError:
            pkg = "openai-whisper" if mod == "whisper" else mod
            missing.append(pkg)
    
    if missing:
        print(f"Missing: {', '.join(missing)}")
        print(f"Run: pip install {' '.join(missing)}")
        sys.exit(1)


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
    """Record while is_recording is True"""
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
    """Transcribe with Whisper"""
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


def send_to_jarvis_brain(text):
    """Send to VPS, get response"""
    import requests
    
    try:
        response = requests.post(
            f"{VPS_URL}/chat",
            json={"text": text},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("response"), data.get("latency_ms", 0)
        return None, 0
    except requests.exceptions.ConnectionError:
        return "I can't reach my brain on the VPS. Is Tailscale connected?", 0
    except Exception as e:
        return f"Error: {e}", 0


def speak_with_jarvis_voice(text):
    """Use local Jarvis TTS server"""
    import requests
    
    try:
        # Call local TTS server
        response = requests.post(
            f"{LOCAL_TTS_URL}/speak",
            json={"text": text},
            timeout=60
        )
        
        if response.status_code == 200:
            # Save and play the WAV
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(response.content)
                temp_path = f.name
            
            # Play with afplay (macOS)
            subprocess.run(["afplay", temp_path], check=True)
            os.unlink(temp_path)
        else:
            print(f"TTS error: {response.status_code}")
            fallback_speak(text)
            
    except requests.exceptions.ConnectionError:
        print("⚠️  Can't reach local Jarvis TTS. Is it running on port 5001?")
        fallback_speak(text)
    except Exception as e:
        print(f"TTS error: {e}")
        fallback_speak(text)


def fallback_speak(text):
    """Fallback to macOS say"""
    subprocess.run(["say", "-v", "Daniel", "-r", "180", text])


def check_services():
    """Check VPS and local TTS are reachable"""
    import requests
    
    # Check VPS
    print(f"Checking VPS ({VPS_URL})...", end=" ", flush=True)
    try:
        r = requests.get(f"{VPS_URL}/health", timeout=5)
        if r.status_code == 200:
            print("✅")
        else:
            print("❌")
            return False
    except:
        print("❌")
        print("   → Make sure Tailscale is connected")
        print("   → VPS voice server should be running")
        return False
    
    # Check local TTS
    print(f"Checking local TTS ({LOCAL_TTS_URL})...", end=" ", flush=True)
    try:
        r = requests.get(f"{LOCAL_TTS_URL}/test", timeout=5)
        if r.status_code == 200:
            print("✅")
        else:
            print("❌")
            return False
    except:
        print("❌")
        print("   → Start your Jarvis TTS: python jarvis_server_5001.py")
        return False
    
    return True


def main():
    check_deps()
    
    from pynput import keyboard
    import numpy as np
    
    global is_recording
    
    print("=" * 50)
    print("🔵 JARVIS Push-to-Talk")
    print("=" * 50)
    print()
    
    if not check_services():
        print("\n❌ Services not ready. Fix the above and try again.")
        sys.exit(1)
    
    # Preload Whisper
    load_whisper()
    
    print()
    print("=" * 50)
    print("  Hold SPACE to talk")
    print("  Release to send")
    print("  Press ESC to quit")
    print("=" * 50)
    print()
    
    recording_thread = None
    recorded_audio = None
    
    def on_press(key):
        global is_recording
        nonlocal recording_thread, recorded_audio
        
        if key == keyboard.Key.space and not is_recording:
            is_recording = True
            recorded_audio = None
            print("🎤 Recording...", end=" ", flush=True)
            
            def do_record():
                nonlocal recorded_audio
                recorded_audio = record_audio()
            
            recording_thread = threading.Thread(target=do_record)
            recording_thread.start()
        
        elif key == keyboard.Key.esc:
            print("\n👋 Goodbye, sir.")
            return False
    
    def on_release(key):
        global is_recording
        nonlocal recording_thread, recorded_audio
        
        if key == keyboard.Key.space and is_recording:
            is_recording = False
            
            if recording_thread:
                recording_thread.join()
            
            if recorded_audio is not None and len(recorded_audio) > SAMPLE_RATE * 0.3:
                print("transcribing...", end=" ", flush=True)
                text = transcribe(recorded_audio)
                
                if text and len(text.strip()) > 1:
                    print(f"\n🗣️  You: {text}")
                    
                    # Exit commands
                    if any(x in text.lower() for x in ["goodbye", "exit", "quit", "bye jarvis"]):
                        speak_with_jarvis_voice("Goodbye, sir.")
                        return False
                    
                    # Get response from VPS
                    print("🧠 Thinking...", end=" ", flush=True)
                    response, latency = send_to_jarvis_brain(text)
                    
                    if response:
                        print(f"({latency}ms)")
                        print(f"🤖 Jarvis: {response}")
                        speak_with_jarvis_voice(response)
                    else:
                        print("\n❌ No response")
                else:
                    print("(no speech detected)")
            else:
                print("(too short)")
            
            print()
    
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()


if __name__ == "__main__":
    main()
