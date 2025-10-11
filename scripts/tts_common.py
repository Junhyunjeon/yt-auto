#!/usr/bin/env python3
"""
TTS Common Module
=================
Shared utilities for text segmentation and audio post-processing
Used by both OpenAI TTS and Piper TTS for consistent results
"""

import re
import math
from typing import List, Tuple, Dict
from pydub import AudioSegment
from pydub.silence import detect_silence


# Text segmentation patterns
PARA_SPLIT = re.compile(r'\n\s*\n')  # Double newline
SENT_END = re.compile(r'([\.!?。．]+[)\"\'\u00BB]*)(\s+)')  # Sentence endings
CLAUSE_SPLIT = re.compile(r'([,;:\u2014\u2013])')  # Clause markers


def segment_text(
    full_text: str,
    max_chars: int = 800,
    mode: str = "sentence"
) -> List[str]:
    """
    Split text into segments for TTS synthesis

    Args:
        full_text: Input text to segment
        max_chars: Maximum characters per segment (default 800)
        mode: Segmentation mode - "sentence" (default) or "paragraph"

    Returns:
        List of text segments

    Strategy:
        1. Split by paragraphs (double newline)
        2. Split paragraphs into sentences
        3. Combine sentences until max_chars limit
        4. Preserve sentence boundaries (never split mid-sentence)
    """
    segments = []

    # Split into paragraphs
    paragraphs = [p.strip() for p in PARA_SPLIT.split(full_text.strip()) if p.strip()]

    for para in paragraphs:
        # Split paragraph into sentences
        sentences = _split_sentences(para)

        if mode == "paragraph":
            # Keep whole paragraph if under limit
            if len(para) <= max_chars:
                segments.append(para)
                continue

        # Combine sentences until max_chars
        current_segment = []
        current_length = 0

        for sent in sentences:
            sent_len = len(sent)

            # If single sentence exceeds max_chars, split it further
            if sent_len > max_chars:
                if current_segment:
                    segments.append(' '.join(current_segment))
                    current_segment = []
                    current_length = 0

                # Split long sentence by clause markers
                clauses = _split_by_clauses(sent, max_chars)
                segments.extend(clauses)
                continue

            # Add sentence to current segment if it fits
            if current_length + sent_len + 1 <= max_chars:
                current_segment.append(sent)
                current_length += sent_len + (1 if current_segment else 0)
            else:
                # Flush current segment and start new one
                if current_segment:
                    segments.append(' '.join(current_segment))
                current_segment = [sent]
                current_length = sent_len

        # Flush remaining sentences
        if current_segment:
            segments.append(' '.join(current_segment))

    return segments


def _split_sentences(paragraph: str) -> List[str]:
    """Split paragraph into sentences"""
    sentences = []
    parts = SENT_END.split(paragraph)

    i = 0
    while i < len(parts):
        if i + 2 < len(parts) and parts[i+1]:  # Has end marker and space
            sentences.append((parts[i] + parts[i+1]).strip())
            i += 3  # Skip text, end marker, space
        elif parts[i].strip():
            sentences.append(parts[i].strip())
            i += 1
        else:
            i += 1

    return [s for s in sentences if s]


def _split_by_clauses(sentence: str, max_chars: int) -> List[str]:
    """Split long sentence by clause markers"""
    clauses = []
    parts = CLAUSE_SPLIT.split(sentence)

    current = []
    current_len = 0

    for part in parts:
        part_len = len(part)
        if current_len + part_len > max_chars and current:
            clauses.append(''.join(current))
            current = [part]
            current_len = part_len
        else:
            current.append(part)
            current_len += part_len

    if current:
        clauses.append(''.join(current))

    return clauses


