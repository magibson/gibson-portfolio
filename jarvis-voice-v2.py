#!/usr/bin/env python3
"""
Jarvis Voice v2 — Wake Word + Local Whisper + Claude + Qwen3-TTS
================================================
Wake word: "Jarvis" / "Hey Jarvis" / "Ok Jarvis"
Transcription: Local Whisper (tiny.en — fast)
AI: Claude API (claude-sonnet-4-6)
TTS: Qwen3-TTS (local, cloned voice when available)
Fallback TTS: macOS say -v Daniel

Usage:
    python3 jarvis-voice-v2.py

Requirements:
    pip install openai-whisper sounddevice soundfile numpy requests anthropic openwakeword
"""

import os, sys, time, threading, queue, tempfile, subprocess, json
import numpy as np
import sounddevice as sd
import soundfile as sf
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path.home() / "clawd" / ".env")

# ── Config ───────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
SAMPLE_RATE       = 16000
CHANNELS          = 1
WHISPER_MODEL     = "tiny.en"    # Fast, English-only
WAKE_WORDS        = ["jarvis", "hey jarvis", "ok jarvis"]
VOICE_SAMPLE      = Path.home() / "clawd" / "jarvis-voicemail.mp3"  # Set tomorrow
SILENCE_THRESHOLD = 0.01         # RMS below this = silence
SILENCE_DURATION  = 1.5          # Seconds of silence to stop recording

# ── State ─────────────────────────────────────────────────────────────────────
is_awake     = False
audio_queue  = queue.Queue()
conversation = []   # Conversation history for Claude

# ── Imports (lazy to allow startup without all deps) ──────────────────────────
def load_whisper():
    import whisper
    print("⚙️  Loading Whisper (tiny.en)...")
    model = whisper.load_model(WHISPER_MODEL)
    print("✅ Whisper ready")
    return model

def load_openwakeword():
    try:
        from openwakeword.model import Model
        oww = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
        print("✅ OpenWakeWord ready — listening for 'Hey Jarvis'")
        return oww
    except Exception as e:
        print(f"⚠️  OpenWakeWord not available ({e}), falling back to Whisper-based wake word")
        return None

# ── TTS ───────────────────────────────────────────────────────────────────────
def speak(text: str):
    """Speak text using Qwen3-TTS if voice sample available, else macOS say."""
    print(f"🔊 Jarvis: {text}")
    
    if VOICE_SAMPLE.exists():
        try:
            _speak_qwen(text)
            return
        except Exception as e:
            print(f"⚠️  Qwen TTS failed: {e}, falling back to macOS")
    
    # Fallback: macOS Daniel voice
    subprocess.run(["say", "-v", "Daniel", "-r", "190", text], check=False)

def _speak_qwen(text: str):
    """Use Qwen3-TTS to generate speech with cloned voice."""
    import torch, soundfile as sf
    from qwen_tts import Qwen3TTSModel  # type: ignore
    
    model = Qwen3TTSModel.from_pretrained(
        "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
        device_map="mps",
        dtype=torch.float32
    )
    voice_prompt = model.create_voice_clone_prompt(
        ref_audio=str(VOICE_SAMPLE),
        ref_text="Please excuse the interruption, but you have a new voice message"
    )
    wavs, sr = model.generate_voice_clone(
        text=text,
        language="English",
        voice_clone_prompt=voice_prompt
    )
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        sf.write(f.name, wavs[0], sr)
        subprocess.run(["afplay", f.name], check=False)

# ── Claude ────────────────────────────────────────────────────────────────────
def ask_claude(text: str) -> str:
    """Send text to Claude and get a response."""
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    conversation.append({"role": "user", "content": text})
    
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system="""You are Jarvis, an AI assistant. Respond conversationally and concisely. 
You are speaking aloud so keep responses natural, under 3 sentences unless asked for detail.
Do not use markdown, bullet points, or formatting — plain spoken language only.""",
        messages=conversation
    )
    
    reply = response.content[0].text
    conversation.append({"role": "assistant", "content": reply})
    
    # Keep conversation history manageable
    if len(conversation) > 20:
        conversation.pop(0)
        conversation.pop(0)
    
    return reply

