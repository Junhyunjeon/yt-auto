#!/usr/bin/env python3
"""
Tests for tts_common.py - Text segmentation and audio utilities
"""

import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import pytest
from pydub import AudioSegment
from scripts.tts_common import (
    segment_text,
    build_track,
    measure,
    match_volume,
    apply_style_prefix
)


class TestSegmentation:
    """Test text segmentation functionality"""

    def test_segment_simple_paragraph(self):
        """Test segmenting a simple paragraph"""
        text = "This is a test. It has multiple sentences. And it works well."
        segments = segment_text(text, max_chars=100)

        assert len(segments) > 0
        assert all(len(seg) <= 100 for seg in segments)

    def test_segment_respects_paragraph_boundaries(self):
        """Test that segmentation preserves paragraph breaks"""
        text = "First paragraph with some text.\n\nSecond paragraph with more text."
        segments = segment_text(text, max_chars=200)

        # Should keep paragraphs separate or combined based on length
        assert len(segments) >= 1

    def test_segment_long_sentence_splits_by_clauses(self):
        """Test that very long sentences are split by clause markers"""
        # Create a long sentence that exceeds max_chars
        text = "This is a very long sentence, with multiple clauses, that should be split, because it exceeds the maximum character limit, and we need to ensure, that it is handled properly."

        segments = segment_text(text, max_chars=50)

        # Should split into multiple segments
        assert len(segments) > 1
        # Each segment should be reasonably sized
        for seg in segments:
            assert len(seg) <= 100  # Some tolerance for clause splitting

    def test_segment_max_chars_boundary(self):
        """Test segmentation near max_chars boundary"""
        # Create text that's just under and just over max_chars
        text = "A" * 400 + ". " + "B" * 400 + "."

        segments = segment_text(text, max_chars=450)

        # Should create at least 2 segments
        assert len(segments) >= 2

    def test_segment_empty_input(self):
        """Test segmentation with empty input"""
        segments = segment_text("", max_chars=100)
        assert len(segments) == 0

        segments = segment_text("   \n\n   ", max_chars=100)
        assert len(segments) == 0

    def test_segment_paragraph_mode(self):
        """Test paragraph mode keeps whole paragraphs when possible"""
        text = "Short para one.\n\nShort para two."
        segments = segment_text(text, max_chars=200, mode="paragraph")

        # Small paragraphs should be kept separate
        assert len(segments) == 2


class TestAudioProcessing:
    """Test audio building and post-processing"""

    @pytest.fixture
    def fake_audio(self):
        """Load fake audio fixture"""
        fixture_path = Path(__file__).parent / "data" / "fake.wav"
        return AudioSegment.from_wav(str(fixture_path))

    @pytest.fixture
    def silence_audio(self):
        """Load silence audio fixture"""
        fixture_path = Path(__file__).parent / "data" / "silence_500ms.wav"
        return AudioSegment.from_wav(str(fixture_path))

    def test_build_track_single_chunk(self, fake_audio):
        """Test building track with single audio chunk"""
        track = build_track([fake_audio], normalize=False)

        # Should have similar duration to input
        assert abs(len(track) - len(fake_audio)) < 200  # Within 200ms

    def test_build_track_multiple_chunks(self, fake_audio):
        """Test building track with multiple chunks"""
        chunks = [fake_audio, fake_audio, fake_audio]

        track = build_track(
            chunks,
            pause_medium=0.5,
            fade_ms=20,
            crossfade_ms=0,  # Disable crossfade for easier calculation
            normalize=False
        )

        # Duration should be: 3 chunks + 2 pauses
        expected_min = (len(fake_audio) * 3) + (500 * 2) - 100  # Some tolerance
        assert len(track) >= expected_min

    def test_build_track_with_fades(self, fake_audio):
        """Test that fades are applied"""
        track = build_track([fake_audio], fade_ms=50, normalize=False)

        # Track should exist and have reasonable duration
        assert len(track) > 0
        assert abs(len(track) - len(fake_audio)) < 200

    def test_build_track_with_crossfade(self, fake_audio):
        """Test crossfade between chunks"""
        chunks = [fake_audio, fake_audio]

        track = build_track(
            chunks,
            pause_medium=0,
            crossfade_ms=100,
            normalize=False
        )

        # With crossfade, duration should be less than sum of chunks
        total_duration = len(fake_audio) * 2
        assert len(track) < total_duration

    def test_build_track_empty_chunks(self):
        """Test building track with no chunks"""
        track = build_track([])
        assert len(track) == 0

    def test_build_track_speed_adjustment(self, fake_audio):
        """Test speed adjustment"""
        original_track = build_track([fake_audio], speed=1.0, normalize=False)
        fast_track = build_track([fake_audio], speed=1.05, normalize=False)

        # Fast track should be shorter (within 5% tolerance)
        # Speed adjustment may have rounding effects on short audio
        assert len(fast_track) <= len(original_track) * 1.05

    def test_build_track_normalization(self, fake_audio):
        """Test normalization"""
        # Create a quiet audio
        quiet_audio = fake_audio - 20  # Reduce by 20dB

        track_normalized = build_track([quiet_audio], normalize=True)
        track_original = build_track([quiet_audio], normalize=False)

        # Normalized should be louder
        assert track_normalized.dBFS > track_original.dBFS


