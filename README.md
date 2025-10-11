# YouTube Automation Pipeline (MVP)

A complete offline pipeline that transforms Korean scripts into English content with audio and video outputs.

## 🎯 Features

- **Text Processing**: Cleans and prepares Korean input text
- **Translation**: Korean to English (with Argos Translate fallback)
- **Content Generation**: Creates structured English markdown posts
- **Text-to-Speech**: **OpenAI TTS (Onyx Natural) with natural breathing pauses** - Default high-quality narration
  - **Common TTS Module**: Shared segmentation and post-processing for consistent results across engines
- **Video Creation**: Creates MP4 videos with waveform visualization and titles
- **Publishing**: Optional WordPress integration (configurable)

## 📁 Directory Structure

```
~/yt-auto/
├── input/           # Place Korean .txt files here
├── work/           # Intermediate processing files
├── output/         # Final audio/video outputs
├── assets/         # Background images (optional)
├── scripts/        # Processing pipeline scripts
├── config.yaml     # Configuration file
└── run_pipeline.sh # Main execution script
```

## 🚀 Quick Start

### Prerequisites

```bash
# Install system dependencies
brew install xz ffmpeg piper

# Download Piper voice model
mkdir -p ~/piper_models
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx -P ~/piper_models/
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json -P ~/piper_models/

# Setup configuration
cp config.yaml.example config.yaml
cp .env.example .env
# Edit .env to set PIPER_MODEL path if needed

# Run environment check
./scripts/diagnose.sh
```

### Running the Pipeline

1. **Place your Korean script** in the `input/` directory:
   ```
   input/my-script.txt
   ```

2. **Run the pipeline**:
   ```bash
   ./run_pipeline.sh input/my-script.txt
   ```

3. **Check outputs**:
   - English markdown: `work/my-script/post_en.md`
   - Audio file: `output/my-script/voice_en.wav`
   - Video file: `output/my-script/video_en.mp4`

## 📝 Manual Step-by-Step

```bash
cd ~/yt-auto
source .venv/bin/activate

# Step 1: Prepare
SLUG=$(python scripts/01_prepare.py input/my-script.txt)

# Step 2: Translate
python scripts/02_translate.py $SLUG

# Step 3: Edit
TITLE=$(python scripts/03_edit_en.py $SLUG)

# Step 4: TTS
python scripts/04_tts.py $SLUG

# Step 5: Video
python scripts/05_video.py $SLUG --title-text "$TITLE"

# Optional: Publish
python scripts/06_publish.py wordpress $SLUG
```

## ⚙️ Configuration

### Default TTS: Onyx Natural Profile

The pipeline uses **OpenAI TTS with Onyx voice** by default with natural breathing pauses:

```yaml
# config.yaml
tts:
  engine: openai
  default_preset: onyx_natural  # Deep, confident male voice

openai:
  tts:
    voice: onyx                 # Deep male voice
    model: tts-1                # Fast, cost-effective
    format: wav
    speed: 1.0
    pause_profile: natural      # Natural breathing
    pause_short: 0.25           # After commas
    pause_medium: 0.50          # After sentences
    pause_long: 0.80            # Between paragraphs
```

### OpenAI TTS Usage

#### Basic Usage

```bash
# Use default Onyx Natural (no options needed)
python scripts/openai_tts.py input/text.txt --output output/audio.wav

# With metrics export
python scripts/openai_tts.py input/text.txt --output output/audio.wav --json-out metrics.json

# Use a different preset
python scripts/openai_tts.py input/text.txt --output output/audio.wav --preset onyx_broadcast
```

#### Available Presets

- `onyx_natural`: Default, balanced narration (default)
- `onyx_broadcast`: Authoritative, HD quality, slower pace
- `onyx_fast`: Quick briefings, tight pauses
- `alloy_warm_low`: Warm, emotional tone

#### Advanced Options

