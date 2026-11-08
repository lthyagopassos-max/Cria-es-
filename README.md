# Criações — Skills de vídeo para o Claude Code

Conjunto de skills em `.claude/skills/` que ensinam o Claude a planejar, editar e produzir vídeos.
Ao abrir este repositório no Claude Code, as skills são carregadas automaticamente e usadas quando o pedido combinar (ou chame pelo nome, ex.: `/legendas`).

| Skill | Para que serve | Scripts |
|---|---|---|
| `roteiro-video` | Roteiros com gancho, tempo por cena e indicação visual (Reels, TikTok, Shorts, YouTube, anúncios) | — |
| `edicao-ffmpeg` | Cortar, juntar, comprimir, normalizar áudio, música com ducking, logo, texto, GIF | `info.sh`, `juntar.sh`, `comprimir.sh` |
| `legendas` | Transcrição com Whisper, SRT, legendas estilo Reels, queimar/embutir, traduzir | `transcrever.py` |
| `cortes-verticais` | Transformar vídeo horizontal em cortes 9:16 (crop, fundo desfocado, tela dividida) | `vertical.sh` |
| `thumbnail` | Thumbnails do YouTube e capas verticais com texto e contorno, variações A/B | `thumb.py` |
| `video-programatico` | Vídeos a partir de imagens, texto, CSV ou código (FFmpeg, MoviePy, Remotion), narração TTS | — |

## Requisitos
- **FFmpeg** (obrigatório para quase tudo)
- **Python 3 + Pillow** (`pip install pillow`) para thumbnails
- **faster-whisper** (`pip install faster-whisper`) para transcrição
- Opcional: `moviepy`, `edge-tts`, Node.js para Remotion

## Fluxo típico
1. `roteiro-video` → roteiro com timestamps
2. Gravação / `video-programatico` → vídeo bruto
3. `edicao-ffmpeg` → cortes, áudio, música
4. `legendas` → SRT revisado e queimado
5. `cortes-verticais` → versões para Reels/TikTok/Shorts
6. `thumbnail` → capa e miniatura