def build_track(
    chunks: List[AudioSegment],
    pause_short: float = 0.25,
    pause_medium: float = 0.50,
    pause_long: float = 0.80,
    fade_ms: int = 20,
    crossfade_ms: int = 50,
    normalize: bool = True,
    speed: float = 1.0
) -> AudioSegment:
    """
    Combine audio chunks with pauses, fades, and crossfades

    Args:
        chunks: List of AudioSegment objects
        pause_short: Short pause duration (seconds) - after commas
        pause_medium: Medium pause duration (seconds) - after sentences
        pause_long: Long pause duration (seconds) - between paragraphs
        fade_ms: Fade in/out duration (milliseconds)
        crossfade_ms: Crossfade duration between chunks (milliseconds)
        normalize: Apply loudness normalization
        speed: Playback speed multiplier (0.95-1.05 recommended)

    Returns:
        Combined AudioSegment
    """
    if not chunks:
        return AudioSegment.silent(duration=0)

    # Start with silent track
    track = AudioSegment.silent(duration=0)

    for i, chunk in enumerate(chunks):
        # Apply fade in/out to each chunk
        if fade_ms > 0:
            chunk = chunk.fade_in(fade_ms).fade_out(fade_ms)

        if i == 0:
            # First chunk - just add it
            track = chunk
        else:
            # Add pause before this chunk (medium pause by default)
            pause_duration = int(pause_medium * 1000)

            if crossfade_ms > 0 and len(track) > crossfade_ms:
                # Crossfade with previous chunk
                track = track.append(chunk, crossfade=crossfade_ms)
            else:
                # Simple concatenation with pause
                track = track + AudioSegment.silent(duration=pause_duration) + chunk

    # Apply speed adjustment if needed
    if abs(speed - 1.0) > 0.001:
        if abs(speed - 1.0) > 0.05:
            print(f"⚠️  Speed {speed} is outside recommended range (0.95-1.05)")

        new_frame_rate = int(track.frame_rate / speed)
        track = track._spawn(track.raw_data, overrides={
            "frame_rate": new_frame_rate
        }).set_frame_rate(track.frame_rate)

    # Apply normalization
    if normalize:
        track = track.normalize(headroom=0.1)

    return track


def measure(audio: AudioSegment) -> Dict[str, float]:
    """
    Measure audio characteristics

    Args:
        audio: AudioSegment to measure

    Returns:
        Dictionary with metrics:
        - duration_sec: Duration in seconds
        - rms_dbfs: RMS level in dBFS
        - peak_dbfs: Peak level in dBFS
        - silence_ratio: Percentage of silence (%)
    """
    duration_sec = len(audio) / 1000.0

    # RMS and peak levels
    rms_dbfs = audio.dBFS
    peak_dbfs = audio.max_dBFS

    # Detect silence (threshold: -40 dBFS, min duration: 100ms)
    silence_ranges = detect_silence(
        audio,
        min_silence_len=100,
        silence_thresh=-40,
        seek_step=10
    )

    # Calculate silence ratio
    total_silence_ms = sum(end - start for start, end in silence_ranges)
    silence_ratio = (total_silence_ms / len(audio)) * 100 if len(audio) > 0 else 0

    return {
        "duration_sec": round(duration_sec, 2),
        "rms_dbfs": round(rms_dbfs, 2),
        "peak_dbfs": round(peak_dbfs, 2),
        "silence_ratio": round(silence_ratio, 2)
    }


def apply_style_prefix(text: str, style_prefix: str = None) -> str:
    """
    Prepend style instruction to text

    Args:
        text: Original text
        style_prefix: Style instruction (e.g., "Speak calmly and confidently...")

    Returns:
        Text with style prefix prepended
    """
    if not style_prefix:
        return text

    return f"{style_prefix}\n\n{text}"


def match_volume(
    audio1: AudioSegment,
    audio2: AudioSegment,
    max_diff_db: float = 1.5
) -> Tuple[AudioSegment, AudioSegment]:
    """
    Match volume levels between two audio segments

    Args:
        audio1: First audio segment
        audio2: Second audio segment
        max_diff_db: Maximum dB difference to trigger adjustment

    Returns:
        Tuple of (audio1_matched, audio2_matched)
    """
    rms1 = audio1.dBFS
    rms2 = audio2.dBFS
    diff = abs(rms1 - rms2)

    if diff > max_diff_db:
        # Boost the quieter one
        if rms1 < rms2:
            # Boost audio1
            gain = min(diff, 6.0)  # Cap at 6dB to avoid clipping
            audio1 = audio1.apply_gain(gain)
            print(f"   Matched volumes: boosted audio1 by {gain:.1f}dB")
        else:
            # Boost audio2
            gain = min(diff, 6.0)
            audio2 = audio2.apply_gain(gain)
            print(f"   Matched volumes: boosted audio2 by {gain:.1f}dB")

    return audio1, audio2


if __name__ == "__main__":
    # Quick test
    test_text = """This is a test paragraph with multiple sentences.
    It should be split properly, even with punctuation!

    This is a second paragraph. It demonstrates paragraph splitting."""

    segments = segment_text(test_text, max_chars=100)
    print("Segments:")
    for i, seg in enumerate(segments, 1):
        print(f"{i}. [{len(seg)} chars] {seg[:60]}...")
