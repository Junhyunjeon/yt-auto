#!/usr/bin/env python3
"""
Compare Report to Markdown/CSV - Aggregate comparison reports
Converts multiple compare_report.json files to CSV and Markdown tables
"""
import json
import csv
import argparse
import pathlib
import datetime as dt
from glob import glob

FIELDS = [
    "slug", "pause_profile", "fade_ms", "crossfade_ms", "max_chars",
    "openai_duration", "openai_rms", "openai_peak", "openai_silence_pct",
    "piper_duration", "piper_rms", "piper_peak", "piper_silence_pct",
    "piper_skipped"
]


def g(d, *ks, default=None):
    """Safe nested dict getter"""
    cur = d
    for k in ks:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def row_from(j: dict) -> dict:
    """Extract row data from compare_report.json structure"""
    # Use slug field first, fallback to input file stem
    slug = j.get("slug", "")
    if not slug:
        inp = j.get("input_file", "")
        slug = pathlib.Path(inp).stem if inp else ""

    # Settings can be in "settings" or "notes" field
    settings = j.get("settings", j.get("notes", {})) or {}
    oa = j.get("openai", {}) or {}
    pp = j.get("piper", {}) or {}

    return {
        "slug": slug,
        "pause_profile": settings.get("pause_profile"),
        "fade_ms": settings.get("fade_ms"),
        "crossfade_ms": settings.get("crossfade_ms"),
        "max_chars": settings.get("max_chars"),
        "openai_duration": oa.get("duration_sec"),
        "openai_rms": oa.get("rms_dbfs"),
        "openai_peak": oa.get("peak_dbfs"),
        "openai_silence_pct": oa.get("silence_ratio"),  # Note: silence_ratio in current schema
        "piper_duration": pp.get("duration_sec"),
        "piper_rms": pp.get("rms_dbfs"),
        "piper_peak": pp.get("peak_dbfs"),
        "piper_silence_pct": pp.get("silence_ratio"),
        "piper_skipped": pp.get("status") == "skipped",
    }


def write_csv(rows, path: pathlib.Path):
    """Write rows to CSV file"""
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    with path.open("w", newline="", encoding="utf-8") as fp:
        w = csv.DictWriter(fp, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})


def write_md(rows, path: pathlib.Path, title_ts: str):
    """Write rows to Markdown table"""
    with path.open("w", encoding="utf-8") as fp:
        fp.write(f"# TTS Compare Summary ({title_ts})\n\n")

        if not rows:
            fp.write("_No data found._\n")
            return

        # Header
        hdr = "| " + " | ".join(FIELDS) + " |\n"
        sep = "| " + " | ".join(["---"] * len(FIELDS)) + " |\n"
        fp.write(hdr)
        fp.write(sep)

        # Rows
        for r in rows:
            fp.write("| " + " | ".join([str(r.get(k, "")) for k in FIELDS]) + " |\n")


def main():
    """CLI interface"""
    ap = argparse.ArgumentParser(
        description="Aggregate compare_report.json files to CSV/Markdown."
    )
    ap.add_argument("--work-glob", default="work/*/compare_report.json",
                    help="Glob pattern to find reports")
    ap.add_argument("--outdir", default="output/reports",
                    help="Output directory")
    ap.add_argument("--sort", default="",
                    help="Sort key (e.g., openai_rms,-openai_duration)")
    ap.add_argument("--limit", type=int, default=0,
                    help="Limit number of rows")
    args = ap.parse_args()

    outdir = pathlib.Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    files = sorted(glob(args.work_glob))
    rows = []

    for f in files:
        try:
            j = json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
            rows.append(row_from(j))
        except Exception as e:
            # Skip files that can't be parsed
            print(f"[skip] {f}: {e}")

    # Sort if requested
    # Format: "key1,-key2" (- prefix for descending)
    if args.sort:
        keys = [k.strip() for k in args.sort.split(",") if k.strip()]
        for k in reversed(keys):
            rev = k.startswith("-")
            kk = k[1:] if rev else k
            rows.sort(key=lambda r: (r.get(kk) is None, r.get(kk)), reverse=rev)

    # Limit if requested
    if args.limit > 0:
        rows = rows[:args.limit]

    # Generate timestamped output files
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    csvp = outdir / f"tts_compare_{ts}.csv"
    mdp = outdir / f"tts_compare_{ts}.md"

    write_csv(rows, csvp)
    write_md(rows, mdp, ts)

    print(f"CSV: {csvp}\nMD:  {mdp}\nRows: {len(rows)}")


if __name__ == "__main__":
    main()