# ── Recording ─────────────────────────────────────────────────────────────────
def record_until_silence() -> np.ndarray:
    """Record audio until silence detected."""
    print("🎤 Listening...")
    frames = []
    silence_frames = 0
    min_frames = int(SAMPLE_RATE * 0.5)  # Minimum 0.5s of audio
    silence_limit = int(SAMPLE_RATE * SILENCE_DURATION / 512)
    
    def callback(indata, frame_count, time_info, status):
        rms = np.sqrt(np.mean(indata**2))
        frames.append(indata.copy())
        if rms < SILENCE_THRESHOLD and len(frames) > min_frames // 512:
            silence_frames_ref[0] += 1
        else:
            silence_frames_ref[0] = 0
    
    silence_frames_ref = [0]
    
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                        dtype='float32', callback=callback, blocksize=512):
        while silence_frames_ref[0] < silence_limit:
            sd.sleep(50)
    
    return np.concatenate(frames, axis=0)

def transcribe(whisper_model, audio: np.ndarray) -> str:
    """Transcribe audio using local Whisper."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        sf.write(f.name, audio, SAMPLE_RATE)
        result = whisper_model.transcribe(f.name, language="en", fp16=False)
        os.unlink(f.name)
    return result["text"].strip().lower()

# ── Wake Word Detection ───────────────────────────────────────────────────────
def listen_for_wake_word_whisper(whisper_model) -> bool:
    """Fallback: Use Whisper to detect wake word in short audio bursts."""
    chunk_duration = 2.0  # seconds
    frames = []
    
    def callback(indata, frame_count, time_info, status):
        frames.append(indata.copy())
    
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                        dtype='float32', callback=callback):
        sd.sleep(int(chunk_duration * 1000))
    
    if not frames:
        return False
    
    audio = np.concatenate(frames, axis=0)
    rms = np.sqrt(np.mean(audio**2))
    if rms < SILENCE_THRESHOLD:
        return False  # Too quiet, skip transcription
    
    text = transcribe(whisper_model, audio)
    return any(w in text for w in WAKE_WORDS)

def listen_for_wake_word_oww(oww) -> bool:
    """Use OpenWakeWord for efficient wake word detection."""
    chunk = int(SAMPLE_RATE * 0.08)  # 80ms chunks
    detected = [False]
    
    def callback(indata, frame_count, time_info, status):
        audio_int16 = (indata[:, 0] * 32768).astype(np.int16)
        pred = oww.predict(audio_int16)
        if any(v > 0.5 for v in pred.values()):
            detected[0] = True
    
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                        dtype='float32', callback=callback, blocksize=chunk):
        for _ in range(50):  # Check for 4 seconds
            if detected[0]:
                return True
            sd.sleep(80)
    
    return False

# ── Main Loop ─────────────────────────────────────────────────────────────────
def main():
    print("=" * 50)
    print("  JARVIS VOICE v2")
    print("  Say 'Jarvis' or 'Hey Jarvis' to activate")
    print("  Ctrl+C to exit")
    print("=" * 50)
    
    whisper_model = load_whisper()
    oww = load_openwakeword()
    
    speak("Jarvis online. Say hey Jarvis to activate.")
    
    while True:
        try:
            # Wake word detection
            if oww:
                detected = listen_for_wake_word_oww(oww)
            else:
                detected = listen_for_wake_word_whisper(whisper_model)
            
            if not detected:
                continue
            
            print("\n🟢 Wake word detected!")
            speak("Yes?")
            
            # Record user's command
            audio = record_until_silence()
            text = transcribe(whisper_model, audio)
            print(f"👤 You: {text}")
            
            if not text or len(text.strip()) < 3:
                speak("Sorry, I didn't catch that.")
                continue
            
            # Handle exit commands
            if any(w in text for w in ["goodbye", "go to sleep", "shut down", "that's all"]):
                speak("Goodbye.")
                break
            
            # Get Claude response
            response = ask_claude(text)
            speak(response)
            
        except KeyboardInterrupt:
            print("\n\nShutting down...")
            speak("Goodbye.")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
