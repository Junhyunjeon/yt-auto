#!/usr/bin/env bash
set -euo pipefail

# 옵션 로딩 (있으면 읽고, 없어도 무시)
[ -f "scripts/.tts_env" ] && source scripts/.tts_env

# 기본값 설정 (환경변수 또는 .tts_env로 덮어쓸 수 있음)
MODEL_PATH=${MODEL_PATH:-assets/voices/en_GB-northern_english_male-medium.onnx}
INPUT_TXT=${1:-work/tts_en.txt}
OUT_WAV=${2:-${OUT_WAV_DEFAULT:-output/mail_medium_northern.wav}}

LENGTH_SCALE=${LENGTH_SCALE:-1.03}
NOISE_SCALE=${NOISE_SCALE:-0.30}
NOISE_W_SCALE=${NOISE_W_SCALE:-0.70}
SENTENCE_SILENCE=${SENTENCE_SILENCE:-0.25}
VOLUME=${VOLUME:-1.0}

test -f "$MODEL_PATH" || { echo "Model not found: $MODEL_PATH"; exit 1; }
test -f "$INPUT_TXT" || { echo "Input text not found: $INPUT_TXT"; exit 1; }

source .venv/bin/activate
python -m piper \
  --model "$MODEL_PATH" \
  --output_file "$OUT_WAV" \
  --length-scale "$LENGTH_SCALE" \
  --noise-scale "$NOISE_SCALE" \
  --noise-w-scale "$NOISE_W_SCALE" \
  --sentence-silence "$SENTENCE_SILENCE" \
  --volume "$VOLUME" \
  < "$INPUT_TXT"

echo "OK: generated $OUT_WAV"
