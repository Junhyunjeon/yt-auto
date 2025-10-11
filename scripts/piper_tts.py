#!/usr/bin/env python3
"""
Piper TTS - Generate audio using Piper Text-to-Speech
Uses tts_common for consistent segmentation and post-processing with OpenAI TTS
"""

import os
import sys
import io
import json
import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List
from loguru import logger
from pydub import AudioSegment

# Import common TTS utilities
try:
    from tts_common import segment_text, build_track, measure, apply_style_prefix
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    from tts_common import segment_text, build_track, measure, apply_style_prefix


def have_piper() -> bool:
    """Check if Piper is installed and available"""
    return shutil.which("piper") is not None


def synthesize_with_piper(text: str, voice_path: str) -> AudioSegment:
    """
    Synthesize text using Piper TTS

    Args:
        text: Text to synthesize
        voice_path: Path to Piper voice model (.onnx)

    Returns:
        AudioSegment with synthesized audio
    """
    # Piper supports both file output and stdout modes
    # Try file output first (more reliable)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        tmpwav = tf.name

    try:
        # File output mode: piper -m model.onnx -f output.wav < input.txt
        cmd = ["piper", "-m", voice_path, "-f", tmpwav]
        result = subprocess.run(
            cmd,
            input=text.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )

        audio = AudioSegment.from_file(tmpwav, format="wav")
        os.unlink(tmpwav)
        return audio

    except subprocess.CalledProcessError as e:
        # Cleanup temp file
        if os.path.exists(tmpwav):
            os.unlink(tmpwav)

        # Try stdout mode as fallback
        try:
            logger.info("File mode failed, trying stdout mode...")
            cmd = ["piper", "-m", voice_path]
            result = subprocess.run(
                cmd,
                input=text.encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            return AudioSegment.from_file(io.BytesIO(result.stdout), format="wav")

        except subprocess.CalledProcessError as e2:
            logger.error(f"Piper synthesis failed: {e2.stderr.decode('utf-8', 'ignore')}")
            raise


def main():
    """CLI interface"""
    parser = argparse.ArgumentParser(
        description="Piper TTS - Generate audio with tts_common integration"
    )

    parser.add_argument("input", help="Input text file")
    parser.add_argument("--output", "-o", required=True, help="Output WAV file path")

    # Voice and model
    parser.add_argument("--voice", help="Piper voice model path (.onnx)")

    # Audio processing (same as OpenAI TTS for consistency)
    parser.add_argument("--pause-profile", choices=["natural", "broadcast", "tight"],
                        help="Preset pause profile")
    parser.add_argument("--pause-short", type=float, help="Pause after commas (seconds)")
    parser.add_argument("--pause-medium", type=float, help="Pause after sentences (seconds)")
    parser.add_argument("--pause-long", type=float, help="Pause between paragraphs (seconds)")
    parser.add_argument("--fade-ms", type=int, help="Fade in/out duration (milliseconds)")
    parser.add_argument("--crossfade-ms", type=int, help="Crossfade duration (ms)")
    parser.add_argument("--max-chars", type=int, help="Maximum characters per segment")
    parser.add_argument("--style-prefix", help="Style instruction to prepend to text")
    parser.add_argument("--speed", "-s", type=float, help="Playback speed multiplier")
    parser.add_argument("--normalize", action="store_true", help="Apply volume normalization")

    # Output options
    parser.add_argument("--json-out", help="Save metrics to JSON file")

    args = parser.parse_args()

    # Check if Piper is available
    if not have_piper():
        logger.warning("⚠️ Piper not found in PATH. Skipping synthesis gracefully.")
        logger.info("Install Piper: brew install piper")
        # Exit successfully to allow pipeline to continue
        return 0

    # Set defaults
    voice = args.voice or os.getenv("PIPER_VOICE", str(Path.home() / "piper_models" / "en_US-amy-medium.onnx"))
    pause_short = args.pause_short if args.pause_short is not None else 0.25
    pause_medium = args.pause_medium if args.pause_medium is not None else 0.50
    pause_long = args.pause_long if args.pause_long is not None else 0.80
    fade_ms = args.fade_ms if args.fade_ms is not None else 20
    crossfade_ms = args.crossfade_ms if args.crossfade_ms is not None else 50
    max_chars = args.max_chars if args.max_chars is not None else 800
    speed = args.speed if args.speed is not None else 1.0

    # Check if voice model exists
    voice_path = Path(voice)
    if not voice_path.exists():
        logger.error(f"❌ Piper voice model not found: {voice_path}")
        logger.info("Download models from: https://github.com/rhasspy/piper/releases/tag/v1.2.0")
        return 1

    # Read input text
    try:
        text = Path(args.input).read_text(encoding="utf-8").strip()
    except Exception as e:
        logger.error(f"Failed to read input file: {e}")
        return 1

    if not text:
        logger.error("Input file is empty")
        return 1

    # Apply style prefix if specified
    if args.style_prefix:
        text = apply_style_prefix(text, args.style_prefix)
        logger.info(f"Applied style prefix: {args.style_prefix[:50]}...")

    # Segment text using tts_common
    segments = segment_text(text, max_chars=max_chars, mode="sentence")
    logger.info(f"Segmented into {len(segments)} chunks (max {max_chars} chars each)")

    # Synthesize each segment
    logger.info(f"🎙️  Synthesizing with Piper TTS...")
    logger.info(f"   Voice model: {voice_path.name}")
    logger.info(f"   Pauses: short={pause_short}s, medium={pause_medium}s, long={pause_long}s")

    chunks: List[AudioSegment] = []
    for i, seg in enumerate(segments, 1):
        logger.info(f"   [{i}/{len(segments)}] Synthesizing: {seg[:60]}...")
        audio = synthesize_with_piper(seg, str(voice_path))
        chunks.append(audio)
        logger.info(f"   [{i}/{len(segments)}] OK ({len(audio)}ms)")

    # Build track using tts_common
    logger.info("Building final track with pauses and crossfades...")
    track = build_track(
        chunks,
        pause_short=pause_short,
        pause_medium=pause_medium,
        pause_long=pause_long,
        fade_ms=fade_ms,
        crossfade_ms=crossfade_ms,
        normalize=args.normalize,
        speed=speed
    )

    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Export to WAV
    logger.info("Exporting to WAV...")
    track.export(str(output_path), format="wav")

    # Measure and log metrics
    metrics = measure(track)
    file_size_mb = output_path.stat().st_size / (1024 * 1024)

    logger.success(f"✅ Audio generated: {output_path}")
    logger.info(f"   Duration: {metrics['duration_sec']:.2f}s")
    logger.info(f"   RMS: {metrics['rms_dbfs']:.1f} dBFS")
    logger.info(f"   Peak: {metrics['peak_dbfs']:.1f} dBFS")
    logger.info(f"   Silence: {metrics['silence_ratio']:.1f}%")
    logger.info(f"   File size: {file_size_mb:.2f} MB")

    # Save metrics to JSON if requested
    if args.json_out:
        json_path = Path(args.json_out)
        json_path.parent.mkdir(parents=True, exist_ok=True)

        metrics_full = {
            **metrics,
            "file_size_mb": round(file_size_mb, 2),
            "segments": len(segments),
            "voice_model": voice_path.name,
            "speed": speed
        }

        with open(json_path, 'w') as f:
            json.dump(metrics_full, f, indent=2)

        logger.info(f"   Metrics saved to: {json_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
