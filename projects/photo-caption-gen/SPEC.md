# Photo Caption & Hashtag Generator — Spec

## Purpose
AI-powered Instagram caption + hashtag generator for @mattgibsonpics.
Matt has 5 years of photo backlog and struggles to write captions consistently.
This removes that friction — describe the photo, get captions ready to copy.

## Tech Stack
- Python Flask, single file (app.py)
- SQLite for history
- Gemini API for generation (REST, no SDK needed)
  - GEMINI_API_KEY = 'AIzaSyCcuSJULuk7MFemZtUrzS0x0WtEJGR2IGM'
  - URL: https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}
- Port 8100
- Dark theme, mobile-first (matches other Jarvis tools: dark bg #0f1117, blue accent #3b82f6)

## Pages / Routes

### GET / — Caption Generator
Form fields:
- Photo description (textarea, required) — e.g. "Golden hour drone shot over Barnegat Lighthouse, NJ, warm orange sky"
- Location (text input, optional) — e.g. "Barnegat Light, NJ"
- Mood/Vibe (select): Peaceful, Epic, Nostalgic, Adventurous, Minimal, Moody
- Photo Type (select): Landscape, Drone/Aerial, Cityscape, Portrait, Architecture, Seascape, Travel, Wildlife, Abstract
- Tone (select): Storytelling (personal, narrative), Minimal (1-2 lines), Question (engage followers), Factual (teach something), Poetic (lyrical)
- Include location tag? (checkbox, default true)
- Include call-to-action? (checkbox, default true) — "Drop a 🔥 below", "Save this one", etc.

Submit → POST /generate → returns JSON with captions + hashtags

### POST /generate
Calls Gemini API with a well-crafted prompt.
Returns JSON:
```json
{
  "captions": [
    {"style": "Storytelling", "text": "..."},
    {"style": "Minimal", "text": "..."},
    {"style": "Question", "text": "..."},
    {"style": "Factual", "text": "..."},
    {"style": "Poetic", "text": "..."}
  ],
  "hashtags": {
    "niche": ["#barnegatlighthouse", "#njdrone", "#jerseyshore"],
    "mid": ["#aerialphotography", "#goldenhourlighting", "#lighthouse"],
    "large": ["#photography", "#drone", "#explore"]
  },
  "hashtag_string": "#barnegatlighthouse #njdrone ... (30 total)"
}
```

Also saves to SQLite history table.

### GET /history
List of last 20 generated sets with copy buttons.
Shows: date, description snippet, 1 caption preview, copy all button.

### POST /save-to-calendar
Saves a selected caption + hashtags to the content calendar DB
at ~/clawd/projects/content-calendar/content.db
Table: posts (date TEXT, caption TEXT, hashtags TEXT, type TEXT, status TEXT)
If DB doesn't exist or table mismatch, just skip gracefully (show success-ish message).

## Gemini Prompt Template

System: "You are a social media expert specializing in photography Instagram accounts. You write authentic, engaging captions that feel human — not corporate. The account is @mattgibsonpics, a landscape and drone photographer based in New Jersey."

User prompt:
```
Generate 5 Instagram captions for this photo:
- Description: {description}
- Location: {location}
- Mood: {mood}
- Type: {photo_type}
- Include location tag: {include_location}
- Include CTA: {include_cta}

Return EXACTLY this JSON format (no markdown, no extra text):
{
  "captions": [
    {"style": "Storytelling", "text": "caption here"},
    {"style": "Minimal", "text": "caption here"},
    {"style": "Question", "text": "caption here"},
    {"style": "Factual", "text": "caption here"},
    {"style": "Poetic", "text": "caption here"}
  ],
  "hashtags": {
    "niche": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5", "#tag6", "#tag7", "#tag8", "#tag9", "#tag10"],
    "mid": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5", "#tag6", "#tag7", "#tag8", "#tag9", "#tag10"],
    "large": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5", "#tag6", "#tag7", "#tag8", "#tag9", "#tag10"]
  }
}

Rules:
- Captions should sound like a real person, not a brand
- Niche hashtags: 1K-50K posts (very specific to location/style)
- Mid hashtags: 50K-500K posts (photography genre specific)
- Large hashtags: 500K+ posts (broad photography community)
- Storytelling: 3-5 sentences, personal narrative
- Minimal: 1-10 words max, punchy
- Question: ends with a question to drive comments
- Factual: interesting fact about the location/subject
- Poetic: lyrical, metaphorical, 2-4 lines
- If location provided, weave it in naturally
- If include_cta=true, add a natural CTA at end of storytelling and question styles
```

## UI Layout (mobile-first)

Header: "📸 Caption Generator" | @mattgibsonpics

Tabs: [Generator] [History]

### Generator Tab
- Big textarea: "Describe your photo..."
- Row: [Location input] [Photo Type dropdown]
- Row: [Mood dropdown] [Tone (optional, default all 5)]
- Row: [📍 Include location] [📢 Add CTA]
- Big blue "Generate Captions" button

Results section (appears after generation):
- 5 caption cards, each with:
  - Style badge (Storytelling/Minimal/etc.)
  - Caption text
  - 📋 Copy button
  - ✅ Save to Calendar button (triggers date picker modal)
- Hashtag section:
  - 3 colored tag clouds: Niche (purple), Mid (blue), Large (gray)
  - "📋 Copy All 30 Hashtags" button
  - "📋 Copy Caption + Hashtags" (picks first caption + all hashtags)

### History Tab
- Cards showing past generations
- Date, photo description snippet
- All 5 captions collapsible
- Copy buttons

## SQLite Schema
```sql
CREATE TABLE history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  description TEXT,
  location TEXT,
  mood TEXT,
  photo_type TEXT,
  response_json TEXT
);
```

## Notes
- No auth needed (local tool)
- Handle Gemini errors gracefully (show error card with retry button)
- JSON parse errors from Gemini: try to extract JSON from response, fallback to error state
- Copy buttons use navigator.clipboard.writeText() with fallback
- Keep it fast — show loading spinner on generate
- DB path: ~/clawd/projects/photo-caption-gen/captions.db