```bash
# Custom voice and pauses
python scripts/openai_tts.py input/text.txt --output output/audio.wav \
  --voice alloy --pause-profile tight

# With style prefix for better narration
python scripts/openai_tts.py input/text.txt --output output/audio.wav \
  --style-prefix "Speak calmly and confidently with emphasis."

# Fine-tune audio processing
python scripts/openai_tts.py input/text.txt --output output/audio.wav \
  --fade-ms 30 --crossfade-ms 100 --max-chars 600 --normalize

# Export metrics for analysis
python scripts/openai_tts.py input/text.txt --output output/audio.wav \
  --json-out work/metrics.json
```

#### New Options (Common TTS Integration)

| Option | Default | Description |
|--------|---------|-------------|
| `--fade-ms` | 20 | Fade in/out duration (milliseconds) |
| `--crossfade-ms` | 50 | Crossfade duration between segments (ms) |
| `--max-chars` | 800 | Maximum characters per segment |
| `--style-prefix` | None | Style instruction to prepend to text |
| `--json-out` | None | Save metrics to JSON file |
| `--normalize` | False | Apply volume normalization |

### API Keys

Set your OpenAI API key in `.env`:

```bash
# .env
OPENAI_API_KEY=sk-proj-your-key-here

# Optional: Override TTS defaults
OPENAI_TTS_VOICE=onyx
OPENAI_TTS_MODEL=tts-1
OPENAI_TTS_FORMAT=wav
OPENAI_TTS_PAUSE_PROFILE=natural
```

### TTS Common Module

The pipeline uses a **shared segmentation and post-processing module** (`scripts/tts_common.py`) for consistent audio quality across all TTS engines:

**Features**:
- **Smart Segmentation**: Splits text by paragraphs/sentences with configurable max length (default 800 chars)
- **Audio Processing**: Crossfade, fade in/out, normalization, speed adjustment
- **Metrics**: Measures duration, RMS/peak levels, silence ratio
- **Volume Matching**: Automatically balances volume between different engines

**Test the module**:
```bash
bash scripts/smoke_tts_common.sh
```

### Other Configuration

Edit `config.yaml` to customize:

- **Translation**: Claude API or Argos Translate
- **TTS Engine**: OpenAI (default) or Piper (fallback)
- **Video Settings**: Resolution, FPS, background image
- **Publishing**: WordPress and YouTube settings (disabled by default)

## 🔄 Piper vs OpenAI TTS Comparison

Run a fair A/B comparison with unified segmentation and post-processing:

```bash
# Quick comparison with defaults
bash scripts/compare_tts.sh input/text.txt output/compare_demo

# Or use Python script directly for more control
python scripts/compare_tts.py input/text.txt --outdir output/compare_demo \
  --style-prefix "Speak calmly and confidently, as if narrating a professional video." \
  --pause-profile natural \
  --openai-voice onyx \
  --ab-swap-sec 8
```

**Prerequisites**:
- `.env` with `OPENAI_API_KEY` set
- Piper TTS installed (optional - comparison works with OpenAI only if Piper not available)
- `PIPER_VOICE` in `.env` or pass `--piper-voice path/to/model.onnx`

**Generated Outputs**:

The comparison generates several files in the output directory:

- `openai.wav` - Raw OpenAI TTS output
- `openai_match.wav` - Volume-matched OpenAI audio
- `piper.wav` - Raw Piper TTS output (if Piper installed)
- `piper_match.wav` - Volume-matched Piper audio (if Piper installed)
- `AB_openai_piper.wav` - A/B swap mix alternating between engines (if `--ab-swap-sec` specified)
- `work/cmp_*/compare_report.json` - Comprehensive comparison metrics

**Comparison Report Structure**:

