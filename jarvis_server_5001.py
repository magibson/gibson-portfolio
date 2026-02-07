from flask import Flask, request, jsonify, send_file
import torch
import soundfile as sf
from qwen_tts import Qwen3TTSModel
import time
import os

app = Flask(__name__)

print("Loading Jarvis voice model...")
model = Qwen3TTSModel.from_pretrained('Qwen/Qwen3-TTS-12Hz-0.6B-Base', device_map='mps', dtype=torch.float32)
voice_clone_prompt = model.create_voice_clone_prompt(
    ref_audio='jarvis-voicemail.mp3',
    ref_text='Please excuse the interruption, but you have a new voice message'
)
print("Jarvis voice ready!")

@app.route('/speak', methods=['POST'])
def speak():
    text = request.json['text']
    print(f"Jarvis speaking: {text}")
    wavs, sr = model.generate_voice_clone(text=text, language='English', voice_clone_prompt=voice_clone_prompt)
    filename = f'jarvis_speech_{int(time.time())}.wav'
    sf.write(filename, wavs[0], sr)
    return send_file(filename, as_attachment=True)

@app.route('/test')
def test():
    return "Jarvis voice server is running!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)  # Changed to 5001
