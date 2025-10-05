#!/usr/bin/env bash
# TTS Pipeline with Piper synthesis, silence insertion, and concat
# Dependencies: piper, ffmpeg, python3 (for JSON parsing)

set -euo pipefail

# Activate virtual environment if it exists
if [[ -f ".venv/bin/activate" ]]; then
    source .venv/bin/activate
fi

# Default values
CONFIG="config.yaml"
OUT_WAV=""
SLUG=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --config)
            CONFIG="$2"
            shift 2
            ;;
        --out)
            OUT_WAV="$2"
            shift 2
            ;;
        *)
            INPUT_TXT="$1"
            shift
            ;;
    esac
done

if [[ -z "${INPUT_TXT:-}" ]]; then
    echo "Usage: $0 work/<slug>.txt [--config config.yaml] [--out output/<slug>.wav]"
    exit 1
fi

# Derive slug from input filename
SLUG=$(basename "$INPUT_TXT" .txt)
MANIFEST="work/${SLUG}.manifest.jsonl"

# Check if manifest exists, if not run prepare script
if [[ ! -f "$MANIFEST" ]]; then
    echo "Manifest not found, running prepare_tts_text.py..."
    python3 scripts/prepare_tts_text.py "$INPUT_TXT" --config "$CONFIG"
fi

if [[ ! -f "$MANIFEST" ]]; then
    echo "Error: Failed to generate manifest: $MANIFEST"
    exit 1
fi

