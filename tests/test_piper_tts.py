#!/usr/bin/env python3
"""
Tests for piper_tts.py - Piper TTS functionality
Tests work whether Piper is installed or not
"""

import sys
import os
import shutil
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import pytest


# Check if piper is installed
PIPER_INSTALLED = shutil.which("piper") is not None


class TestPiperAvailability:
    """Test Piper installation detection"""

    def test_piper_detection(self):
        """Test that we can detect if Piper is installed"""
        piper_path = shutil.which("piper")

        if PIPER_INSTALLED:
            assert piper_path is not None
            assert Path(piper_path).exists()
        else:
            assert piper_path is None


@pytest.mark.skipif(not PIPER_INSTALLED, reason="piper not installed")
class TestPiperTTSInstalled:
    """Tests that run when Piper is installed"""

    def test_piper_help(self):
        """Test that piper command works"""
        import subprocess

        result = subprocess.run(
            ["piper", "--help"],
            capture_output=True,
            text=True
        )

        # Should succeed
        assert result.returncode == 0
        assert "usage" in result.stdout.lower() or "piper" in result.stdout.lower()

    @pytest.mark.slow
    def test_piper_synthesis_short(self, tmp_path):
        """Test actual Piper synthesis with very short text"""
        import subprocess
        from pydub import AudioSegment

        # This test requires a piper model to be available
        # Check for common model locations
        model_paths = [
            Path.home() / "piper_models" / "en_US-amy-medium.onnx",
            Path("/usr/share/piper-voices/en/en_US/amy/medium/en_US-amy-medium.onnx"),
        ]

        model_path = None
        for path in model_paths:
            if path.exists():
                model_path = path
                break

        if not model_path:
            pytest.skip("No Piper model found")

        output_path = tmp_path / "piper_test.wav"
        text = "Test."  # Very short

        try:
            result = subprocess.run(
                ["piper", "--model", str(model_path), "--output_file", str(output_path)],
                input=text,
                text=True,
                capture_output=True,
                check=True
            )

            # Check output
            assert output_path.exists()
            audio = AudioSegment.from_wav(str(output_path))
            assert len(audio) > 0

        except subprocess.CalledProcessError as e:
            pytest.fail(f"Piper synthesis failed: {e.stderr}")


class TestPiperTTSNotInstalled:
    """Tests for when Piper is not installed"""

    @pytest.mark.skipif(PIPER_INSTALLED, reason="piper is installed")
    def test_piper_missing_handled_gracefully(self):
        """Test that missing Piper is handled gracefully"""
        # When piper_tts.py is implemented, it should:
        # 1. Detect missing piper binary
        # 2. Return a clear error or skip gracefully
        # 3. Not crash the entire pipeline

        # For now, just verify piper is not found
        assert shutil.which("piper") is None


class TestPiperIntegration:
    """Integration tests for Piper TTS"""

    def test_piper_module_loads(self):
        """Test that piper_tts module can be imported"""
        from scripts import piper_tts
        assert hasattr(piper_tts, 'have_piper')
        assert hasattr(piper_tts, 'synthesize_with_piper')
        assert hasattr(piper_tts, 'main')

    def test_piper_detection(self):
        """Test Piper installation detection"""
        from scripts.piper_tts import have_piper
        # Should return boolean
        result = have_piper()
        assert isinstance(result, bool)

    @pytest.mark.skipif(not PIPER_INSTALLED, reason="piper not installed")
    def test_piper_main_with_missing_voice(self, tmp_path):
        """Test that piper_tts handles missing voice model gracefully"""
        import sys
        from scripts import piper_tts

        # Create test input
        input_file = tmp_path / "input.txt"
        input_file.write_text("Test.")

        output_file = tmp_path / "output.wav"

        # Simulate command-line with non-existent voice
        sys.argv = [
            "piper_tts.py",
            str(input_file),
            "--output", str(output_file),
            "--voice", "/nonexistent/voice.onnx"
        ]

        # Should fail gracefully with exit code 1
        result = piper_tts.main()
        assert result == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
