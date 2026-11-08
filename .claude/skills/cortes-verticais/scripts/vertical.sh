#!/usr/bin/env bash
# Uso: vertical.sh entrada saida INICIO FIM MODO(crop|blur|split) [OFFSET_X -1..1] [TITULO]
set -euo pipefail
in="${1:?entrada}"; out="${2:?saida}"; ss="${3:?inicio}"; to="${4:?fim}"; modo="${5:-crop}"
off="${6:-0}"; titulo="${7:-}"
mkdir -p "$(dirname "$out")"
case "$modo" in
  crop)
    vf="scale=-2:1920,crop=1080:1920:(iw-1080)/2*(1+${off}):0" ;;
  blur)
    vf="split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg];[b]scale=1080:-2[fg];[bg][fg]overlay=0:(H-h)/2" ;;
  split)
    vf="split[l][r];[l]crop=iw/2:ih:0:0,scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[top];[r]crop=iw/2:ih:iw/2:0,scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[bot];[top][bot]vstack" ;;
  *) echo "Modo inválido: $modo (use crop|blur|split)" >&2; exit 1 ;;
esac
vf="$vf,setsar=1,fps=30,format=yuv420p"
if [[ -n "$titulo" ]]; then
  tf=$(mktemp); printf '%s' "$titulo" > "$tf"; trap 'rm -f "$tf"' EXIT
  vf="$vf,drawtext=textfile=$tf:fontsize=64:fontcolor=white:borderw=5:bordercolor=black:x=(w-tw)/2:y=260"
fi
ffmpeg -y -ss "$ss" -to "$to" -i "$in" -filter_complex "[0:v]$vf[v]" -map "[v]" -map 0:a? \
  -c:v libx264 -preset medium -crf 20 -c:a aac -b:a 192k -af loudnorm=I=-14:TP=-1.5 -movflags +faststart "$out"
echo "✔ $out"
