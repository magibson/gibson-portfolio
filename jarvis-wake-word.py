#!/usr/bin/env python3
"""
Jarvis Wake Word System
- Listens for "Hey Jarvis" or "Jarvis"
- Uses Whisper for offline STT (no API calls, no internet needed)
- Sends voice input to Claude via OpenClaw API
- Responds with macOS TTS (say -v Daniel)
"""

import pyaudio
import wave
import whisper
import numpy as np
import subprocess
import threading
import tempfile
import os
import sys
import time
import json
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/clawd/.env"))

# ── Config ──────────────────────────────────────────────────────────────
WAKE_WORDS = ["jarvis", "hey jarvis", "ok jarvis"]
MIC_INDEX = 1          # Blue Yeti (device 1)
SAMPLE_RATE = 48000    # Yeti native rate (downsampled to 16k for Whisper)
CHUNK = 1024
SILENCE_THRESHOLD = 500    # amplitude below this = silence
SILENCE_SECS = 1.5         # seconds of silence = end of utterance
MAX_RECORD_SECS = 15       # max recording per utterance
VOICE = "Daniel"           # macOS TTS voice

# Anthropic API
import anthropic as _anthropic_mod
_anthropic_key = None
_anthropic_client = None

# ── Whisper model ────────────────────────────────────────────────────────
print("🔄 Loading Whisper model...")
model = whisper.load_model("base")
print("✅ Whisper ready")

pa = pyaudio.PyAudio()


def speak(text: str):
    """Speak text using macOS TTS."""
    print(f"🤖 Jarvis: {text}")
    subprocess.run(["say", "-v", VOICE, text], check=False)


def record_until_silence(max_secs=MAX_RECORD_SECS) -> bytes | None:
    """Record audio from mic until silence detected. Returns raw PCM bytes."""
    stream = pa.open(
        format=pyaudio.paInt16,
        channels=2,
        rate=SAMPLE_RATE,
        input=True,
        input_device_index=MIC_INDEX,
        frames_per_buffer=CHUNK,
    )

    frames = []
    silent_chunks = 0
    silent_limit = int(SILENCE_SECS * SAMPLE_RATE / CHUNK)
    max_chunks = int(max_secs * SAMPLE_RATE / CHUNK)
    got_speech = False

    for _ in range(max_chunks):
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)
        amplitude = np.abs(np.frombuffer(data, dtype=np.int16)).max()

        if amplitude > SILENCE_THRESHOLD:
            got_speech = True
            silent_chunks = 0
        else:
            silent_chunks += 1

        if got_speech and silent_chunks >= silent_limit:
            break

    stream.stop_stream()
    stream.close()

    if not got_speech:
        return None
    return b"".join(frames)


def pcm_to_wav(pcm_data: bytes) -> str:
    """Write PCM bytes to a temp WAV file (mono, 16kHz for Whisper), return path."""
    # Downmix stereo -> mono
    stereo = np.frombuffer(pcm_data, dtype=np.int16).reshape(-1, 2)
    mono = stereo.mean(axis=1).astype(np.float32)
    # Resample 48kHz -> 16kHz (simple decimation by 3)
    mono_16k = mono[::3].astype(np.int16)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    with wave.open(tmp.name, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(16000)
        wf.writeframes(mono_16k.tobytes())
    return tmp.name


def transcribe(pcm_data: bytes) -> str:
    """Transcribe PCM audio via Whisper. Returns lowercased text."""
    wav_path = pcm_to_wav(pcm_data)
    try:
        result = model.transcribe(wav_path, fp16=False, language="en")
        return result["text"].strip().lower()
    finally:
        os.unlink(wav_path)


def ask_jarvis(user_text: str) -> str:
    """Send text to Claude (Anthropic API) and get Jarvis response."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return fallback_response(user_text)
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=256,
            system=(
                "You are Jarvis, the AI assistant from Iron Man. "
                "You speak in a refined, helpful British manner and call the user 'sir' or 'Mr. Gibson'. "
                "Keep responses concise — 1-3 sentences max. No markdown, no bullet points, just natural spoken language."
            ),
            messages=[{"role": "user", "content": user_text}],
        )
        return message.content[0].text.strip()
    except Exception as e:
        print(f"  [claude error] {e}")
        return fallback_response(user_text)


def fallback_response(user_text: str) -> str:
    """Fallback when OpenClaw API isn't reachable."""
    responses = {
        "what time is it": f"It's {time.strftime('%I:%M %p')}, sir.",
        "what's today": f"Today is {time.strftime('%A, %B %d')}, sir.",
        "hello": "Good day, Mr. Gibson.",
        "how are you": "All systems nominal, sir.",
    }
    for key, val in responses.items():
        if key in user_text:
            return val
    return "I'm having trouble reaching my core systems. Please try again shortly, sir."


def listen_for_wake_word() -> bool:
    """
    Listen for ~3 seconds, transcribe, check for wake word.
    Returns True if wake word detected.
    """
    stream = pa.open(
        format=pyaudio.paInt16,
        channels=2,
        rate=SAMPLE_RATE,
        input=True,
        input_device_index=MIC_INDEX,
        frames_per_buffer=CHUNK,
    )

    frames = []
    chunks_to_capture = int(3 * SAMPLE_RATE / CHUNK)  # 3 seconds

    for _ in range(chunks_to_capture):
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)

    stream.stop_stream()
    stream.close()

    pcm = b"".join(frames)
    amplitude = np.abs(np.frombuffer(pcm, dtype=np.int16)).max()

    # Skip transcription if essentially silent
    if amplitude < SILENCE_THRESHOLD:
        return False

    text = transcribe(pcm)
    if text:
        print(f"  [heard] {text}")

    return any(w in text for w in WAKE_WORDS)


def conversation_loop():
    """Active conversation after wake word detected."""
    speak("At your service, Mr. Gibson.")

    timeout_secs = 30
    last_speech = time.time()

    while True:
        if time.time() - last_speech > timeout_secs:
            speak("Returning to standby, sir.")
            break

        print("💬 Listening...")
        pcm = record_until_silence()

        if pcm is None:
            continue

        text = transcribe(pcm)
        if not text:
            continue

        print(f"👤 You: {text}")
        last_speech = time.time()

        # End conversation
        if any(phrase in text for phrase in ["goodbye", "that's all", "stand by", "standby", "stop"]):
            speak("Understood, sir. Standing by.")
            break

        # Get response
        response = ask_jarvis(text)
        speak(response)


def main():
    print("\n🤖 JARVIS WAKE WORD SYSTEM")
    print("=" * 40)
    print(f"Mic: {pa.get_device_info_by_index(MIC_INDEX)['name']}")
    print(f"Wake words: {', '.join(WAKE_WORDS)}")
    print("Say 'goodbye' or 'that's all' to end conversation")
    print("Ctrl+C to shut down\n")

    speak("Jarvis online. Listening for your command, Mr. Gibson.")

    try:
        while True:
            if listen_for_wake_word():
                print("🎯 Wake word detected!")
                conversation_loop()
            # Brief pause between wake word checks
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        speak("Goodbye, Mr. Gibson.")
        pa.terminate()


if __name__ == "__main__":
    main()
