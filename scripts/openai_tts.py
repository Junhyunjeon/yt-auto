#!/usr/bin/env python3
"""
OpenAI TTS - Generate audio using OpenAI Text-to-Speech API
Supports multiple voices with natural pauses and breathing
"""

import os
import sys
import re
import io
import subprocess
import yaml
from pathlib import Path
from typing import List, Tuple, Dict, Any
from openai import OpenAI
from pydub import AudioSegment

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
            print(f"⚠️  Failed to load presets.yaml: {e}")
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
            print(f"⚠️  Failed to load config.yaml: {e}")
    return {}

def expand_env_vars(obj):
    """Recursively expand environment variables in config"""
    if isinstance(obj, dict):
        return {k: expand_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [expand_env_vars(item) for item in obj]
    elif isinstance(obj, str):
        # Handle ${VAR:-default} syntax
        expanded = os.path.expandvars(obj)
        expanded = os.path.expanduser(expanded)
        return expanded
    return obj

load_env()

# Load configuration
CONFIG = load_config()
PRESETS = load_presets()

# Configuration with fallbacks
API_KEY = os.getenv("OPENAI_API_KEY")
DEFAULT_MODEL = os.getenv("OPENAI_TTS_MODEL", "tts-1")
DEFAULT_VOICE = os.getenv("OPENAI_TTS_VOICE", "onyx")  # Changed default to onyx
DEFAULT_FORMAT = os.getenv("OPENAI_TTS_FORMAT", "wav")
DEFAULT_SPEED = float(os.getenv("OPENAI_TTS_SPEED", "1.0"))
DEFAULT_PAUSE_PROFILE = os.getenv("OPENAI_TTS_PAUSE_PROFILE", "natural")

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

# Voice presets - merge presets.yaml with hardcoded defaults
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
        "description": "Natural breathing with onyx voice (default)"
    },
}

# Merge loaded presets with built-in presets (loaded take precedence)
VOICE_PRESETS = {**_BUILTIN_PRESETS, **PRESETS}

# Text segmentation patterns
SENT_END = re.compile(r'([\.!?。．]+[)\"\'\u00BB]*)(\s+)')
CLAUSE_SPLIT = re.compile(r'([,;:\u2014\u2013])')


def split_paragraphs(text: str) -> List[str]:
    """Split text into paragraphs (double newline)"""
    return [p.strip() for p in re.split(r'\n\s*\n', text.strip()) if p.strip()]


def split_sentences(paragraph: str) -> List[str]:
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


def should_add_clause_pause(text: str, min_length: int = 12) -> bool:
    """Check if clause pause should be added (prevent excessive pauses)"""
    return len(text) >= min_length


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
        print(f"⚠️  Synthesis error: {e}")
        # Return silent segment on error
        return AudioSegment.silent(duration=100)


def build_audio_with_pauses(
    text: str,
    pause_short: float,
    pause_medium: float,
    pause_long: float,
    model: str,
    voice: str,
    response_format: str = "mp3",
    speed: float = 1.0,
    normalize: bool = False,
    warmth_db: float = 0.0
) -> AudioSegment:
    """
    Build complete audio with natural pauses between sentences/paragraphs

    Args:
        text: Full text to synthesize
        pause_short: Pause after commas/semicolons (seconds)
        pause_medium: Pause after sentence endings (seconds)
        pause_long: Pause between paragraphs (seconds)
        model: TTS model (tts-1 or tts-1-hd)
        voice: Voice name
        response_format: Audio format (mp3, wav, etc)
        speed: Playback speed multiplier (0.95-1.05 recommended)
        normalize: Apply volume normalization
        warmth_db: Low-frequency boost in dB (0-4)

    Returns:
        Combined AudioSegment with pauses
    """
    if not API_KEY:
        raise EnvironmentError("OPENAI_API_KEY not found in environment")

    client = OpenAI(api_key=API_KEY)
    track = AudioSegment.silent(duration=0)

    paragraphs = split_paragraphs(text)
    total_segments = sum(len(split_sentences(p)) for p in paragraphs)
    current_segment = 0

    print(f"\n🎙️  Synthesizing {total_segments} segments...")
    print(f"   Paragraphs: {len(paragraphs)}")
    print(f"   Pauses: short={pause_short}s, medium={pause_medium}s, long={pause_long}s")

    for pi, para in enumerate(paragraphs):
        if not para.strip():
            continue

        sentences = split_sentences(para)

        for si, sent in enumerate(sentences):
            current_segment += 1
            print(f"   [{current_segment}/{total_segments}] Synthesizing: {sent[:60]}...")

            # Synthesize sentence
            audio = synthesize_segment(client, sent, model, voice, response_format)
            track += audio

            # Add pause after sentence
            if si < len(sentences) - 1:  # Not last sentence in paragraph
                # Check if sentence ends with strong punctuation
                if sent.rstrip().endswith(('.', '!', '?', '。', '．')):
                    track += AudioSegment.silent(duration=int(pause_medium * 1000))
                # Check for clause markers (commas, semicolons)
                elif CLAUSE_SPLIT.search(sent) and should_add_clause_pause(sent):
                    track += AudioSegment.silent(duration=int(pause_short * 1000))

        # Add long pause between paragraphs
        if pi < len(paragraphs) - 1:
            track += AudioSegment.silent(duration=int(pause_long * 1000))

    print(f"\n✅ Synthesis complete ({len(track)/1000:.1f} seconds)")

    # Speed adjustment (±5% max recommended)
    if abs(speed - 1.0) > 0.001:
        if abs(speed - 1.0) > 0.05:
            print(f"⚠️  Speed {speed} is outside recommended range (0.95-1.05)")

        print(f"   Applying speed adjustment: {speed}x")
        new_frame_rate = int(track.frame_rate / speed)
        track = track._spawn(track.raw_data, overrides={
            "frame_rate": new_frame_rate
        }).set_frame_rate(track.frame_rate)

    # Normalization
    if normalize:
        print("   Applying normalization...")
        track = track.normalize(headroom=0.1)

    # Warmth boost (low frequency enhancement)
    if warmth_db > 0:
        print(f"   Applying warmth boost: +{warmth_db}dB @ 140Hz")
        track = apply_warmth_boost(track, warmth_db)

    return track


