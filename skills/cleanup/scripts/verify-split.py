#!/usr/bin/env python3
"""Split verification: all original lines must be present across output files in a directory."""
import sys
import os
import re


def normalize(line):
    """Normalize for fuzzy matching: lowercase, collapse whitespace, strip markers."""
    s = line.strip().lower()
    s = re.sub(r'\[([^\]]*)\]\([^\)]*\)', r'\1', s)
    s = re.sub(r'https?://\S+', '', s)
    s = re.sub(r'^[-*>\d.)\]#]+\s*', '', s)
    s = re.sub(r'^\[[ x]\]\s*', '', s)
    s = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', s)
    s = re.sub(r'_{1,2}([^_]+)_{1,2}', r'\1', s)
    s = re.sub(r'`([^`]+)`', r'\1', s)
    s = re.sub(r'<[^>]+>', ' ', s)
    s = re.sub(r'[;:—–]', ' ', s)
    s = re.sub(r'\s+', ' ', s)
    s = s.replace('ё', 'е')
    return s.strip()


def words_set(text):
    """Extract significant words (3+ chars)."""
    return set(re.findall(r'[a-zA-Zа-яА-ЯёЁ0-9]{3,}', text.lower().replace('ё', 'е')))


def extract_urls(text):
    return set(re.findall(r'https?://[^\s\)>\]]+', text))


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <original> <output-dir>")
        sys.exit(2)

    original_path = sys.argv[1]
    output_dir = sys.argv[2]

    if not os.path.isfile(original_path):
        print(f"❌ Original file not found: {original_path}")
        sys.exit(2)
    if not os.path.isdir(output_dir):
        print(f"❌ Output directory not found: {output_dir}")
        sys.exit(2)

    # Read original
    with open(original_path) as f:
        original_lines = [l.rstrip() for l in f if l.strip()]

    # Concatenate all .md files in output dir
    combined_text = ""
    file_count = 0
    for fname in sorted(os.listdir(output_dir)):
        if fname.endswith('.md'):
            fpath = os.path.join(output_dir, fname)
            with open(fpath) as f:
                combined_text += f.read() + "\n"
            file_count += 1

    if file_count == 0:
        print(f"❌ No .md files found in {output_dir}")
        sys.exit(1)

    combined_norm = normalize(combined_text)
    combined_urls = extract_urls(combined_text)
    combined_words = words_set(combined_text)

    uncovered = []
    for line in original_lines:
        if line.startswith('## ') or line.startswith('### ') or line.startswith('####'):
            continue
        if line.strip().startswith('```'):
            continue
        if len(line.strip()) < 5:
            continue

        norm = normalize(line)
        if len(norm) < 4:
            continue

        # URL check
        line_urls = extract_urls(line)
        if line_urls and all(url in combined_urls for url in line_urls):
            continue

        # Normalized substring match
        if norm in combined_norm:
            continue

        # Prefix match
        if len(norm) >= 20 and norm[:40] in combined_norm:
            continue

        # Word overlap
        line_words = words_set(line)
        if len(line_words) >= 3:
            overlap = line_words & combined_words
            ratio = len(overlap) / len(line_words)
            threshold = 0.65 if len(line.strip()) < 50 else 0.5
            if ratio >= threshold:
                continue

        uncovered.append(line)

    if not uncovered:
        print(f"✅ SPLIT VERIFIED: all {len(original_lines)} original lines found across {file_count} files")
        sys.exit(0)
    else:
        print(f"⚠️  UNCOVERED: {len(uncovered)} lines not found in split files ({file_count} files checked)")
        for line in uncovered[:20]:
            print(f"  «{line[:120]}»")
        if len(uncovered) > 20:
            print(f"  ... and {len(uncovered) - 20} more")
        sys.exit(1)


if __name__ == "__main__":
    main()
