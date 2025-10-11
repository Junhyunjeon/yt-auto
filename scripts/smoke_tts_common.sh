#!/usr/bin/env bash
set -euo pipefail

# Smoke test for tts_common module
# Tests text segmentation and audio processing functions

echo "🧪 Smoke Test: TTS Common Module"
echo "=================================="

# Activate virtual environment
if [ -d .venv ]; then
    source .venv/bin/activate
fi

# Test 1: Text segmentation
echo ""
echo "📝 Test 1: Text Segmentation"
python3 -c "
import sys
sys.path.insert(0, 'scripts')
from tts_common import segment_text

test_text = '''This is the first paragraph with multiple sentences.
Each sentence should be handled properly, even with punctuation!

This is a second paragraph. It demonstrates paragraph splitting.
We want to ensure proper segmentation for TTS synthesis.

And here is a third paragraph, just to be thorough.'''

segments = segment_text(test_text, max_chars=150)
print(f'   Segments created: {len(segments)}')
for i, seg in enumerate(segments, 1):
    print(f'   {i}. [{len(seg):3d} chars] {seg[:50]}...')

assert len(segments) > 0, 'No segments created'
assert all(len(s) <= 150 for s in segments), 'Segment exceeds max_chars'
print('   ✅ Segmentation test passed')
"

# Test 2: Audio processing (requires pydub and sample audio)
echo ""
echo "🎵 Test 2: Audio Processing"
python3 -c "
import sys
sys.path.insert(0, 'scripts')
from tts_common import build_track, measure
from pydub import AudioSegment
from pydub.generators import Sine

# Create test audio chunks (sine waves)
chunk1 = Sine(440).to_audio_segment(duration=1000)  # 1 second, 440Hz
chunk2 = Sine(880).to_audio_segment(duration=1000)  # 1 second, 880Hz
chunk3 = Sine(220).to_audio_segment(duration=500)   # 0.5 second, 220Hz

print('   Created 3 test audio chunks')

# Build track with pauses and crossfade
track = build_track(
    [chunk1, chunk2, chunk3],
    pause_short=0.1,
    pause_medium=0.2,
    pause_long=0.3,
    fade_ms=10,
    crossfade_ms=20,
    normalize=True,
    speed=1.0
)

print(f'   Combined track duration: {len(track)/1000:.2f}s')

# Measure track
metrics = measure(track)
print(f'   Duration: {metrics[\"duration_sec\"]}s')
print(f'   RMS: {metrics[\"rms_dbfs\"]} dBFS')
print(f'   Peak: {metrics[\"peak_dbfs\"]} dBFS')
print(f'   Silence: {metrics[\"silence_ratio\"]}%')

assert metrics['duration_sec'] > 2.0, 'Track too short'
assert metrics['rms_dbfs'] < 0, 'Invalid RMS level'
print('   ✅ Audio processing test passed')
"

# Test 3: Volume matching
echo ""
echo "🔊 Test 3: Volume Matching"
python3 -c "
import sys
sys.path.insert(0, 'scripts')
from tts_common import match_volume
from pydub import AudioSegment
from pydub.generators import Sine

# Create two audio segments with different volumes
audio1 = Sine(440).to_audio_segment(duration=1000)
audio2 = Sine(880).to_audio_segment(duration=1000).apply_gain(-6)  # 6dB quieter

print(f'   Before: audio1={audio1.dBFS:.1f}dB, audio2={audio2.dBFS:.1f}dB')

# Match volumes
matched1, matched2 = match_volume(audio1, audio2, max_diff_db=2.0)

print(f'   After:  audio1={matched1.dBFS:.1f}dB, audio2={matched2.dBFS:.1f}dB')

# Check volumes are closer
diff_before = abs(audio1.dBFS - audio2.dBFS)
diff_after = abs(matched1.dBFS - matched2.dBFS)

assert diff_after < diff_before, 'Volume matching failed'
print('   ✅ Volume matching test passed')
"

echo ""
echo "✅ All TTS Common Module tests passed!"
echo ""
echo "📦 Module ready for use by OpenAI TTS and Piper TTS"