def apply_warmth_boost(audio: AudioSegment, boost_db: float) -> AudioSegment:
    """
    Apply low-frequency boost using ffmpeg equalizer

    Args:
        audio: Input audio
        boost_db: Boost amount in dB (1-4 recommended)

    Returns:
        Processed audio with enhanced warmth
    """
    if boost_db <= 0 or boost_db > 4:
        return audio

    try:
        # Export to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_in:
            audio.export(temp_in.name, format="wav")
            temp_in_path = temp_in.name

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_out:
            temp_out_path = temp_out.name

        # Apply equalizer filter
        cmd = [
            "ffmpeg", "-y", "-i", temp_in_path,
            "-af", f"equalizer=f=140:width_type=o:width=2:g={boost_db}",
            temp_out_path
        ]

        subprocess.run(cmd, capture_output=True, check=True)

        # Load processed audio
        result = AudioSegment.from_wav(temp_out_path)

        # Cleanup
        os.unlink(temp_in_path)
        os.unlink(temp_out_path)

        return result

    except Exception as e:
        print(f"⚠️  Warmth boost failed: {e}")
        return audio


def generate_tts(
    text: str,
    output_path: str,
    voice: str = DEFAULT_VOICE,
    model: str = DEFAULT_MODEL,
    response_format: str = DEFAULT_FORMAT,
    speed: float = 1.0,
    pause_short: float = 0.25,
    pause_medium: float = 0.50,
    pause_long: float = 0.80,
    normalize: bool = False,
    warmth_db: float = 0.0
):
    """
    Generate TTS audio with natural pauses

    Args:
        text: Text to synthesize
        output_path: Output file path
        voice: Voice name
        model: TTS model
        response_format: Audio format
        speed: Playback speed
        pause_short/medium/long: Pause durations
        normalize: Apply normalization
        warmth_db: Low-frequency boost
    """
    print(f"🎙️  Generating audio with pauses...")
    print(f"   Voice: {voice}")
    print(f"   Model: {model}")
    print(f"   Format: {response_format}")
    print(f"   Speed: {speed}x")
    print(f"   Text length: {len(text)} characters")

    # Build audio with pauses
    audio = build_audio_with_pauses(
        text=text,
        pause_short=pause_short,
        pause_medium=pause_medium,
        pause_long=pause_long,
        model=model,
        voice=voice,
        response_format="mp3",  # Use MP3 for synthesis, convert to final format
        speed=speed,
        normalize=normalize,
        warmth_db=warmth_db
    )

    # Ensure output directory exists
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export to final format
    print(f"\n💾 Exporting to {response_format}...")
    audio.export(output_path, format=response_format)

    file_size = os.path.getsize(output_path) / (1024 * 1024)
    print(f"✅ Audio generated: {output_path}")
    print(f"   Duration: {len(audio)/1000:.1f} seconds")
    print(f"   File size: {file_size:.2f} MB")


