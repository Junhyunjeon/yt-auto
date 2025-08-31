#!/bin/bash
# YouTube Automation Pipeline Runner

set -e
cd ~/yt-auto
source .venv/bin/activate

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
SLUG=$(python scripts/01_prepare.py "$INPUT_FILE")
echo "Generated slug: $SLUG"

echo "🌐 Step 2: Translating to English..."
python scripts/02_translate.py "$SLUG"

echo "✏️  Step 3: Editing English content..."
TITLE=$(python scripts/03_edit_en.py "$SLUG")
echo "Generated title: $TITLE"

echo "🔊 Step 4: Generating speech..."
python scripts/04_tts.py "$SLUG"

echo "🎬 Step 5: Creating video..."
python scripts/05_video.py "$SLUG" --title-text "$TITLE"

echo ""
echo "✅ Pipeline completed!"
echo "📁 Output files:"
echo "   - Markdown: work/$SLUG/post_en.md"
echo "   - Audio: output/$SLUG/voice_en.wav"
echo "   - Video: output/$SLUG/video_en.mp4"
echo ""
echo "🎯 To publish to WordPress (if configured):"
echo "   python scripts/06_publish.py wordpress $SLUG"