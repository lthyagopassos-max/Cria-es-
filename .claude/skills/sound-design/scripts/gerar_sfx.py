#!/usr/bin/env python3
"""Gera uma biblioteca de efeitos sonoros sintetizados (WAV 48 kHz, estéreo), sem downloads.

Uso: python gerar_sfx.py [PASTA=sfx] [--so whoosh,pop,...]
Efeitos: whoosh, whoosh-curto, swoosh-reverso, pop, clique, tecla, ding, notificacao,
         impacto, boom, riser, drop, glitch, swipe, erro, sucesso, tick-relogio
"""
import argparse
import wave
from pathlib import Path

import numpy as np

SR = 48000
rng = np.random.default_rng(7)


def t(d): return np.arange(int(SR * d)) / SR
def ruido(d): return rng.standard_normal(int(SR * d))


def env(n, a=0.01, r=0.2, forma=2.0):
    """Envelope ataque/decay exponencial."""
    x = np.arange(n) / SR
    at = np.clip(x / max(a, 1e-4), 0, 1)
    dec = np.exp(-np.maximum(x - a, 0) / max(r, 1e-4) * forma)
    return at * dec


def passa_banda_variavel(sinal, f_ini, f_fim, q=2.0):
    """Filtro passa-banda (state variable) com frequência variando no tempo."""
    n = len(sinal)
    f = np.geomspace(f_ini, f_fim, n)
    out = np.zeros(n); low = band = 0.0
    k = 1 / q
    g = 2 * np.sin(np.pi * np.clip(f, 20, SR / 6) / SR)
    for i in range(n):
        high = sinal[i] - low - k * band
        band += g[i] * high
        low += g[i] * band
        out[i] = band
    return out


def passa_baixa(sinal, fc):
    a = np.exp(-2 * np.pi * fc / SR); out = np.zeros_like(sinal); y = 0.0
    for i, x in enumerate(sinal):
        y = (1 - a) * x + a * y; out[i] = y
    return out


def tom(freqs, d, decays=None):
    x = t(d); s = np.zeros_like(x)
    for i, f in enumerate(freqs):
        dec = decays[i] if decays else 1.0
        s += np.sin(2 * np.pi * f * x) * np.exp(-x * 4 / dec) / (i + 1)
    return s


def sweep(f0, f1, d):
    f = np.geomspace(f0, f1, int(SR * d))
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def whoosh(d=0.9, f0=300, f1=4000):
    n = int(SR * d); x = np.linspace(0, 1, n)
    forma = np.sin(np.pi * x) ** 2
    return passa_banda_variavel(ruido(d), f0, f1, 1.5) * forma


def efeitos():
    E = {}
    E["whoosh"] = whoosh()
    E["whoosh-curto"] = whoosh(0.4, 500, 6000)
    E["swoosh-reverso"] = whoosh(1.2, 200, 3000) * np.linspace(0, 1, int(SR * 1.2)) ** 3
    x = t(0.12); E["pop"] = np.sin(2 * np.pi * np.cumsum(np.geomspace(900, 300, len(x))) / SR) * env(len(x), 0.002, 0.05)
    E["clique"] = passa_banda_variavel(ruido(0.03), 3000, 3000, 4) * env(int(SR * 0.03), 0.0005, 0.008)
    E["tecla"] = (passa_banda_variavel(ruido(0.06), 2000, 1500, 3) + 0.3 * tom([180], 0.06)) * env(int(SR * 0.06), 0.001, 0.015)
    E["ding"] = tom([1318.5, 2637, 3955], 1.5, [1.5, 0.8, 0.4]) * env(int(SR * 1.5), 0.002, 0.6, 1)
    a = tom([880, 1760], 0.18, [0.5, 0.3]) * env(int(SR * 0.18), 0.002, 0.08)
    b = tom([1174.7, 2349], 0.5, [0.8, 0.4]) * env(int(SR * 0.5), 0.002, 0.2)
    E["notificacao"] = np.concatenate([a, b])
    d = 1.4; x = t(d)
    corpo = np.sin(2 * np.pi * np.cumsum(np.geomspace(120, 35, len(x))) / SR) * env(len(x), 0.002, 0.45, 1.5)
    estalo = passa_baixa(ruido(d), 2500) * env(len(x), 0.001, 0.05)
    E["impacto"] = corpo + 0.8 * estalo
    d = 2.5; x = t(d)
    E["boom"] = np.tanh(2 * np.sin(2 * np.pi * np.cumsum(np.geomspace(70, 28, len(x))) / SR)) * env(len(x), 0.005, 1.0, 1.2)
    d = 2.5; x = np.linspace(0, 1, int(SR * d))
    E["riser"] = (0.5 * passa_banda_variavel(ruido(d), 200, 8000, 3) + 0.25 * sweep(150, 1200, d)) * x ** 2
    d = 1.0; x = np.linspace(0, 1, int(SR * d))
    E["drop"] = (sweep(1200, 60, d) * 0.5 + passa_banda_variavel(ruido(d), 6000, 150, 2) * 0.5) * (1 - x) ** 1.5
    g = []
    for _ in range(8):
        dd = rng.uniform(0.015, 0.05)
        g.append((np.sign(np.sin(2 * np.pi * rng.uniform(80, 2000) * t(dd))) * 0.5 + ruido(dd) * rng.uniform(0, .5)))
    E["glitch"] = np.concatenate(g) * 0.7
    E["swipe"] = whoosh(0.25, 1500, 7000)
    E["erro"] = np.concatenate([np.sign(np.sin(2 * np.pi * 220 * t(0.15))) * env(int(SR * .15), .002, .1) * .4,
                                np.sign(np.sin(2 * np.pi * 165 * t(0.3))) * env(int(SR * .3), .002, .2) * .4])
    E["sucesso"] = np.concatenate([tom([f, 2 * f], 0.12, [0.4, 0.2]) * env(int(SR * 0.12), 0.002, 0.08)
                                   for f in (523.3, 659.3, 784)] + [tom([1046.5, 2093], 0.6, [0.8, 0.4]) * env(int(SR * 0.6), 0.002, 0.3)])
    tk = passa_banda_variavel(ruido(0.02), 4000, 4000, 6) * env(int(SR * 0.02), 0.0005, 0.005)
    E["tick-relogio"] = np.concatenate([np.pad(tk, (0, int(SR * 0.5) - len(tk))) for _ in range(4)])
    return E


def salvar(nome, s, pasta):
    s = s / (np.max(np.abs(s)) + 1e-9) * 0.89  # pico em -1 dBFS
    fade = min(len(s), int(SR * 0.005))
    s[-fade:] *= np.linspace(1, 0, fade)
    est = np.stack([s, s], axis=1)
    pcm = (est * 32767).astype("<i2")
    with wave.open(str(pasta / f"{nome}.wav"), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pasta", nargs="?", default="sfx")
    ap.add_argument("--so", help="lista separada por vírgula")
    a = ap.parse_args()
    pasta = Path(a.pasta); pasta.mkdir(parents=True, exist_ok=True)
    so = set(a.so.split(",")) if a.so else None
    for nome, s in efeitos().items():
        if so and nome not in so:
            continue
        salvar(nome, s, pasta)
        print(f"✔ {pasta / nome}.wav  ({len(s) / SR:.2f}s)")


if __name__ == "__main__":
    main()
