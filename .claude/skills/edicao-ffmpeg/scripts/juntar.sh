#!/usr/bin/env bash
# Uso: juntar.sh saida.mp4 a.mp4 b.mp4 [...] [-- LARGURAxALTURA FPS]
# Junta vídeos de formatos diferentes, normalizando resolução (padrão: a do 1º), fps e áudio.
set -euo pipefail
out="${1:?Uso: juntar.sh saida.mp4 a.mp4 b.mp4 ...}"; shift
files=(); size=""; fps="30"
while [[ $# -gt 0 ]]; do
  if [[ "$1" == "--" ]]; then size="$2"; fps="${3:-30}"; break; fi
  files+=("$1"); shift
done
(( ${#files[@]} >= 2 )) || { echo "Informe ao menos 2 vídeos" >&2; exit 1; }
if [[ -z "$size" ]]; then
  size=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "${files[0]}")
fi
W=${size%x*}; H=${size#*x}
inputs=(); filter=""; n=${#files[@]}
for i in "${!files[@]}"; do
  f="${files[$i]}"; inputs+=(-i "$f")
  filter+="[$i:v]scale=$W:$H:force_original_aspect_ratio=decrease,pad=$W:$H:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=$fps,format=yuv420p[v$i];"
  if ffprobe -v error -select_streams a -show_entries stream=index -of csv=p=0 "$f" | grep -q .; then
    filter+="[$i:a]aresample=48000,aformat=channel_layouts=stereo[a$i];"
  else
    d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")
    filter+="anullsrc=r=48000:cl=stereo,atrim=0:$d[a$i];"
  fi
done
for i in $(seq 0 $((n-1))); do filter+="[v$i][a$i]"; done
filter+="concat=n=$n:v=1:a=1[v][a]"
ffmpeg -y "${inputs[@]}" -filter_complex "$filter" -map "[v]" -map "[a]" \
  -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart "$out"
