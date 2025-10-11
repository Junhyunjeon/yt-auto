#!/usr/bin/env python3
"""
Generate test audio fixtures
Run once to create fake.wav and silence_500ms.wav
"""

import numpy as np
from pydub import AudioSegment
from pathlib import Path

def generate_tone(frequency_hz: float, duration_sec: float, sample_rate: int = 44100) -> AudioSegment:
    """Generate a sine wave tone"""
    num_samples = int(duration_sec * sample_rate)
    t = np.linspace(0, duration_sec, num_samples, False)

    # Generate sine wave
    wave = np.sin(2 * np.pi * frequency_hz * t)

    # Convert to 16-bit PCM
    audio_array = (wave * 32767).astype(np.int16)

    # Create AudioSegment
    audio = AudioSegment(
        audio_array.tobytes(),
        frame_rate=sample_rate,
        sample_width=2,  # 16-bit
        channels=1
    )

    return audio

def main():
    """Generate fixture files"""
    fixtures_dir = Path(__file__).parent / "data"
    fixtures_dir.mkdir(exist_ok=True, parents=True)

    # Generate 440Hz tone for 0.5 seconds
    print("Generating fake.wav (440Hz tone, 0.5s)...")
    tone = generate_tone(440, 0.5)
    tone.export(fixtures_dir / "fake.wav", format="wav")

    # Generate 0.5s silence
    print("Generating silence_500ms.wav...")
    silence = AudioSegment.silent(duration=500)  # 500ms
    silence.export(fixtures_dir / "silence_500ms.wav", format="wav")

    print(f"✅ Fixtures generated in {fixtures_dir}")
    print(f"   fake.wav: {(fixtures_dir / 'fake.wav').stat().st_size} bytes")
    print(f"   silence_500ms.wav: {(fixtures_dir / 'silence_500ms.wav').stat().st_size} bytes")

if __name__ == "__main__":
    main()
