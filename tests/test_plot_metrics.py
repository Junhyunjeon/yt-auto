#!/usr/bin/env python3
"""
Tests for plot_tts_metrics.py - Metrics visualization
Tests CSV to PNG conversion, chart generation, and headless rendering
"""

import csv
import pathlib
import subprocess
import sys
import pytest


SAMPLE_ROWS = [
    {
        "slug": "cmp_a",
        "openai_rms": "-20.1",
        "piper_rms": "-21.0",
        "openai_duration": "8.2",
        "piper_duration": "8.0",
        "openai_silence_pct": "6.0",
        "piper_silence_pct": "7.0"
    },
    {
        "slug": "cmp_b",
        "openai_rms": "-19.3",
        "piper_rms": "-20.2",
        "openai_duration": "7.5",
        "piper_duration": "7.6",
        "openai_silence_pct": "5.5",
        "piper_silence_pct": "6.4"
    },
]


def write_csv(p):
    """Write sample CSV file"""
    with open(p, "w", newline="", encoding="utf-8") as fp:
        w = csv.DictWriter(fp, fieldnames=SAMPLE_ROWS[0].keys())
        w.writeheader()
        w.writerows(SAMPLE_ROWS)


class TestPlotMetrics:
    """Test plot generation"""

    def test_plot_generates_pngs(self, tmp_path):
        """Test that plot script generates PNG files"""
        out_reports = tmp_path / "output" / "reports"
        out_reports.mkdir(parents=True)
        csvp = out_reports / "tts_compare_20250101_000000.csv"
        write_csv(csvp)

        plots = tmp_path / "output" / "reports" / "plots"
        cmd = [
            sys.executable,
            "scripts/plot_tts_metrics.py",
            "--csv-glob", str(out_reports / "tts_compare_*.csv"),
            "--outdir", str(plots),
            "--rolling", "2"
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        assert r.returncode == 0, f"Plot failed: {r.stderr}"

        # Check PNG outputs
        outs = list(plots.glob("*.png"))
        assert outs, "No plots generated"

        names = {p.name for p in outs}
        assert "rms_trend.png" in names
        assert "duration_scatter.png" in names
        assert "openai_silence_hist.png" in names

    def test_plot_with_title_suffix(self, tmp_path):
        """Test plot with custom title suffix"""
        out_reports = tmp_path / "output" / "reports"
        out_reports.mkdir(parents=True)
        csvp = out_reports / "tts_compare_20250101_000000.csv"
        write_csv(csvp)

        plots = tmp_path / "output" / "reports" / "plots"
        cmd = [
            sys.executable,
            "scripts/plot_tts_metrics.py",
            "--csv-glob", str(out_reports / "tts_compare_*.csv"),
            "--outdir", str(plots),
            "--title-suffix", "Test Run"
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        assert r.returncode == 0

        # Should still generate plots
        outs = list(plots.glob("*.png"))
        assert len(outs) >= 3

    def test_plot_with_limit(self, tmp_path):
        """Test plot with row limit"""
        out_reports = tmp_path / "output" / "reports"
        out_reports.mkdir(parents=True)
        csvp = out_reports / "tts_compare_20250101_000000.csv"
        write_csv(csvp)

        plots = tmp_path / "output" / "reports" / "plots"
        cmd = [
            sys.executable,
            "scripts/plot_tts_metrics.py",
            "--csv-glob", str(out_reports / "tts_compare_*.csv"),
            "--outdir", str(plots),
            "--limit", "1"
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        assert r.returncode == 0

        # Should still generate plots with limited data
        outs = list(plots.glob("*.png"))
        assert len(outs) >= 3

    def test_plot_empty_csv(self, tmp_path):
        """Test plot with no data rows"""
        out_reports = tmp_path / "output" / "reports"
        out_reports.mkdir(parents=True)
        csvp = out_reports / "tts_compare_20250101_000000.csv"

        # Write header only
        with open(csvp, "w", newline="", encoding="utf-8") as fp:
            w = csv.DictWriter(fp, fieldnames=SAMPLE_ROWS[0].keys())
            w.writeheader()

        plots = tmp_path / "output" / "reports" / "plots"
        cmd = [
            sys.executable,
            "scripts/plot_tts_metrics.py",
            "--csv-glob", str(out_reports / "tts_compare_*.csv"),
            "--outdir", str(plots)
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        assert r.returncode == 0

        # Should handle gracefully
        assert "No CSV rows found" in r.stdout or plots.exists()

    def test_plot_openai_only(self, tmp_path):
        """Test plot with OpenAI data only (Piper skipped)"""
        out_reports = tmp_path / "output" / "reports"
        out_reports.mkdir(parents=True)
        csvp = out_reports / "tts_compare_20250101_000000.csv"

        # OpenAI only data
        openai_only_rows = [
            {
                "slug": "cmp_a",
                "openai_rms": "-20.1",
                "piper_rms": "",
                "openai_duration": "8.2",
                "piper_duration": "",
                "openai_silence_pct": "6.0",
                "piper_silence_pct": ""
            }
        ]

        with open(csvp, "w", newline="", encoding="utf-8") as fp:
            w = csv.DictWriter(fp, fieldnames=openai_only_rows[0].keys())
            w.writeheader()
            w.writerows(openai_only_rows)

        plots = tmp_path / "output" / "reports" / "plots"
        cmd = [
            sys.executable,
            "scripts/plot_tts_metrics.py",
            "--csv-glob", str(out_reports / "tts_compare_*.csv"),
            "--outdir", str(plots)
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        assert r.returncode == 0

        # Should generate OpenAI plots only
        names = {p.name for p in plots.glob("*.png")}
        assert "openai_silence_hist.png" in names
        # Piper plot may or may not exist depending on skip logic


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
