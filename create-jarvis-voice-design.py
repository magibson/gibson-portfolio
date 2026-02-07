#!/usr/bin/env python3
"""
Create Custom Jarvis Voice using ElevenLabs Voice Design
Legal, high-quality alternative to voice cloning
"""

import requests
import json

def create_jarvis_voice_design():
    """Create Jarvis voice using text description"""
    
    # Perfect Jarvis voice description
    voice_description = """
A sophisticated British male AI assistant with a deep, warm, and authoritative tone. 
Professional yet approachable, like an intelligent butler or high-tech personal assistant. 
Clear articulation, measured pace, with the confidence of advanced artificial intelligence. 
Think sophisticated computer system with human warmth and British refinement.
"""
    
    print("🎨 CREATING CUSTOM JARVIS VOICE")
    print("=" * 50)
    print(f"Description: {voice_description.strip()}")
    
    # This would call ElevenLabs Voice Design API
    print("\n🔧 Process:")
    print("1. Get ElevenLabs API key (free signup)")
    print("2. Use Voice Design feature")
    print("3. Input description above")
    print("4. Generate test samples")
    print("5. Refine until perfect")
    
    return voice_description

def test_with_existing_voices():
    """Test with pre-existing British voices first"""
    
    test_phrases = [
        "Good morning, Mr. Gibson. All systems are operational.",
        "Drone flying conditions are optimal today, sir.",
        "Your daily briefing is ready. Shall I proceed?",
        "Weather analysis complete. Cold temperatures detected.",
        "At your service, sir. How may I assist you today?"
    ]
    
    print("\n🎭 BRITISH VOICES TO TEST:")
    print("=" * 40)
    print("1. **Brian** - Professional, clear British male")
    print("2. **Daniel** - Deep, authoritative British")
    print("3. **Callum** - Sophisticated, refined")
    print("4. **Charlie** - Warm British gentleman")
    
    print(f"\n📝 Test phrases:")
    for i, phrase in enumerate(test_phrases, 1):
        print(f"{i}. {phrase}")
    
    return test_phrases

def calculate_usage_cost():
    """Calculate actual cost for Matt's usage"""
    
    daily_usage = {
        "morning_briefing": 300,    # characters
        "drone_alerts": 150,        # 2-3 per day
        "status_updates": 100,      # 2-3 per day  
        "responses": 200            # occasional
    }
    
    daily_total = sum(daily_usage.values())  # ~750 chars/day
    monthly_total = daily_total * 30        # ~22,500 chars/month
    
    print("\n💰 ACTUAL COST CALCULATION")
    print("=" * 40)
    print("Your estimated usage:")
    for item, chars in daily_usage.items():
        print(f"  {item.replace('_', ' ').title()}: {chars} chars/day")
    
    print(f"\nTotal: {daily_total} characters/day")
    print(f"Monthly: {monthly_total:,} characters")
    
    print(f"\nElevenLabs Starter Plan:")
    print(f"  Cost: $5/month")  
    print(f"  Includes: 30,000 characters")
    print(f"  Your usage: {monthly_total:,} characters") 
    print(f"  Remaining: {30000 - monthly_total:,} characters")
    
    cost_per_day = 5 / 30  # $0.17/day
    print(f"\n🎯 Daily cost: ${cost_per_day:.2f}")
    print("   Less than a candy bar!")
    
    return monthly_total

if __name__ == "__main__":
    
    print("🤖 CUSTOM JARVIS VOICE CREATION")
    print("=" * 50)
    
    # Show voice design approach
    description = create_jarvis_voice_design()
    
    # Show testing options
    test_phrases = test_with_existing_voices()
    
    # Calculate real costs
    monthly_chars = calculate_usage_cost()
    
    print(f"\n🚀 QUICK START STEPS:")
    print("1. Sign up: https://elevenlabs.io (free)")
    print("2. Get API key from profile settings")
    print("3. Run: python3 setup-elevenlabs-jarvis.py")
    print("4. Test Brian voice first")
    print("5. Create custom voice if needed")
    
    print(f"\n✨ RESULT: Professional Jarvis voice for $5/month")
    print(f"   ({monthly_chars:,} chars fits easily in Starter plan)")