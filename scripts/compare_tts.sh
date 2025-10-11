#!/usr/bin/env bash
#
# Compare TTS - Convenient wrapper for compare_tts.py
# Usage: ./scripts/compare_tts.sh input.txt [output_dir]
#

set -euo pipefail

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Activate virtual environment if it exists
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
fi

# Use venv python if available
if [ -f .venv/bin/python3 ]; then
    PYTHON=.venv/bin/python3
else
    PYTHON=python3
fi

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs 2>/dev/null || true)
fi

# Arguments
INPUT="${1:-tests/data/sample_short.txt}"
OUTDIR="${2:-output/compare_run_$(date +%s)}"

echo "🎙️  TTS Comparison"
echo "   Input: $INPUT"
echo "   Output: $OUTDIR"
echo ""

# Run comparison
$PYTHON scripts/compare_tts.py "$INPUT" \
  --outdir "$OUTDIR" \
  --style-prefix "Speak calmly and confidently, as if narrating a professional video." \
  --pause-profile natural \
  --fade-ms 20 \
  --crossfade-ms 50 \
  --max-chars 800 \
  --openai-voice onyx \
  --openai-model tts-1 \
  --openai-format wav \
  --ab-swap-sec 8

echo ""
echo "✅ Comparison complete!"
echo ""
echo "Generated files:"
ls -lh "$OUTDIR"/*.wav 2>/dev/null || echo "  (no WAV files generated)"
echo ""
echo "Comparison report:"
cat work/cmp_*/compare_report.json | $PYTHON -m json.tool 2>/dev/null || echo "  (report not found)"
echo ""
