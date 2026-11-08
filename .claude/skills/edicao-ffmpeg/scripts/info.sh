#!/usr/bin/env bash
# Uso: info.sh arquivo.mp4  — mostra resumo técnico do vídeo
set -euo pipefail
f="${1:?Uso: info.sh arquivo}"
v=$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height,r_frame_rate -of csv=p=0 "$f" || true)
a=$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name,sample_rate,channels -of csv=p=0 "$f" || true)
fmt=$(ffprobe -v error -show_entries format=duration,size,bit_rate -of csv=p=0 "$f")
IFS=, read -r vc w h fr <<<"$v"
IFS=, read -r d s br <<<"$fmt"
echo "arquivo:    $f"
awk -v d="$d" -v s="$s" -v br="$br" 'BEGIN{printf "duração:    %.2f s\ntamanho:    %.2f MB\nbitrate:    %d kb/s\n", d, s/1048576, br/1000}'
if [[ -n "$v" ]]; then
  echo "vídeo:      $vc ${w}x${h} @ $(awk -v f="$fr" 'BEGIN{split(f,x,"/"); printf "%.2f", x[1]/(x[2]?x[2]:1)}') fps"
else echo "vídeo:      (nenhum)"; fi
if [[ -n "$a" ]]; then IFS=, read -r ac sr ch <<<"$a"; echo "áudio:      $ac ${sr} Hz, ${ch} canal(is)"
else echo "áudio:      (nenhum)"; fi
