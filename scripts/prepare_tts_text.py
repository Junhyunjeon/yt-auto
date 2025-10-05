#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TTS Text Preparation
Generate manifest.jsonl with sentence-level chunking and pause metadata
"""

import sys
import os
import argparse
import json
import yaml
import logging
from pathlib import Path

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent))
from utils.textseg import segment_text


def validate_pause_config(pause_cfg: dict) -> bool:
    """Validate pause settings (must be 0.0~3.0s)"""
    required_keys = ['short', 'medium', 'long']
    for key in required_keys:
        if key not in pause_cfg:
            logging.error(f"Missing pause config: {key}")
            return False
        val = pause_cfg[key]
        if not isinstance(val, (int, float)) or not (0.0 <= val <= 3.0):
            logging.error(f"Invalid pause.{key}={val} (must be 0.0~3.0)")
            return False
    return True


def main():
    parser = argparse.ArgumentParser(description="Prepare TTS text with pause metadata")
    parser.add_argument("input", help="Input text file path")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    parser.add_argument("--slug", default=None, help="Slug name (default: derived from input filename)")
    parser.add_argument("--min-chars", type=int, default=10, help="Minimum characters per chunk")
    args = parser.parse_args()

    # Setup logging
    log_path = Path("logs/tts.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )

    # Load config
    config_path = Path(args.config)
    if not config_path.exists():
        logging.error(f"Config file not found: {config_path}")
        print(f"Error: Config file not found: {config_path}")
        return 1

    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)

    # Validate pause settings
    pause_cfg = cfg.get("tts", {}).get("pause", {})
    if not validate_pause_config(pause_cfg):
        print("Error: Invalid TTS pause configuration")
        return 1

    # Read input
    input_path = Path(args.input)
    if not input_path.exists():
        logging.error(f"Input file not found: {input_path}")
        print(f"Error: Input file not found: {input_path}")
        return 1

    try:
        text = input_path.read_text(encoding="utf-8")
    except Exception as e:
        logging.error(f"Failed to read input: {e}")
        print(f"Error: Failed to read input: {e}")
        return 1

    # Normalize CRLF
    text = text.replace('\r\n', '\n')

    # Segment text
    segments = segment_text(text)

    if not segments:
        logging.warning("No segments generated from input text")
        print("Warning: No segments generated")
        return 0

    # Filter by minimum characters
    segments = [(txt, pause) for txt, pause in segments if len(txt.strip()) >= args.min_chars]

    # Determine slug
    slug = args.slug or input_path.stem

    # Generate manifest
    manifest_path = Path(f"work/{slug}.manifest.jsonl")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    # Count pause types
    pause_counts = {'short': 0, 'medium': 0, 'long': 0, 'none': 0}
    paragraph_count = 0

    try:
        with open(manifest_path, "w", encoding="utf-8") as f:
            for idx, (chunk_text, pause_type) in enumerate(segments, 1):
                entry = {
                    "idx": idx,
                    "text": chunk_text,
                    "pause_after": pause_type
                }
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

                # Count
                pause_counts[pause_type] += 1
                if pause_type == 'long':
                    paragraph_count += 1

    except Exception as e:
        logging.error(f"Failed to write manifest: {e}")
        print(f"Error: Failed to write manifest: {e}")
        return 1

    # Logging
    logging.info(
        "prepared | slug=%s | sentences=%d | short=%d | medium=%d | long=%d | paragraphs=%d",
        slug, len(segments), pause_counts['short'], pause_counts['medium'],
        pause_counts['long'], paragraph_count + 1  # +1 for first paragraph
    )

    print(f"✅ Prepared manifest: {manifest_path}")
    print(f"   Sentences: {len(segments)}")
    print(f"   Pauses: short={pause_counts['short']}, medium={pause_counts['medium']}, long={pause_counts['long']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
