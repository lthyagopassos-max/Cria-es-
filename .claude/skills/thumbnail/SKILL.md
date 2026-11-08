---
name: thumbnail
description: Cria thumbnails e capas de vídeo (YouTube 1280×720, capa de Reels/TikTok 1080×1920) — escolhe o melhor frame, compõe texto grande com contorno, cores de contraste e gera variações para teste A/B. Use quando o usuário pedir thumbnail, miniatura, capa, cover ou imagem de destaque de um vídeo.
---

# Thumbnail

## Tamanhos
| Uso | Resolução | Proporção |
|---|---|---|
| YouTube | 1280×720 (máx. 2 MB, JPG/PNG) | 16:9 |
| Capa Reels/TikTok/Shorts | 1080×1920 (texto no centro, área 1080×1350 é a que aparece no perfil) | 9:16 |
| Quadrado (feed) | 1080×1080 | 1:1 |

## Princípios
- **Até 4 palavras**, que complementam o título (não repetem).
- Legível em tamanho pequeno: teste reduzindo para 168×94 px.
- Um ponto focal: rosto com expressão forte **ou** objeto/resultado — não os dois brigando.
- Contraste alto: texto branco/amarelo com contorno preto grosso, ou caixa colorida atrás.
- Evite o canto inferior direito no YouTube (fica o tempo do vídeo).

## Fluxo
1. **Escolha frames candidatos** do vídeo:
   ```bash
   mkdir -p thumbs && ffmpeg -i video.mp4 -vf "select='gt(scene,0.3)',scale=1280:-2" -vsync vfr -frames:v 12 thumbs/cand_%02d.jpg
   ```
   Ou um momento específico: `ffmpeg -ss 00:02:13 -i video.mp4 -frames:v 1 -q:v 2 thumbs/frame.jpg`.
   Olhe as imagens (Read) e escolha a com expressão/visual mais forte.
2. **Componha** com `scripts/thumb.py`:
   ```bash
   python scripts/thumb.py thumbs/frame.jpg saida.jpg --texto "EDITEI ERRADO" --cor amarelo --posicao esquerda
   python scripts/thumb.py frame.jpg capa.jpg --texto "3 ERROS" --formato vertical
   ```
   Opções: `--formato youtube|vertical|quadrado`, `--cor branco|amarelo|vermelho|verde`, `--posicao esquerda|direita|centro|topo|base`, `--caixa` (fundo colorido atrás do texto), `--escurecer 0.3` (vinheta/escurecimento para destacar o texto), `--fonte caminho.ttf`.
3. **Gere 2–3 variações** (texto diferente ou cor diferente) para o usuário escolher ou testar A/B.
4. Abra o resultado (Read na imagem) e confira legibilidade antes de entregar.
