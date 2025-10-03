#!/usr/bin/env bash
set -euo pipefail
[ -f "scripts/.tts_env" ] && source scripts/.tts_env

IN_WAV=${1:-${OUT_WAV_DEFAULT:-output/mail_medium_northern.wav}}
OUT_MP4=${2:-output/video_en.mp4}

test -f "$IN_WAV" || { echo "Input wav not found: $IN_WAV"; exit 1; }

ffmpeg -y -i "$IN_WAV" \
  -filter_complex "[0:a]showwaves=s=1920x1080:mode=cline,format=yuv420p[v]" \
  -map "[v]" -map 0:a \
  -r 30 "$OUT_MP4"

echo "OK: generated $OUT_MP4"
