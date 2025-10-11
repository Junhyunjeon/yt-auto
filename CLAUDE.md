# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTube Automation Pipeline - An offline pipeline that transforms Korean scripts into English content with audio and video outputs. The system processes Korean text through translation, content generation, text-to-speech, and video creation stages, with integrated TTS quality management.

**Key Characteristics:**
- Offline-first design (Argos Translate, Piper TTS)
- Sequential processing pipeline with 6 numbered scripts
- TTS quality management system (comparison, reporting, visualization)
- Configuration-driven via `config.yaml` and `.env`
- Hard-fail philosophy on misconfiguration (translation/TTS must work or halt)
- macOS-focused (tested on Mac Mini with Apple Silicon)

## Pipeline Architecture

The pipeline follows a strictly sequential 6-stage process:

1. **01_prepare.py** - Cleans Korean input, generates slug, creates work directory
   - Input: `input/*.txt` (Korean text)
   - Output: `work/{slug}/clean_ko.txt`
   - Prints slug to stdout for shell capture

2. **02_translate.py** - Translates Korean to English using Argos
   - Input: `work/{slug}/clean_ko.txt`
   - Output: `work/{slug}/draft_en.txt`
   - **CRITICAL**: Hard-fails if lzma module missing or Argos unavailable
   - No fallback mode - must be properly configured

3. **03_edit_en.py** - Formats English content as structured markdown
   - Input: `work/{slug}/draft_en.txt`
   - Output: `work/{slug}/post_en.md` with title, body, tags
   - Prints title to stdout for shell capture
   - Requires `seo.title_prefix` and `seo.tags` in config.yaml

4. **04_tts.py** - Generates speech using Piper TTS
   - Input: `work/{slug}/post_en.md`
   - Output: `output/{slug}/voice_en.wav`
   - **CRITICAL**: Hard-fails if piper binary or model (.onnx) not found
   - Validates PIPER_EXEC path and PIPER_MODEL file before proceeding
   - Creates intermediate `work/{slug}/tts_en.txt` (body only, no headers)

5. **05_video.py** - Creates video with waveform and title overlay
   - Input: `output/{slug}/voice_en.wav` + background image
   - Output: `output/{slug}/video_en.mp4`
   - Generates black background if `video.bg_image` missing
   - Fallback mode if showwaves filter fails (simple title overlay only)

6. **06_publish.py** - Optional WordPress/YouTube publishing
   - WordPress: Requires `publish.wordpress.enabled=true` in config
   - YouTube: Stub implementation (not functional yet)

## Essential Commands

### Running the Pipeline

```bash
# Full pipeline (recommended)
./run_pipeline.sh input/my-script.txt

# Manual step-by-step (advanced)
source .venv/bin/activate
SLUG=$(python scripts/01_prepare.py input/my-script.txt)
python scripts/02_translate.py "$SLUG"
TITLE=$(python scripts/03_edit_en.py "$SLUG")
python scripts/04_tts.py "$SLUG"
python scripts/05_video.py "$SLUG" --title-text "$TITLE"

# Publish to WordPress (if configured)
python scripts/06_publish.py wordpress "$SLUG"
```

### Testing & Validation

```bash
# Validate system dependencies (lzma, piper, ffmpeg)
./scripts/diagnose.sh

# Check individual components
python -c "import lzma; print('lzma OK')"
which piper && piper --help
which ffmpeg && ffmpeg -version

# Run TTS comparison smoke test
./scripts/smoke_tts_common.sh

# Run full quality management workflow
./scripts/compare_tts.sh "Hello world" test01
./scripts/export_reports.sh
./scripts/plot_reports.sh
```

### Development Setup

```bash
# Environment setup
cp config.yaml.example config.yaml
cp .env.example .env

# Edit .env to set:
# - PIPER_EXEC (default: piper from PATH)
# - PIPER_MODEL (default: ~/piper_models/en_US-amy-medium.onnx)

# Install dependencies
source .venv/bin/activate
pip install -r requirements.txt

# Download Piper voice model
mkdir -p ~/piper_models
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx -P ~/piper_models/
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json -P ~/piper_models/
```

## Configuration System

**config.yaml** - Main configuration (checked into git as example)
- `translator`: "argos" (google not implemented)
- `use_api`: false (API mode disabled)
- `tts.engine`: "piper" (elevenlabs not implemented)
- `video.bg_image`: Path to background (auto-generates black if missing)
- `seo.title_prefix` and `seo.tags`: Required for 03_edit_en.py
- `publish.wordpress.enabled` / `publish.youtube.enabled`: Must be true to publish

