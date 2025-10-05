#!/usr/bin/env bash
# Download and install Piper voice models
# Usage: ./scripts/get_piper_voice.sh <voice-name>
# Example: ./scripts/get_piper_voice.sh en_GB-northern_english_male-medium

set -euo pipefail

VOICE_NAME="${1:-}"
VOICES_DIR="assets/voices"

if [[ -z "$VOICE_NAME" ]]; then
    echo "Usage: $0 <voice-name>"
    echo ""
    echo "Examples:"
    echo "  $0 en_GB-northern_english_male-medium"
    echo "  $0 en_US-amy-medium"
    echo "  $0 en_US-ryan-high"
    echo ""
    echo "Available voices: https://github.com/rhasspy/piper/blob/master/VOICES.md"
    exit 1
fi

# Create voices directory
mkdir -p "$VOICES_DIR"

# Piper voice download base URL
BASE_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/en"

# Determine language prefix (en_GB, en_US, etc.)
LANG_PREFIX=$(echo "$VOICE_NAME" | cut -d'-' -f1-2)

# Model files to download
ONNX_FILE="${VOICE_NAME}.onnx"
JSON_FILE="${VOICE_NAME}.onnx.json"

echo "Downloading Piper voice: $VOICE_NAME"
echo "Target directory: $VOICES_DIR"

# Download .onnx model
if [[ -f "$VOICES_DIR/$ONNX_FILE" ]]; then
    echo "✓ Model already exists: $VOICES_DIR/$ONNX_FILE"
else
    echo "Downloading $ONNX_FILE..."
    curl -L -o "$VOICES_DIR/$ONNX_FILE" \
        "$BASE_URL/$LANG_PREFIX/$VOICE_NAME/$ONNX_FILE" || {
        echo "Error: Failed to download $ONNX_FILE"
        echo "Check voice name or visit: https://github.com/rhasspy/piper/blob/master/VOICES.md"
        exit 1
    }
    echo "✓ Downloaded: $ONNX_FILE"
fi

# Download .onnx.json config
if [[ -f "$VOICES_DIR/$JSON_FILE" ]]; then
    echo "✓ Config already exists: $VOICES_DIR/$JSON_FILE"
else
    echo "Downloading $JSON_FILE..."
    curl -L -o "$VOICES_DIR/$JSON_FILE" \
        "$BASE_URL/$LANG_PREFIX/$VOICE_NAME/$JSON_FILE" || {
        echo "Warning: Failed to download $JSON_FILE (optional)"
    }
    echo "✓ Downloaded: $JSON_FILE"
fi

echo ""
echo "✅ Voice installation complete!"
echo "   Model: $VOICES_DIR/$ONNX_FILE"
echo ""
echo "Update config.yaml:"
echo "  tts:"
echo "    voice_model_path: $VOICES_DIR/$ONNX_FILE"
echo ""
