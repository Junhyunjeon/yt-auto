#!/bin/bash
# YouTube Automation Pipeline Runner

set -e

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
fi

# Use venv python if available
if [ -f .venv/bin/python3 ]; then
    PYTHON=.venv/bin/python3
elif [ -f .venv/bin/python ]; then
    PYTHON=.venv/bin/python
else
    PYTHON=python3
fi

if [ $# -eq 0 ]; then
    echo "Usage: $0 <input_file>"
    echo "Example: $0 input/my-script.txt"
    exit 1
fi

INPUT_FILE="$1"

if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: File $INPUT_FILE not found"
    exit 1
fi

echo "🚀 Starting YouTube automation pipeline..."

echo "📝 Step 1: Preparing input..."
SLUG=$($PYTHON scripts/01_prepare.py "$INPUT_FILE")
echo "Generated slug: $SLUG"

echo "🌐 Step 2: Translating to English..."
$PYTHON scripts/02_translate.py "$SLUG"

echo "✏️  Step 3: Editing English content..."
TITLE=$($PYTHON scripts/03_edit_en.py "$SLUG")
echo "Generated title: $TITLE"

echo "🔊 Step 4: Generating speech..."
$PYTHON scripts/04_tts.py "$SLUG"

echo "🎬 Step 5: Creating video..."
$PYTHON scripts/05_video.py "$SLUG" --title-text "$TITLE"

echo ""
echo "✅ Pipeline completed!"
echo "📁 Output files:"
echo "   - Markdown: work/$SLUG/post_en.md"
echo "   - Audio: output/$SLUG/voice_en.wav"
echo "   - Video: output/$SLUG/video_en.mp4"
echo ""
echo "🎯 To publish to WordPress (if configured):"
echo "   $PYTHON scripts/06_publish.py wordpress $SLUG"