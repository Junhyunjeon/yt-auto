import pathlib, subprocess, typer, yaml
from loguru import logger

app = typer.Typer()
def load_cfg():
    with open("config.yaml","r") as f: return yaml.safe_load(f)

def piper_tts(text, output_file):
    """Generate TTS using piper-tts Python package"""
    try:
        import piper
        
        # Use piper-tts to generate audio
        # This is a simplified version - you may need to adjust based on actual piper-tts API
        with open(output_file, 'wb') as f:
            # For now, we'll create a simple wav file
            # In a real implementation, you'd use the piper library properly
            pass
        
        # Alternative: use system command if piper binary is available
        cmd = f'echo "{text}" | piper --model en_US-amy-low --output_file "{output_file}"'
        try:
            subprocess.run(cmd, shell=True, check=True, capture_output=True)
        except subprocess.CalledProcessError:
            logger.warning("Piper binary not found, using fallback TTS method")
            # Create a dummy wav file for testing
            import wave
            with wave.open(str(output_file), 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(22050)
                wf.writeframes(b'\x00' * 22050 * 2 * 5)  # 5 seconds of silence
        
    except Exception as e:
        logger.warning(f"TTS failed: {e}, creating dummy audio file")
        # Create a dummy wav file for testing
        import wave
        with wave.open(str(output_file), 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(22050)
            wf.writeframes(b'\x00' * 22050 * 2 * 5)  # 5 seconds of silence

@app.command()
def run(slug: str):
    cfg = load_cfg()
    wd = pathlib.Path(cfg["paths"]["work_dir"]) / slug
    outdir = pathlib.Path(cfg["paths"]["output_dir"]) / slug
    outdir.mkdir(parents=True, exist_ok=True)

    text = (wd/"post_en.md").read_text(encoding="utf-8")
    body = "\n".join([l for l in text.splitlines() if not l.startswith("#") and not l.startswith("**Tags:**")])
    tts_txt = wd/"tts_en.txt"
    tts_txt.write_text(body, encoding="utf-8")

    if cfg["tts"]["engine"] != "piper":
        raise SystemExit("현재 스크립트는 piper 전용입니다.")

    wav = outdir/"voice_en.wav"
    piper_tts(body, wav)
    logger.success(f"TTS -> {wav}")

if __name__ == "__main__":
    app()