#!/usr/bin/env python3
"""
Drone Flying Conditions Checker for Matt's Photography
Evaluates weather for optimal drone shooting conditions
"""

import subprocess
import sys
import re
from datetime import datetime

def get_weather_data(location="Highlands,NJ"):
    """Get comprehensive weather data for drone flying assessment"""
    try:
        # Get detailed forecast
        result = subprocess.run([
            'curl', '-s', f'wttr.in/{location}?T'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            return None
            
        return result.stdout
    except Exception as e:
        print(f"Error fetching weather: {e}")
        return None

def parse_current_conditions(weather_text):
    """Extract current weather conditions for drone assessment"""
    if not weather_text:
        return None
    
    lines = weather_text.split('\n')
    
    # Extract current conditions (usually in first few lines)
    current_temp = None
    current_wind = None
    visibility = None
    condition = None
    
    # Look for current weather in the header
    for line in lines[:10]:
        # Temperature pattern: "17(5) °F"
        temp_match = re.search(r'(\d+)\(\d+\)\s*°F', line)
        if temp_match:
            current_temp = int(temp_match.group(1))
        
        # Wind pattern: "↗ 11 mph" 
        wind_match = re.search(r'[\↑↗→↘↓↙←↖]\s*(\d+)\s*mph', line)
        if wind_match:
            current_wind = int(wind_match.group(1))
        
        # Visibility pattern: "9 mi"
        vis_match = re.search(r'(\d+)\s*mi', line)
        if vis_match:
            visibility = int(vis_match.group(1))
        
        # Weather condition
        if 'Sunny' in line:
            condition = 'Sunny'
        elif 'Clear' in line:
            condition = 'Clear'  
        elif 'Overcast' in line:
            condition = 'Overcast'
        elif 'Rain' in line or 'Drizzle' in line:
            condition = 'Rain'
        elif 'Snow' in line:
            condition = 'Snow'
        elif 'Fog' in line:
            condition = 'Fog'
    
    return {
        'temperature': current_temp,
        'wind_mph': current_wind,
        'visibility_mi': visibility,
        'condition': condition
    }

def assess_flying_conditions(conditions, drone_model="DJI Mini 4 Pro"):
    """Evaluate if conditions are good for drone flying (optimized for DJI Mini 4 Pro)"""
    if not conditions:
        return {"status": "unknown", "score": 0, "issues": ["Weather data unavailable"]}
    
    score = 100
    issues = []
    warnings = []
    
    # Wind assessment for DJI Mini 4 Pro (max wind resistance ~24 mph)
    wind = conditions.get('wind_mph', 0)
    if wind >= 20:
        score -= 50
        issues.append(f"High winds ({wind} mph) - exceeds Mini 4 Pro safe limits")
    elif wind >= 15:
        score -= 30
        issues.append(f"Strong winds ({wind} mph) - challenging for Mini 4 Pro")
    elif wind >= 10:
        score -= 15
        warnings.append(f"Moderate winds ({wind} mph) - manageable but use Sport mode")
    elif wind >= 5:
        score -= 5
        warnings.append(f"Light winds ({wind} mph) - good conditions")
    else:
        warnings.append(f"Calm winds ({wind} mph) - perfect for video/landscapes")
    
    # Temperature assessment for DJI Mini 4 Pro (14°F to 104°F operating range)
    temp = conditions.get('temperature')
    if temp is not None:
        if temp < 14:
            score -= 40
            issues.append(f"Below operating temp ({temp}°F) - unsafe for Mini 4 Pro")
        elif temp < 25:
            score -= 25
            issues.append(f"Very cold ({temp}°F) - severely reduced battery, warm batteries first")
        elif temp < 35:
            score -= 15
            warnings.append(f"Cold ({temp}°F) - expect 30-40% less flight time")
        elif temp > 100:
            score -= 20
            warnings.append(f"Very hot ({temp}°F) - overheating risk, shorter flights")
        elif temp > 85:
            score -= 10
            warnings.append(f"Hot ({temp}°F) - monitor battery temps")
    
    # Visibility assessment
    visibility = conditions.get('visibility_mi', 0)
    if visibility < 3:
        score -= 30
        issues.append(f"Poor visibility ({visibility} mi) - unsafe for VLOS")
    elif visibility < 5:
        score -= 15
        warnings.append(f"Reduced visibility ({visibility} mi) - stay close")
    
    # Weather condition assessment
    condition = conditions.get('condition', 'Unknown')
    if condition in ['Rain', 'Snow', 'Drizzle']:
        score -= 50
        issues.append(f"{condition} - no flying (moisture risk)")
    elif condition == 'Fog':
        score -= 40
        issues.append("Fog - dangerous visibility")
    elif condition == 'Overcast':
        score -= 5
        warnings.append("Overcast - reduced light for photography")
    
    # Determine overall status
    if score >= 80:
        status = "excellent"
        emoji = "🟢"
    elif score >= 60:
        status = "good" 
        emoji = "🟡"
    elif score >= 40:
        status = "marginal"
        emoji = "🟠"
    else:
        status = "poor"
        emoji = "🔴"
    
    return {
        "status": status,
        "emoji": emoji,
        "score": max(0, score),
        "issues": issues,
        "warnings": warnings,
        "raw_conditions": conditions
    }

def get_photography_insights(conditions, assessment):
    """Provide specific insights for landscape/video photography with Mini 4 Pro"""
    insights = []
    
    condition = conditions.get('condition', 'Unknown')
    wind = conditions.get('wind_mph', 0)
    temp = conditions.get('temperature')
    
    # Lighting insights for landscapes
    if condition == 'Sunny':
        insights.append("🌅 Perfect for golden hour landscapes - plan 1hr before sunset")
        insights.append("☀️ Use ND filters for smooth water/cloud motion at Hartshorne")
    elif condition == 'Overcast':
        insights.append("☁️ Even lighting - great for waterfall shots & forest scenes")
        insights.append("🎬 Ideal for cinematic video - no harsh shadows")
    elif condition == 'Clear':
        insights.append("🌟 Crystal clear - perfect for sunrise/sunset timelapses")
    
    # Video-specific insights
    if wind <= 5:
        insights.append("🎬 Perfect for smooth video pans & orbits")
        insights.append("📹 Ideal for hyperlapse & long tracking shots")
    elif wind <= 10:
        insights.append("🎥 Good for standard video - use Normal mode for stability")
    elif wind <= 15:
        insights.append("⚠️ Video: Use Sport mode, avoid slow movements")
    else:
        insights.append("🌪️ Video challenging - stick to quick dynamic shots")
    
    # Temperature & battery insights
    if temp and temp < 35:
        insights.append("🔋 Cold weather: Bring 3-4 batteries, keep spares warm")
        insights.append("⏱️ Plan shorter flights (12-15min vs normal 20min)")
    elif temp and temp > 85:
        insights.append("🌡️ Hot weather: Land if overheat warning appears")
    
    # Location-specific suggestions
    if assessment['status'] in ['excellent', 'good']:
        insights.append("📍 Great day for: Hartshorne Park coastal shots or Red Bank riverside")
    
    return insights

def get_favorite_locations_forecast():
    """Check conditions at Matt's favorite drone spots"""
    locations = {
        "Hartshorne Park": "Hartshorne+Park,Highlands,NJ",
        "Red Bank": "Red+Bank,NJ", 
        "Home (Newark)": "Newark,NJ"
    }
    
    results = {}
    
    for name, location in locations.items():
        weather_text = get_weather_data(location)
        conditions = parse_current_conditions(weather_text)
        assessment = assess_flying_conditions(conditions)
        
        results[name] = {
            'conditions': conditions,
            'assessment': assessment
        }
    
    return results

def get_best_flying_time():
    """Analyze when conditions will be best for flying today"""
    # Get Newark forecast for timing analysis
    weather_text = get_weather_data("Newark,NJ")
    if not weather_text:
        return "Unable to get forecast data"
    
    lines = weather_text.split('\n')
    
    # Look for today's hourly breakdown
    best_time = "Unknown"
    best_score = 0
    
    # Parse morning/noon/evening from forecast
    time_periods = []
    
    for line in lines:
        if 'Morning' in line or 'Noon' in line or 'Evening' in line:
            # This is a simplified analysis - in practice we'd parse the structured forecast
            if 'Sunny' in line and '5-8 mph' in line:
                best_time = "Morning (6-10 AM) and Evening (6-8 PM)"
                break
            elif 'Clear' in line:
                best_time = "Evening (golden hour)"
                break
            elif wind_in_line := re.search(r'(\d+)-\d+\s*mph', line):
                wind = int(wind_in_line.group(1))
                if wind < 10:
                    if 'Morning' in line:
                        best_time = "Morning (8-11 AM)"
                    elif 'Noon' in line:
                        best_time = "Midday (11 AM - 2 PM)"
                    else:
                        best_time = "Evening (4-7 PM)"
    
    return best_time

def print_flying_report(location="Newark,NJ"):
    """Generate comprehensive flying conditions report"""
    print(f"🚁 **DRONE FLYING CONDITIONS - {location.upper()}**")
    print("=" * 50)
    
    # Get weather data
    weather_text = get_weather_data(location)
    if not weather_text:
        print("❌ Unable to get weather data")
        return
    
    # Parse current conditions
    conditions = parse_current_conditions(weather_text)
    if not conditions:
        print("❌ Unable to parse weather conditions")
        return
    
    # Assess flying conditions
    assessment = assess_flying_conditions(conditions, "DJI Mini 4 Pro")
    
    # Current conditions
    print(f"\n📊 **CURRENT CONDITIONS:**")
    print(f"• **Temperature:** {conditions.get('temperature', 'N/A')}°F")
    print(f"• **Wind:** {conditions.get('wind_mph', 'N/A')} mph")
    print(f"• **Visibility:** {conditions.get('visibility_mi', 'N/A')} miles") 
    print(f"• **Condition:** {conditions.get('condition', 'Unknown')}")
    
    # Flying assessment
    print(f"\n{assessment['emoji']} **FLYING STATUS: {assessment['status'].upper()}** ({assessment['score']}/100)")
    
    # Issues (red flags)
    if assessment['issues']:
        print(f"\n🚨 **SAFETY CONCERNS:**")
        for issue in assessment['issues']:
            print(f"• {issue}")
    
    # Warnings (cautions)
    if assessment['warnings']:
        print(f"\n⚠️ **CONSIDERATIONS:**")
        for warning in assessment['warnings']:
            print(f"• {warning}")
    
    # Photography insights
    insights = get_photography_insights(conditions, assessment)
    if insights:
        print(f"\n📸 **PHOTOGRAPHY INSIGHTS:**")
        for insight in insights:
            print(f"• {insight}")
    
    # Recommendation
    print(f"\n🎯 **RECOMMENDATION:**")
    if assessment['status'] == 'excellent':
        print("✈️ Perfect flying weather! Great time for important shoots.")
    elif assessment['status'] == 'good':
        print("👍 Good conditions for flying. Normal precautions apply.")
    elif assessment['status'] == 'marginal':
        print("⚠️ Challenging conditions. Only fly if experienced and necessary.")
    else:
        print("🛑 Not recommended for flying. Wait for better conditions.")
    
    # Next check suggestion
    print(f"\n💡 **Next check:** Run again in 2-4 hours for updated conditions")

def quick_check(location="Newark,NJ"):
    """Quick go/no-go assessment"""
    weather_text = get_weather_data(location)
    conditions = parse_current_conditions(weather_text)
    assessment = assess_flying_conditions(conditions, "DJI Mini 4 Pro")
    
    if assessment:
        status = assessment['status']
        emoji = assessment['emoji']
        wind = conditions.get('wind_mph', 'N/A')
        condition = conditions.get('condition', 'Unknown')
        
        print(f"{emoji} **{status.upper()}** - Wind: {wind}mph, {condition}")
        if assessment['issues']:
            print(f"⚠️ {assessment['issues'][0]}")

def daily_briefing_summary():
    """Generate brief drone summary for daily briefing"""
    weather_text = get_weather_data("Newark,NJ")
    conditions = parse_current_conditions(weather_text)
    assessment = assess_flying_conditions(conditions, "DJI Mini 4 Pro")
    best_time = get_best_flying_time()
    
    if not assessment:
        return "🚁 **Drone:** Weather data unavailable"
    
    emoji = assessment['emoji']
    status = assessment['status']
    wind = conditions.get('wind_mph', 'N/A')
    temp = conditions.get('temperature', 'N/A')
    
    # Keep it concise for daily briefing
    summary = f"🚁 **Drone:** {emoji} {status.title()} ({wind}mph wind, {temp}°F)"
    
    if assessment['status'] in ['excellent', 'good']:
        summary += f" - Best time: {best_time}"
    elif assessment['issues']:
        # Show first major issue
        summary += f" - {assessment['issues'][0].split(' - ')[1] if ' - ' in assessment['issues'][0] else assessment['issues'][0]}"
    
    return summary

def weekend_forecast():
    """Generate weekend flying forecast (Thu-Sun)"""
    print("🚁 **WEEKEND FLYING FORECAST**")
    print("=" * 40)
    
    # Check favorite locations for the weekend
    locations_forecast = get_favorite_locations_forecast()
    
    print(f"\n📍 **LOCATION COMPARISON:**")
    for location, data in locations_forecast.items():
        if data['assessment']:
            emoji = data['assessment']['emoji']
            status = data['assessment']['status']
            wind = data['conditions'].get('wind_mph', 'N/A') if data['conditions'] else 'N/A'
            print(f"• **{location}:** {emoji} {status.title()} ({wind}mph)")
    
    print(f"\n🎯 **WEEKEND PLANNING:**")
    print("• **Friday:** Good for scouting locations after work")
    print("• **Saturday-Sunday:** Prime time for landscape/video projects")
    print("• **Golden hours:** Best for cinematic shots at Hartshorne Park")
    print("• **Backup plan:** Red Bank riverside if coastal winds too strong")
    
    print(f"\n📋 **WHAT TO BRING:**")
    print("• Extra batteries (cold weather reduces flight time)")
    print("• ND filter set for smooth water/cloud motion")
    print("• Lens cloth (sea spray at Hartshorne)")
    print("• Backup memory cards for video projects")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("🚁 Drone Weather Checker for DJI Mini 4 Pro")
        print("Commands:")
        print("  python3 drone-weather.py check       # Full conditions report")
        print("  python3 drone-weather.py quick       # Quick go/no-go") 
        print("  python3 drone-weather.py briefing    # Daily briefing summary")
        print("  python3 drone-weather.py weekend     # Weekend forecast")
        print("  python3 drone-weather.py locations   # Check favorite spots")
        print("  python3 drone-weather.py hartshorne  # Hartshorne Park specific")
        print("  python3 drone-weather.py redbank     # Red Bank specific")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "check":
        print_flying_report()
    elif command == "quick":
        quick_check()
    elif command == "briefing":
        print(daily_briefing_summary())
    elif command == "weekend":
        weekend_forecast()
    elif command == "locations":
        locations_forecast = get_favorite_locations_forecast()
        print("📍 **FAVORITE LOCATIONS STATUS:**")
        for location, data in locations_forecast.items():
            if data['assessment']:
                emoji = data['assessment']['emoji']
                status = data['assessment']['status']
                wind = data['conditions'].get('wind_mph', 'N/A') if data['conditions'] else 'N/A'
                print(f"• **{location}:** {emoji} {status.title()} ({wind}mph)")
    elif command == "hartshorne":
        print_flying_report("Hartshorne+Park,Highlands,NJ")
    elif command == "redbank":
        print_flying_report("Red+Bank,NJ")
    else:
        print(f"Unknown command: {command}")