```json
{
  "input_file": "input/text.txt",
  "slug": "cmp_abc123",
  "settings": {
    "pause_profile": "natural",
    "fade_ms": 20,
    "crossfade_ms": 50,
    "max_chars": 800
  },
  "openai": {
    "duration_sec": 45.2,
    "rms_dbfs": -18.5,
    "peak_dbfs": -3.2,
    "silence_ratio": 12.3
  },
  "piper": {
    "duration_sec": 43.8,
    "rms_dbfs": -19.1,
    "peak_dbfs": -4.5,
    "silence_ratio": 10.5
  },
  "comparison": {
    "duration_diff_sec": 1.4,
    "duration_ratio": 1.032,
    "rms_diff_db": 0.6,
    "faster_engine": "piper"
  }
}
```

**Note**: If Piper is not installed, the script will skip Piper synthesis gracefully and still produce OpenAI outputs and report. This allows the comparison pipeline to work even when only one TTS engine is available.

### Exporting Comparison Reports

Aggregate multiple `compare_report.json` files into CSV/Markdown for analysis:

```bash
# Default: scan work/*/compare_report.json and write to output/reports/
python3 scripts/compare_report_to_md.py

# Or via shell helper
bash scripts/export_reports.sh output/reports "work/*/compare_report.json"

# With sorting and limit
python3 scripts/compare_report_to_md.py --sort "openai_rms,-openai_duration" --limit 10
```

**Outputs:**
- `output/reports/tts_compare_YYYYMMDD_HHMMSS.csv` - Spreadsheet-ready format
- `output/reports/tts_compare_YYYYMMDD_HHMMSS.md` - Markdown table for documentation

**Options:**
- `--work-glob`: Glob pattern to scan reports (default: `work/*/compare_report.json`)
- `--outdir`: Output directory (default: `output/reports`)
- `--sort`: Sort by fields, e.g., `openai_rms,-openai_duration` (- for descending)
- `--limit`: Cap number of rows

**Use Cases:**
- Track audio quality metrics over time
- Compare different TTS settings
- Share results with team (CSV import to spreadsheet)
- Document comparison results in pull requests (Markdown)

### Plotting Metrics

Turn CSV reports into visual charts for quick insights (no pandas):

```bash
# One-line plotting with defaults
bash scripts/plot_reports.sh

# Or use Python script directly for more control
python3 scripts/plot_tts_metrics.py \
  --csv-glob "output/reports/tts_compare_*.csv" \
  --outdir output/reports/plots \
  --rolling 3 \
  --title-suffix "Onyx Natural vs Piper"

# Limit to latest N runs and apply smoothing
python3 scripts/plot_tts_metrics.py \
  --csv-glob "output/reports/tts_compare_*.csv" \
  --outdir output/reports/plots \
  --rolling 5 \
  --limit 20
```

**Generated Plots:**
- `output/reports/plots/rms_trend.png` - RMS levels over time (line chart with rolling mean)
- `output/reports/plots/duration_scatter.png` - OpenAI vs Piper duration comparison (scatter with y=x reference)
- `output/reports/plots/openai_silence_hist.png` - OpenAI silence ratio distribution
- `output/reports/plots/piper_silence_hist.png` - Piper silence ratio distribution (if available)

**Options:**
- `--rolling N`: Apply N-point rolling mean to smooth trend lines (default: 0, disabled)
- `--limit N`: Show only latest N runs (sorted by timestamp)
- `--title-suffix "text"`: Add custom suffix to chart titles
- `--csv-glob "pattern"`: Custom glob pattern for CSV files

**Use Cases:**
- **Quality monitoring**: Spot RMS/peak anomalies at a glance
- **A/B testing**: Visual comparison of different voice settings
- **Trend analysis**: Track audio quality degradation or improvement over time
- **Quick debugging**: Identify outliers in silence ratio or duration

**Requirements:**
- matplotlib (already installed in venv)
- Runs in headless mode (no display required)
- Works in CI/CD environments

## 🔧 System Requirements