**.env** - Environment variables (gitignored)
- `PIPER_EXEC`: Path to piper binary (default: "piper")
- `PIPER_MODEL`: Path to .onnx model file (default: ~/piper_models/en_US-amy-medium.onnx)

Environment variable expansion happens in Python using `os.path.expandvars()` and `os.path.expanduser()`.

## Critical Dependencies

### Python lzma Module
The `_lzma` module is required for Argos Translate. If missing:
1. Install xz: `brew install xz`
2. Reinstall Python with xz support:
   - pyenv users: `pyenv install --force $(pyenv version-name)`
   - Or use system Python with xz available

Script 02_translate.py will hard-fail with detailed fix instructions if lzma is unavailable.

### Piper TTS Setup
Piper requires both binary and voice model:
1. Binary: `brew install piper` or download from releases
2. Model: Download .onnx + .onnx.json from HuggingFace (see setup commands)
3. Configure paths in .env

Script 04_tts.py validates both before proceeding and hard-fails with fix instructions.

### FFmpeg
Used for video generation (05_video.py):
- `brew install ffmpeg`
- Must support h264 codec, aac audio, showwaves filter
- Fallback mode available if showwaves fails

## Key Design Patterns

**Slug-Based Organization**: Each input file generates a slug (via `slugify()`) that determines work/output directory names. The slug is captured from stdout in shell scripts.

**Hard-Fail on Misconfiguration**: Translation (02) and TTS (04) scripts validate dependencies and exit with detailed fix instructions rather than using dummy/fallback mode. This ensures production quality.

**Config Loading Pattern**: Every script uses:
```python
def load_cfg():
    with open("config.yaml","r") as f: return yaml.safe_load(f)
```

**Stdout Capture for Shell**: Scripts 01_prepare.py and 03_edit_en.py print slug/title to stdout (via `print()`) for bash variable capture. All other output goes through `loguru.logger`.

**Directory Structure Contract**:
- `input/` - User-provided Korean .txt files
- `work/{slug}/` - Intermediate processing files (clean_ko.txt, draft_en.txt, post_en.md, tts_en.txt)
- `work/cmp_*/` - TTS comparison outputs (openai.wav, piper.wav, compare_report.json)
- `output/{slug}/` - Final outputs (voice_en.wav, video_en.mp4)
- `output/reports/` - Aggregated CSV/Markdown reports
- `output/reports/plots/` - Visualization charts (PNG)
- `assets/` - Optional resources (background images)

## Testing Changes

When modifying pipeline scripts:

1. **Test individual script**: Run with a known-good slug from previous run
   ```bash
   python scripts/04_tts.py test-slug
   ```

2. **Test full pipeline**: Use small input file
   ```bash
   echo "테스트 입력" > input/test.txt
   ./run_pipeline.sh input/test.txt
   ```

3. **Verify outputs**: Check work/ and output/ directories for expected files

4. **Test error paths**: Remove piper binary, model, or lzma to verify hard-fail messages

## Common Gotchas

### Pipeline Scripts
- **Script 03_edit_en.py requires seo config**: Will fail if `config.yaml` missing `seo.title_prefix` or `seo.tags`
- **Video background**: If `video.bg_image` path invalid, script auto-generates black.png (not an error)
- **Shell variable capture**: Scripts 01 and 03 must print to stdout (not logger) for `$(...)` capture to work
- **Environment variables in config.yaml**: Use `${VAR:-default}` syntax, expanded by Python at runtime
- **Piper model files**: Need both .onnx AND .onnx.json in same directory
- **WordPress publish**: Requires REST API authentication, not WP-CLI

### TTS Quality Management
- **Audio files ARE generated**: `compare_tts.py` creates openai.wav, piper.wav, and volume-matched versions
- **Graceful degradation**: System works with OpenAI only when Piper unavailable
- **Slug field priority**: Report aggregation uses `slug` field first, falls back to input filename stem
- **matplotlib in venv**: Shell wrappers auto-detect .venv/bin/python3 to find matplotlib
- **Headless mode**: Charts use Agg backend for CI/CD (no display server needed)
- **CSV format**: Standard library csv module (no pandas) - clean, fast, zero dependencies

## TTS Quality Management System

The project includes a comprehensive TTS quality management system for comparing, analyzing, and visualizing TTS engine performance.

### TTS Comparison (`compare_tts.py`)

Compares OpenAI TTS and Piper TTS outputs with detailed audio analysis:

