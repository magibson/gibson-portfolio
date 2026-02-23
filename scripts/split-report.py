#!/usr/bin/env python3
"""Split the Carter report into sections"""

import re
import os

INPUT_FILE = "/Users/jarvis/clawd/carter-gibson-job-search-strategy.md"
OUTPUT_DIR = "/Users/jarvis/clawd/carter-report-pdfs"

# Define sections to extract
SECTIONS = [
    {
        "filename": "01-Executive-Summary.md",
        "title": "# Carter Gibson | Executive Summary\n## Job Search Strategy for Mechanical Engineering Graduate\n\n*Prepared by Jarvis | January 2026*\n\n---\n",
        "start": "## Executive Summary",
        "end": "## 🔱 Navy NUPOC"
    },
    {
        "filename": "02-Navy-NUPOC-Complete-Guide.md",
        "title": "# Navy NUPOC Program\n## Complete Guide for Carter Gibson\n\n*Nuclear Propulsion Officer Candidate Program*\n\n---\n",
        "start": "## 🔱 Navy NUPOC Program",
        "end": "## What Makes Carter Stand Out"
    },
    {
        "filename": "03-Strengths-and-Market-Outlook.md",
        "title": "# Carter's Strengths & Market Outlook\n## What Makes You Stand Out + Salary Expectations\n\n---\n",
        "start": "## What Makes Carter Stand Out",
        "end": "## Top 15 Target Companies"
    },
    {
        "filename": "04-Target-Companies.md",
        "title": "# Top 15 Target Companies\n## Ranked by Fit for Carter Gibson\n\n---\n",
        "start": "## Top 15 Target Companies",
        "end": "## Job Titles to Search"
    },
    {
        "filename": "05-Job-Titles-and-Action-Plan.md",
        "title": "# Job Titles & Action Plan\n## What to Search For + Week-by-Week Timeline\n\n---\n",
        "start": "## Job Titles to Search",
        "end": "## Resume Optimization"
    },
    {
        "filename": "06-Resume-and-LinkedIn.md",
        "title": "# Resume & LinkedIn Optimization\n## How to Present Yourself\n\n---\n",
        "start": "## Resume Optimization",
        "end": "## Networking Strategy"
    },
    {
        "filename": "07-Networking-and-Resources.md",
        "title": "# Networking Strategy & Resources\n## How to Connect + Job Boards\n\n---\n",
        "start": "## Networking Strategy",
        "end": "## Interview Preparation"
    },
    {
        "filename": "08-Interview-Prep.md",
        "title": "# Interview Preparation\n## Technical & Behavioral Questions\n\n---\n",
        "start": "## Interview Preparation",
        "end": "## Navy vs Civilian"
    },
    {
        "filename": "09-Decision-Framework.md",
        "title": "# Navy vs Civilian: Decision Framework\n## Making the Right Choice\n\n---\n",
        "start": "## Navy vs Civilian",
        "end": "## Final Thoughts"
    },
    {
        "filename": "10-Final-Thoughts.md",
        "title": "# Final Thoughts & Next Steps\n## Your Winning Narrative + Immediate Actions\n\n---\n",
        "start": "## Final Thoughts",
        "end": "## Appendix"
    }
]

def extract_sections():
    with open(INPUT_FILE, 'r') as f:
        content = f.read()
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    for section in SECTIONS:
        start_pattern = section["start"]
        end_pattern = section["end"]
        
        # Find start position
        start_match = re.search(re.escape(start_pattern), content)
        if not start_match:
            print(f"⚠️ Could not find start: {start_pattern}")
            continue
        
        start_pos = start_match.start()
        
        # Find end position
        if end_pattern:
            end_match = re.search(re.escape(end_pattern), content[start_pos + len(start_pattern):])
            if end_match:
                end_pos = start_pos + len(start_pattern) + end_match.start()
            else:
                end_pos = len(content)
        else:
            end_pos = len(content)
        
        # Extract section content
        section_content = content[start_pos:end_pos].strip()
        
        # Add title header
        full_content = section["title"] + section_content
        
        # Write to file
        output_path = os.path.join(OUTPUT_DIR, section["filename"])
        with open(output_path, 'w') as f:
            f.write(full_content)
        
        print(f"✅ Created: {section['filename']}")

if __name__ == "__main__":
    extract_sections()
    print("\n📁 All sections extracted to:", OUTPUT_DIR)
