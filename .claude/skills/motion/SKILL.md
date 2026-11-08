---
name: motion
description: Cria motion graphics para vídeos — títulos animados, lower thirds (nome e cargo), texto palavra por palavra, contadores, barra de progresso, botão de CTA, seta/círculo de destaque, emoji animado e zoom de ênfase — exportados com fundo transparente para sobrepor na edição, além de animações avançadas com Remotion. Use quando o usuário pedir motion, animação, texto animado, lower third, GC, vinheta, CTA animado, "efeito de texto" ou elementos gráficos no vídeo.
---

# Motion graphics

Gerador principal: `scripts/motion.py` (requer FFmpeg e `pip install pillow`). Exporta **ProRes 4444 `.mov` com transparência** — funciona na skill `montagem`, DaVinci, Premiere, Final Cut e After Effects.

## Modelos
| Modelo | Uso | Exemplo |
|---|---|---|
| `titulo` | abertura, título de bloco | `--texto "3 ERROS DE EDIÇÃO"` |
| `lower` | nome e cargo de quem fala | `--texto "Ana Souza" --sub "Editora"` |
| `palavras` | frase de impacto, uma palavra por vez | `--texto "ISSO MUDA TUDO" --intervalo 0.25` |
| `contador` | números, resultados | `--de 0 --ate 10000 --sufixo " seguidores"` (também `--prefixo "R$ " --decimais 2`) |
| `barra` | barra de progresso (retenção em Reels) | `--duracao 45` (= duração do vídeo) |
| `cta` | "Siga", "Inscreva-se", "Link na bio" | `--texto "SIGA PARA MAIS"` |
| `destaque` | círculo + seta apontando algo na tela | `--x 1300 --y 400 --raio 120` |
| `emoji` | emoji/ícone PNG entrando com pulo | `--imagem fogo.png --x 1500 --pos-y 0.3` |

```bash
python scripts/motion.py titulo motion/titulo.mov --texto "3 ERROS DE EDIÇÃO" --duracao 3
python scripts/motion.py palavras motion/frase.mov --texto "ISSO MUDA TUDO" --tamanho 1080x1920
python scripts/motion.py titulo previa.mp4 --texto "TESTE" --previa   # MP4 sobre fundo azul para conferir
```
Opções comuns: `--tamanho 1920x1080|1080x1920`, `--fps 30`, `--duracao`, `--cor` (principal), `--fundo` (caixas), `--cor-texto` (texto sobre caixas), `--fonte arquivo.ttf`, `--fonte-tam`, `--pos-y 0–1`.

**Sempre** use o mesmo `--tamanho` e `--fps` do vídeo final, e confira 1–2 frames antes de entregar:
```bash
ffmpeg -f lavfi -i color=c=gray:s=1920x1080 -ss 1.5 -i motion/titulo.mov -filter_complex overlay -frames:v 1 check.png
```

## Identidade visual
Pergunte (ou procure no projeto) as cores e fontes da marca e use em todos os motions: `--cor "#FF5A1F" --fundo "#111111" --cor-texto "#FFFFFF" --fonte Marca-Bold.ttf`. Fontes boas e gratuitas (Google Fonts): Anton, Montserrat Black, Poppins Bold, Bebas Neue — o script já procura Anton/Montserrat/Poppins se estiverem instaladas.

## Colocando no vídeo
Na timeline da skill `montagem`:
```json
"overlays": [
  {"arquivo": "motion/lower.mov", "em": 2.0},
  {"arquivo": "motion/titulo.mov", "em": 0.0, "sfx": "sfx/whoosh.wav"}
]
```
Combine cada motion com um SFX (skill `sound-design`): título → `whoosh`/`impacto`, palavras → `pop`, contador → `tick-relogio` + `ding` no final, CTA → `pop`, destaque → `swipe`.

## Zoom de ênfase (punch-in)
Não é um arquivo de motion: é um campo do clipe na timeline da `montagem`:
- `"zoom": 1.15` — zoom fixo (alternar 1.0 / 1.15 entre cortes dá dinamismo em vídeos falados).
- `"zoom": [1.0, 1.2]` — zoom animado lento durante o clipe (Ken Burns).

## Regras de bom motion
- Entradas rápidas (0,3–0,6 s), saídas mais rápidas ainda; o texto precisa ficar parado tempo suficiente para ser lido (≈ 0,3 s por palavra + 1 s).
- Um elemento animado por vez; não cubra o rosto de quem fala.
- Vertical: mantenha textos entre 15% e 75% da altura (área segura das redes).
- Consistência: mesma fonte, mesmas cores e mesmo tipo de entrada no vídeo inteiro.

## Avançado: Remotion
Para animações que o gerador não cobre (gráficos animados, telas de app, vinhetas complexas), use Remotion (React):
```bash
npx create-video@latest motion-remotion && cd motion-remotion && npm i
npx remotion render <Id> out/anim.mov --codec=prores --prores-profile=4444 --pixel-format=yuva444p10le --image-format=png
```
Use `useCurrentFrame()`, `interpolate()`, `spring()` e `<Sequence>`; deixe o fundo transparente (sem `backgroundColor` no container). Mesmo tamanho/fps do vídeo final. Remotion tem licença paga para empresas acima de certo porte.
