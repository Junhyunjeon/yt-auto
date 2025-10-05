#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Text Segmentation Utilities
Sentence splitting with abbreviation exceptions and pause type detection
"""

import re
from typing import List, Tuple

# Abbreviations that should NOT trigger sentence breaks
ABBREVIATIONS = {
    'e.g', 'i.e', 'Mr', 'Mrs', 'Ms', 'Dr', 'Prof', 'Sr', 'Jr',
    'vs', 'etc', 'No', 'Fig', 'Inc', 'Ltd', 'Co', 'Corp',
    'U.S', 'U.K', 'Ph.D', 'M.D', 'B.A', 'M.A', 'D.D.S',
    'Rev', 'Hon', 'Gen', 'Col', 'Capt', 'Lt', 'Sgt',
    'Ave', 'Blvd', 'St', 'Rd', 'Jan', 'Feb', 'Mar', 'Apr',
    'Jun', 'Jul', 'Aug', 'Sep', 'Sept', 'Oct', 'Nov', 'Dec',
    'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun',
    'Vol', 'Ver', 'Ed', 'p', 'pp', 'cf', 'approx', 'est'
}

# Build set of abbreviations for checking
# We'll use a different approach: filter out false positives after matching


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace: CRLF to LF, tabs to spaces, collapse multiple spaces"""
    # CRLF to LF
    text = text.replace('\r\n', '\n')
    # Tabs to spaces
    text = text.replace('\t', ' ')
    # Collapse multiple spaces (but preserve newlines)
    text = re.sub(r'[ \t]+', ' ', text)
    return text


def split_paragraphs(text: str) -> List[str]:
    """Split text into paragraphs by blank lines (\\n\\n+)"""
    text = normalize_whitespace(text)
    # Split by blank lines (one or more consecutive newlines with optional spaces)
    paragraphs = re.split(r'\n\s*\n+', text)
    # Strip and filter empty
    return [p.strip() for p in paragraphs if p.strip()]


def _is_abbreviation(text: str, pos: int) -> bool:
    """Check if a period at position is part of an abbreviation"""
    # Look backward for abbreviation pattern (including multi-part like e.g.)
    # Check for patterns like "e.g." where there might be multiple periods
    before = text[:pos+1]

    # Check for multi-dot abbreviations (e.g., i.e.)
    # Look for pattern: letter.letter. at the end
    if re.search(r'\b\w\.\w\.$', before):
        return True

    # Extract word before the period
    match = re.search(r'(\b\w+)\.?$', before)
    if match:
        word = match.group(1)
        # Check if it's in our abbreviation list (case-insensitive)
        if word in ABBREVIATIONS or word.lower() in {a.lower() for a in ABBREVIATIONS}:
            return True
        # Check for single letter abbreviations (e.g., "A. Smith")
        if len(word) == 1 and word.isupper():
            return True
        # Check for numbers with decimal points (1.5, 3.14)
        if re.search(r'\d+\.\d*$', before):
            return True

    return False


def split_sentences(paragraph: str) -> List[Tuple[str, str]]:
    """
    Split paragraph into sentences with pause type detection.

    Returns:
        List of (sentence_text, pause_type) tuples
        pause_type: 'short' (comma), 'medium' (. ? !), 'none' (last chunk)
    """
    # Normalize whitespace within paragraph
    paragraph = normalize_whitespace(paragraph.strip())

    if not paragraph:
        return []

    chunks = []

    # Pattern: sentence-ending punctuation + optional quotes/parens + whitespace
    sentence_pattern = r'([.!?])(["\')\]]*)\s+'

    # Find all potential sentence boundaries
    potential_splits = list(re.finditer(sentence_pattern, paragraph))

    # Filter out abbreviations
    valid_splits = []
    for match in potential_splits:
        punct = match.group(1)
        # If it's a period, check if it's an abbreviation
        if punct == '.':
            if not _is_abbreviation(paragraph, match.start()):
                valid_splits.append(match)
        else:
            # ? and ! are always sentence endings
            valid_splits.append(match)

    if not valid_splits:
        # No sentence splits found, treat whole paragraph as one chunk
        # Check for comma splits
        return _split_by_commas(paragraph)

    # Extract sentences
    last_end = 0
    for match in valid_splits:
        # Get text up to and including the punctuation
        sent_text = paragraph[last_end:match.end()].strip()
        if sent_text:
            # Check if sentence is too long (>600 chars) and needs comma splitting
            if len(sent_text) > 600:
                chunks.extend(_split_by_commas(sent_text))
            else:
                chunks.append((sent_text, 'medium'))
        last_end = match.end()

    # Handle remaining text after last sentence split
    if last_end < len(paragraph):
        remaining = paragraph[last_end:].strip()
        if remaining:
            # Check for comma splits in remaining text
            comma_chunks = _split_by_commas(remaining)
            chunks.extend(comma_chunks)

    # Mark last chunk as 'none' (no pause needed within paragraph)
    if chunks:
        text, _ = chunks[-1]
        chunks[-1] = (text, 'none')

    return chunks


def _split_by_commas(text: str) -> List[Tuple[str, str]]:
    """
    Split long text by commas (auxiliary splitting).
    Excludes commas in numbers (e.g., 1,000) and after abbreviations.

    Returns:
        List of (chunk_text, 'short') tuples
    """
    # Pattern: comma NOT followed by a digit (to exclude 1,000)
    # and NOT preceded by abbreviation patterns
    comma_pattern = r',(?!\d)'

    splits = re.split(comma_pattern, text)

    if len(splits) <= 1:
        # No comma splits, return as single chunk
        return [(text.strip(), 'none')]

    chunks = []
    for i, chunk in enumerate(splits):
        chunk = chunk.strip()
        if not chunk:
            continue

        # Add comma back (except for last chunk where we split it off)
        if i < len(splits) - 1:
            chunk = chunk + ','

        # All comma-split chunks get 'short' pause except the last
        pause = 'short' if i < len(splits) - 1 else 'none'
        chunks.append((chunk, pause))

    return chunks


def segment_text(text: str) -> List[Tuple[str, str]]:
    """
    Full text segmentation pipeline.

    Returns:
        List of (chunk_text, pause_type) tuples
        Last chunk in entire text gets 'none'
    """
    paragraphs = split_paragraphs(text)

    if not paragraphs:
        return []

    all_chunks = []

    for i, para in enumerate(paragraphs):
        para_chunks = split_sentences(para)

        # Change last chunk's pause to 'long' if not the last paragraph
        if para_chunks and i < len(paragraphs) - 1:
            text, _ = para_chunks[-1]
            para_chunks[-1] = (text, 'long')

        all_chunks.extend(para_chunks)

    return all_chunks


if __name__ == '__main__':
    # Test
    test_text = """In reality, even tasks that seemed impossible become manageable as we iterate. For example, we often say e.g. or i.e. in notes, which should not break sentences. A price might be 1,000 dollars. That comma must not trigger a pause!

When a new paragraph begins, the listener should feel a longer breath."""

    result = segment_text(test_text)
    for i, (chunk, pause) in enumerate(result, 1):
        print(f"{i}. [{pause:6s}] {chunk}")
