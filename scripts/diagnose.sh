#!/usr/bin/env bash
set -euo pipefail

echo "== Python & lzma check =="
python3 - <<'PY'
try:
    import lzma
    print("OK: python lzma available")
except Exception as e:
    print("ERR: python lzma not available -> On macOS: brew install xz && (pyenv 사용시 xz 경로로 파이썬 재설치 필요).", flush=True)
    raise
PY

echo "== FFmpeg check =="
if command -v ffmpeg >/dev/null 2>&1; then
  ffmpeg -version | head -n1
else
  echo "ERR: ffmpeg not found -> brew install ffmpeg"
  exit 1
fi

echo "== Piper check =="
if command -v piper >/dev/null 2>&1; then
  echo "OK: piper found"
else
  echo "ERR: piper not found -> brew install piper 또는 릴리스 바이너리 다운로드 후 PATH 등록"
  exit 1
fi

echo "== Piper model check =="
# 모델 경로는 .env 또는 config.yaml에서 읽도록 안내. 여기선 존재 유무만 가이드.
POSSIBLE_DIRS=("$HOME/piper_models" "./piper_models")
FOUND_MODEL="no"
for d in "${POSSIBLE_DIRS[@]}"; do
  if ls "$d"/*.onnx >/dev/null 2>&1; then
    echo "OK: model candidate in $d"
    FOUND_MODEL="yes"
    break
  fi
done
if [ "$FOUND_MODEL" = "no" ]; then
  echo "WARN: piper 모델(.onnx/.json) 미발견 -> 예: en_US-amy-medium.onnx 를 ~/piper_models/ 에 두고 config에 경로 설정"
fi

echo "== All basic checks passed (or warnings printed) =="