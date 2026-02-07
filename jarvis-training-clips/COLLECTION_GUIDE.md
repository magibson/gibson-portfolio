
# JARVIS VOICE CLONING - AUDIO COLLECTION GUIDE

## Target Clips Needed (Save to jarvis-training-clips/)

For best voice cloning results, collect 3-5 clean audio clips:

### Essential Clips:
1. "At your service, sir" - jarvis_service.wav
2. "Good morning, sir" - jarvis_morning.wav  
3. "All systems online" - jarvis_systems.wav
4. "Right away, sir" - jarvis_right_away.wav
5. "Welcome home, sir" - jarvis_welcome.wav

### Audio Requirements:
- **Format:** WAV or MP3
- **Length:** 2-10 seconds each
- **Quality:** Clear, no background music/noise
- **Voice only:** Just Paul Bettany speaking, no sound effects

### Collection Methods:

#### Method A: YouTube + Audio Extraction
```bash
# Install yt-dlp
pip install yt-dlp

# Extract audio from Iron Man clips
yt-dlp -x --audio-format wav "https://youtube.com/watch?v=VIDEO_ID"
```

#### Method B: Movie/DVD Audio Rips
- Use Iron Man (2008) DVD/Blu-ray
- Extract dialogue scenes with Jarvis
- Use audio editing software (Audacity) to isolate clips

#### Method C: Existing Sound Libraries
- Search for "Iron Man Jarvis voice pack"
- Game mods often have clean Jarvis audio files
- Fan-created soundboards

### Audio Editing Tips:
1. Use Audacity (free) to clean up clips
2. Remove background noise/music
3. Normalize volume levels
4. Trim to just the essential phrase
5. Save as 22kHz WAV files

### Quality Check:
- Can you clearly hear every word?
- No background music/effects?
- Sounds like natural speech (not filtered/processed)?
- 2-10 seconds long?

Once you have 3-5 good clips, run:
```bash
python3 setup-jarvis-clone.py
```