# Load config using Python (YAML parsing)
read -r MODEL_PATH SAMPLE_RATE PAUSE_SHORT PAUSE_MEDIUM PAUSE_LONG < <(python3 -c "
import yaml
with open('$CONFIG', 'r') as f:
    cfg = yaml.safe_load(f)
tts = cfg.get('tts', {})
print(tts.get('voice_model_path', ''), tts.get('sample_rate', 22050),
      tts['pause']['short'], tts['pause']['medium'], tts['pause']['long'])
")

# Validate model path
if [[ -z "$MODEL_PATH" ]]; then
    echo "Error: voice_model_path not set in config"
    exit 1
fi

if [[ ! -f "$MODEL_PATH" ]]; then
    echo "Error: Model file not found: $MODEL_PATH"
    echo "Please download the Piper voice model (.onnx file) and update config.yaml"
    exit 1
fi

# Setup output
if [[ -z "$OUT_WAV" ]]; then
    OUT_WAV="output/${SLUG}.wav"
fi

WORK_DIR="output/${SLUG}"
mkdir -p "$WORK_DIR"

# Logging
LOG_FILE="logs/tts.log"
mkdir -p logs

echo "$(date '+%Y-%m-%d %H:%M:%S') | INFO | synth_start | slug=$SLUG | model=$MODEL_PATH | sr=$SAMPLE_RATE" >> "$LOG_FILE"

# Counters
TOTAL_ITEMS=0
SUCCESS_COUNT=0
FAIL_COUNT=0

# Sample rate detection (will be set after first successful synthesis)
ACTUAL_SR=""

# Generate concat list
CONCAT_LIST="$WORK_DIR/concat.txt"
> "$CONCAT_LIST"

# Process each line in manifest
while IFS= read -r line; do
    # Parse JSON using Python
    IDX=$(echo "$line" | python3 -c "import sys, json; print(json.load(sys.stdin)['idx'])")
    TEXT=$(echo "$line" | python3 -c "import sys, json; print(json.load(sys.stdin)['text'])")
    PAUSE=$(echo "$line" | python3 -c "import sys, json; print(json.load(sys.stdin)['pause_after'])")

    TOTAL_ITEMS=$((TOTAL_ITEMS + 1))

    # Zero-padded index
    IDX_PAD=$(printf "%04d" "$IDX")

    TXT_FILE="$WORK_DIR/${IDX_PAD}.txt"
    WAV_FILE="$WORK_DIR/${IDX_PAD}.wav"
    SIL_FILE="$WORK_DIR/${IDX_PAD}_sil.wav"

    # Write text to file
    echo "$TEXT" > "$TXT_FILE"

    # Synthesize with Piper (with retry)
    RETRIES=3
    SUCCESS=0
    for attempt in $(seq 1 $RETRIES); do
        if piper --model "$MODEL_PATH" --output_file "$WAV_FILE" < "$TXT_FILE" 2>/dev/null; then
            SUCCESS=1
            break
        else
            echo "Warning: Piper synthesis failed for idx=$IDX (attempt $attempt/$RETRIES)"
            sleep 0.5
        fi
    done

    if [[ $SUCCESS -eq 0 ]]; then
        echo "Error: Failed to synthesize idx=$IDX after $RETRIES attempts"
        echo "$(date '+%Y-%m-%d %H:%M:%S') | ERROR | synth_failed | idx=$IDX | text=${TEXT:0:50}..." >> "$LOG_FILE"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        continue
    fi

    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))

    # Detect actual sample rate from first synthesized file
    if [[ -z "$ACTUAL_SR" ]]; then
        ACTUAL_SR=$(ffprobe -v error -select_streams a:0 -show_entries stream=sample_rate \
            -of default=noprint_wrappers=1:nokey=1 "$WAV_FILE" 2>/dev/null || echo "$SAMPLE_RATE")
        echo "Detected sample rate: ${ACTUAL_SR}Hz"
    fi

    # Add to concat list
    echo "file '${IDX_PAD}.wav'" >> "$CONCAT_LIST"

    # Generate silence based on pause type
    if [[ "$PAUSE" != "none" ]]; then
        case "$PAUSE" in
            short)
                PAUSE_DUR=$PAUSE_SHORT
                ;;
            medium)
                PAUSE_DUR=$PAUSE_MEDIUM
                ;;
            long)
                PAUSE_DUR=$PAUSE_LONG
                ;;
            *)
                PAUSE_DUR=0
                ;;
        esac

        # Generate silence WAV (use bc for float comparison if available, otherwise use awk)
        if command -v bc &> /dev/null; then
            HAS_PAUSE=$(echo "$PAUSE_DUR > 0" | bc -l)
        else
            HAS_PAUSE=$(awk -v dur="$PAUSE_DUR" 'BEGIN { print (dur > 0) ? 1 : 0 }')
        fi

        if [[ $HAS_PAUSE -eq 1 ]]; then
            # Generate silence WAV using actual sample rate (not config sample rate)
            ffmpeg -f lavfi -i anullsrc=r=${ACTUAL_SR}:cl=mono -t "$PAUSE_DUR" -q:a 9 -acodec pcm_s16le "$SIL_FILE" -y 2>/dev/null

            # Add silence to concat list
            echo "file '${IDX_PAD}_sil.wav'" >> "$CONCAT_LIST"
        fi
    fi

done < "$MANIFEST"

# Merge all segments
if [[ $SUCCESS_COUNT -eq 0 ]]; then
    echo "Error: No segments successfully synthesized"
    exit 1
fi

echo "Merging $SUCCESS_COUNT segments..."
ffmpeg -f concat -safe 0 -i "$CONCAT_LIST" -c copy "$OUT_WAV" -y 2>/dev/null

# Get duration
DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$OUT_WAV" 2>/dev/null || echo "0")

# Log
echo "$(date '+%Y-%m-%d %H:%M:%S') | INFO | merged | slug=$SLUG | out=$OUT_WAV | items=$SUCCESS_COUNT | failed=$FAIL_COUNT | seconds=$DURATION" >> "$LOG_FILE"

echo "✅ TTS synthesis complete: $OUT_WAV"
echo "   Synthesized: $SUCCESS_COUNT/$TOTAL_ITEMS segments"
echo "   Duration: ${DURATION}s"

exit 0
