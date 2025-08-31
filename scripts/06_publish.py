import pathlib, requests, typer, yaml
from loguru import logger

app = typer.Typer()
def load_cfg():
    with open("config.yaml","r") as f: return yaml.safe_load(f)

@app.command()
def wordpress(slug: str):
    cfg = load_cfg()
    wp = cfg["publish"]["wordpress"]
    if not wp["enabled"]:
        raise SystemExit("WordPress publish disabled in config.yaml")

    wd = pathlib.Path(cfg["paths"]["work_dir"]) / slug
    post_md = (wd/"post_en.md").read_text(encoding="utf-8")
    title = post_md.splitlines()[0].lstrip("# ").strip()

    r = requests.post(
        f"{wp['base_url'].rstrip('/')}/posts",
        auth=(wp["username"], wp["app_password"]),
        json={"title": title, "status": "draft", "content": post_md, "categories": wp["category_ids"]},
        timeout=30
    )
    r.raise_for_status()
    logger.success(f"WP Draft URL: {r.json().get('link')}")

@app.command()
def youtube(slug: str):
    cfg = load_cfg()
    yt = cfg["publish"]["youtube"]
    if not yt["enabled"]:
        raise SystemExit("YouTube publish disabled in config.yaml")
    
    wd = pathlib.Path(cfg["paths"]["work_dir"]) / slug
    outdir = pathlib.Path(cfg["paths"]["output_dir"]) / slug
    
    post_md = (wd/"post_en.md").read_text(encoding="utf-8")
    title = post_md.splitlines()[0].lstrip("# ").strip()
    
    video_file = outdir / "video_en.mp4"
    
    logger.info(f"YouTube upload would upload: {video_file}")
    logger.info(f"Title: {title}")
    logger.info(f"Privacy: {yt['default_privacy']}")
    logger.warning("YouTube upload not implemented yet - would require OAuth setup")

if __name__ == "__main__":
    app()