import pathlib, subprocess, typer, yaml, os
from loguru import logger

app = typer.Typer()
def load_cfg():
    with open("config.yaml","r") as f: return yaml.safe_load(f)

def piper_tts(text, output_file, cfg):
    """Generate TTS using piper binary"""
    # Get piper settings from config or environment
    piper_exec = os.getenv("PIPER_EXEC", "piper")
    piper_model = os.getenv("PIPER_MODEL", f"{os.path.expanduser('~')}/piper_models/en_US-amy-medium.onnx")

    # Check if config specifies custom paths
    if "paths" in cfg:
        piper_exec = cfg["paths"].get("piper_exec", piper_exec)
        piper_model = cfg["paths"].get("piper_model", piper_model)

    # Expand environment variables and home directory
    piper_exec = os.path.expandvars(os.path.expanduser(piper_exec))
    piper_model = os.path.expandvars(os.path.expanduser(piper_model))
    
    # Check if piper binary exists
    piper_check = subprocess.run(["which", piper_exec], capture_output=True, text=True)
    if piper_check.returncode != 0:
        logger.error(f"❌ Piper executable not found: {piper_exec}")
        logger.error("   Fix: brew install piper")
        logger.error("   Or download from: https://github.com/rhasspy/piper/releases")
        logger.error("   Then add to PATH or set PIPER_EXEC environment variable")
        raise SystemExit(1)
    
    # Check if model file exists
    if not pathlib.Path(piper_model).exists():
        logger.error(f"❌ Piper model not found: {piper_model}")
        logger.error("   Fix: Download a model from https://github.com/rhasspy/piper/blob/master/VOICES.md")
        logger.error(f"   Example: wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx -P ~/piper_models/")
        logger.error(f"   Then set PIPER_MODEL={piper_model} in .env")
        raise SystemExit(1)
    
    # Run piper TTS
    try:
        # Save text to temporary file (piper works better with file input)
        temp_txt = pathlib.Path(output_file).parent / "temp_tts.txt"
        temp_txt.write_text(text, encoding="utf-8")
        
        cmd = [piper_exec, "--model", piper_model, "--output_file", str(output_file)]
        
        with open(temp_txt, 'r') as stdin_file:
            result = subprocess.run(cmd, stdin=stdin_file, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"❌ Piper TTS failed: {result.stderr}")
            raise SystemExit(1)
        
        # Clean up temp file
        temp_txt.unlink(missing_ok=True)
        
        logger.info(f"✓ Generated TTS audio with Piper: {output_file}")
        
    except Exception as e:
        logger.error(f"❌ TTS generation failed: {e}")
        raise SystemExit(1)

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
    piper_tts(body, wav, cfg)
    logger.success(f"TTS -> {wav}")

if __name__ == "__main__":
    app()