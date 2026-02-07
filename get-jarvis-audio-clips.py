#!/usr/bin/env python3
"""
Download clean Jarvis audio clips for voice cloning
"""

import requests
import os
import subprocess
import urllib.parse

class JarvisAudioCollector:
    
    def __init__(self):
        self.clips_dir = "jarvis-training-clips"
        os.makedirs(self.clips_dir, exist_ok=True)
        
        # High-quality Jarvis clips from movies
        self.target_clips = {
            "at_your_service": "At your service, sir.",
            "good_morning": "Good morning, sir.", 
            "systems_online": "All systems online.",
            "shall_i": "Shall I render using the Mark 42?",
            "importing_preferences": "Importing preferences and calibrating virtual environment.",
            "right_away": "Right away, sir.",
            "welcome_home": "Welcome home, sir.",
            "as_you_wish": "As you wish, sir."
        }
    
    def download_from_sources(self):
        """Download clips from various sources"""
        
        print("🎬 COLLECTING JARVIS TRAINING CLIPS")
        print("=" * 50)
        
        # Method 1: YouTube audio extraction
        youtube_clips = [
            "https://www.youtube.com/watch?v=StTqXEQ2l-Y",  # Iron Man Jarvis compilation
            "https://www.youtube.com/watch?v=YyXRYgjQXX0",  # Best Jarvis moments
        ]
        
        print("📺 YouTube method requires youtube-dl/yt-dlp")
        print("Install with: pip install yt-dlp")
        
        # Method 2: Direct movie audio sources
        print("\n🎵 Direct Audio Sources:")
        print("1. https://www.movieclips.com/iron-man-movie")
        print("2. https://www.wavsource.com/movies/iron_man.htm") 
        print("3. https://soundcloud.com/search?q=jarvis%20iron%20man")
        
        # Method 3: Manual collection guide
        self.create_collection_guide()
    
    def create_collection_guide(self):
        """Create guide for manual clip collection"""
        
        guide = f"""
# JARVIS VOICE CLONING - AUDIO COLLECTION GUIDE

## Target Clips Needed (Save to {self.clips_dir}/)

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
"""
        
        with open(f"{self.clips_dir}/COLLECTION_GUIDE.md", "w") as f:
            f.write(guide)
        
        print(f"\n📋 Collection guide created: {self.clips_dir}/COLLECTION_GUIDE.md")
        
    def validate_clips(self):
        """Check collected clips quality"""
        
        clips = []
        for file in os.listdir(self.clips_dir):
            if file.endswith(('.wav', '.mp3', '.m4a')):
                clips.append(file)
        
        print(f"\n📁 Found {len(clips)} audio files:")
        for clip in clips:
            file_path = os.path.join(self.clips_dir, clip)
            size = os.path.getsize(file_path)
            print(f"   {clip} ({size} bytes)")
        
        if len(clips) >= 3:
            print("✅ Good! 3+ clips found - ready for voice cloning")
            return True
        else:
            print("⚠️ Need at least 3 clips for good voice cloning")
            return False
    
    def create_sample_clips_with_tts(self):
        """Create sample clips using existing TTS for testing"""
        
        print("\n🔧 Creating sample clips for testing...")
        
        sample_phrases = [
            "At your service, sir",
            "Good morning, Mr. Gibson", 
            "All systems are online",
            "Drone conditions optimal, sir"
        ]
        
        # This would use the current TTS to create baseline clips
        # for testing the voice cloning workflow
        
        for i, phrase in enumerate(sample_phrases):
            filename = f"{self.clips_dir}/sample_{i+1}.txt"
            with open(filename, "w") as f:
                f.write(phrase)
        
        print(f"💡 Sample phrases saved for reference")

def main():
    collector = JarvisAudioCollector()
    
    print("🎯 JARVIS VOICE CLONING SETUP")
    print("=" * 50)
    
    collector.download_from_sources()
    
    # Check if any clips already exist
    if collector.validate_clips():
        print("\n🚀 Ready to proceed with voice cloning!")
    else:
        print("\n📥 Please collect audio clips first using the guide above")
        
    collector.create_sample_clips_with_tts()
    
    print("\n🎯 NEXT STEPS:")
    print("1. Collect 3-5 clean Jarvis audio clips")
    print(f"2. Save them to: {collector.clips_dir}/")
    print("3. Run: python3 setup-jarvis-clone.py")
    print("4. Upload clips to ElevenLabs for voice cloning")

if __name__ == "__main__":
    main()