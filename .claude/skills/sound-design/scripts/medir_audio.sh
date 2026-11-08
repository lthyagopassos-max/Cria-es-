#!/usr/bin/env bash
# Uso: medir_audio.sh arquivo  — loudness integrado (LUFS), pico real (dBTP), faixa dinâmica e ruído de fundo
set -euo pipefail
f="${1:?arquivo}"
ffmpeg -hide_banner -nostats -i "$f" -vn -af ebur128=peak=true -f null - 2>&1 | \
  awk '/Summary/{s=1} s&&/I:|LRA:|Peak:/{gsub(/^ +/,""); print}'
ffmpeg -hide_banner -nostats -i "$f" -vn -af astats=metadata=0:reset=0 -f null - 2>&1 | \
  grep -E "Noise floor dB|RMS level dB" | tail -2 | sed 's/.*\] //'
