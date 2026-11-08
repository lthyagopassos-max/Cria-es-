#!/usr/bin/env bash
# Uso: limpar_voz.sh entrada saida [ruido_db=-25] [lufs=-16]
# Cadeia de voz: corta graves, reduz ruído, de-esser, compressor, EQ de presença e loudness em 2 passes.
# Funciona com vídeo (copia a imagem) ou áudio.
set -euo pipefail
in="${1:?entrada}"; out="${2:?saida}"; nr="${3:--25}"; lufs="${4:--16}"
cadeia="highpass=f=80,afftdn=nr=12:nf=${nr}:tn=1,deesser=i=0.4,acompressor=threshold=-20dB:ratio=3:attack=10:release=150:makeup=2,equalizer=f=3500:t=q:w=1:g=2,equalizer=f=250:t=q:w=1:g=-2"
# passo 1: mede loudness após a cadeia
stats=$(ffmpeg -hide_banner -nostats -i "$in" -vn -af "$cadeia,loudnorm=I=${lufs}:TP=-1.5:LRA=11:print_format=json" -f null - 2>&1 | sed -n '/^{/,/^}/p')
val() { echo "$stats" | grep "\"$1\"" | sed -E 's/.*: "([^"]+)".*/\1/'; }
ln="loudnorm=I=${lufs}:TP=-1.5:LRA=11:measured_I=$(val input_i):measured_TP=$(val input_tp):measured_LRA=$(val input_lra):measured_thresh=$(val input_thresh):offset=$(val target_offset):linear=true"
if ffprobe -v error -select_streams v -show_entries stream=index -of csv=p=0 "$in" | grep -q .; then
  ffmpeg -v error -y -i "$in" -af "$cadeia,$ln,aresample=48000" -c:v copy -c:a aac -b:a 192k "$out"
else
  ffmpeg -v error -y -i "$in" -af "$cadeia,$ln,aresample=48000" "$out"
fi
echo "✔ $out (entrada: $(val input_i) LUFS → alvo ${lufs} LUFS)"
