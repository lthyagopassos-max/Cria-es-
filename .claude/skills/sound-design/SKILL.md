---
name: sound-design
description: Cuida do áudio do vídeo — limpa e masteriza a voz (ruído, chiado, sibilância, volume), cria efeitos sonoros (whoosh, pop, impacto, riser, ding, glitch, clique etc.), posiciona SFX nos cortes e textos, escolhe e mixa trilha com ducking e entrega no loudness certo para cada plataforma. Use quando o usuário falar de som, áudio, efeito sonoro, SFX, trilha, música de fundo, ruído, volume baixo/alto ou mixagem.
---

# Sound design

Scripts (requer FFmpeg; `gerar_sfx.py` requer `numpy`):
- `scripts/limpar_voz.sh in out [ruido_db] [lufs]` — tratamento de voz completo
- `scripts/medir_audio.sh arquivo` — LUFS, pico, LRA, ruído de fundo
- `scripts/gerar_sfx.py [pasta]` — gera biblioteca de 17 efeitos sem precisar baixar nada

## 1. Diagnóstico
```bash
bash scripts/medir_audio.sh bruto.mp4
```
- Ruído de fundo acima de -50 dB → precisa redução de ruído.
- Integrado muito abaixo de -20 LUFS → voz baixa.
- Pico em 0 dBTP → houve clipping na gravação (não tem como recuperar totalmente).

## 2. Limpar a voz
```bash
bash scripts/limpar_voz.sh bruto.mp4 voz_limpa.mp4          # padrão
bash scripts/limpar_voz.sh bruto.mp4 voz_limpa.mp4 -20      # ruído forte (ar-condicionado, rua)
```
Cadeia: passa-alta 80 Hz → redução de ruído (afftdn) → de-esser → compressor 3:1 → +2 dB em 3,5 kHz (presença) / −2 dB em 250 Hz (embolado) → loudnorm em 2 passes.
Ouça o resultado (ou meça): redução de ruído forte demais deixa a voz "metálica" — se acontecer, use `-30`.

## 3. Efeitos sonoros
```bash
python scripts/gerar_sfx.py sfx/
```
| Efeito | Onde usar |
|---|---|
| `whoosh`, `whoosh-curto`, `swipe` | transições, entrada de texto/imagem, zoom |
| `swoosh-reverso`, `riser` | antes de uma revelação ou do drop da música (termina no corte) |
| `impacto`, `boom`, `drop` | revelação, número grande, mudança de bloco |
| `pop`, `clique`, `tecla` | texto/emoji aparecendo, lista item a item, digitação |
| `ding`, `notificacao`, `sucesso` | acerto, dica, resultado, "check" |
| `erro`, `glitch` | erro, "não faça isso", corte cômico |
| `tick-relogio` | tempo, urgência, contagem |

Se o usuário tiver uma biblioteca própria (ou baixar de Pixabay, Freesound, YouTube Audio Library, Epidemic etc.), prefira-a e use estes como fallback.

### Regras de posicionamento
- O SFX acompanha um evento **visual**: corte, texto entrando, zoom, motion. Sem evento, sem efeito.
- `whoosh` começa ~0,15 s **antes** do corte; `riser` **termina** exatamente no corte; `pop`/`impacto` caem **no frame** do evento.
- Vídeo curto: 1 SFX a cada 2–5 s no máximo. Vídeo longo: só nos momentos-chave.
- Volume: SFX entre 25% e 60% (`"volume": 0.25–0.6` na montagem); nunca mais alto que a voz.
- Varie: não repita o mesmo whoosh 10 vezes seguidas.

Os tempos de cada evento vêm da timeline da skill `montagem` (início de cada clipe = corte) e dos motions da skill `motion`. Adicione os SFX na lista `sfx` da timeline.

## 4. Trilha
- Escolha pelo clima do roteiro (BPM): tutorial/calmo 80–100, vlog 100–120, energético/Reels 120–140.
- Música só com licença: biblioteca do usuário, YouTube Audio Library, Pixabay Music, Free Music Archive (verifique a licença), ou trilha que o usuário comprou.
- Na timeline (`montagem`): `"musica": [{"arquivo": "m.mp3", "volume": 0.25, "ducking": true, "fade_in": 1, "fade_out": 2}]`. O ducking abaixa a música automaticamente quando há voz.
- Corte no ritmo: faça os cortes de vídeo caírem nas batidas. Intervalo entre batidas = 60/BPM (ex.: 120 BPM → corte a cada 0,5 s, 1 s ou 2 s). Para detectar as batidas: `pip install librosa` e `librosa.beat.beat_track`, ou `aubio beat m.mp3`.

## 5. Loudness de entrega
| Destino | Alvo integrado | Pico |
|---|---|---|
| YouTube, Instagram, TikTok, Spotify vídeo | -14 LUFS | -1 dBTP |
| Podcast / voz pura | -16 LUFS | -1,5 dBTP |
| TV / broadcast | -23 LUFS (EBU R128) | -1 dBTP |

Referência de mixagem: voz ≈ -16 a -14 LUFS, música sob voz ≈ 18–22 dB abaixo da voz (volume 0,15–0,3 com ducking), SFX picos ≈ 6 dB abaixo da voz.
A skill `montagem` aplica o loudnorm final (`"loudness": -14`). Confira o arquivo final com `medir_audio.sh`.
