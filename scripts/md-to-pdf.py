#!/usr/bin/env python3
"""Convert markdown to professional PDF using WeasyPrint"""

import markdown
from weasyprint import HTML, CSS
import sys
import os

CSS_STYLE = """
@page {
    margin: 1in;
    @bottom-center {
        content: "Page " counter(page) " of " counter(pages);
        font-size: 10px;
        color: #666;
    }
}

body {
    font-family: 'Helvetica Neue', Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #333;
    max-width: 100%;
}

h1 {
    color: #1a365d;
    border-bottom: 3px solid #2b6cb0;
    padding-bottom: 10px;
    font-size: 24pt;
    margin-top: 0;
}

h2 {
    color: #2c5282;
    border-bottom: 1px solid #bee3f8;
    padding-bottom: 5px;
    font-size: 16pt;
    margin-top: 25px;
}

h3 {
    color: #2d3748;
    font-size: 13pt;
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
    font-size: 10pt;
}

th {
    background-color: #2b6cb0;
    color: white;
    padding: 10px;
    text-align: left;
    font-weight: bold;
}

td {
    padding: 8px 10px;
    border-bottom: 1px solid #e2e8f0;
}

tr:nth-child(even) {
    background-color: #f7fafc;
}

code {
    background-color: #edf2f7;
    padding: 2px 6px;
    border-radius: 3px;
    font-family: 'Courier New', monospace;
    font-size: 10pt;
}

pre {
    background-color: #2d3748;
    color: #e2e8f0;
    padding: 15px;
    border-radius: 5px;
    overflow-x: auto;
    font-size: 9pt;
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
    margin: 5px 0;
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
    margin: 30px 0;
}

a {
    color: #2b6cb0;
    text-decoration: none;
}

.emoji {
    font-size: 14pt;
}
"""

def md_to_pdf(input_file, output_file, title=None):
    """Convert markdown file to PDF"""
    
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
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """
    
    # Convert to PDF
    html = HTML(string=full_html)
    css = CSS(string=CSS_STYLE)
    html.write_pdf(output_file, stylesheets=[css])
    
    print(f"✅ Created: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 md-to-pdf.py input.md output.pdf [title]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    title = sys.argv[3] if len(sys.argv) > 3 else None
    
    md_to_pdf(input_file, output_file, title)
