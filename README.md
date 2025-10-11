# YouTube Automation Pipeline (MVP)

A complete offline pipeline that transforms Korean scripts into English content with audio and video outputs.

## 🎯 Features

- **Text Processing**: Cleans and prepares Korean input text
- **Translation**: Korean to English (with Argos Translate fallback)
- **Content Generation**: Creates structured English markdown posts
- **Text-to-Speech**: **OpenAI TTS (Onyx Natural) with natural breathing pauses** - Default high-quality narration
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

### Quick Usage

```bash
# Use default Onyx Natural (no options needed)
python scripts/openai_tts.py input/text.txt --output output/audio.wav

# Use a different preset
python scripts/openai_tts.py input/text.txt --preset onyx_broadcast

# Available presets (see presets.yaml):
# - onyx_natural: Default, balanced narration
# - onyx_broadcast: Authoritative, HD quality, slower pace
# - onyx_fast: Quick briefings, tight pauses
# - alloy_warm_low: Warm, emotional tone
# - echo_clear: Clear, energetic
# - fable_storytelling: Warm storytelling voice
```

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

### Other Configuration

Edit `config.yaml` to customize:

- **Translation**: Claude API or Argos Translate
- **TTS Engine**: OpenAI (default) or Piper (fallback)
- **Video Settings**: Resolution, FPS, background image
- **Publishing**: WordPress and YouTube settings (disabled by default)

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

## 🔮 Next Steps

1. **Fix Argos Translation**: Resolve Python lzma dependency
2. **Proper TTS**: Configure real Piper TTS with voice models
3. **API Integration**: Add Google Translate, ElevenLabs as options
4. **Publishing**: Complete YouTube upload integration
5. **Error Handling**: Improve robustness and logging