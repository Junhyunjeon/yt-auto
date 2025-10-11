#!/usr/bin/env python3
"""
OpenAI TTS - Generate audio using OpenAI Text-to-Speech API
Refactored to use tts_common for segmentation and post-processing
"""

import os
import sys
import io
import json
import yaml
import argparse
from pathlib import Path
from typing import Dict, Any, List
from openai import OpenAI
from pydub import AudioSegment
from loguru import logger

# Import common TTS utilities
try:
    from tts_common import segment_text, build_track, measure, apply_style_prefix
except ImportError:
    # For when run from scripts/ directory
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from tts_common import segment_text, build_track, measure, apply_style_prefix


# Load environment variables from .env file
def load_env():
    """Load .env file from project root"""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    value = os.path.expandvars(value)
                    value = os.path.expanduser(value)
                    os.environ[key] = value


def load_presets() -> Dict[str, Any]:
    """Load voice presets from presets.yaml"""
    presets_path = Path(__file__).parent.parent / "presets.yaml"
    if presets_path.exists():
        try:
            with open(presets_path) as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Failed to load presets.yaml: {e}")
    return {}


def load_config() -> Dict[str, Any]:
    """Load config.yaml for default settings"""
    config_path = Path(__file__).parent.parent / "config.yaml"
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f) or {}
                # Expand environment variables in config values
                return expand_env_vars(config)
        except Exception as e:
            logger.warning(f"Failed to load config.yaml: {e}")
    return {}


