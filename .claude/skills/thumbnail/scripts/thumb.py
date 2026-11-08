#!/usr/bin/env python3
"""Compõe uma thumbnail: recorta a imagem no formato, escurece e aplica texto com contorno.

Uso: python thumb.py entrada.jpg saida.jpg --texto "TEXTO" [--formato youtube] [--cor amarelo]
     [--posicao esquerda] [--caixa] [--escurecer 0.3] [--fonte arquivo.ttf]
"""
import argparse
import glob
import textwrap

from PIL import Image, ImageDraw, ImageFont, ImageOps

FORMATOS = {"youtube": (1280, 720), "vertical": (1080, 1920), "quadrado": (1080, 1080)}
CORES = {"branco": "#FFFFFF", "amarelo": "#FFE600", "vermelho": "#FF2D2D", "verde": "#3DFF6E"}
FONTES = ["*Anton*.ttf", "*Impact*.ttf", "*Montserrat*Black*.ttf", "*DejaVuSans-Bold.ttf",
          "*LiberationSans-Bold.ttf", "*Bold*.ttf"]


def achar_fonte(caminho):
    if caminho:
        return caminho
    for padrao in FONTES:
        for d in ("/usr/share/fonts", "/usr/local/share/fonts", "/Library/Fonts", "C:/Windows/Fonts"):
            achados = glob.glob(f"{d}/**/{padrao}", recursive=True)
            if achados:
                return achados[0]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("entrada"); ap.add_argument("saida")
    ap.add_argument("--texto", required=True)
    ap.add_argument("--formato", choices=FORMATOS, default="youtube")
    ap.add_argument("--cor", choices=CORES, default="amarelo")
    ap.add_argument("--posicao", choices=["esquerda", "direita", "centro", "topo", "base"], default="esquerda")
    ap.add_argument("--caixa", action="store_true")
    ap.add_argument("--escurecer", type=float, default=0.25)
    ap.add_argument("--fonte")
    a = ap.parse_args()

    W, H = FORMATOS[a.formato]
    img = ImageOps.fit(Image.open(a.entrada).convert("RGB"), (W, H), Image.LANCZOS)
    if a.escurecer > 0:
        img = Image.blend(img, Image.new("RGB", (W, H), "black"), a.escurecer)

    lateral = a.posicao in ("esquerda", "direita")
    largura_max = W * (0.55 if lateral else 0.9)
    linhas = textwrap.wrap(a.texto.upper(), width=10 if lateral else 14) or [a.texto]

    fonte_path = achar_fonte(a.fonte)
    tam = int(H * (0.22 if a.formato == "youtube" else 0.11))
    while True:
        fonte = ImageFont.truetype(fonte_path, tam) if fonte_path else ImageFont.load_default(tam)
        d = ImageDraw.Draw(img)
        caixas = [d.textbbox((0, 0), l, font=fonte) for l in linhas]
        lw = max(b[2] - b[0] for b in caixas)
        lh = int(tam * 1.05)
        th = lh * len(linhas)
        if (lw <= largura_max and th <= H * 0.8) or tam <= 20:
            break
        tam -= 4

    margem = int(W * 0.05)
    x = {"esquerda": margem, "direita": W - margem - lw}.get(a.posicao, (W - lw) // 2)
    y = {"topo": int(H * 0.08), "base": H - th - int(H * 0.1)}.get(a.posicao, (H - th) // 2)

    contorno = max(4, tam // 12)
    cor = CORES[a.cor]
    for i, l in enumerate(linhas):
        b = caixas[i]
        lx = x if a.posicao in ("esquerda",) else x + (lw - (b[2] - b[0])) // (1 if a.posicao == "direita" else 2)
        ly = y + i * lh
        if a.caixa:
            pad = tam // 8
            d.rectangle([lx - pad, ly + b[1] - pad, lx + b[2] - b[0] + pad, ly + b[3] + pad], fill=cor)
            d.text((lx - b[0], ly), l, font=fonte, fill="black")
        else:
            d.text((lx - b[0], ly), l, font=fonte, fill=cor, stroke_width=contorno, stroke_fill="black")

    img.save(a.saida, quality=92)
    print(f"✔ {a.saida} ({W}x{H}, fonte: {fonte_path or 'padrão'}, tamanho {tam})")


if __name__ == "__main__":
    main()
