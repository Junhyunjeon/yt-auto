#!/usr/bin/env python3
"""
Tests for compare_report_to_md.py - Report export functionality
Tests JSON aggregation, CSV/Markdown generation, sorting, and error handling
"""

import json
import pathlib
import subprocess
import sys
import tempfile
import pytest


# Minimal test data - OpenAI only (Piper skipped)
MIN_JSON_OA = {
    "input_file": "work/slugA/input.txt",
    "slug": "slugA",
    "openai": {
        "duration_sec": 1.23,
        "rms_dbfs": -18.1,
        "peak_dbfs": -2.2,
        "silence_ratio": 7.5
    },
    "piper": {
        "status": "skipped",
        "reason": "Piper not available"
    },
    "settings": {
        "pause_profile": "natural",
        "fade_ms": 20,
        "crossfade_ms": 50,
        "max_chars": 800
    }
}

# Test data with both engines
MIN_JSON_PP = {
    "input_file": "work/slugB/input.txt",
    "slug": "slugB",
    "openai": {
        "duration_sec": 2.0,
        "rms_dbfs": -19.0,
        "peak_dbfs": -3.0,
        "silence_ratio": 5.0
    },
    "piper": {
        "duration_sec": 1.95,
        "rms_dbfs": -20.5,
        "peak_dbfs": -3.2,
        "silence_ratio": 6.0
    },
    "settings": {
        "pause_profile": "natural",
        "fade_ms": 20,
        "crossfade_ms": 50,
        "max_chars": 800
    }
}


def run_export(work_glob, outdir):
    """Run compare_report_to_md.py with given parameters"""
    cmd = [
        sys.executable,
        "scripts/compare_report_to_md.py",
        "--work-glob", work_glob,
        "--outdir", str(outdir)
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, f"Export failed: {r.stderr}"
    return r.stdout


class TestReportExport:
    """Test report export functionality"""

    def test_export_basic(self, tmp_path):
        """Test basic export with two reports"""
        # Create first report (OpenAI only)
        w1 = tmp_path / "work" / "x1"
        w1.mkdir(parents=True)
        (w1 / "compare_report.json").write_text(
            json.dumps(MIN_JSON_OA), encoding="utf-8"
        )

        # Create second report (both engines)
        w2 = tmp_path / "work" / "x2"
        w2.mkdir(parents=True)
        (w2 / "compare_report.json").write_text(
            json.dumps(MIN_JSON_PP), encoding="utf-8"
        )

        outdir = tmp_path / "out"
        out = run_export(str(tmp_path / "work/*/compare_report.json"), outdir)

        # Check output message
        assert "CSV:" in out
        assert "MD:" in out
        assert "Rows: 2" in out

        # Check files exist
        csvs = list(outdir.glob("*.csv"))
        mds = list(outdir.glob("*.md"))
        assert len(csvs) == 1
        assert len(mds) == 1

        # Verify CSV content
        csvtext = csvs[0].read_text(encoding="utf-8")
        assert "openai_duration" in csvtext
        assert "piper_skipped" in csvtext
        assert "slugA" in csvtext
        assert "slugB" in csvtext

        # Verify CSV has header + 2 data rows
        lines = csvtext.strip().split("\n")
        assert len(lines) == 3  # header + 2 rows

        # Verify Markdown content
        mdtext = mds[0].read_text(encoding="utf-8")
        assert "TTS Compare Summary" in mdtext
        assert "slugA" in mdtext
        assert "slugB" in mdtext
        assert "|" in mdtext  # Table format

    def test_export_empty(self, tmp_path):
        """Test export with no reports found"""
        outdir = tmp_path / "out"
        out = run_export(str(tmp_path / "nonexistent/*/report.json"), outdir)

        assert "Rows: 0" in out

        # Files should still be created but empty/minimal
        csvs = list(outdir.glob("*.csv"))
        mds = list(outdir.glob("*.md"))
        assert len(csvs) == 1
        assert len(mds) == 1

        # MD should have "No data" message
        mdtext = mds[0].read_text(encoding="utf-8")
        assert "No data found" in mdtext

    def test_export_malformed_json(self, tmp_path):
        """Test that malformed JSON is skipped gracefully"""
        w1 = tmp_path / "work" / "good"
        w1.mkdir(parents=True)
        (w1 / "compare_report.json").write_text(
            json.dumps(MIN_JSON_OA), encoding="utf-8"
        )

        w2 = tmp_path / "work" / "bad"
        w2.mkdir(parents=True)
        (w2 / "compare_report.json").write_text(
            "{ invalid json }", encoding="utf-8"
        )

        outdir = tmp_path / "out"
        out = run_export(str(tmp_path / "work/*/compare_report.json"), outdir)

        # Should process the good one and skip the bad one
        assert "Rows: 1" in out
        assert "[skip]" in out  # Should print skip message

    def test_export_missing_fields(self, tmp_path):
        """Test that missing fields are handled gracefully"""
        # Minimal JSON with only required fields
        minimal = {
            "input_file": "test.txt",
            "openai": {"duration_sec": 1.0}
        }

        w1 = tmp_path / "work" / "minimal"
        w1.mkdir(parents=True)
        (w1 / "compare_report.json").write_text(
            json.dumps(minimal), encoding="utf-8"
        )

        outdir = tmp_path / "out"
        out = run_export(str(tmp_path / "work/*/compare_report.json"), outdir)

        assert "Rows: 1" in out

        # CSV should have empty cells for missing fields
        csvs = list(outdir.glob("*.csv"))
        csvtext = csvs[0].read_text(encoding="utf-8")
        assert "test" in csvtext  # slug from filename

    def test_piper_skipped_flag(self, tmp_path):
        """Test that piper_skipped flag is correctly set"""
        w1 = tmp_path / "work" / "x1"
        w1.mkdir(parents=True)
        (w1 / "compare_report.json").write_text(
            json.dumps(MIN_JSON_OA), encoding="utf-8"
        )

        outdir = tmp_path / "out"
        run_export(str(tmp_path / "work/*/compare_report.json"), outdir)

        csvs = list(outdir.glob("*.csv"))
        csvtext = csvs[0].read_text(encoding="utf-8")

        # Should have True for piper_skipped
        lines = csvtext.strip().split("\n")
        header = lines[0].split(",")
        data = lines[1].split(",")

        piper_skipped_idx = header.index("piper_skipped")
        assert data[piper_skipped_idx] == "True"


class TestReportExportCLI:
    """Test CLI options"""

    def test_custom_output_dir(self, tmp_path):
        """Test custom output directory"""
        w1 = tmp_path / "work" / "x1"
        w1.mkdir(parents=True)
        (w1 / "compare_report.json").write_text(
            json.dumps(MIN_JSON_OA), encoding="utf-8"
        )

        custom_outdir = tmp_path / "custom_reports"
        run_export(str(tmp_path / "work/*/compare_report.json"), custom_outdir)

        assert custom_outdir.exists()
        assert len(list(custom_outdir.glob("*.csv"))) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
