#!/usr/bin/env python3
"""Decupagem automática de material bruto.

Para cada vídeo: detecta planos (mudança de cena), silêncios e falas; marca repetições
(takes refeitos), gera planilhas, folha de contato e uma timeline sugerida para a skill `montagem`.

Uso:
  python decupar.py bruto1.mp4 [bruto2.mp4 ...] [--saida decupagem] [--transcrever] [--modelo small]
                    [--srt arquivo.srt] [--limiar-cena 0.3] [--silencio-db -35] [--silencio-min 0.6]
                    [--folga 0.12] [--resolucao 1920x1080]

Saídas (na pasta --saida):
  planos.csv       um plano por linha: arquivo, início, fim, duração, % de silêncio, fala, frame
  falas.csv        uma fala por linha, com marcação REPETIÇÃO/USAR
  decupagem.md     resumo legível
  contato_<video>.jpg   folha de contato com um frame por plano
  frames/          frames de cada plano
  timeline_sugerida.json   corte bruto (sem silêncios e sem takes repetidos) no formato da skill montagem
"""
import argparse
import csv
import difflib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Instale: pip install pillow")


def ff(args):
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostats"] + args, capture_output=True, text=True).stderr


def duracao(v):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", v],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def tem_audio(v):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                        "-of", "csv=p=0", v], capture_output=True, text=True)
    return bool(r.stdout.strip())


def hms(s):
    h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return f"{int(h):02}:{int(m):02}:{s:05.2f}"


def detectar_cortes(v, limiar):
    log = ff(["-i", v, "-an", "-vf", f"scale=320:-2,select='gt(scene,{limiar})',showinfo", "-f", "null", "-"])
    return [float(x) for x in re.findall(r"pts_time:([\d.]+)", log)]


def detectar_silencios(v, db, dmin, dur):
    if not tem_audio(v):
        return [(0.0, dur)]
    log = ff(["-i", v, "-vn", "-af", f"silencedetect=n={db}dB:d={dmin}", "-f", "null", "-"])
    ini = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", log)]
    fim = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
    if len(fim) < len(ini):
        fim.append(dur)
    return [(max(0, a), b) for a, b in zip(ini, fim)]


def ler_srt(caminho):
    txt = Path(caminho).read_text(encoding="utf-8-sig")
    falas = []
    for bloco in re.split(r"\n\s*\n", txt.strip()):
        m = re.search(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)", bloco)
        if not m:
            continue
        g = list(map(int, m.groups()))
        ini = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
        fim = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        texto = " ".join(bloco.split("\n")[2:]).strip() if bloco.split("\n")[0].strip().isdigit() \
            else " ".join(bloco.split("\n")[1:]).strip()
        falas.append({"inicio": ini, "fim": fim, "texto": texto})
    return falas


def transcrever(v, modelo, idioma):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("⚠ faster-whisper não instalado (pip install faster-whisper) — seguindo sem transcrição")
        return []
    m = WhisperModel(modelo, device="auto", compute_type="int8")
    segs, _ = m.transcribe(v, language=idioma, vad_filter=True)
    return [{"inicio": s.start, "fim": s.end, "texto": s.text.strip()} for s in segs]


def normalizar(t):
    return re.sub(r"[^\w\s]", "", t.lower()).strip()


def marcar_repeticoes(falas, janela=4, limiar=0.6):
    """Quando uma fala é parecida com uma das próximas, a anterior é um take descartado."""
    for i, f in enumerate(falas):
        f.setdefault("status", "USAR")
        a = normalizar(f["texto"])
        for j in range(i + 1, min(i + 1 + janela, len(falas))):
            b = normalizar(falas[j]["texto"])
            if not a or not b:
                continue
            # compara o começo das falas (takes refeitos começam igual)
            n = min(len(a), len(b), 60)
            r = difflib.SequenceMatcher(None, a[:n], b[:n]).ratio()
            if r >= limiar:
                f["status"] = "REPETIÇÃO"
                f["obs"] = f"refeita em {hms(falas[j]['inicio'])} (semelhança {r:.0%})"
                break
        if f["status"] == "USAR" and len(a.split()) <= 2 and re.fullmatch(r"(é|eh|ah|hum|então|tá|ok|corta|de novo|vai)( \w+)?", a):
            f["status"] = "DESCARTAR"
            f["obs"] = "muleta / fala de bastidor"
    return falas


