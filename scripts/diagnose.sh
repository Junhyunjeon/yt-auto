#!/usr/bin/env bash
set -euo pipefail

say_ok()   { printf "OK: %s\n" "$1"; }
say_err()  { printf "ERR: %s\n" "$1"; }

echo "== Python & venv check =="
if python -c "import sys; assert sys.version_info[:2] == (3,10); print(sys.version)" 2>/dev/null; then
  say_ok "Python 3.10.x active"
else
  say_err "Python 3.10.x not active (run: source .venv/bin/activate)"
fi
python -c "import sys; print('exe=', sys.executable)"

echo "== lzma check =="
python - <<'PY'
try:
    import lzma; print("OK: lzma available")
except Exception as e:
    print("ERR: lzma not available", e)
PY

echo "== FFmpeg check =="
if command -v ffmpeg >/dev/null 2>&1; then
  ffmpeg -version | head -n1
  say_ok "ffmpeg found"
else
  say_err "ffmpeg not found (brew install ffmpeg)"
fi

echo "== Piper binary check =="
if command -v piper >/dev/null 2>&1; then
  piper -h >/dev/null 2>&1 && say_ok "piper binary found"
else
  say_err "piper binary not found (this is OK if you use: python -m piper)"
fi

echo "== Piper (python module) check =="
if python -m piper -h >/dev/null 2>&1; then
  say_ok "python -m piper works"
else
  say_err "python -m piper failed (check venv and installation: pip install piper-tts)"
fi

echo "== Piper voice model check (en_US-amy) =="
if [[ -f "assets/voices/en_US-amy-medium.onnx" && -f "assets/voices/en_US-amy-medium.onnx.json" ]]; then
  say_ok "en_US-amy model present"
else
  say_err "voice model missing (download .onnx & .json to assets/voices/)"
fi

echo "== Argos Translate check =="
python - <<'PY'
try:
    import argostranslate.package, argostranslate.translate
    print("OK: argostranslate import")
    # Check ko->en installed
    installed = argostranslate.package.get_installed_packages()
    ko_en_ok = any(p.from_code=="ko" and p.to_code=="en" for p in installed)
    print("OK: ko->en package installed" if ko_en_ok else "ERR: ko->en package NOT installed")
except Exception as e:
    print("ERR: argostranslate problem:", e)
PY
