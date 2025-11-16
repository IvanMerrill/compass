#!/usr/bin/env python3
"""
Extract conversation text from saved Claude chat HTML files.
"""

import os
import re
from pathlib import Path
from html.parser import HTMLParser

class ConversationExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_conversation = False
        self.current_text = []
        self.conversation_parts = []
        self.current_tag = None

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag

    def handle_data(self, data):
        # Clean up the text
        text = data.strip()
        if text and len(text) > 10:  # Filter out very short snippets
            # Avoid JavaScript/CSS code
            if not any(x in text for x in ['function(', 'const ', 'var ', '.css', 'return', '{', '}', 'px', 'font-']):
                self.current_text.append(text)

    def get_text(self):
        # Remove duplicates while preserving order
        seen = set()
        unique_parts = []
        for part in self.current_text:
            if part not in seen and len(part) > 20:  # Only keep substantial text
                seen.add(part)
                unique_parts.append(part)
        return '\n\n'.join(unique_parts)

def extract_conversation(html_file):
    """Extract conversation text from HTML file."""
    try:
        with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()

        parser = ConversationExtractor()
        parser.feed(html_content)
        text = parser.get_text()

        # Clean up common web artifacts
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            # Skip common UI elements
            if line and not any(skip in line.lower() for skip in [
                'cookie', 'accept', 'privacy policy', 'terms of service',
                'sign in', 'sign up', 'log in', 'log out', 'subscribe',
                'loading', 'error', 'try again', 'click here'
            ]):
                lines.append(line)

        return '\n'.join(lines)

    except Exception as e:
        return f"Error extracting {html_file}: {e}"

def main():
    chats_dir = Path('/Users/ivanmerrill/compass/chats')
    output_dir = Path('/Users/ivanmerrill/compass/chats_extracted')
    output_dir.mkdir(exist_ok=True)

    # Find all HTML files
    html_files = list(chats_dir.glob('*.html'))

    print(f"Found {len(html_files)} HTML chat files")

    for html_file in html_files:
        print(f"\nProcessing: {html_file.name}")

        # Extract conversation
        text = extract_conversation(html_file)

        # Save to text file
        output_file = output_dir / f"{html_file.stem}.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# {html_file.stem}\n\n")
            f.write(text)

        print(f"  Saved to: {output_file.name} ({len(text)} chars)")

if __name__ == '__main__':
    main()
