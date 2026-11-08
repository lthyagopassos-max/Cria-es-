#!/usr/bin/env python3
"""Transcreve um vídeo/áudio para SRT usando faster-whisper.

Uso: python transcrever.py video.mp4 [--modelo small] [--idioma pt] [--max-chars 42] [--palavras-por-bloco 3]
Gera <nome>.srt (frases) e <nome>.palavras.srt (blocos curtos estilo Reels).
"""
import argparse
from pathlib import Path


def ts(s: float) -> str:
    ms = int(round(s * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    sec, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{sec:02},{ms:03}"


def quebrar(texto: str, max_chars: int) -> str:
    palavras, linhas, atual = texto.split(), [], ""
    for p in palavras:
        if atual and len(atual) + 1 + len(p) > max_chars:
            linhas.append(atual)
            atual = p
        else:
            atual = f"{atual} {p}".strip()
    linhas.append(atual)
    return "\n".join(linhas)


def dividir(palavras, max_chars: int):
    """Agrupa palavras (com tempos) em blocos de no máximo 2 linhas de max_chars."""
    blocos, grupo = [], []
    for w in palavras:
        teste = " ".join(x.word.strip() for x in grupo + [w])
        if grupo and quebrar(teste, max_chars).count("\n") >= 2:
            blocos.append(grupo)
            grupo = []
        grupo.append(w)
    if grupo:
        blocos.append(grupo)
    return [(g[0].start, g[-1].end, quebrar(" ".join(x.word.strip() for x in g), max_chars)) for g in blocos]


def escrever(blocos, caminho: Path):
    with caminho.open("w", encoding="utf-8") as f:
        for i, (ini, fim, txt) in enumerate(blocos, 1):
            f.write(f"{i}\n{ts(ini)} --> {ts(fim)}\n{txt}\n\n")
    print(f"✔ {caminho} ({len(blocos)} blocos)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("arquivo")
    ap.add_argument("--modelo", default="small")
    ap.add_argument("--idioma", default="pt")
    ap.add_argument("--max-chars", type=int, default=42)
    ap.add_argument("--palavras-por-bloco", type=int, default=3)
    a = ap.parse_args()

    from faster_whisper import WhisperModel

    modelo = WhisperModel(a.modelo, device="auto", compute_type="int8")
    segs, info = modelo.transcribe(a.arquivo, language=a.idioma, word_timestamps=True, vad_filter=True)
    print(f"Idioma: {info.language} | duração: {info.duration:.1f}s")

    frases, palavras = [], []
    for s in segs:
        if s.words:
            frases.extend(dividir(s.words, a.max_chars))
            palavras.extend(s.words)
        else:
            frases.append((s.start, s.end, quebrar(s.text.strip(), a.max_chars)))

    base = Path(a.arquivo).with_suffix("")
    escrever(frases, base.with_suffix(".srt"))

    n = a.palavras_por_bloco
    curtos = [
        (g[0].start, g[-1].end, " ".join(w.word.strip() for w in g).upper())
        for g in (palavras[i:i + n] for i in range(0, len(palavras), n))
    ]
    escrever(curtos, Path(f"{base}.palavras.srt"))


if __name__ == "__main__":
    main()
