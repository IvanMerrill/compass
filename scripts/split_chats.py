#!/usr/bin/env python3
"""
Split extracted chat files into smaller chunks for reading.
"""

from pathlib import Path

def split_file(input_file, output_dir, max_lines=200):
    """Split a file into chunks of max_lines each."""
    output_dir.mkdir(exist_ok=True)

    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    total_lines = len(lines)
    num_parts = (total_lines + max_lines - 1) // max_lines  # Ceiling division

    base_name = input_file.stem

    for i in range(num_parts):
        start = i * max_lines
        end = min((i + 1) * max_lines, total_lines)

        chunk_lines = lines[start:end]

        output_file = output_dir / f"{base_name}_part{i+1:02d}.txt"

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# Part {i+1}/{num_parts}\n")
            f.write(f"# Lines {start+1}-{end} of {total_lines}\n\n")
            f.writelines(chunk_lines)

        print(f"  Created {output_file.name} ({len(chunk_lines)} lines)")

    return num_parts

def main():
    extracted_dir = Path('/Users/ivanmerrill/compass/chats_extracted')
    split_dir = Path('/Users/ivanmerrill/compass/chats_split')
    split_dir.mkdir(exist_ok=True)

    txt_files = sorted(extracted_dir.glob('*.txt'))

    print(f"Found {len(txt_files)} extracted chat files\n")

    for txt_file in txt_files:
        print(f"Splitting: {txt_file.name}")

        file_output_dir = split_dir / txt_file.stem
        num_parts = split_file(txt_file, file_output_dir)

        print(f"  Total: {num_parts} parts\n")

if __name__ == '__main__':
    main()