def expand_env_vars(obj):
    """Recursively expand environment variables in config"""
    if isinstance(obj, dict):
        return {k: expand_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [expand_env_vars(item) for item in obj]
    elif isinstance(obj, str):
        expanded = os.path.expandvars(obj)
        expanded = os.path.expanduser(expanded)
        return expanded
    return obj


# Initialize
load_env()
CONFIG = load_config()
PRESETS = load_presets()

# Voice categories
MALE_VOICES = ["alloy", "echo", "fable", "onyx"]
FEMALE_VOICES = ["nova", "shimmer"]
ALL_VOICES = MALE_VOICES + FEMALE_VOICES

# Pause profiles (seconds)
PAUSE_PROFILES = {
    "broadcast": {"short": 0.30, "medium": 0.60, "long": 1.00},
    "natural": {"short": 0.25, "medium": 0.50, "long": 0.80},
    "tight": {"short": 0.15, "medium": 0.35, "long": 0.60},
}

# Built-in voice presets
_BUILTIN_PRESETS = {
    "onyx_fast": {
        "voice": "onyx",
        "model": "tts-1",
        "pause_profile": "tight",
        "speed": 1.02,
        "description": "Fast narration for quick briefings/news"
    },
    "onyx_broadcast": {
        "voice": "onyx",
        "model": "tts-1-hd",
        "pause_profile": "broadcast",
        "speed": 0.98,
        "description": "Authoritative broadcast tone with rich detail"
    },
    "alloy_warm_low": {
        "voice": "alloy",
        "model": "tts-1-hd",
        "pause_profile": "natural",
        "speed": 0.99,
        "description": "Warm, emotional tone (less deep than onyx)"
    },
    "onyx_natural": {
        "voice": "onyx",
        "model": "tts-1",
        "format": "wav",
        "pause_profile": "natural",
        "speed": 1.0,
        "pause_short": 0.25,
        "pause_medium": 0.50,
        "pause_long": 0.80,
        "fade_ms": 20,
        "crossfade_ms": 50,
        "description": "Natural breathing with onyx voice (default)"
    },
}

# Merge loaded presets with built-in presets (loaded take precedence)
VOICE_PRESETS = {**_BUILTIN_PRESETS, **PRESETS}


def synthesize_segment(client: OpenAI, text: str, model: str, voice: str,
                       response_format: str = "mp3") -> AudioSegment:
    """Synthesize a single text segment using OpenAI TTS"""
    try:
        response = client.audio.speech.create(
            model=model,
            voice=voice,
            input=text,
            response_format=response_format
        )

        # Convert to AudioSegment
        audio_data = response.content
        return AudioSegment.from_file(io.BytesIO(audio_data), format=response_format)

    except Exception as e:
        logger.error(f"Synthesis error: {e}")
        # Return silent segment on error
        return AudioSegment.silent(duration=100)


def resolve_defaults(args: argparse.Namespace, config: Dict, presets: Dict) -> argparse.Namespace:
    """
    Resolve configuration priority: CLI args > preset > config.yaml > env > hardcoded defaults

    Args:
        args: Parsed command-line arguments
        config: Loaded config.yaml
        presets: Loaded presets.yaml

    Returns:
        args with all fields filled in with appropriate defaults
    """
    # Apply preset if specified
    preset = {}
    if args.preset and args.preset in presets:
        preset = presets[args.preset]
        logger.info(f"Using preset: {args.preset} - {preset.get('description', '')}")

    # Helper to get value with priority: CLI > preset > config > env > default
    def get_value(arg_name, preset_key, config_path, env_var, default):
        # If explicitly set via CLI
        arg_val = getattr(args, arg_name, None)
        if arg_val is not None:
            return arg_val

        # Check preset
        if preset_key in preset:
            return preset[preset_key]

        # Check config.yaml (navigate nested dict)
        config_val = config
        for key in config_path.split('.'):
            config_val = config_val.get(key, {}) if isinstance(config_val, dict) else {}
        if config_val != {}:
            return config_val

        # Check environment
        if env_var and env_var in os.environ:
            env_val = os.environ[env_var]
            # Type conversion
            if isinstance(default, float):
                return float(env_val)
            elif isinstance(default, int):
                return int(env_val)
            return env_val

        # Return default
        return default

    # Apply all defaults
    args.model = get_value('model', 'model', 'tts.model', 'OPENAI_TTS_MODEL', 'tts-1')
    args.voice = get_value('voice', 'voice', 'tts.voice', 'OPENAI_TTS_VOICE', 'onyx')
    args.format = get_value('format', 'format', 'tts.format', 'OPENAI_TTS_FORMAT', 'wav')
    args.speed = get_value('speed', 'speed', 'tts.speed', 'OPENAI_TTS_SPEED', 1.0)

    # Pause profile
    pause_profile_name = get_value('pause_profile', 'pause_profile', 'tts.pause_profile',
                                    'OPENAI_TTS_PAUSE_PROFILE', 'natural')
    profile = PAUSE_PROFILES.get(pause_profile_name, PAUSE_PROFILES['natural'])

    args.pause_short = get_value('pause_short', 'pause_short', 'tts.pause_short', None, profile['short'])
    args.pause_medium = get_value('pause_medium', 'pause_medium', 'tts.pause_medium', None, profile['medium'])
    args.pause_long = get_value('pause_long', 'pause_long', 'tts.pause_long', None, profile['long'])

    # Processing options
    args.fade_ms = get_value('fade_ms', 'fade_ms', 'tts.fade_ms', None, 20)
    args.crossfade_ms = get_value('crossfade_ms', 'crossfade_ms', 'tts.crossfade_ms', None, 50)
    args.max_chars = get_value('max_chars', 'max_chars', 'tts.max_chars', None, 800)
    args.style_prefix = get_value('style_prefix', 'style_prefix', 'tts.style_prefix', None, None)

    return args


def main():
    """CLI interface"""
    parser = argparse.ArgumentParser(
        description="OpenAI TTS - Generate audio with tts_common integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Pause Profiles:
  broadcast: short=0.30s, medium=0.60s, long=1.00s (authoritative)
  natural:   short=0.25s, medium=0.50s, long=0.80s (default)
  tight:     short=0.15s, medium=0.35s, long=0.60s (fast-paced)

Voice Presets:
  {chr(10).join(f"  {name}: {info['description']}" for name, info in VOICE_PRESETS.items())}

Examples:
  # Basic usage (uses onyx_natural preset by default)
  {sys.argv[0]} input.txt --output output/audio.wav

  # With metrics export
  {sys.argv[0]} input.txt --output output/audio.wav --json-out metrics.json

  # Custom voice and pauses
  {sys.argv[0]} input.txt --output output/audio.wav --voice alloy --pause-profile tight

  # With style prefix
  {sys.argv[0]} input.txt --output output/audio.wav --style-prefix "Speak calmly and confidently."
        """
    )

    parser.add_argument("input", help="Input text file")
    parser.add_argument("--output", "-o", required=True, help="Output file path")

    # Voice selection
    parser.add_argument("--voice", "-v", choices=ALL_VOICES, help="Voice to use")
    parser.add_argument("--preset", choices=list(VOICE_PRESETS.keys()),
                        help="Use voice preset (overrides other settings)")

    # Model and format
    parser.add_argument("--model", "-m", choices=["tts-1", "tts-1-hd"],
                        help="TTS model (tts-1-hd for higher quality)")
    parser.add_argument("--format", "-f", choices=["mp3", "opus", "aac", "flac", "wav", "pcm"],
                        help="Output audio format")

    # Pause control
    parser.add_argument("--pause-profile", choices=list(PAUSE_PROFILES.keys()),
                        help="Preset pause profile")
    parser.add_argument("--pause-short", type=float, help="Pause after commas (seconds)")
    parser.add_argument("--pause-medium", type=float, help="Pause after sentences (seconds)")
    parser.add_argument("--pause-long", type=float, help="Pause between paragraphs (seconds)")

    # Processing options (NEW)
    parser.add_argument("--fade-ms", type=int, help="Fade in/out duration (milliseconds)")
    parser.add_argument("--crossfade-ms", type=int, help="Crossfade duration between chunks (ms)")
    parser.add_argument("--max-chars", type=int, help="Maximum characters per segment")
    parser.add_argument("--style-prefix", help="Style instruction to prepend to text")

    # Speed and effects
    parser.add_argument("--speed", "-s", type=float, help="Playback speed (0.95-1.05 recommended)")
    parser.add_argument("--normalize", action="store_true", help="Apply volume normalization")

    # Output options (NEW)
    parser.add_argument("--json-out", help="Save metrics to JSON file")

    args = parser.parse_args()

    # Read input text
    try:
        text = Path(args.input).read_text(encoding="utf-8").strip()
    except Exception as e:
        logger.error(f"Failed to read input file: {e}")
        return 1

    if not text:
        logger.error("Input file is empty")
        return 1

    # Resolve all configuration with proper priority
    args = resolve_defaults(args, CONFIG, VOICE_PRESETS)

    # Validate API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not found in environment")
        return 1

    client = OpenAI(api_key=api_key)

    # Apply style prefix if specified
    if args.style_prefix:
        text = apply_style_prefix(text, args.style_prefix)
        logger.info(f"Applied style prefix: {args.style_prefix[:50]}...")

    # Segment text using tts_common
    segments = segment_text(text, max_chars=args.max_chars, mode="sentence")
    logger.info(f"Segmented into {len(segments)} chunks (max {args.max_chars} chars each)")

    # Synthesize each segment
    logger.info(f"🎙️  Synthesizing with OpenAI TTS...")
    logger.info(f"   Voice: {args.voice}, Model: {args.model}, Format: {args.format}")
    logger.info(f"   Pauses: short={args.pause_short}s, medium={args.pause_medium}s, long={args.pause_long}s")

    chunks: List[AudioSegment] = []
    for i, seg in enumerate(segments, 1):
        logger.info(f"   [{i}/{len(segments)}] Synthesizing: {seg[:60]}...")
        audio = synthesize_segment(client, seg, args.model, args.voice, "mp3")
        chunks.append(audio)

    # Build track using tts_common
    logger.info("Building final track with pauses and crossfades...")
    track = build_track(
        chunks,
        pause_short=args.pause_short,
        pause_medium=args.pause_medium,
        pause_long=args.pause_long,
        fade_ms=args.fade_ms,
        crossfade_ms=args.crossfade_ms,
        normalize=args.normalize,
        speed=args.speed
    )

    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Export to final format
    logger.info(f"Exporting to {args.format}...")
    track.export(str(output_path), format=args.format)

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
            "voice": args.voice,
            "model": args.model,
            "format": args.format,
            "speed": args.speed
        }

        with open(json_path, 'w') as f:
            json.dump(metrics_full, f, indent=2)

        logger.info(f"   Metrics saved to: {json_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
