#!/usr/bin/env bash
#
# Export Reports - Convenient wrapper for compare_report_to_md.py
# Usage: ./scripts/export_reports.sh [output_dir] [work_glob]
#
set -euo pipefail

OUTDIR="${1:-output/reports}"
WORKGLOB="${2:-work/*/compare_report.json}"

python3 scripts/compare_report_to_md.py --outdir "$OUTDIR" --work-glob "$WORKGLOB"

echo "✅ Reports exported to: $OUTDIR"