- macOS (tested on Mac Mini)
- Python 3.11+
- FFmpeg 8.0+
- uv package manager

## 📋 Output Files

For input `input/my-script.txt`, the pipeline generates:

1. **work/my-script/post_en.md** - Structured English markdown
2. **output/my-script/voice_en.wav** - English audio (22kHz, mono)
3. **output/my-script/video_en.mp4** - Video (1920x1080, H.264)

## 🔍 Troubleshooting

### lzma Module Error (Python)
**Error**: `ModuleNotFoundError: No module named '_lzma'`
**Solution**:
```bash
brew install xz
# If using pyenv:
pyenv install --force $(pyenv version-name)
# Or reinstall Python with proper xz support
```

### Piper Not Found
**Error**: `Piper executable not found`
**Solution**:
```bash
brew install piper
# Or download binary from https://github.com/rhasspy/piper/releases
# Set PIPER_EXEC in .env if not in PATH
```

### Piper Model Not Found
**Error**: `Piper model not found`
**Solution**:
```bash
mkdir -p ~/piper_models
# Download voice model (example: US English Amy voice)
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx -P ~/piper_models/
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json -P ~/piper_models/
# Update PIPER_MODEL path in .env
```

### FFmpeg Issues
**Error**: `ffmpeg not found`
**Solution**:
```bash
brew install ffmpeg
```

### Video Issues
- Background image not found: auto-generates black background
- FFmpeg errors: Check ffmpeg installation with `ffmpeg -version`

## ✅ Acceptance Criteria Status

- ✅ Input processing: Handles Korean .txt files
- ✅ Text cleaning: Removes extra whitespace, normalizes
- ⚠️ Translation: Working (fallback mode, needs Argos fix)
- ✅ English content: Generates structured markdown
- ✅ Audio generation: Creates WAV files (dummy for now)
- ✅ Video generation: Creates MP4 with title overlay
- ✅ File structure: Proper organization
- ⚠️ WordPress publishing: Framework ready (needs configuration)

## 🧪 Testing

### Running Tests

The project includes comprehensive test coverage for TTS functionality:

```bash
# Quick test run
make test

# Verbose output
make test-v

# With coverage report
make cov

# Install test dependencies
make install-dev
```

### Test Organization

```
tests/
  test_tts_common.py      # Unit tests for text segmentation and audio processing
  test_openai_tts.py      # OpenAI TTS tests (mocked + optional live)
  test_piper_tts.py       # Piper TTS tests (conditional on installation)
  test_compare_tts.py     # Integration tests for TTS comparison
  data/
    sample_short.txt      # Test input text
    fake.wav              # Audio fixtures
    silence_500ms.wav
```

### Test Coverage

- **Text Segmentation**: Paragraph/sentence splitting, max character limits
- **Audio Processing**: Fades, crossfades, normalization, speed adjustment
- **Metrics**: Duration, RMS/peak levels, silence ratio
- **Volume Matching**: Automatic level balancing between engines
- **API Mocking**: Fast tests without API costs
- **Optional Live Tests**: Set `RUN_LIVE_TTS=1` with valid `OPENAI_API_KEY`

### Continuous Integration

Tests run automatically on GitHub Actions for all pushes and PRs. See `.github/workflows/ci-tests.yml`.

### Running Live API Tests

```bash
# Set environment variables
export OPENAI_API_KEY=sk-proj-your-key-here
export RUN_LIVE_TTS=1

# Run OpenAI live tests only
pytest tests/test_openai_tts.py::TestOpenAITTSLive -v
```

**Note**: Live tests use very short text samples to minimize API costs.

## 🔮 Next Steps

1. **Fix Argos Translation**: Resolve Python lzma dependency
2. **Proper TTS**: Configure real Piper TTS with voice models
3. **API Integration**: Add Google Translate, ElevenLabs as options
4. **Publishing**: Complete YouTube upload integration
5. **Error Handling**: Improve robustness and logging