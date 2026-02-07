#!/usr/bin/env python3
"""
Jarvis Voice Chat - Talk to Jarvis with your voice!
Runs on Mac. Uses:
- Whisper for speech-to-text
- Telegram bot API to talk to Jarvis (Clawdbot)
- Qwen3-TTS with Jarvis voice clone for speech output

Requirements (Mac):
pip install openai-whisper sounddevice soundfile numpy requests

Usage:
1. Set environment variables (or edit below):
   export TELEGRAM_BOT_TOKEN="your_bot_token"
   export TELEGRAM_CHAT_ID="your_chat_id"

2. Make sure Qwen3-TTS is set up with jarvis voice

3. Run: python jarvis-voice-chat.py
"""

import os
import sys
import time
import tempfile
import subprocess
import threading
import queue

# Check for required packages
try:
    import whisper
    import sounddevice as sd
    import soundfile as sf
    import numpy as np
    import requests
except ImportError as e:
    print(f"Missing package: {e}")
    print("Install with: pip install openai-whisper sounddevice soundfile numpy requests")
    sys.exit(1)

# ===== CONFIGURATION =====
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID_HERE")

# Whisper model (tiny/base/small for speed, medium/large for accuracy)
WHISPER_MODEL = "base"

# Audio settings
SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.01
SILENCE_DURATION = 1.5  # seconds of silence to stop recording
MIN_RECORDING_TIME = 0.5  # minimum recording length

# TTS settings - adjust path to your Qwen3-TTS setup
JARVIS_VOICE_REF = os.path.expanduser("~/jarvis-voice/reference.mp3")  # Your Jarvis voice reference
QWEN_TTS_PATH = os.path.expanduser("~/Qwen3-TTS")  # Path to Qwen3-TTS

# ===== GLOBALS =====
whisper_model = None
last_update_id = 0


def load_whisper():
    """Load Whisper model (cached after first load)"""
    global whisper_model
    if whisper_model is None:
        print(f"Loading Whisper model ({WHISPER_MODEL})...")
        whisper_model = whisper.load_model(WHISPER_MODEL)
    return whisper_model


def record_until_silence():
    """Record audio until user stops speaking"""
    print("🎤 Listening... (speak now)")
    
    audio_chunks = []
    silence_samples = 0
    silence_threshold_samples = int(SILENCE_DURATION * SAMPLE_RATE)
    min_samples = int(MIN_RECORDING_TIME * SAMPLE_RATE)
    
    def audio_callback(indata, frames, time_info, status):
        nonlocal silence_samples
        audio_chunks.append(indata.copy())
        
        # Check for silence
        volume = np.abs(indata).mean()
        if volume < SILENCE_THRESHOLD:
            silence_samples += frames
        else:
            silence_samples = 0
    
    # Start recording
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=audio_callback):
        while True:
            time.sleep(0.1)
            total_samples = sum(len(c) for c in audio_chunks)
            
            # Stop if we have enough silence after minimum recording time
            if total_samples > min_samples and silence_samples > silence_threshold_samples:
                break
            
            # Safety timeout (30 seconds max)
            if total_samples > SAMPLE_RATE * 30:
                break
    
    if not audio_chunks:
        return None
    
    audio = np.concatenate(audio_chunks)
    print(f"📝 Recorded {len(audio)/SAMPLE_RATE:.1f}s of audio")
    return audio


def transcribe(audio):
    """Transcribe audio using Whisper"""
    model = load_whisper()
    
    # Save to temp file (Whisper needs a file)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        sf.write(f.name, audio, SAMPLE_RATE)
        temp_path = f.name
    
    try:
        result = model.transcribe(temp_path, language="en")
        text = result["text"].strip()
        print(f"🗣️ You said: {text}")
        return text
    finally:
        os.unlink(temp_path)


