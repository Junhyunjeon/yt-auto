#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plot TTS Comparison Metrics - Visualize CSV reports
Converts CSV reports from compare_report_to_md.py into PNG charts
- No pandas. Uses csv + matplotlib only.
- Saves PNGs under output/reports/plots/
"""
import os
import csv
import argparse
import pathlib
import re
from glob import glob
import matplotlib
matplotlib.use("Agg")  # headless mode for CI/server
import matplotlib.pyplot as plt


def parse_args():
    """Parse command-line arguments"""
    ap = argparse.ArgumentParser(
        description="Plot TTS metrics from CSV reports."
    )
    ap.add_argument("--csv-glob", default="output/reports/tts_compare_*.csv",
                    help="Glob pattern for input CSV files")
    ap.add_argument("--outdir", default="output/reports/plots",
                    help="Directory to save plot images")
    ap.add_argument("--rolling", type=int, default=0,
                    help="Rolling window for trend lines (0=disabled)")
    ap.add_argument("--limit", type=int, default=0,
                    help="Limit number of rows (after sort)")
    ap.add_argument("--title-suffix", default="",
                    help="Extra title suffix for charts")
    return ap.parse_args()


def load_rows(csv_paths):
    """Load all rows from CSV files"""
    rows = []
    for p in csv_paths:
        try:
            with open(p, newline="", encoding="utf-8") as fp:
                rdr = csv.DictReader(fp)
                for r in rdr:
                    r["_source"] = p
                    rows.append(r)
        except Exception as e:
            print(f"[skip] {p}: {e}")
    return rows


def to_float(x):
    """Safely convert to float"""
    try:
        if x is None or x == "":
            return None
        return float(x)
    except Exception:
        return None


def sort_key(row):
    """Sort key: timestamp from filename → slug"""
    # Extract timestamp from filename: tts_compare_20251011_220027.csv
    m = re.search(r"tts_compare_(\d{8}_\d{6})", row.get("_source", ""))
    ts = m.group(1) if m else ""
    return (ts, row.get("slug", ""))


def rolling_mean(seq, w):
    """Calculate rolling mean with window size w"""
    if w <= 1:
        return seq[:]

    out = []
    buf = []
    for v in seq:
        buf.append(v)
        if len(buf) > w:
            buf.pop(0)
        valid = [x for x in buf if x is not None]
        out.append(sum(valid) / len(valid) if valid else None)
    return out


def ensure_outdir(p):
    """Ensure output directory exists"""
    p = pathlib.Path(p)
    p.mkdir(parents=True, exist_ok=True)
    return p


def plot_trend(x_idx, y1, y2, labels, title, outpath, rolling=0):
    """Plot trend line chart"""
    xi = list(range(len(x_idx)))
    plt.figure(figsize=(12, 6))

    # Apply rolling mean if requested
    y1p = rolling_mean(y1, rolling) if rolling > 1 else y1
    plt.plot(xi, y1p, label=labels[0], marker='o', markersize=4)

    # Plot second series if available
    if any(v is not None for v in y2):
        y2p = rolling_mean(y2, rolling) if rolling > 1 else y2
        plt.plot(xi, y2p, label=labels[1], marker='s', markersize=4)

    plt.xticks(xi, x_idx, rotation=45, ha="right", fontsize=8)
    plt.legend()
    plt.title(title)
    plt.ylabel("RMS (dBFS)")
    plt.xlabel("Comparison Run")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(outpath, dpi=100)
    plt.close()


def plot_scatter(x, y, title, outpath):
    """Plot scatter plot with y=x reference line"""
    xs = [a for a, b in zip(x, y) if a is not None and b is not None]
    ys = [b for a, b in zip(x, y) if a is not None and b is not None]

    plt.figure(figsize=(8, 8))
    plt.scatter(xs, ys, s=30, alpha=0.6)

    # Add y=x reference line
    if xs and ys:
        lo = min(min(xs), min(ys))
        hi = max(max(xs), max(ys))
        plt.plot([lo, hi], [lo, hi], 'r--', alpha=0.5, label='y=x')
        plt.legend()

    plt.xlabel("OpenAI duration (sec)")
    plt.ylabel("Piper duration (sec)")
    plt.title(title)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(outpath, dpi=100)
    plt.close()


def plot_hist(data, title, outpath, bins=20):
    """Plot histogram"""
    v = [d for d in data if d is not None]

    if not v:
        print(f"[skip] {title}: no data")
        return

    plt.figure(figsize=(10, 6))
    plt.hist(v, bins=bins, edgecolor='black', alpha=0.7)
    plt.title(title)
    plt.xlabel("Silence Ratio (%)")
    plt.ylabel("Frequency")
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    plt.savefig(outpath, dpi=100)
    plt.close()


def main():
    """Main execution"""
    args = parse_args()
    outdir = ensure_outdir(args.outdir)

    # Load CSV files
    csv_paths = sorted(glob(args.csv_glob))
    rows = load_rows(csv_paths)

    if not rows:
        print("No CSV rows found. Make sure to run compare_report_to_md.py first.")
        return 0

    # Sort and limit
    rows.sort(key=sort_key)
    if args.limit > 0:
        rows = rows[-args.limit:]

    # Extract data
    x_idx = [r.get("slug", "") for r in rows]
    oa_rms = [to_float(r.get("openai_rms")) for r in rows]
    pp_rms = [to_float(r.get("piper_rms")) for r in rows]
    oa_dur = [to_float(r.get("openai_duration")) for r in rows]
    pp_dur = [to_float(r.get("piper_duration")) for r in rows]
    oa_sil = [to_float(r.get("openai_silence_pct")) for r in rows]
    pp_sil = [to_float(r.get("piper_silence_pct")) for r in rows]

    suf = f" {args.title_suffix}" if args.title_suffix else ""

    # 1) RMS Trend
    print("Generating RMS trend plot...")
    plot_trend(
        x_idx, oa_rms, pp_rms,
        labels=("OpenAI RMS (dBFS)", "Piper RMS (dBFS)"),
        title=f"TTS RMS Trend{suf}",
        outpath=outdir / "rms_trend.png",
        rolling=args.rolling
    )

    # 2) Duration Scatter
    print("Generating duration scatter plot...")
    plot_scatter(
        oa_dur, pp_dur,
        title=f"Duration: OpenAI vs Piper (y=x){suf}",
        outpath=outdir / "duration_scatter.png"
    )

    # 3) Silence Histograms
    print("Generating silence histograms...")
    plot_hist(
        oa_sil,
        title=f"OpenAI Silence % Histogram{suf}",
        outpath=outdir / "openai_silence_hist.png"
    )

    if any(v is not None for v in pp_sil):
        plot_hist(
            pp_sil,
            title=f"Piper Silence % Histogram{suf}",
            outpath=outdir / "piper_silence_hist.png"
        )

    print(f"✅ Plots saved to: {outdir}")
    print(f"   - rms_trend.png")
    print(f"   - duration_scatter.png")
    print(f"   - openai_silence_hist.png")
    if any(v is not None for v in pp_sil):
        print(f"   - piper_silence_hist.png")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
