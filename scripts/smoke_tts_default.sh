#!/usr/bin/env bash
set -euo pipefail

# Smoke test for default Onyx Natural TTS profile
# Verifies that TTS works without any command-line arguments

echo "🧪 Smoke Test: Default Onyx Natural TTS"
echo "========================================"

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs 2>/dev/null || true)
fi

# Create test directory
slug="sample_onyx_$(date +%s)"
mkdir -p "work/$slug" "output/$slug"

# Create test text
cat > "work/$slug/tts_en.txt" << 'EOF'
This is a short smoke test for the default Onyx Natural TTS profile.
We expect calm, confident male narration with natural pauses between sentences.

The default settings should be: voice equals onyx, model equals tts-1, format equals wav, speed equals 1.0, and natural breathing profile with pauses of 0.25, 0.50, and 0.80 seconds.
EOF

echo ""
echo "📄 Test input: work/$slug/tts_en.txt"
echo "🎯 Expected: Onyx voice, tts-1 model, WAV format, natural pauses"
echo ""

# Run TTS without any arguments (should use defaults)
python3 scripts/openai_tts.py \
  "work/$slug/tts_en.txt" \
  --output "output/$slug/voice_en.wav"

echo ""

# Verify output exists
if [ -s "output/$slug/voice_en.wav" ]; then
    file_size=$(du -h "output/$slug/voice_en.wav" | cut -f1)
    echo "✅ Default Onyx Natural TTS OK"
    echo "   Output: output/$slug/voice_en.wav"
    echo "   Size: $file_size"
    echo ""
    echo "🎧 Play audio:"
    echo "   afplay output/$slug/voice_en.wav"
else
    echo "❌ FAILED: Output file not created or empty"
    exit 1
fi