def send_telegram_message(text):
    """Send message to Jarvis via Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    response = requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text
    })
    return response.json()


def get_telegram_updates():
    """Get new messages from Telegram"""
    global last_update_id
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {"offset": last_update_id + 1, "timeout": 30}
    
    try:
        response = requests.get(url, params=params, timeout=35)
        data = response.json()
        
        if data.get("ok") and data.get("result"):
            for update in data["result"]:
                last_update_id = update["update_id"]
                msg = update.get("message", {})
                # Only return messages from the bot (Jarvis responses)
                if msg.get("from", {}).get("is_bot"):
                    return msg.get("text", "")
    except Exception as e:
        print(f"Error getting updates: {e}")
    
    return None


def wait_for_jarvis_response(timeout=60):
    """Wait for Jarvis to respond"""
    print("⏳ Waiting for Jarvis...")
    start = time.time()
    
    while time.time() - start < timeout:
        response = get_telegram_updates()
        if response:
            print(f"🤖 Jarvis: {response[:100]}...")
            return response
        time.sleep(0.5)
    
    print("⚠️ Timeout waiting for response")
    return None


def speak_with_jarvis_voice(text):
    """Generate and play speech using Jarvis voice"""
    print("🔊 Speaking...")
    
    # Save text to temp file for TTS
    with tempfile.NamedTemporaryFile(mode='w', suffix=".txt", delete=False) as f:
        f.write(text)
        text_file = f.name
    
    output_file = tempfile.mktemp(suffix=".wav")
    
    try:
        # Run Qwen3-TTS with Jarvis voice
        # Adjust this command based on your Qwen3-TTS setup
        cmd = [
            "python", "-c", f'''
import sys
sys.path.insert(0, "{QWEN_TTS_PATH}")
from qwen3_tts import Qwen3TTS

tts = Qwen3TTS()
tts.generate(
    text="""{text}""",
    reference_audio="{JARVIS_VOICE_REF}",
    output_path="{output_file}"
)
'''
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if os.path.exists(output_file):
            # Play the audio
            subprocess.run(["afplay", output_file], check=True)
        else:
            print(f"TTS failed: {result.stderr}")
            # Fallback to macOS say command
            subprocess.run(["say", "-v", "Daniel", text])
            
    except Exception as e:
        print(f"TTS error: {e}")
        # Fallback to macOS say
        subprocess.run(["say", "-v", "Daniel", text])
    finally:
        if os.path.exists(text_file):
            os.unlink(text_file)
        if os.path.exists(output_file):
            os.unlink(output_file)


def simple_speak(text):
    """Simple TTS using macOS say (fallback)"""
    # Use Daniel voice (British) as fallback
    subprocess.run(["say", "-v", "Daniel", text])


def main():
    """Main conversation loop"""
    print("=" * 50)
    print("🔵 JARVIS Voice Interface")
    print("=" * 50)
    print(f"Telegram Bot: {'✅ Configured' if TELEGRAM_BOT_TOKEN != 'YOUR_BOT_TOKEN_HERE' else '❌ Not set'}")
    print(f"Whisper Model: {WHISPER_MODEL}")
    print()
    print("Commands:")
    print("  - Just speak to interact with Jarvis")
    print("  - Say 'goodbye' or 'exit' to quit")
    print("  - Press Ctrl+C to force quit")
    print("=" * 50)
    print()
    
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("⚠️ Please set TELEGRAM_BOT_TOKEN environment variable")
        print("   export TELEGRAM_BOT_TOKEN='your_token_here'")
        sys.exit(1)
    
    # Pre-load Whisper
    load_whisper()
    
    # Clear any pending updates
    get_telegram_updates()
    
    print("\n🎙️ Ready! Start speaking...\n")
    
    try:
        while True:
            # Record user's voice
            audio = record_until_silence()
            
            if audio is None or len(audio) < SAMPLE_RATE * 0.3:
                continue
            
            # Transcribe
            text = transcribe(audio)
            
            if not text or len(text.strip()) < 2:
                continue
            
            # Check for exit commands
            if any(word in text.lower() for word in ["goodbye", "exit", "quit", "bye jarvis"]):
                speak_with_jarvis_voice("Goodbye, sir.")
                break
            
            # Send to Jarvis via Telegram
            send_telegram_message(text)
            
            # Wait for response
            response = wait_for_jarvis_response()
            
            if response:
                # Speak the response
                speak_with_jarvis_voice(response)
            else:
                simple_speak("I didn't receive a response. Please try again.")
            
            print()  # Blank line between exchanges
            
    except KeyboardInterrupt:
        print("\n\n👋 Jarvis signing off.")


if __name__ == "__main__":
    main()
