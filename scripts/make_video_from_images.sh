#!/usr/bin/env bash
# Simple compositor: background PNG + character PNG -> MP4
# deps: ffmpeg
set -euo pipefail

# --- defaults ---
FPS=30
RES="1920:1080"        # W:H
DUR=30                 # seconds (used when no audio)
POS_X=1400             # character x
POS_Y=620              # character base y
BOB_AMPL=10            # character subtle up-down pixels
BOB_HZ=0.25            # bobbing cycles per second
CHAR_MAX_W=420         # scale down character width if larger
KEY_MODE="none"        # none|green
AUDIO=""               # optional audio path

usage() {
  cat <<USAGE
Usage:
  $0 --bg images/background_office1.png \\
     --char images/character.png \\
     --out output/final_office1.mp4 \\
     [--audio output/sample_en.wav] \\
     [--dur 45] [--pos 1400,620] [--res 1920:1080] [--key green]

Notes:
  - If --audio is given, video length matches audio (shortest).
  - --key green : remove green background from character.
  - Subtle bobbing applied: y = base_y + A*sin(2*pi*t*f)
USAGE
}

# --- parse args ---
BG=""
CHAR=""
OUT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --bg) BG="$2"; shift 2;;
    --char) CHAR="$2"; shift 2;;
    --out) OUT="$2"; shift 2;;
    --audio) AUDIO="$2"; shift 2;;
    --dur) DUR="$2"; shift 2;;
    --fps) FPS="$2"; shift 2;;
    --res) RES="$2"; shift 2;;
    --pos) POS_X="$(echo "$2" | cut -d, -f1)"; POS_Y="$(echo "$2" | cut -d, -f2)"; shift 2;;
    --char-max-w) CHAR_MAX_W="$2"; shift 2;;
    --key) KEY_MODE="$2"; shift 2;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown arg: $1"; usage; exit 1;;
  esac
done

[[ -z "${BG}" || -z "${CHAR}" || -z "${OUT}" ]] && { usage; exit 1; }

W="${RES%:*}"
H="${RES#*:}"

# inputs
IN_OPTS=()
IN_OPTS+=( -loop 1 -framerate "${FPS}" -i "${BG}" )
IN_OPTS+=( -loop 1 -framerate "${FPS}" -i "${CHAR}" )
[[ -n "${AUDIO}" ]] && IN_OPTS+=( -i "${AUDIO}" )

# build filter graph
#  [0:v] -> bg scaled
#  [1:v] -> char scaled (cap width), optional green-key, slight bobbing on overlay y
#  overlay -> composited video
BG_F="[0:v]scale=${W}:${H},format=yuv420p[bg]"
CHAR_SCALE="scale='min(${CHAR_MAX_W},iw)':'-1':force_original_aspect_ratio=decrease,format=rgba"
case "${KEY_MODE}" in
  green)
    # Adjust key color/thresholds if needed
    CHAR_CHAIN="[1:v]${CHAR_SCALE},colorkey=0x00FF00:0.35:0.20[char]"
    ;;
  none|*)
    CHAR_CHAIN="[1:v]${CHAR_SCALE}[char]"
    ;;
esac

# overlay with bobbing motion (y = base + A*sin(2*pi*t*f))
OVER_Y="'${POS_Y}+${BOB_AMPL}*sin(2*PI*t*${BOB_HZ})'"
COMPOSE="[bg][char]overlay=x=${POS_X}:y=${OVER_Y}:format=auto[vid]"

FILTERS="${BG_F};${CHAR_CHAIN};${COMPOSE}"

# map & duration handling
MAP_OPTS=( -map "[vid]" )
if [[ -n "${AUDIO}" ]]; then
  MAP_OPTS+=( -map 2:a -shortest )
else
  MAP_OPTS+=( -t "${DUR}" )
fi

# encode
ffmpeg -y \
  "${IN_OPTS[@]}" \
  -filter_complex "${FILTERS}" \
  "${MAP_OPTS[@]}" \
  -r "${FPS}" -c:v libx264 -crf 18 -pix_fmt yuv420p \
  -c:a aac -b:a 192k \
  "${OUT}"

echo "✅ Video created: ${OUT}"