```bash
# Compare two TTS engines
python scripts/compare_tts.py \
  --text "Hello world" \
  --slug "test01" \
  --outdir "work/cmp_20250611_140523"
```

**Outputs Generated:**
- `openai.wav` / `openai_match.wav` - OpenAI TTS (raw and volume-matched)
- `piper.wav` / `piper_match.wav` - Piper TTS (raw and volume-matched)
- `AB_openai_piper.wav` - A/B comparison mix (optional with `--ab-swap-sec`)
- `compare_report.json` - Detailed comparison metrics

**Metrics Collected:**
- `duration_sec` - Audio duration
- `rms_dbfs` - RMS level in dBFS
- `peak_dbfs` - Peak level in dBFS
- `silence_ratio` - Percentage of silence
- `pause_profile` - Comma, period, colon pause settings

**Key Features:**
- Volume matching using RMS-based gain adjustment
- Graceful degradation (works with OpenAI only if Piper unavailable)
- Pause profile configuration for natural speech pacing
- Metadata preservation in JSON reports

### Report Aggregation (`compare_report_to_md.py`)

Aggregates multiple comparison reports into CSV and Markdown tables:

```bash
# Aggregate all reports
./scripts/export_reports.sh

# Custom glob pattern
python scripts/compare_report_to_md.py \
  --work-glob "work/cmp_*/compare_report.json" \
  --outdir "output/reports"
```

**Outputs:**
- `tts_compare_YYYYMMDD_HHMMSS.csv` - Spreadsheet-ready data
- `tts_compare_YYYYMMDD_HHMMSS.md` - Human-readable table

**Features:**
- Zero dependencies (standard library only)
- Chronological sorting by timestamp
- Flexible filtering and sorting options
- Graceful handling of missing/malformed data

### Visualization (`plot_tts_metrics.py`)

Generates PNG charts from CSV reports using matplotlib:

```bash
# Generate all charts
./scripts/plot_reports.sh

# Custom parameters
python scripts/plot_tts_metrics.py \
  --csv-glob "output/reports/*.csv" \
  --outdir "output/reports/plots" \
  --rolling 3
```

**Charts Generated:**
1. **RMS Trend** (`rms_trend.png`)
   - Shows audio levels over time
   - Good range: -18 to -24 dBFS
   - Optional rolling mean smoothing

2. **Duration Scatter** (`duration_scatter.png`)
   - OpenAI vs Piper duration comparison
   - y=x reference line for parity
   - Identifies speed differences

3. **Silence Histograms** (`*_silence_hist.png`)
   - Distribution of silence percentages
   - Good range: 8-15%
   - 20 bins for granular analysis

**Features:**
- Headless mode (Agg backend) for CI/CD
- No pandas dependency (pure csv module)
- Automatic chart selection based on data availability
- Configurable rolling window for trend smoothing

### Quality Management Workflow

```bash
# 1. Run TTS comparisons
for text in input/*.txt; do
  python scripts/compare_tts.py --text-file "$text" --slug "$(basename $text .txt)"
done

# 2. Aggregate reports
./scripts/export_reports.sh

# 3. Generate visualizations
./scripts/plot_reports.sh

# 4. Review quality metrics
open output/reports/plots/rms_trend.png
open output/reports/tts_compare_*.csv
```

**Quality Thresholds:**
- **RMS Level**: -18 to -24 dBFS (optimal), <-30 dBFS (too quiet), >-15 dBFS (too loud)
- **Silence Ratio**: 8-15% (natural), <5% (rushed), >20% (too slow)
- **Duration**: Piper typically 20-30% slower than OpenAI

## Recent Changes (Git History Context)

- TTS Quality Management System added (Steps 4-5: reporting and visualization)
- `compare_tts.py` implements OpenAI vs Piper comparison with audio analysis
- `compare_report_to_md.py` aggregates JSON reports to CSV/Markdown (zero dependencies)
- `plot_tts_metrics.py` generates quality trend charts (matplotlib only, no pandas)
- Shell wrappers added: `export_reports.sh`, `plot_reports.sh`
- README.md fully localized to Korean with quality management guides
- Latest commit enforces hard-fail on translation/TTS misconfiguration with guided fix messages
- diagnose.sh script added for pre-flight validation of lzma/piper/ffmpeg
- Config templates (.env.example, config.yaml.example) added for easier setup

## Code Style Notes

- Scripts use compact imports: `import pathlib, subprocess, typer, yaml`
- Minimal error handling - let exceptions bubble up for debugging
- Prefer pathlib over os.path
- Use loguru for logging, print() only for stdout capture
- Shell scripts use `set -e` for fail-fast behavior
