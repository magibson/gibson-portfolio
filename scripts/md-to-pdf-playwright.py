#!/usr/bin/env python3
"""Convert markdown to professional PDF using Playwright"""

import markdown
from playwright.sync_api import sync_playwright
import sys
import os

CSS_STYLE = """
@page {
    margin: 0.75in;
}

body {
    font-family: 'Helvetica Neue', Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #333;
    max-width: 100%;
    padding: 20px;
}

h1 {
    color: #1a365d;
    border-bottom: 3px solid #2b6cb0;
    padding-bottom: 10px;
    font-size: 22pt;
    margin-top: 0;
}

h2 {
    color: #2c5282;
    border-bottom: 1px solid #bee3f8;
    padding-bottom: 5px;
    font-size: 15pt;
    margin-top: 25px;
}

h3 {
    color: #2d3748;
    font-size: 12pt;
    margin-top: 20px;
}

h4 {
    color: #4a5568;
    font-size: 11pt;
    margin-top: 15px;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 15px 0;
    font-size: 9pt;
}

th {
    background-color: #2b6cb0;
    color: white;
    padding: 8px;
    text-align: left;
    font-weight: bold;
}

td {
    padding: 6px 8px;
    border-bottom: 1px solid #e2e8f0;
}

tr:nth-child(even) {
    background-color: #f7fafc;
}

code {
    background-color: #edf2f7;
    padding: 2px 5px;
    border-radius: 3px;
    font-family: 'Courier New', monospace;
    font-size: 9pt;
}

pre {
    background-color: #2d3748;
    color: #e2e8f0;
    padding: 12px;
    border-radius: 5px;
    overflow-x: auto;
    font-size: 8pt;
}

pre code {
    background-color: transparent;
    padding: 0;
    color: inherit;
}

ul, ol {
    margin: 10px 0;
    padding-left: 25px;
}

li {
    margin: 4px 0;
}

blockquote {
    border-left: 4px solid #2b6cb0;
    margin: 15px 0;
    padding: 10px 20px;
    background-color: #ebf8ff;
    font-style: italic;
}

strong {
    color: #1a202c;
}

hr {
    border: none;
    border-top: 2px solid #e2e8f0;
    margin: 25px 0;
}

a {
    color: #2b6cb0;
    text-decoration: none;
}

.footer {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    text-align: center;
    font-size: 9pt;
    color: #666;
    padding: 10px;
}
"""

def md_to_pdf(input_file, output_file, title=None):
    """Convert markdown file to PDF using Playwright"""
    
    with open(input_file, 'r') as f:
        md_content = f.read()
    
    # Convert markdown to HTML
    html_content = markdown.markdown(
        md_content,
        extensions=['tables', 'fenced_code', 'toc']
    )
    
    # Wrap in full HTML document
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{title or 'Document'}</title>
        <style>{CSS_STYLE}</style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """
    
    # Write temp HTML file
    temp_html = '/tmp/temp_report.html'
    with open(temp_html, 'w') as f:
        f.write(full_html)
    
    # Convert to PDF using Playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(f'file://{temp_html}')
        page.pdf(path=output_file, format='Letter', margin={
            'top': '0.75in',
            'bottom': '0.75in', 
            'left': '0.75in',
            'right': '0.75in'
        }, print_background=True)
        browser.close()
    
    # Clean up
    os.remove(temp_html)
    
    print(f"✅ Created: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 md-to-pdf-playwright.py input.md output.pdf [title]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    title = sys.argv[3] if len(sys.argv) > 3 else None
    
    md_to_pdf(input_file, output_file, title)
