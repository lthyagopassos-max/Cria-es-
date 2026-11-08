---
name: correcao-cor
description: Corrige e dá look de cor em vídeos — exposição, contraste, balanço de branco, saturação, pele, igualar câmeras, aplicar LUT .cube e looks prontos (quente, frio, cinema, teal-orange, vlog, P&B), com imagem de antes/depois e exportação do look como LUT para DaVinci/Premiere. Use quando o usuário pedir correção de cor, color grading, colorização, LUT, "deixar a imagem mais bonita/cinematográfica" ou disser que o vídeo está escuro, estourado, amarelado, azulado ou lavado.
---

# Correção de cor

Script único: `scripts/cor.py` (requer FFmpeg, `pip install pillow numpy`).

## Ordem de trabalho (sempre nesta ordem)
1. **Analisar** — mede, não "acha":
   ```bash
   python scripts/cor.py analisar video.mp4
   ```
   Retorna luma média, pontos de preto/branco por canal, dominante de cor, saturação, % estourado e um `filtro_auto`. Leia o `diagnostico`.
2. **Correção primária** (deixar neutro e correto): `--auto` (níveis por canal + exposição), ou ajuste manual com `--filtro`.
3. **Look criativo** (opcional): `--preset` ou `--lut`, quase sempre com `--intensidade 0.5–0.8`.
4. **Comparar antes/depois** e **olhar a imagem** (Read) antes de renderizar o vídeo inteiro:
   ```bash
   python scripts/cor.py comparar video.mp4 comp.jpg --tempo 12 --auto --preset cinema --intensidade 0.7
   ```
   Gere a comparação em 2–3 momentos diferentes (cenas claras e escuras).
5. **Aplicar** no vídeo, ou passar o look para a skill `montagem` (campo `cor`):
   ```bash
   python scripts/cor.py aplicar video.mp4 video_cor.mp4 --auto --preset quente --intensidade 0.6
   ```

## Looks prontos (`python scripts/cor.py presets`)
`neutro`, `clarear`, `escurecer`, `mais-contraste`, `menos-contraste`, `mais-saturacao`, `pele`, `quente`, `frio`, `cinema`, `teal-orange`, `vlog`, `vintage`, `desbotado`, `pb`, `pb-suave`, `noturno`.
Os presets ficam em `scripts/presets.py` — adicione os looks do usuário lá para reutilizar.

## Ajustes manuais (`--filtro`)
| Problema | Filtro |
|---|---|
| Escuro | `eq=gamma=1.2` (meios-tons) ou `eq=brightness=0.05` (tudo) |
| Estourado | `eq=gamma=0.85`, `curves=highlights...` — o que estourou não volta |
| Lavado | `curves=master='0/0 0.25/0.2 0.75/0.8 1/1'` (curva em S) |
| Amarelado/laranja | `colortemperature=temperature=7500` ou `colorbalance=rm=-0.05:bm=0.05` |
| Azulado | `colortemperature=temperature=5000` |
| Verde (luz fluorescente) | `colorbalance=gm=-0.06:gs=-0.03` |
| Pele sem vida | `colorbalance=rm=0.03:bm=-0.03,eq=saturation=1.05` |
| Imagem mole | `unsharp=5:5:0.6` |
| Log de câmera (S-Log, V-Log, C-Log) | `--lut` com a LUT de conversão do fabricante **antes** de qualquer look |

`colorbalance`: `rs/gs/bs` = sombras, `rm/gm/bm` = meios-tons, `rh/gh/bh` = altas luzes (-1 a 1, use ±0.02–0.12).

## Igualar câmeras/cenas
Rode `analisar` em cada arquivo, compare `rgb_medio_meios_tons` e `luma_media`, e corrija cada um com `--auto` (que normaliza para neutro) antes de aplicar o **mesmo** look a todos.

## Exportar o look como LUT
```bash
python scripts/cor.py lut meu_look.cube --preset cinema
python scripts/cor.py lut correcao_cam_a.cube --auto-de cam_a.mp4 --preset quente
```
Gera `.cube` 64³ que funciona no DaVinci Resolve, Premiere, Final Cut, CapCut (PC) e no próprio FFmpeg.

## Regras
- Primeiro corrigir, depois estilizar. Nunca empilhe vários looks.
- Pele é a referência: se a pele ficou laranja, verde ou cinza, o look está errado.
- Prefira intensidade parcial a looks fortes; mostre a comparação ao usuário antes do render final.
