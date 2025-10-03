#!/usr/bin/env bash
set -euo pipefail
[ -f "scripts/.tts_env" ] && source scripts/.tts_env
source .venv/bin/activate

MODEL_PATH=${MODEL_PATH:-assets/voices/en_GB-northern_english_male-medium.onnx}
OUT_WAV=${OUT_WAV_DEFAULT:-output/mail_medium_northern.wav}
TEXT="${*:-This is a default line for TTS.}"

python -m piper \
  --model "$MODEL_PATH" \
  --output_file "$OUT_WAV" \
  --length-scale "${LENGTH_SCALE:-1.03}" \
  --noise-scale "${NOISE_SCALE:-0.30}" \
  --noise-w-scale "${NOISE_W_SCALE:-0.70}" \
  --sentence-silence "${SENTENCE_SILENCE:-0.25}" \
  --volume "${VOLUME:-1.0}" \
  <<< "$TEXT"

echo "OK: generated $OUT_WAV"
