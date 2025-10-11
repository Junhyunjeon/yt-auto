#!/usr/bin/env python3
"""
Tests for openai_tts.py - OpenAI TTS functionality
Includes both mocked tests and optional live API tests
"""

import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import io

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import pytest
from pydub import AudioSegment


# Environment variable for enabling live tests
RUN_LIVE = os.getenv("RUN_LIVE_TTS") == "1"


class TestOpenAITTSMocked:
    """Mocked tests for OpenAI TTS (no API calls)"""

    @pytest.fixture
    def fake_audio_bytes(self):
        """Generate fake audio bytes for mocking"""
        # Load our test fixture
        fixture_path = Path(__file__).parent / "data" / "fake.wav"
        with open(fixture_path, "rb") as f:
            return f.read()

    @pytest.fixture
    def mock_openai_client(self, fake_audio_bytes):
        """Create mocked OpenAI client"""
        with patch("scripts.openai_tts.OpenAI") as mock_client_class:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = fake_audio_bytes

            # Mock the nested structure: client.audio.speech.create()
            mock_client.audio.speech.create.return_value = mock_response
            mock_client_class.return_value = mock_client

            yield mock_client_class

    def test_synthesize_segment_mocked(self, mock_openai_client, fake_audio_bytes, tmp_path):
        """Test synthesizing a single segment with mocked API"""
        from scripts.openai_tts import synthesize_segment
        from openai import OpenAI

        # Set fake API key
        os.environ["OPENAI_API_KEY"] = "fake-key-for-testing"

        client = OpenAI(api_key="fake-key")
        text = "This is a test sentence."

        audio = synthesize_segment(
            client=client,
            text=text,
            model="tts-1",
            voice="onyx",
            response_format="mp3"
        )

        # Should return an AudioSegment
        assert isinstance(audio, AudioSegment)
        assert len(audio) > 0

    def test_build_audio_with_pauses_mocked(self, mock_openai_client, tmp_path):
        """Test building audio with pauses (mocked) - now uses tts_common.build_track"""
        # This functionality is now tested in test_tts_common.py
        # Here we just verify the openai_tts module loads correctly
        from scripts import openai_tts
        assert hasattr(openai_tts, 'synthesize_segment')
        assert hasattr(openai_tts, 'resolve_defaults')

    def test_main_execution_mocked(self, mock_openai_client, tmp_path):
        """Test full TTS execution via main() with mocked API"""
        import sys
        from scripts import openai_tts

        # Set fake API key
        os.environ["OPENAI_API_KEY"] = "fake-key-for-testing"

        # Create test input
        input_file = tmp_path / "input.txt"
        input_file.write_text("This is a short test.")

        output_path = tmp_path / "output.wav"

        # Simulate command-line arguments
        sys.argv = [
            "openai_tts.py",
            str(input_file),
            "--output", str(output_path)
        ]

        # Run main
        result = openai_tts.main()

        # Should complete successfully
        assert result == 0
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_voice_presets_loaded(self):
        """Test that voice presets are loaded"""
        from scripts.openai_tts import VOICE_PRESETS

        # Should have at least the built-in presets
        assert "onyx_natural" in VOICE_PRESETS
        assert "onyx_broadcast" in VOICE_PRESETS
        assert "onyx_fast" in VOICE_PRESETS

        # Each preset should have required fields
        for name, preset in VOICE_PRESETS.items():
            assert "voice" in preset
            assert "description" in preset

    def test_pause_profiles(self):
        """Test pause profiles are defined"""
        from scripts.openai_tts import PAUSE_PROFILES

        assert "natural" in PAUSE_PROFILES
        assert "broadcast" in PAUSE_PROFILES
        assert "tight" in PAUSE_PROFILES

        # Each should have pause values
        for profile in PAUSE_PROFILES.values():
            assert "short" in profile
            assert "medium" in profile
            assert "long" in profile


@pytest.mark.skipif(not RUN_LIVE, reason="set RUN_LIVE_TTS=1 for live API tests")
class TestOpenAITTSLive:
    """Live API tests (requires OPENAI_API_KEY and RUN_LIVE_TTS=1)"""

    def test_live_short_synthesis(self, tmp_path):
        """Test live API call with very short text"""
        from scripts.openai_tts import generate_tts

        # Check for API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key.startswith("sk-proj-"):
            pytest.skip("Valid OPENAI_API_KEY not set")

        output_path = tmp_path / "live_test.wav"
        text = "Testing."  # Very short to minimize cost

        try:
            generate_tts(
                text=text,
                output_path=str(output_path),
                voice="onyx",
                model="tts-1",  # Use cheaper model
                response_format="wav",
                speed=1.0,
                pause_short=0.1,
                pause_medium=0.2,
                pause_long=0.3
            )

            # Verify output
            assert output_path.exists()
            assert output_path.stat().st_size > 0

            # Load and check audio
            audio = AudioSegment.from_wav(str(output_path))
            assert len(audio) > 0
            assert len(audio) < 5000  # Should be under 5 seconds

        except Exception as e:
            pytest.fail(f"Live API test failed: {e}")

    def test_live_api_key_validation(self):
        """Test that API key is validated"""
        from scripts.openai_tts import build_audio_with_pauses

        # Temporarily unset API key
        original_key = os.environ.get("OPENAI_API_KEY")
        os.environ.pop("OPENAI_API_KEY", None)

        try:
            with pytest.raises(EnvironmentError, match="OPENAI_API_KEY"):
                build_audio_with_pauses(
                    text="Test",
                    pause_short=0.1,
                    pause_medium=0.2,
                    pause_long=0.3,
                    model="tts-1",
                    voice="onyx"
                )
        finally:
            # Restore API key
            if original_key:
                os.environ["OPENAI_API_KEY"] = original_key


class TestTextSplitting:
    """Test text splitting functionality - now uses tts_common"""

    def test_segmentation_integration(self):
        """Test that openai_tts correctly uses tts_common.segment_text"""
        # Text splitting is now handled by tts_common.segment_text
        # which is tested in test_tts_common.py
        from scripts.tts_common import segment_text

        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        segments = segment_text(text, max_chars=100)

        # Should create segments
        assert len(segments) > 0
        assert all(isinstance(seg, str) for seg in segments)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
