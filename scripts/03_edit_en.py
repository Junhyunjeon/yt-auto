import pathlib, re, typer, yaml
from loguru import logger

app = typer.Typer()
def load_cfg():
    with open("config.yaml","r") as f: return yaml.safe_load(f)

@app.command()
def run(slug: str):
    cfg = load_cfg()
    wd = pathlib.Path(cfg["paths"]["work_dir"]) / slug
    text = (wd/"draft_en.txt").read_text(encoding="utf-8")
    first_line = text.splitlines()[0][:90] if text.strip() else "Untitled"
    title = f'{cfg["seo"]["title_prefix"]}{first_line}'.strip()
    body = re.sub(r'\s+\.', '.', text).strip()
    tags = ", ".join(cfg["seo"]["tags"])
    md = f"# {title}\n\n{body}\n\n---\n**Tags:** {tags}\n"
    (wd/"post_en.md").write_text(md, encoding="utf-8")
    logger.success(f"Edited -> {wd}/post_en.md")
    print(title)

if __name__ == "__main__":
    app()