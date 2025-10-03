#!/usr/bin/env bash
set -euo pipefail

MODEL_PATH=${MODEL_PATH:-assets/voices/en_US-amy-medium.onnx}
INPUT_TXT=${1:-work/tts_en.txt}
OUT_WAV=${2:-output/voice_en.wav}

test -f "$MODEL_PATH" || { echo "Model not found: $MODEL_PATH"; exit 1; }
test -f "$INPUT_TXT" || { echo "Input text not found: $INPUT_TXT"; exit 1; }

source .venv/bin/activate
python -m piper \
  --model "$MODEL_PATH" \
  --output_file "$OUT_WAV" \
  --sentence_silence 0.2 \
  < "$INPUT_TXT"

echo "OK: generated $OUT_WAV"
