---
name: edicao-ffmpeg
description: Edita vídeos pela linha de comando com FFmpeg — cortar, juntar, redimensionar, comprimir, trocar/normalizar áudio, adicionar música, marca d'água, texto, acelerar, gerar GIF e extrair frames. Use quando o usuário pedir para editar, cortar, juntar, converter, comprimir ou exportar um arquivo de vídeo.
---

# Edição de vídeo com FFmpeg

## Fluxo
1. **Inspecione sempre primeiro:** `bash scripts/info.sh entrada.mp4` (duração, resolução, fps, codecs, áudio).
2. Nunca sobrescreva o original: grave em `saida/` ou com sufixo (`_editado.mp4`).
3. Prefira `-c copy` quando não há mudança de imagem (rápido, sem perda). Reencode só quando necessário.
4. Ao final, rode `info.sh` na saída e informe duração, resolução e tamanho.

## Padrão de exportação (compatível com todas as redes)
```
-c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart
```
CRF: 18 = quase sem perda, 23 = padrão, 28 = arquivo pequeno.

## Receitas

**Cortar trecho** (preciso, com reencode):
```bash
ffmpeg -ss 00:01:05 -to 00:01:35 -i in.mp4 -c:v libx264 -crf 20 -c:a aac out.mp4
```
Rápido sem reencode (corta no keyframe mais próximo): `ffmpeg -ss 65 -to 95 -i in.mp4 -c copy out.mp4`

**Juntar vídeos** — use `scripts/juntar.sh saida.mp4 a.mp4 b.mp4 c.mp4`. Ele normaliza resolução/fps/áudio e funciona mesmo com arquivos diferentes.

**Redimensionar mantendo proporção com barras:**
```bash
ffmpeg -i in.mp4 -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1" -c:a copy out.mp4
```

**Comprimir para tamanho-alvo** (ex.: WhatsApp/e-mail): `bash scripts/comprimir.sh in.mp4 out.mp4 16` (16 MB).

**Normalizar volume (padrão de redes, -14 LUFS):**
```bash
ffmpeg -i in.mp4 -af loudnorm=I=-14:TP=-1.5:LRA=11 -c:v copy out.mp4
```

**Música de fundo abaixando sob a voz (ducking):**
```bash
ffmpeg -i video.mp4 -i musica.mp3 -filter_complex \
"[1:a]volume=0.5[m];[m][0:a]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=300[duck];[0:a][duck]amix=inputs=2:duration=first:normalize=0[a]" \
-map 0:v -map "[a]" -c:v copy -c:a aac -shortest out.mp4
```
Música simples em volume baixo: `[1:a]volume=0.15[m];[0:a][m]amix=inputs=2:duration=first[a]`.

**Remover áudio:** `ffmpeg -i in.mp4 -an -c:v copy out.mp4`
**Extrair áudio:** `ffmpeg -i in.mp4 -vn -c:a libmp3lame -q:a 2 audio.mp3`

**Marca d'água / logo (canto inferior direito):**
```bash
ffmpeg -i in.mp4 -i logo.png -filter_complex "[1]scale=iw*0.15:-1[l];[0][l]overlay=W-w-30:H-h-30" -c:a copy out.mp4
```

**Texto na tela** (entre 0 e 3 s):
```bash
ffmpeg -i in.mp4 -vf "drawtext=text='SEU TEXTO':fontsize=72:fontcolor=white:borderw=4:bordercolor=black:x=(w-tw)/2:y=h*0.15:enable='between(t,0,3)'" -c:a copy out.mp4
```
Se a fonte padrão falhar, adicione `fontfile=/caminho/fonte.ttf` (procure com `fc-list`).

**Acelerar 2x (vídeo e áudio):**
```bash
ffmpeg -i in.mp4 -filter_complex "[0:v]setpts=0.5*PTS[v];[0:a]atempo=2.0[a]" -map "[v]" -map "[a]" out.mp4
```

**Fade in/out** (vídeo de 30 s): `-vf "fade=t=in:d=0.5,fade=t=out:st=29.5:d=0.5" -af "afade=t=in:d=0.5,afade=t=out:st=29.5:d=0.5"`

**GIF de qualidade:**
```bash
ffmpeg -ss 5 -t 4 -i in.mp4 -vf "fps=15,scale=600:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse" out.gif
```

**Extrair frames** (1 por segundo): `ffmpeg -i in.mp4 -vf fps=1 frames/f_%04d.png`
**Slideshow de imagens** (3 s cada): veja `video-programatico`.

## Problemas comuns
- Vídeo não toca no iPhone/WhatsApp → falta `-pix_fmt yuv420p` ou o codec é HEVC; reexporte com o padrão acima.
- Áudio dessincronizado após corte → use corte com reencode, não `-c copy`.
- `concat` falha → arquivos com codecs/resoluções diferentes; use `scripts/juntar.sh`.
- Dimensão ímpar ("width not divisible by 2") → use `scale=-2:1080`.
