import re, pathlib
import typer, yaml
from slugify import slugify
from loguru import logger

app = typer.Typer()
def load_cfg():
    with open("config.yaml","r") as f: return yaml.safe_load(f)

@app.command()
def run(input_path: str):
    cfg = load_cfg()
    text = pathlib.Path(input_path).read_text(encoding="utf-8")
    text = re.sub(r'[^\S\r\n]+',' ', text).strip()
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    clean = "\n".join(lines)
    slug = slugify(pathlib.Path(input_path).stem)[:80]
    outdir = pathlib.Path(cfg["paths"]["work_dir"]) / slug
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir/"clean_ko.txt").write_text(clean, encoding="utf-8")
    logger.success(f"Prepared -> {outdir}/clean_ko.txt")
    print(slug)

if __name__ == "__main__":
    app()