def intervalos_com_som(silencios, dur):
    res, t = [], 0.0
    for a, b in sorted(silencios):
        if a > t:
            res.append((t, a))
        t = max(t, b)
    if t < dur:
        res.append((t, dur))
    return res


def mesclar(intervalos, folga, dur, gap=0.35):
    out = []
    for a, b in sorted(intervalos):
        a, b = max(0, a - folga), min(dur, b + folga)
        if out and a - out[-1][1] <= gap:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return [(a, b) for a, b in out if b - a >= 0.3]


def fonte(tam):
    for nome in ("DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(nome, tam)
        except OSError:
            pass
    return ImageFont.load_default()


def folha_contato(planos, caminho, cols=5, larg=320):
    if not planos:
        return
    imgs = [Image.open(p["frame"]).convert("RGB") for p in planos]
    alt = int(larg * imgs[0].height / imgs[0].width)
    linhas = (len(imgs) + cols - 1) // cols
    folha = Image.new("RGB", (cols * (larg + 8) + 8, linhas * (alt + 34) + 8), (20, 20, 20))
    d = ImageDraw.Draw(folha); f = fonte(16)
    for i, (im, p) in enumerate(zip(imgs, planos)):
        x, y = 8 + (i % cols) * (larg + 8), 8 + (i // cols) * (alt + 34)
        folha.paste(im.resize((larg, alt)), (x, y))
        d.text((x, y + alt + 6), f"#{p['plano']}  {hms(p['inicio'])}  ({p['duracao']:.1f}s)", fill="white", font=f)
    folha.save(caminho, quality=85)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("videos", nargs="+")
    ap.add_argument("--saida", default="decupagem")
    ap.add_argument("--transcrever", action="store_true")
    ap.add_argument("--modelo", default="small")
    ap.add_argument("--idioma", default="pt")
    ap.add_argument("--srt", action="append", default=[], help="SRT já existente (um por vídeo, na mesma ordem)")
    ap.add_argument("--limiar-cena", type=float, default=0.3)
    ap.add_argument("--silencio-db", type=float, default=-35)
    ap.add_argument("--silencio-min", type=float, default=0.6)
    ap.add_argument("--folga", type=float, default=0.12, help="segundos mantidos antes/depois de cada fala")
    ap.add_argument("--resolucao", default="1920x1080")
    a = ap.parse_args()

    out = Path(a.saida); (out / "frames").mkdir(parents=True, exist_ok=True)
    todos_planos, todas_falas, clipes, md = [], [], [], ["# Decupagem\n"]

    for vi, v in enumerate(a.videos):
        nome = Path(v).stem
        dur = duracao(v)
        print(f"▶ {v} ({hms(dur)})")
        cortes = [0.0] + [c for c in detectar_cortes(v, a.limiar_cena) if 0.3 < c < dur - 0.3] + [dur]
        silencios = detectar_silencios(v, a.silencio_db, a.silencio_min, dur)
        if vi < len(a.srt):
            falas = ler_srt(a.srt[vi])
        elif a.transcrever:
            falas = transcrever(v, a.modelo, a.idioma)
        else:
            falas = []
        falas = marcar_repeticoes(falas)
        for f in falas:
            f["arquivo"] = v

        planos = []
        for i, (ini, fim) in enumerate(zip(cortes, cortes[1:]), 1):
            meio = (ini + fim) / 2
            frame = out / "frames" / f"{nome}_p{i:03}.jpg"
            ff(["-y", "-ss", f"{meio:.3f}", "-i", v, "-frames:v", "1", "-vf", "scale=480:-2", "-q:v", "4", str(frame)])
            sil = sum(max(0, min(fim, b) - max(ini, a_)) for a_, b in silencios)
            texto = " ".join(f["texto"] for f in falas if f["inicio"] < fim and f["fim"] > ini)
            planos.append({"arquivo": v, "plano": i, "inicio": round(ini, 2), "fim": round(fim, 2),
                           "duracao": round(fim - ini, 2), "silencio_%": round(100 * sil / max(fim - ini, 1e-3)),
                           "fala": texto[:300], "frame": str(frame), "nota": ""})
        folha_contato(planos, out / f"contato_{nome}.jpg")

        # corte sugerido: falas marcadas USAR; sem transcrição, trechos com som
        if falas:
            uteis = [(f["inicio"], f["fim"]) for f in falas if f["status"] == "USAR"]
        else:
            uteis = intervalos_com_som(silencios, dur)
        trechos = mesclar(uteis, a.folga, dur)
        rel = os.path.relpath(Path(v).resolve(), out.resolve())  # caminho relativo à timeline
        clipes += [{"arquivo": rel, "inicio": round(x, 2), "fim": round(y, 2)} for x, y in trechos]

        usado = sum(y - x for x, y in trechos)
        rep = sum(1 for f in falas if f["status"] != "USAR")
        md += [f"## {nome}\n",
               f"- Duração: {hms(dur)} | Planos: {len(planos)} | Silêncios: {len(silencios)} "
               f"({sum(b - a_ for a_, b in silencios):.1f}s)",
               f"- Falas: {len(falas)} ({rep} repetições/descartes)" if falas else "- Falas: sem transcrição",
               f"- Corte sugerido: {len(trechos)} trechos, {hms(usado)} ({100 * usado / dur:.0f}% do bruto)",
               f"- Folha de contato: `contato_{nome}.jpg`\n",
               "| # | Início | Dur. | Silêncio | Fala |", "|---|---|---|---|---|"]
        md += [f"| {p['plano']} | {hms(p['inicio'])} | {p['duracao']}s | {p['silencio_%']}% | {p['fala'][:80]} |"
               for p in planos]
        if falas:
            md += ["\n### Falas\n", "| Início | Fim | Status | Texto | Obs. |", "|---|---|---|---|---|"]
            md += [f"| {hms(f['inicio'])} | {hms(f['fim'])} | {f['status']} | {f['texto'][:90]} | {f.get('obs', '')} |"
                   for f in falas]
        md.append("")
        todos_planos += planos; todas_falas += falas

    with open(out / "planos.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(todos_planos[0].keys())); w.writeheader(); w.writerows(todos_planos)
    if todas_falas:
        with open(out / "falas.csv", "w", newline="", encoding="utf-8") as fh:
            campos = ["arquivo", "inicio", "fim", "status", "texto", "obs"]
            w = csv.DictWriter(fh, fieldnames=campos, extrasaction="ignore"); w.writeheader()
            w.writerows([{**f, "inicio": round(f["inicio"], 2), "fim": round(f["fim"], 2)} for f in todas_falas])
    W, H = map(int, a.resolucao.split("x"))
    tl = {"saida": "final.mp4", "resolucao": [W, H], "fps": 30, "video": clipes,
          "musica": [], "sfx": [], "overlays": [], "loudness": -14}
    (out / "timeline_sugerida.json").write_text(json.dumps(tl, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "decupagem.md").write_text("\n".join(md), encoding="utf-8")
    print(f"✔ {out}/decupagem.md, planos.csv{', falas.csv' if todas_falas else ''}, timeline_sugerida.json, "
          f"{len(todos_planos)} planos, {len(clipes)} trechos sugeridos")


if __name__ == "__main__":
    main()
