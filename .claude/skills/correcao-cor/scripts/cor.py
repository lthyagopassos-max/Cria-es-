#!/usr/bin/env python3
"""Correção e grading de cor com FFmpeg.

Subcomandos:
  analisar  VIDEO                         mede exposição/contraste/dominante de cor e sugere filtro
  aplicar   VIDEO SAIDA [--auto] [--preset P] [--lut X.cube] [--filtro F] [--intensidade 0-1]
  comparar  VIDEO SAIDA.jpg --tempo T [mesmas opções de cor]   imagem antes | depois
  lut       SAIDA.cube [--auto-de VIDEO] [--preset P] [--filtro F]  exporta o look para .cube (DaVinci/Premiere)
  presets                                 lista os looks disponíveis
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from presets import PRESETS, filtro as resolver  # noqa: E402

try:
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
except ImportError:  # pragma: no cover
    sys.exit("Instale: pip install pillow numpy")


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"Erro no ffmpeg:\n{' '.join(cmd)}\n{r.stderr[-2000:]}")
    return r


def duracao(v):
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", v]).stdout
    return float(out.strip())


def frames(video, n=6, largura=640):
    d = duracao(video)
    tmp = Path(tempfile.mkdtemp())
    imgs = []
    for i in range(n):
        t = d * (i + 0.5) / n
        f = tmp / f"f{i}.png"
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1",
             "-vf", f"scale={largura}:-2", str(f)])
        imgs.append(np.asarray(Image.open(f).convert("RGB"), dtype=np.float32) / 255)
    return imgs


def analisar(video):
    px = np.concatenate([f.reshape(-1, 3) for f in frames(video)])
    luma = px @ np.array([0.2126, 0.7152, 0.0722])
    p_lo, p_hi = np.percentile(px, 0.5, axis=0), np.percentile(px, 99.5, axis=0)
    meio = px[(luma > 0.2) & (luma < 0.8)]
    media_rgb = meio.mean(axis=0) if len(meio) else px.mean(axis=0)
    sat = float(np.mean(px.max(axis=1) - px.min(axis=1)))  # croma médio (0 = cinza)
    r = {
        "luma_media": round(float(luma.mean()), 3),
        "preto_p0.5": [round(float(x), 3) for x in p_lo],
        "branco_p99.5": [round(float(x), 3) for x in p_hi],
        "rgb_medio_meios_tons": [round(float(x), 3) for x in media_rgb],
        "saturacao_media": round(sat, 3),
        "clipado_preto_%": round(float((luma < 0.01).mean() * 100), 2),
        "clipado_branco_%": round(float((luma > 0.99).mean() * 100), 2),
    }
    diag = []
    if r["luma_media"] < 0.35: diag.append("subexposto (escuro)")
    if r["luma_media"] > 0.62: diag.append("superexposto (claro)")
    if min(p_lo) > 0.06 or max(p_hi) < 0.9: diag.append("pouco contraste / imagem 'lavada'")
    dom = media_rgb - media_rgb.mean()
    if dom[2] - dom[0] > 0.04: diag.append("dominante azul (frio)")
    if dom[0] - dom[2] > 0.06: diag.append("dominante laranja/vermelha (quente)")
    if dom[1] - (dom[0] + dom[2]) / 2 > 0.03: diag.append("dominante verde")
    if dom[1] - (dom[0] + dom[2]) / 2 < -0.03: diag.append("dominante magenta")
    if sat < 0.08: diag.append("pouca saturação")
    if sat > 0.38: diag.append("saturação excessiva")
    if r["clipado_branco_%"] > 2: diag.append("altas luzes estouradas (irrecuperável no 8-bit)")
    r["diagnostico"] = diag or ["sem problemas evidentes"]
    r["filtro_auto"] = filtro_auto(p_lo, p_hi, luma.mean(), sat)
    return r


def filtro_auto(p_lo, p_hi, luma, sat):
    """Níveis por canal (corrige contraste e balanço de branco) + gamma para exposição."""
    lo = np.clip(p_lo, 0, 0.25)
    hi = np.clip(p_hi, 0.7, 1)
    partes = [f"colorlevels=rimin={lo[0]:.3f}:gimin={lo[1]:.3f}:bimin={lo[2]:.3f}"
              f":rimax={hi[0]:.3f}:gimax={hi[1]:.3f}:bimax={hi[2]:.3f}"]
    # luma estimada após níveis
    l2 = (luma - lo.mean()) / max(hi.mean() - lo.mean(), 1e-3)
    l2 = min(max(l2, 0.05), 0.95)
    gamma = float(np.clip(np.log(0.45) / np.log(l2), 0.7, 1.5))  # leva a média para ~0.45
    eq = []
    if abs(gamma - 1) > 0.03: eq.append(f"gamma={1 / gamma:.3f}")
    if sat < 0.1: eq.append("saturation=1.15")
    if eq: partes.append("eq=" + ":".join(eq))
    return ",".join(partes)


def montar_filtro(a, video=None):
    partes = []
    if getattr(a, "auto", False):
        partes.append(analisar(video)["filtro_auto"])
    if a.preset: partes.append(resolver(a.preset))
    if a.lut: partes.append(resolver("lut:" + a.lut))
    if a.filtro: partes.append(a.filtro)
    f = ",".join(p for p in partes if p) or "null"
    if a.intensidade < 1:
        f = f"split[o][c];[c]{f}[g];[g][o]blend=all_mode=normal:all_opacity={a.intensidade:.2f}"
    return f


def comparar(video, saida, tempo, f):
    tmp = Path(tempfile.mkdtemp())
    run(["ffmpeg", "-v", "error", "-y", "-ss", str(tempo), "-i", video, "-frames:v", "1",
         "-vf", "scale=960:-2", str(tmp / "a.png")])
    run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp / "a.png"), "-filter_complex", f"[0:v]{f}",
         "-frames:v", "1", str(tmp / "b.png")])
    a, b = Image.open(tmp / "a.png").convert("RGB"), Image.open(tmp / "b.png").convert("RGB")
    out = Image.new("RGB", (a.width * 2 + 10, a.height + 50), "black")
    out.paste(a, (0, 50)); out.paste(b, (a.width + 10, 50))
    d = ImageDraw.Draw(out)
    try:
        fonte = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
    except OSError:
        fonte = ImageFont.load_default()
    d.text((20, 10), "ANTES", fill="white", font=fonte)
    d.text((a.width + 30, 10), "DEPOIS", fill="white", font=fonte)
    out.save(saida, quality=92)
    print(f"✔ {saida}")


def exportar_lut(saida, f, nivel=8):
    """Aplica o filtro numa Hald CLUT identidade e converte para .cube (tamanho nivel²)."""
    tmp = Path(tempfile.mkdtemp())
    run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"haldclutsrc={nivel}", "-frames:v", "1",
         str(tmp / "id.png")])
    run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp / "id.png"), "-filter_complex", f"[0:v]{f}",
         "-frames:v", "1", "-pix_fmt", "rgb24", str(tmp / "lut.png")])
    px = np.asarray(Image.open(tmp / "lut.png").convert("RGB"), dtype=np.float32).reshape(-1, 3) / 255
    n = nivel * nivel
    with open(saida, "w") as fh:
        fh.write(f'TITLE "{Path(saida).stem}"\nLUT_3D_SIZE {n}\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
        for r, g, b in px:  # ordem Hald = R mais rápido, igual ao .cube
            fh.write(f"{r:.6f} {g:.6f} {b:.6f}\n")
    print(f"✔ {saida} (LUT {n}³)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def opcoes(p):
        p.add_argument("--auto", action="store_true", help="correção automática (níveis + exposição)")
        p.add_argument("--preset", help="look: " + ", ".join(PRESETS))
        p.add_argument("--lut", help="arquivo .cube")
        p.add_argument("--filtro", help="filtro FFmpeg extra")
        p.add_argument("--intensidade", type=float, default=1.0, help="0–1, mistura com o original")

    p = sub.add_parser("analisar"); p.add_argument("video")
    p = sub.add_parser("aplicar"); p.add_argument("video"); p.add_argument("saida"); opcoes(p)
    p.add_argument("--crf", default="18")
    p = sub.add_parser("comparar"); p.add_argument("video"); p.add_argument("saida")
    p.add_argument("--tempo", type=float, default=1.0); opcoes(p)
    p = sub.add_parser("lut"); p.add_argument("saida"); opcoes(p)
    p.add_argument("--auto-de", help="vídeo usado para a correção automática")
    sub.add_parser("presets")
    a = ap.parse_args()

    if a.cmd == "presets":
        for k, v in PRESETS.items():
            print(f"{k:16} {v}")
    elif a.cmd == "analisar":
        print(json.dumps(analisar(a.video), ensure_ascii=False, indent=2))
    elif a.cmd == "aplicar":
        f = montar_filtro(a, a.video)
        print("Filtro:", f)
        run(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-filter_complex", f"[0:v]{f},format=yuv420p[v]",
             "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-crf", a.crf, "-preset", "medium",
             "-c:a", "copy", "-movflags", "+faststart", a.saida])
        print(f"✔ {a.saida}")
    elif a.cmd == "comparar":
        comparar(a.video, a.saida, a.tempo, montar_filtro(a, a.video))
    elif a.cmd == "lut":
        a.auto = bool(a.auto_de)
        exportar_lut(a.saida, montar_filtro(a, a.auto_de))


if __name__ == "__main__":
    main()
