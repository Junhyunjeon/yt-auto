import pathlib, typer, yaml
from loguru import logger

app = typer.Typer()
def load_cfg():
    with open("config.yaml","r") as f: return yaml.safe_load(f)

def simple_translate(text, src="ko", tgt="en"):
    # Simple translation fallback if Argos fails
    # This is a placeholder - in production you might want to use Google Translate API
    return text  # For now, just return original text

def argos_translate(text, src="ko", tgt="en"):
    try:
        import argostranslate.translate as T
        return T.translate(text, from_code=src, to_code=tgt)
    except ModuleNotFoundError as e:
        if "_lzma" in str(e):
            logger.error("❌ Python lzma module not available!")
            logger.error("   Fix: brew install xz")
            logger.error("   Then: pyenv install --force $(pyenv version-name)")
            logger.error("   Or reinstall Python with xz support")
            raise SystemExit(1)
        else:
            logger.error(f"❌ Argos translation module not found: {e}")
            logger.error("   Fix: pip install argostranslate")
            raise SystemExit(1)
    except Exception as e:
        logger.error(f"❌ Translation failed: {e}")
        logger.error("   This is a critical error - translation cannot proceed")
        raise SystemExit(1)

@app.command()
def run(slug: str):
    cfg = load_cfg()
    wd = pathlib.Path(cfg["paths"]["work_dir"]) / slug
    src = (wd/"clean_ko.txt").read_text(encoding="utf-8")
    if cfg["use_api"]:
        raise SystemExit("API 번역 분기는 비활성화 상태(use_api=false 권장).")
    en = argos_translate(src, cfg["language"]["source"], cfg["language"]["target"])
    (wd/"draft_en.txt").write_text(en, encoding="utf-8")
    logger.success(f"Translated -> {wd}/draft_en.txt")

if __name__ == "__main__":
    app()