def main():
    """CLI interface"""
    import argparse

    parser = argparse.ArgumentParser(
        description="OpenAI TTS - Generate audio with natural pauses",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Pause Profiles:
  broadcast: short=0.30s, medium=0.60s, long=1.00s (authoritative)
  natural:   short=0.25s, medium=0.50s, long=0.80s (default)
  tight:     short=0.15s, medium=0.35s, long=0.60s (fast-paced)

Voice Presets:
  {chr(10).join(f"  {name}: {info['description']}" for name, info in VOICE_PRESETS.items())}

Examples:
  # Basic with pauses
  {sys.argv[0]} input.txt --voice onyx --pause-profile natural

  # Broadcast preset
  {sys.argv[0]} input.txt --preset onyx_broadcast

  # Custom pauses
  {sys.argv[0]} input.txt --voice onyx --pause-short 0.2 --pause-medium 0.5
        """
    )

    parser.add_argument("input", help="Input text file")
    parser.add_argument("--output", "-o", help="Output file path")

    # Voice selection
    parser.add_argument("--voice", "-v", default=DEFAULT_VOICE, choices=ALL_VOICES,
                        help="Voice to use")
    parser.add_argument("--preset", choices=list(VOICE_PRESETS.keys()),
                        help="Use voice preset (overrides other voice settings)")

    # Model
    parser.add_argument("--model", "-m", default=DEFAULT_MODEL,
                        choices=["tts-1", "tts-1-hd"],
                        help="TTS model (tts-1-hd for higher quality)")

    # Audio format
    parser.add_argument("--format", "-f", default=DEFAULT_FORMAT,
                        choices=["mp3", "opus", "aac", "flac", "wav", "pcm"],
                        help="Output audio format")

    # Pause control
    parser.add_argument("--pause-profile", choices=list(PAUSE_PROFILES.keys()),
                        default="natural", help="Preset pause profile")
    parser.add_argument("--pause-short", type=float, help="Pause after commas (seconds)")
    parser.add_argument("--pause-medium", type=float, help="Pause after sentences (seconds)")
    parser.add_argument("--pause-long", type=float, help="Pause between paragraphs (seconds)")

    # Speed and effects
    parser.add_argument("--speed", "-s", type=float, default=1.0,
                        help="Playback speed (0.95-1.05 recommended)")
    parser.add_argument("--normalize", action="store_true",
                        help="Apply volume normalization")
    parser.add_argument("--warmth-db", type=float, default=0.0,
                        help="Low-frequency boost in dB (0-4, for warmth)")

    # Multiple voices
    parser.add_argument("--male-voices", action="store_true",
                        help="Generate all male voices (ignores --voice)")

    args = parser.parse_args()

    # Read input text
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            text = f.read().strip()
    except Exception as e:
        print(f"❌ Failed to read input file: {e}")
        return 1

    if not text:
        print("❌ Input file is empty")
        return 1

    # Apply default preset from config if no preset specified
    if not args.preset and not any(v in sys.argv for v in ['--voice', '-v']):
        default_preset_name = CONFIG.get('tts', {}).get('default_preset', 'onyx_natural')
        if default_preset_name in VOICE_PRESETS:
            args.preset = default_preset_name
            print(f"\n📋 Using default preset from config: {default_preset_name}")

    # Apply preset if specified
    if args.preset:
        preset = VOICE_PRESETS[args.preset]
        print(f"\n📋 Using preset: {args.preset}")
        print(f"   {preset['description']}")

        # Override with preset values (CLI args take precedence)
        if not any(v in sys.argv for v in ['--voice', '-v']):
            args.voice = preset.get("voice", args.voice)
        if not any(v in sys.argv for v in ['--model', '-m']):
            args.model = preset.get("model", args.model)
        if '--format' not in sys.argv and '-f' not in sys.argv:
            args.format = preset.get("format", args.format)
        if '--pause-profile' not in sys.argv:
            args.pause_profile = preset.get("pause_profile", args.pause_profile)
        if '--speed' not in sys.argv and '-s' not in sys.argv:
            args.speed = preset.get("speed", args.speed)

        # Apply individual pause values from preset if not specified
        if '--pause-short' not in sys.argv and 'pause_short' in preset:
            args.pause_short = preset['pause_short']
        if '--pause-medium' not in sys.argv and 'pause_medium' in preset:
            args.pause_medium = preset['pause_medium']
        if '--pause-long' not in sys.argv and 'pause_long' in preset:
            args.pause_long = preset['pause_long']

    # Get pause durations from profile
    profile = PAUSE_PROFILES[args.pause_profile]
    pause_short = args.pause_short if args.pause_short is not None else profile["short"]
    pause_medium = args.pause_medium if args.pause_medium is not None else profile["medium"]
    pause_long = args.pause_long if args.pause_long is not None else profile["long"]

    # Default output path
    if not args.output:
        base_name = Path(args.input).stem
        args.output = f"output/{base_name}_{args.voice}.{args.format}"

    # Generate audio
    try:
        generate_tts(
            text=text,
            output_path=args.output,
            voice=args.voice,
            model=args.model,
            response_format=args.format,
            speed=args.speed,
            pause_short=pause_short,
            pause_medium=pause_medium,
            pause_long=pause_long,
            normalize=args.normalize,
            warmth_db=args.warmth_db
        )
        return 0

    except Exception as e:
        print(f"\n❌ Generation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
