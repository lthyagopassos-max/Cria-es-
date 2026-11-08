# Criações — Skills de vídeo para o Claude Code

Conjunto de skills em `.claude/skills/` que permitem ao Claude editar um vídeo do zero: decupagem, corte, cor, motion, som, legendas e exportação.
Ao abrir este repositório no Claude Code, as skills são carregadas automaticamente e usadas quando o pedido combinar (ou chame pelo nome, ex.: `/montagem`).

## Skills

| Etapa | Skill | O que faz | Scripts |
|---|---|---|---|
| Planejamento | `roteiro-video` | Roteiros com gancho, tempo por cena e indicação visual | — |
| Decupagem | `decupagem` | Detecta planos, silêncios, falas e takes repetidos; folha de contato; corte bruto sugerido | `decupar.py` |
| Montagem | `montagem` | Renderiza a timeline JSON: cortes, B-roll, transições, zoom, cor, motion, legendas, trilha com ducking, SFX, loudness; exporta EDL | `render.py` |
| Cor | `correcao-cor` | Análise, correção automática, 17 looks, LUT .cube (aplicar e exportar), antes/depois | `cor.py`, `presets.py` |
| Som | `sound-design` | Limpeza de voz, medição de loudness, biblioteca de 17 SFX sintetizados | `limpar_voz.sh`, `medir_audio.sh`, `gerar_sfx.py` |
| Motion | `motion` | Título, lower third, palavra por palavra, contador, barra, CTA, destaque, emoji — com transparência | `motion.py` |
| Legendas | `legendas` | Transcrição com Whisper, SRT, estilos, queimar/embutir, traduzir | `transcrever.py` |
| Edição pontual | `edicao-ffmpeg` | Cortar, juntar, comprimir, normalizar, GIF, texto, logo | `info.sh`, `juntar.sh`, `comprimir.sh` |
| Redes | `cortes-verticais` | Cortes 9:16 (crop, fundo desfocado, tela dividida) | `vertical.sh` |
| Capa | `thumbnail` | Thumbnails e capas com texto e variações A/B | `thumb.py` |
| Sem filmagem | `video-programatico` | Slideshows, vídeos de texto, lotes via CSV, Remotion, narração TTS | — |

## Fluxo de edição completa
```
brutos → decupagem → timeline_sugerida.json → (corte + cor + motion + SFX + trilha + legendas) → montagem → final.mp4 + .edl
                                                                                                └→ cortes-verticais, thumbnail
```

## Requisitos
- **FFmpeg** (obrigatório)
- **Python 3** com `pillow` e `numpy` (`pip install pillow numpy`)
- **faster-whisper** (`pip install faster-whisper`) para transcrição/legendas
- Opcional: `moviepy`, `edge-tts`, Node.js para Remotion

## O que você fornece
- Gravações brutas, B-roll, imagens
- Música licenciada (ou bibliotecas gratuitas: YouTube Audio Library, Pixabay Music)
- Identidade visual: cores, fontes (.ttf) e logo