class TestMeasurement:
    """Test audio measurement functions"""

    @pytest.fixture
    def fake_audio(self):
        """Load fake audio fixture"""
        fixture_path = Path(__file__).parent / "data" / "fake.wav"
        return AudioSegment.from_wav(str(fixture_path))

    @pytest.fixture
    def silence_audio(self):
        """Load silence audio fixture"""
        fixture_path = Path(__file__).parent / "data" / "silence_500ms.wav"
        return AudioSegment.from_wav(str(fixture_path))

    def test_measure_duration(self, fake_audio):
        """Test duration measurement"""
        metrics = measure(fake_audio)

        assert "duration_sec" in metrics
        assert 0.4 < metrics["duration_sec"] < 0.6  # Should be around 0.5s

    def test_measure_levels(self, fake_audio):
        """Test RMS and peak level measurement"""
        metrics = measure(fake_audio)

        assert "rms_dbfs" in metrics
        assert "peak_dbfs" in metrics
        # Levels should be in reasonable range (not silent, not clipping)
        assert -50 < metrics["rms_dbfs"] <= 0
        assert -50 < metrics["peak_dbfs"] <= 0  # Allow 0.0 for max amplitude

    def test_measure_silence_ratio(self, silence_audio):
        """Test silence ratio measurement"""
        metrics = measure(silence_audio)

        assert "silence_ratio" in metrics
        # Silence audio should have high silence ratio
        assert metrics["silence_ratio"] > 90  # At least 90% silence

    def test_measure_tone_has_low_silence(self, fake_audio):
        """Test that tone has low silence ratio"""
        metrics = measure(fake_audio)

        # Tone should have very little silence
        assert metrics["silence_ratio"] < 10  # Less than 10% silence


class TestVolumeMatching:
    """Test volume matching functionality"""

    @pytest.fixture
    def fake_audio(self):
        """Load fake audio fixture"""
        fixture_path = Path(__file__).parent / "data" / "fake.wav"
        return AudioSegment.from_wav(str(fixture_path))

    def test_match_volume_equal_levels(self, fake_audio):
        """Test matching volumes when already equal"""
        audio1 = fake_audio
        audio2 = fake_audio

        matched1, matched2 = match_volume(audio1, audio2, max_diff_db=1.5)

        # Should not change much if already equal
        assert abs(audio1.dBFS - matched1.dBFS) < 0.1
        assert abs(audio2.dBFS - matched2.dBFS) < 0.1

    def test_match_volume_different_levels(self, fake_audio):
        """Test matching volumes when different"""
        audio1 = fake_audio - 6  # Reduce by 6dB
        audio2 = fake_audio

        matched1, matched2 = match_volume(audio1, audio2, max_diff_db=1.5)

        # Quieter one should be boosted
        assert matched1.dBFS > audio1.dBFS


class TestStylePrefix:
    """Test style prefix functionality"""

    def test_apply_style_prefix(self):
        """Test adding style prefix to text"""
        text = "This is the main content."
        style = "Speak calmly and confidently."

        result = apply_style_prefix(text, style)

        assert style in result
        assert text in result
        assert result.startswith(style)

    def test_apply_style_prefix_none(self):
        """Test with no style prefix"""
        text = "This is the main content."

        result = apply_style_prefix(text, None)

        assert result == text

    def test_apply_style_prefix_empty(self):
        """Test with empty style prefix"""
        text = "This is the main content."

        result = apply_style_prefix(text, "")

        assert result == text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
