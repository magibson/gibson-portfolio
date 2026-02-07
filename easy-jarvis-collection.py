#!/usr/bin/env python3
"""
Easy Methods to Collect Real Jarvis Audio for Voice Cloning
"""

def show_collection_methods():
    print("🎯 EASIEST WAYS TO GET REAL JARVIS AUDIO")
    print("=" * 60)
    
    print("\n🥇 METHOD 1: YouTube + yt-dlp (Recommended)")
    print("✅ Best quality compilation videos")
    print("✅ Multiple clean clips in one download")
    print("✅ Easy to extract specific phrases")
    
    print("\nCommands:")
    print("1. Install: pip install yt-dlp")
    print("2. Download: yt-dlp -x --audio-format wav 'YOUTUBE_URL'")
    print("3. Edit with Audacity to extract 3-5 clean phrases")
    
    videos = [
        "Iron Man Jarvis Best Moments - Usually has clean dialogue",
        "MCU Jarvis Compilation - Multiple movies", 
        "Tony Stark and Jarvis Scenes - Good dialogue clips"
    ]
    
    print("\nSearch YouTube for:")
    for video in videos:
        print(f"   • {video}")
    
    print("\n🥈 METHOD 2: Movie Scene Rips")
    print("✅ Highest audio quality")
    print("✅ Direct from source")
    
    print("\nSources:")
    print("   • Iron Man (2008) - First appearance scenes")
    print("   • Avengers (2012) - Helicarrier scenes") 
    print("   • Iron Man 2 (2010) - Lab scenes")
    
    print("\n🥉 METHOD 3: Existing Sound Packs")
    print("✅ Pre-extracted clips")
    print("✅ Ready to use")
    
    print("\nSearch for:")
    print("   • 'Jarvis sound pack download'")
    print("   • 'Iron Man Jarvis voice lines'")
    print("   • Game mod sound files")

def create_target_phrases():
    """Show exactly what phrases to collect"""
    
    target_phrases = [
        {
            "phrase": "Good morning, sir",
            "context": "Lab/workshop greeting",
            "duration": "2-3 seconds",
            "priority": "Essential"
        },
        {
            "phrase": "At your service, sir", 
            "context": "Response to Tony",
            "duration": "2-3 seconds",
            "priority": "Essential"
        },
        {
            "phrase": "All systems online",
            "context": "Status report",
            "duration": "2-3 seconds", 
            "priority": "Essential"
        },
        {
            "phrase": "Right away, sir",
            "context": "Acknowledgment",
            "duration": "2-3 seconds",
            "priority": "Good to have"
        },
        {
            "phrase": "Shall I render using the Mark",
            "context": "Longer phrase for variety",
            "duration": "3-4 seconds",
            "priority": "Good to have"
        }
    ]
    
    print("\n🎯 TARGET PHRASES FOR VOICE CLONING")
    print("=" * 60)
    
    for i, phrase in enumerate(target_phrases, 1):
        print(f"\n{i}. \"{phrase['phrase']}\"")
        print(f"   Context: {phrase['context']}")
        print(f"   Length: {phrase['duration']}")
        print(f"   Priority: {phrase['priority']}")
    
    print("\n💡 QUALITY REQUIREMENTS:")
    print("✅ Clear Paul Bettany voice (no Tony Stark talking over)")
    print("✅ Minimal background music/sound effects")
    print("✅ 22kHz WAV format (use Audacity to convert)")
    print("✅ 2-10 seconds each")
    print("✅ Natural speech pace (not slowed/sped up)")

def show_audio_editing_guide():
    """Guide for cleaning up audio clips"""
    
    print("\n🎛️ AUDIO EDITING WITH AUDACITY (FREE)")
    print("=" * 60)
    
    steps = [
        "Download Audacity (audacityteam.org)",
        "Import your downloaded audio file", 
        "Find clean Jarvis dialogue sections",
        "Select 2-10 second clips with just his voice",
        "Effect → Noise Reduction (if needed)",
        "Effect → Normalize (to standardize volume)",
        "Export each clip as WAV file",
        "Name them: jarvis1.wav, jarvis2.wav, etc."
    ]
    
    for i, step in enumerate(steps, 1):
        print(f"{i}. {step}")
    
    print("\n⚠️ AVOID:")
    print("❌ Clips with Tony Stark talking over Jarvis")
    print("❌ Heavy background music or explosions")
    print("❌ Processed/filtered audio")
    print("❌ Clips longer than 10 seconds")

def show_cloning_workflow():
    """Complete workflow from clips to working voice"""
    
    print("\n🧬 VOICE CLONING WORKFLOW")
    print("=" * 60)
    
    print("1️⃣ **Collect Audio** (15-30 minutes)")
    print("   • Download YouTube compilation")
    print("   • Extract 3-5 clean Jarvis phrases")
    print("   • Save as WAV files")
    
    print("\n2️⃣ **ElevenLabs Setup** (5 minutes)")
    print("   • Sign up at elevenlabs.io")
    print("   • Get free API key")
    print("   • Upload audio clips for voice cloning")
    
    print("\n3️⃣ **Test Clone** (2 minutes)")
    print("   • Generate test phrase")
    print("   • Adjust settings if needed")
    print("   • Save voice ID")
    
    print("\n4️⃣ **Integration** (Already done!)")
    print("   ✅ Scripts ready")
    print("   ✅ Daily briefing integration")
    print("   ✅ Drone alerts with Jarvis voice")
    
    print("\n🎉 **Result: Real Paul Bettany speaking your daily briefings!**")

if __name__ == "__main__":
    show_collection_methods()
    create_target_phrases() 
    show_audio_editing_guide()
    show_cloning_workflow()
    
    print("\n🚀 QUICK START:")
    print("1. Search YouTube: 'Iron Man Jarvis best moments'")
    print("2. Use yt-dlp to download audio")
    print("3. Extract 3-5 clips with Audacity") 
    print("4. Upload to ElevenLabs for cloning")
    print("5. Get authentic Jarvis voice!")