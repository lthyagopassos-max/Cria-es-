---
name: cortes-verticais
description: Transforma vídeos horizontais (podcast, live, aula, YouTube) em cortes verticais 9:16 para Reels, TikTok e Shorts — escolhe os melhores trechos, reenquadra, adiciona fundo desfocado, título e legenda. Use quando o usuário pedir cortes, clipes, shorts, reels, vídeo vertical ou "virais" a partir de um vídeo maior.
---

# Cortes verticais (9:16)

## Especificações por plataforma
| Plataforma | Resolução | Duração | Área segura |
|---|---|---|---|
| Reels | 1080×1920 | até 90 s (ideal 15–45) | evite 250px de baixo e 220px de cima |
| TikTok | 1080×1920 | até 10 min (ideal 21–60) | evite 400px de baixo e a lateral direita (botões) |
| Shorts | 1080×1920 | até 3 min (ideal <60) | evite 300px de baixo |

Exporte sempre em 30 fps, H.264, `yuv420p`, AAC, `-movflags +faststart`.

## Fluxo
1. **Transcreva** o vídeo completo com a skill `legendas` (gera SRT com timestamps).
2. **Escolha os trechos**: leia a transcrição e selecione de 3 a 5 momentos que:
   - começam com uma frase forte (gancho) sem depender de contexto anterior;
   - têm começo, meio e fim (uma ideia completa);
   - duram 20–60 s.
   Apresente uma tabela ao usuário: `nº | início | fim | gancho (primeira frase) | por que funciona`.
3. **Corte e reenquadre** com `scripts/vertical.sh` (abaixo).
4. **Legende** cada corte (SRT de palavras da skill `legendas`, `Alignment=5`, acima da área inferior).
5. Entregue os arquivos em `cortes/` com nome `corte_01_<slug>.mp4` e uma legenda de post para cada.

## Modos de enquadramento (`scripts/vertical.sh`)
```bash
bash scripts/vertical.sh entrada.mp4 saida.mp4 INICIO FIM MODO [OFFSET_X] [TITULO]
```
- `crop` — corta o centro (ou desloca com `OFFSET_X` de -1.0 a 1.0; ex.: -0.5 = pessoa à esquerda). Ideal para uma pessoa falando.
- `blur` — vídeo inteiro no meio com fundo desfocado do próprio vídeo. Ideal quando nada pode ser cortado (telas, slides, 2 pessoas).
- `split` — metade de cima com a esquerda do vídeo, metade de baixo com a direita (podcast com 2 pessoas lado a lado).

Exemplo: `bash scripts/vertical.sh podcast.mp4 cortes/corte_01.mp4 00:12:30 00:13:15 crop -0.3 "O ERRO QUE TODO INICIANTE COMETE"`

O título opcional aparece no topo, dentro da área segura.

## Dicas de retenção
- Corte os primeiros "é…", "então…" — o primeiro frame já deve ter fala.
- Remova silêncios longos: `-af silenceremove=stop_periods=-1:stop_duration=0.4:stop_threshold=-35dB` (só em áudio separado ou com cuidado, pois dessincroniza vídeo — prefira cortes manuais por timestamp).
- Zoom leve em momentos de ênfase: `zoompan` ou alterne entre `crop` mais fechado e mais aberto.
