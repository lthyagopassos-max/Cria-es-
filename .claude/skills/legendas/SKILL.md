---
name: legendas
description: Cria, corrige, traduz e queima legendas em vídeos — transcrição automática com Whisper, arquivos SRT/VTT, legendas estilizadas tipo Reels/TikTok (palavra por palavra, centralizadas, com contorno). Use quando o usuário pedir legenda, transcrição, closed caption, SRT ou texto sincronizado no vídeo.
---

# Legendas

## 1. Transcrever (gerar SRT)
Prefira `faster-whisper` (mais rápido, roda em CPU):
```bash
pip install faster-whisper
python scripts/transcrever.py video.mp4 --modelo small --idioma pt
# gera video.srt (frases) e video.palavras.srt (uma palavra por bloco)
```
Modelos: `tiny`/`base` (rápido, menos preciso), `small` (bom equilíbrio), `medium`/`large-v3` (melhor precisão).
Se o pacote não puder ser instalado, peça ao usuário um SRT pronto ou o texto do roteiro e sincronize manualmente.

## 2. Revisar
Sempre releia o SRT antes de queimar:
- Corrija nomes próprios, marcas e termos técnicos.
- Máx. **2 linhas** e **~42 caracteres por linha**; blocos de 1–6 s.
- Para vídeos verticais, blocos curtos (2–4 palavras) funcionam melhor.

Formato SRT:
```
1
00:00:00,000 --> 00:00:02,400
Pare de editar
seus vídeos assim.
```

## 3. Queimar no vídeo (hardsub)
Estilo padrão limpo:
```bash
ffmpeg -i video.mp4 -vf "subtitles=video.srt:force_style='FontName=Arial,FontSize=14,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=40'" -c:a copy saida.mp4
```
Estilo Reels/TikTok (grande, negrito, centro da tela) — use o SRT de palavras:
```bash
ffmpeg -i video.mp4 -vf "subtitles=video.palavras.srt:force_style='FontName=Arial Black,FontSize=22,Bold=1,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,Outline=3,Alignment=5'" -c:a copy saida.mp4
```
Notas sobre `force_style`:
- Cores em `&HAABBGGRR` (ordem BGR!): branco `&H00FFFFFF`, amarelo `&H0000FFFF`, verde `&H0000FF00`.
- `Alignment`: 2 = embaixo centro, 5 = meio centro, 8 = topo centro.
- `BorderStyle=3` cria caixa de fundo (use `BackColour=&H80000000` para preto semitransparente).
- `FontSize` é relativo a uma tela de 288px de altura — ajuste visualmente.

## 4. Legenda embutida (soft, pode ligar/desligar)
```bash
ffmpeg -i video.mp4 -i video.srt -c copy -c:s mov_text -metadata:s:s:0 language=por saida.mp4
```
Para YouTube, envie o `.srt` separadamente (melhor para SEO).

## 5. Traduzir
Traduza o texto bloco a bloco **mantendo números e timestamps intactos**. Adapte expressões; se a frase traduzida ficar muito mais longa, divida o bloco em dois respeitando o tempo total.

## Conversões
- SRT → VTT: `ffmpeg -i in.srt out.vtt`
- Extrair legenda de um vídeo: `ffmpeg -i video.mkv -map 0:s:0 legenda.srt`
