import pathlib, subprocess, typer, yaml
from loguru import logger

app = typer.Typer()
def load_cfg():
    with open("config.yaml","r") as f: return yaml.safe_load(f)

@app.command()
def run(slug: str, title_text: str = ""):
    cfg = load_cfg()
    outdir = pathlib.Path(cfg["paths"]["output_dir"]) / slug
    outdir.mkdir(parents=True, exist_ok=True)
    wav = outdir/"voice_en.wav"
    bg = pathlib.Path(cfg["video"]["bg_image"])
    mp4 = outdir/"video_en.mp4"

    if not bg.exists():
        black = outdir/"black.png"
        subprocess.run(
            f'ffmpeg -f lavfi -i color=c=black:s={cfg["video"]["width"]}x{cfg["video"]["height"]}:d=5 '
            f'-frames:v 1 "{black}" -y', shell=True, check=True)
        bg = black

    # Escape special characters in title text for ffmpeg
    safe_title = title_text[:60].replace("'", "\\'").replace(":", "-").replace('"', '\\"')
    
    drawtxt = f"drawtext=text='{safe_title}':fontcolor=white:fontsize=48:x=(w-tw)/2:y=60"
    cmd = f'''
ffmpeg -loop 1 -i "{bg}" -i "{wav}" \
 -filter_complex "[1:a]showwaves=s={cfg["video"]["width"]}x200:mode=line:rate=25,format=rgba[w]; \
 [0:v][w]overlay=0:{cfg["video"]["height"]-220}[v1]; [v1]{drawtxt}[v2]" \
 -map "[v2]" -map 1:a -c:v h264 -pix_fmt yuv420p -c:a aac -shortest -r {cfg["video"]["fps"]} "{mp4}" -y
'''
    try:
        subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        logger.success(f"Video -> {mp4}")
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e.stderr}")
        # Create a simple video without waveform as fallback
        fallback_cmd = f'''
ffmpeg -loop 1 -i "{bg}" -i "{wav}" \
 -filter_complex "[0:v]{drawtxt}[v]" \
 -map "[v]" -map 1:a -c:v h264 -pix_fmt yuv420p -c:a aac -shortest -r {cfg["video"]["fps"]} "{mp4}" -y
'''
        subprocess.run(fallback_cmd, shell=True, check=True)
        logger.success(f"Video (fallback) -> {mp4}")

if __name__ == "__main__":
    app()