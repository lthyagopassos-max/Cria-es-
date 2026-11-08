---
name: decupagem
description: Faz a decupagem do material bruto — detecta planos/cenas, silêncios, falas e takes repetidos, gera planilha com timecodes, folha de contato com frames e um corte bruto sugerido (sem silêncios e sem erros) pronto para a skill montagem. Use quando o usuário enviar gravações brutas, pedir decupagem, logging, seleção de takes, "tirar os erros/silêncios", "achar as melhores partes" ou começar uma edição do zero.
---

# Decupagem

Script: `scripts/decupar.py` (FFmpeg + `pip install pillow`; transcrição opcional com `pip install faster-whisper`).

## 1. Rodar a decupagem
```bash
python scripts/decupar.py bruto1.mp4 bruto2.mp4 --transcrever --saida decupagem
# já tem legenda/transcrição? use-a em vez de transcrever:
python scripts/decupar.py bruto.mp4 --srt bruto.srt
```
Ajustes: `--limiar-cena 0.2` (mais sensível a cortes de câmera; 0.4 menos), `--silencio-db -40` (ambiente silencioso) / `-30` (ambiente com ruído), `--silencio-min 0.5`, `--folga 0.15` (respiro antes/depois de cada fala), `--resolucao 1080x1920` (timeline vertical).

## 2. "Assistir" ao material
O script gera, em `decupagem/`:
- `decupagem.md` — resumo por arquivo, tabela de planos e de falas com status.
- `contato_<video>.jpg` — **abra com Read**: é assim que você vê o conteúdo visual (enquadramento, foco, luz, quem aparece, B-roll).
- `planos.csv` / `falas.csv` — planilhas para o usuário (abrem no Excel/Sheets).
- `frames/` — um frame por plano, para inspecionar de perto.
- `timeline_sugerida.json` — corte bruto pronto para a `montagem`.

Leia o `decupagem.md` e as folhas de contato antes de propor qualquer corte.

## 3. Avaliar e classificar
O script marca automaticamente:
- **REPETIÇÃO** — fala refeita logo em seguida (fica o último take, normalmente o certo).
- **DESCARTAR** — muletas e falas de bastidor ("corta", "de novo", "é…").
- Planos com **silêncio alto** (% de silêncio) — possível B-roll, respiro ou material inútil.

Você complementa olhando frames e texto:
- Take bom × ruim: fora de foco, tremido, cortado, olhando para fora, gaguejo, risada no meio.
- **B-roll**: planos sem fala que ilustram o assunto → anote o tema de cada um para cobrir cortes de jump cut.
- **Momentos fortes**: frases de gancho, conclusões, reações → candidatos a abertura e a cortes verticais (skill `cortes-verticais`).

Entregue ao usuário uma tabela: `arquivo | início | fim | tipo (fala/B-roll/descartar) | descrição | nota (1–5)`.

## 4. Do corte bruto à montagem
1. Abra `timeline_sugerida.json`: é a sequência de trechos úteis na ordem de gravação.
2. Reordene/remova trechos conforme o roteiro (skill `roteiro-video`) e as notas da avaliação.
3. Insira B-roll, cor, música, SFX e motion — e renderize com a skill `montagem`.

## Dicas
- Sem transcrição, o corte sugerido apenas remove silêncios (bom para jump cut de vídeos falados). Com transcrição, também remove takes repetidos — sempre confira as REPETIÇÕES antes de confiar.
- Material longo (> 1 h): rode primeiro sem `--transcrever` para mapear planos e silêncios, depois transcreva só os arquivos relevantes.
- Várias câmeras do mesmo evento: decupe a câmera principal (com melhor áudio) e use as outras como cobertura.
