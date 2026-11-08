#!/usr/bin/env bash
# Uso: comprimir.sh entrada.mp4 saida.mp4 TAMANHO_MB  — compressão em 2 passes para tamanho-alvo
set -euo pipefail
in="${1:?entrada}"; out="${2:?saida}"; mb="${3:?tamanho em MB}"
dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$in")
abr=128
vbr=$(awk -v mb="$mb" -v d="$dur" -v a="$abr" 'BEGIN{v=int(mb*8192*0.95/d - a); if(v<100)v=100; print v}')
echo "Bitrate de vídeo alvo: ${vbr}k"
tmp=$(mktemp -d)
ffmpeg -y -i "$in" -c:v libx264 -b:v ${vbr}k -pass 1 -passlogfile "$tmp/log" -an -f mp4 /dev/null
ffmpeg -y -i "$in" -c:v libx264 -b:v ${vbr}k -pass 2 -passlogfile "$tmp/log" -pix_fmt yuv420p \
  -c:a aac -b:a ${abr}k -movflags +faststart "$out"
rm -rf "$tmp"
ls -lh "$out"
