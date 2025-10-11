#!/usr/bin/env python3
"""
Compare TTS - Run OpenAI and Piper TTS side-by-side for comparison
Generates matched audio files and comprehensive comparison report
"""

import os
import sys
import json
import argparse
import subprocess
import uuid
from pathlib import Path
from loguru import logger
from pydub import AudioSegment

# Import common TTS utilities
sys.path.insert(0, str(Path(__file__).parent))
from tts_common import measure, match_volume


def run_command(cmd: list, allow_fail: bool = False) -> subprocess.CompletedProcess:
    """
    Run a shell command and handle errors

    Args:
        cmd: Command as list of strings
        allow_fail: If True, don't raise on non-zero exit

    Returns:
        CompletedProcess object
    """
    logger.info(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        if not allow_fail:
            logger.error(f"Command failed: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
        else:
            logger.warning(f"Command failed (allowed): {result.stderr[:200]}")

    return result


def main():
    """CLI interface"""
    parser = argparse.ArgumentParser(
        description="Compare OpenAI and Piper TTS with unified processing"
    )

    parser.add_argument("input", help="Input text file")
    parser.add_argument("--outdir", required=True, help="Output directory for comparison files")

    # Shared options
    parser.add_argument("--style-prefix", help="Style instruction for both engines")
    parser.add_argument("--pause-profile", default="natural", help="Pause profile")
    parser.add_argument("--fade-ms", type=int, default=20, help="Fade duration")
    parser.add_argument("--crossfade-ms", type=int, default=50, help="Crossfade duration")
    parser.add_argument("--max-chars", type=int, default=800, help="Max chars per segment")

    # OpenAI specific
    parser.add_argument("--openai-voice", default="onyx", help="OpenAI voice")
    parser.add_argument("--openai-model", default="tts-1", help="OpenAI model")
    parser.add_argument("--openai-format", default="wav", help="OpenAI output format")

    # Piper specific
    parser.add_argument("--piper-voice", help="Piper voice model path")

    # AB mixing
    parser.add_argument("--ab-swap-sec", type=int, default=0,
                        help="If >0, create AB swap mix (seconds per segment)")

    args = parser.parse_args()

    # Setup directories
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    slug = f"cmp_{uuid.uuid4().hex[:8]}"
    workdir = Path("work") / slug
    workdir.mkdir(parents=True, exist_ok=True)

    # Prepare input text
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        return 1

    text = input_path.read_text(encoding="utf-8")

    if args.style_prefix:
        text = f"{args.style_prefix.strip()}\n\n{text}"

    # Write processed input
    tmp_input = workdir / "input.txt"
    tmp_input.write_text(text, encoding="utf-8")

    logger.info(f"📊 Starting TTS comparison: {input_path.name}")
    logger.info(f"   Output directory: {outdir}")
    logger.info(f"   Work directory: {workdir}")

    # === 1) OpenAI TTS ===
    logger.info("\n🎙️  Generating with OpenAI TTS...")
    openai_out = outdir / "openai.wav"
    openai_metrics = workdir / "metrics_openai.json"

    openai_cmd = [
        sys.executable, "scripts/openai_tts.py", str(tmp_input),
        "--output", str(openai_out),
        "--json-out", str(openai_metrics),
        "--voice", args.openai_voice,
        "--model", args.openai_model,
        "--format", args.openai_format,
        "--pause-profile", args.pause_profile,
        "--fade-ms", str(args.fade_ms),
        "--crossfade-ms", str(args.crossfade_ms),
        "--max-chars", str(args.max_chars)
    ]

    run_command(openai_cmd)

    # === 2) Piper TTS (optional) ===
    logger.info("\n🎙️  Generating with Piper TTS...")
    piper_out = outdir / "piper.wav"
    piper_metrics = workdir / "metrics_piper.json"

    piper_voice = args.piper_voice or os.getenv("PIPER_VOICE", str(Path.home() / "piper_models" / "en_US-amy-medium.onnx"))

    piper_cmd = [
        sys.executable, "scripts/piper_tts.py", str(tmp_input),
        "--output", str(piper_out),
        "--json-out", str(piper_metrics),
        "--voice", piper_voice,
        "--pause-profile", args.pause_profile,
        "--fade-ms", str(args.fade_ms),
        "--crossfade-ms", str(args.crossfade_ms),
        "--max-chars", str(args.max_chars)
    ]

    piper_result = run_command(piper_cmd, allow_fail=True)
    piper_ok = (piper_result.returncode == 0 and
                piper_out.exists() and
                piper_out.stat().st_size > 0)

    if not piper_ok:
        logger.warning("⚠️ Piper TTS not available - comparison will be OpenAI only")

    # === 3) Volume matching ===
    logger.info("\n🔊 Creating volume-matched versions...")

    # Load OpenAI audio as reference
    openai_audio = AudioSegment.from_file(str(openai_out))
    openai_match_path = outdir / "openai_match.wav"

    # Create matched versions
    if piper_ok:
        piper_audio = AudioSegment.from_file(str(piper_out))
        matched_openai, matched_piper = match_volume(openai_audio, piper_audio, max_diff_db=1.5)

        matched_openai.export(str(openai_match_path), format="wav")
        piper_match_path = outdir / "piper_match.wav"
        matched_piper.export(str(piper_match_path), format="wav")

        logger.info(f"   OpenAI matched: {openai_match_path.name}")
        logger.info(f"   Piper matched: {piper_match_path.name}")
    else:
        # Just copy OpenAI if no Piper
        openai_audio.export(str(openai_match_path), format="wav")
        logger.info(f"   OpenAI only: {openai_match_path.name}")

    # === 4) Generate comparison report ===
    logger.info("\n📊 Generating comparison report...")

    report = {
        "input_file": str(input_path),
        "slug": slug,
        "settings": {
            "pause_profile": args.pause_profile,
            "fade_ms": args.fade_ms,
            "crossfade_ms": args.crossfade_ms,
            "max_chars": args.max_chars,
            "style_prefix": args.style_prefix or None
        },
        "openai": {},
        "piper": {},
        "comparison": {}
    }

    # Load OpenAI metrics
    if openai_metrics.exists():
        report["openai"] = json.loads(openai_metrics.read_text())

    # Load Piper metrics
    if piper_ok and piper_metrics.exists():
        report["piper"] = json.loads(piper_metrics.read_text())
    else:
        report["piper"] = {"status": "skipped", "reason": "Piper not available"}

    # Add comparison stats
    if piper_ok:
        openai_dur = report["openai"].get("duration_sec", 0)
        piper_dur = report["piper"].get("duration_sec", 0)
        openai_rms = report["openai"].get("rms_dbfs", 0)
        piper_rms = report["piper"].get("rms_dbfs", 0)

        report["comparison"] = {
            "duration_diff_sec": round(openai_dur - piper_dur, 2),
            "duration_ratio": round(openai_dur / piper_dur, 3) if piper_dur > 0 else None,
            "rms_diff_db": round(abs(openai_rms - piper_rms), 2),
            "faster_engine": "openai" if openai_dur < piper_dur else "piper"
        }

    # Save report
    report_path = workdir / "compare_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    logger.success(f"✅ Comparison report: {report_path}")

    # === 5) Optional AB swap mix ===
    if args.ab_swap_sec > 0 and piper_ok:
        logger.info(f"\n🔀 Creating AB swap mix ({args.ab_swap_sec}s segments)...")

        openai_matched = AudioSegment.from_file(str(openai_match_path))
        piper_matched = AudioSegment.from_file(str(piper_match_path))

        ab_mix = AudioSegment.silent(duration=0)
        step_ms = args.ab_swap_sec * 1000
        pos = 0
        max_len = min(len(openai_matched), len(piper_matched))

        while pos < max_len:
            # Add OpenAI segment
            ab_mix += openai_matched[pos:pos + step_ms]
            # Add Piper segment
            ab_mix += piper_matched[pos:pos + step_ms]
            pos += step_ms

        ab_out = outdir / "AB_openai_piper.wav"
        ab_mix.export(str(ab_out), format="wav")

        logger.success(f"✅ AB swap mix: {ab_out}")

    # === Summary ===
    logger.info("\n" + "=" * 60)
    logger.success("📊 Comparison Complete!")
    logger.info(f"\nGenerated files in {outdir}:")
    logger.info(f"  - openai.wav, openai_match.wav")
    if piper_ok:
        logger.info(f"  - piper.wav, piper_match.wav")
        if args.ab_swap_sec > 0:
            logger.info(f"  - AB_openai_piper.wav")
    logger.info(f"\nReport: {report_path}")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
