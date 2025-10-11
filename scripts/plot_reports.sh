#!/usr/bin/env bash
#
# Plot Reports - Convenient wrapper for plot_tts_metrics.py
# Usage: ./scripts/plot_reports.sh [csv_glob] [output_dir] [rolling_window]
#
set -euo pipefail

CSVG="${1:-output/reports/tts_compare_*.csv}"
OUTD="${2:-output/reports/plots}"
ROLL="${3:-3}"

# Use venv python if available
if [ -f .venv/bin/python3 ]; then
    PYTHON=.venv/bin/python3
else
    PYTHON=python3
fi

$PYTHON scripts/plot_tts_metrics.py --csv-glob "$CSVG" --outdir "$OUTD" --rolling "$ROLL"

echo "✅ Plot images: $OUTD"
