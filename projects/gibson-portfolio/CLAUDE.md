# Photography Portfolio Website

## Project Overview
A photography portfolio website for Matthew Gibson. Features a splash screen intro, about section, and gallery cards that link to Adobe Lightroom galleries.

## Tech Stack
- Plain HTML5, CSS3, JavaScript (ES6+)
- GSAP for animations (loaded via CDN)
- Adobe Lightroom for photo galleries (external links)

## Project Structure
```
/
├── index.html          # Main homepage
├── css/
│   └── style.css       # Main stylesheet
├── js/
│   └── main.js         # JavaScript and animations
├── assets/
│   ├── images/         # Gallery preview images
│   └── svg/            # SVG graphics
└── CLAUDE.md           # This file
```

## How the Gallery System Works
- Gallery cards on homepage open a fullscreen lightbox
- Images hosted on Cloudinary (cloud name: deihjpq8s)
- Lightbox supports: arrow keys, click navigation, escape to close
- Auto-optimization: WebP format, smart quality compression

### To add images to a gallery:
1. Export photos from Lightroom (File > Export)
2. Upload to Cloudinary Media Library in a folder (e.g., "sorrento")
3. Update the array in js/main.js to include all filenames

### To add a new gallery:
1. Create folder in Cloudinary Media Library
2. Upload images (any names work)
3. Add entry in js/main.js galleries object using cloudImg() helper
4. Add gallery-card in index.html with Cloudinary URL for preview

### Cloudinary URL format:
- Full size: https://res.cloudinary.com/deihjpq8s/image/upload/f_auto,q_auto/FOLDER/FILENAME
- Thumbnail: https://res.cloudinary.com/deihjpq8s/image/upload/f_auto,q_auto,w_600/FOLDER/FILENAME

## Current Design
- Dark theme (--color-bg: #0a0a0a)
- Purple accent (--color-accent: #6366f1)
- Splash screen on first load
- Gallery cards with hover zoom effect

## Sections
- Splash screen (Welcome message)
- Hero (Name + tagline)
- About
- Galleries (linked to Lightroom)
- Contact

## Development
- Open index.html directly in browser for development
- No build step required
