---
name: montagem
description: Monta e renderiza o vídeo final a partir de uma timeline JSON — sequência de cortes, B-roll, transições, zoom, cor por clipe, motion graphics, logo, legendas, trilha com ducking, efeitos sonoros e loudness de entrega — e exporta EDL para DaVinci/Premiere. É a skill que junta decupagem, correcao-cor, motion, sound-design e legendas numa edição completa. Use quando o usuário pedir para editar um vídeo do zero, montar, finalizar, renderizar, exportar, "juntar tudo" ou fazer a edição completa.
---

# Montagem (edição completa)

Motor: `scripts/render.py` (FFmpeg + Python). Usa os looks da skill `correcao-cor` automaticamente.
Modelo comentado de timeline: `modelo_timeline.json`.

```bash
python scripts/render.py timeline.json --mapa        # confere tempos sem renderizar
python scripts/render.py timeline.json --rascunho    # render rápido em meia resolução
python scripts/render.py timeline.json --edl final.edl   # render final + EDL para DaVinci/Premiere
```
Caminhos na timeline são relativos à pasta do `timeline.json`.

## Fluxo de edição do zero
1. **Organizar** a pasta do projeto: `brutos/`, `broll/`, `musica/`, `sfx/`, `motion/`, `legendas/`, `imagens/`.
2. **Roteiro** (opcional, skill `roteiro-video`) — define a ordem e o tom.
3. **Decupagem** (skill `decupagem`) → `timeline_sugerida.json` com o corte bruto.
4. **Corte**: reordene/remova clipes da timeline segundo o roteiro. Rode `--mapa` e mostre ao usuário a estrutura (tempo de cada bloco).
5. **Cor** (skill `correcao-cor`): `analisar` + `comparar`, depois coloque o look em `cor` de cada clipe (ou `cor` global).
6. **Rascunho** (`--rascunho`) e confira frames-chave: `ffmpeg -ss T -i final_rascunho.mp4 -frames:v 1 f.png` → Read.
7. **Motion** (skill `motion`) → `overlays`. **SFX e trilha** (skill `sound-design`) → `sfx`, `sfx_cortes`, `musica`.
8. **Legendas** (skill `legendas`): transcreva o **rascunho já cortado** (os tempos batem com a timeline final), revise e coloque em `legendas`.
9. **Render final** com `--edl`, confira com `edicao-ffmpeg/scripts/info.sh` e `sound-design/scripts/medir_audio.sh`.
10. **Entregáveis**: vídeo, versões verticais (skill `cortes-verticais`), thumbnail (skill `thumbnail`), SRT, EDL.

Mostre o rascunho ao usuário antes do render final em vídeos longos.

## Referência da timeline
### Raiz
| Campo | Padrão | Descrição |
|---|---|---|
| `saida` | `final.mp4` | arquivo de saída |
| `resolucao` | `[1920,1080]` | `[1080,1920]` para vertical |
| `fps` | 30 | |
| `cor` | — | look/filtro aplicado no vídeo inteiro (após os clipes) |
| `loudness` | -14 | LUFS de entrega (`null` desliga) |
| `crf` / `preset` | 20 / medium | qualidade do H.264 |

### `video` — sequência principal (a trilha de voz vem daqui)
| Campo | Descrição |
|---|---|
| `arquivo`, `inicio`, `fim` | trecho do vídeo (segundos) |
| `imagem`, `duracao` | foto/print em vez de vídeo |
| `cor` | preset (`quente`, `cinema`…), `lut:arquivo.cube` ou filtro FFmpeg |
| `zoom` | `1.15` (punch-in fixo) ou `[1.0, 1.2]` (zoom animado) |
| `velocidade` | `1.5` = 50% mais rápido (áudio acompanha) |
| `volume`, `mudo` | volume do áudio do clipe / remove o áudio |
| `ajuste` | `preencher` (corta bordas, padrão) ou `conter` (barras) |
| `transicao` | entrada deste clipe: `{"tipo": "fade", "duracao": 0.5}` |

Transições (`xfade`): `fade`, `fadeblack`, `fadewhite`, `dissolve`, `slideleft`, `slideright`, `slideup`, `slidedown`, `wipeleft`, `wiperight`, `circleopen`, `circleclose`, `radial`, `smoothleft`, `zoomin`, `pixelize`, `hblur`. Em vídeos falados, prefira **corte seco** (sem transição) e use transição só entre blocos.

### `overlays` — camadas por cima (na ordem: o último fica em cima)
| Campo | Descrição |
|---|---|
| `arquivo`, `em` | arquivo (.mov com alfa, .mp4, .png) e instante de entrada na timeline |
| `de`, `duracao` | trecho do arquivo (B-roll) / duração (obrigatória para imagem) |
| `tela_cheia` | B-roll cobrindo a tela (o áudio da sequência principal continua) |
| `x`, `y`, `largura`, `escala`, `centro` | posição/tamanho (`x` aceita expressões: `W-w-40`) |
| `fade` | fade de entrada/saída em segundos |
| `cor` | look aplicado só a esta camada |
| `sfx`, `sfx_volume`, `sfx_atraso` | efeito sonoro disparado junto |

### Áudio
- `musica`: `[{arquivo, inicio, fim, de, volume, ducking, ducking_limiar, fade_in, fade_out, loop}]` — `ducking` (padrão `true`) abaixa a trilha quando há voz.
- `sfx`: `[{arquivo, em, volume}]`.
- `sfx_cortes`: `{arquivo, volume, antecipar}` — põe um SFX em todo corte da sequência principal.
- O áudio de overlays não entra na mixagem (B-roll é mudo); para usar o som de um B-roll, coloque-o como clipe em `video`.

### `legendas`
`{"arquivo": "x.srt", "estilo": "padrao" | "reels" | "caixa" | "<force_style próprio>"}`. Os tempos do SRT são da **timeline final**.

## Edição no DaVinci/Premiere
`--edl` gera um EDL CMX3600 com os cortes da sequência principal (fonte e posição). No DaVinci: *File › Import › Timeline › Pre-Conformed EDL* e aponte a pasta dos brutos. Overlays, cor, música e SFX não vão no EDL — o MP4 renderizado é a referência.

## Problemas comuns
- **Arquivo não encontrado** → caminhos são relativos ao `timeline.json`.
- **Legenda fora de sincronia** → foi gerada sobre o bruto; transcreva o rascunho montado.
- **Música alta demais sob a voz** → `volume` 0.15–0.2 ou `ducking_limiar` 0.01.
- **Render lento** → use `--rascunho` enquanto ajusta; o render final é 1x.
