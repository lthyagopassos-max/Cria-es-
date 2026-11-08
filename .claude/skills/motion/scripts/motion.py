#!/usr/bin/env python3
"""Gera motion graphics com fundo transparente (ProRes 4444 .mov) para sobrepor no vídeo.

Modelos:
  titulo      texto entra com escala elástica, segura e sai
  lower       lower third: barra desliza com nome + subtítulo
  palavras    texto aparece palavra por palavra (kinetic typography)
  contador    número animado de A até B (ex.: 0 → 10.000 seguidores)
  barra       barra de progresso na base, ao longo de toda a duração
  cta         botão (pílula) com pulo + texto, tipo "SIGA PARA MAIS"
  destaque    seta + círculo desenhado em volta de um ponto (x,y)
  emoji       emoji/imagem PNG que entra com pulo e balança

Exemplos:
  python motion.py titulo saida.mov --texto "3 ERROS DE EDIÇÃO" --duracao 3
  python motion.py lower lt.mov --texto "Ana Souza" --sub "Editora de vídeo" --cor "#FFE600"
  python motion.py palavras p.mov --texto "ISSO MUDA TUDO NO SEU VÍDEO" --tamanho 1080x1920
  python motion.py contador c.mov --de 0 --ate 10000 --sufixo " seguidores"
  python motion.py destaque d.mov --x 1300 --y 400
  python motion.py titulo t.mp4 --texto "TESTE" --previa     # MP4 sobre fundo azul para conferir
"""
import argparse
import glob
import math
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont


# ---------- easing ----------
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_out_cubic(x): return 1 - (1 - clamp(x)) ** 3
def ease_in_cubic(x): return clamp(x) ** 3
def ease_in_out(x): x = clamp(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_out_back(x, s=1.70158):
    x = clamp(x) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def ease_out_elastic(x):
    x = clamp(x)
    if x in (0, 1): return x
    return 2 ** (-10 * x) * math.sin((x * 10 - 0.75) * (2 * math.pi) / 3) + 1


def entrada_saida(t, dur, ent=0.4, sai=0.35):
    """Progresso de entrada (0→1) e de saída (0→1)."""
    return clamp(t / ent), clamp((t - (dur - sai)) / sai)


# ---------- utilidades ----------
FONTES = ["*Anton*.ttf", "*Montserrat*Black*.ttf", "*Montserrat*ExtraBold*.ttf", "*Poppins*Bold*.ttf",
          "*Impact*.ttf", "*DejaVuSans-Bold.ttf", "*LiberationSans-Bold.ttf", "*Bold*.ttf"]


def fonte(caminho, tam):
    if caminho:
        return ImageFont.truetype(caminho, tam)
    for p in FONTES:
        for d in ("/usr/share/fonts", "/usr/local/share/fonts", "/Library/Fonts",
                  "/System/Library/Fonts", "C:/Windows/Fonts"):
            r = glob.glob(f"{d}/**/{p}", recursive=True)
            if r:
                return ImageFont.truetype(r[0], tam)
    return ImageFont.load_default(tam)


def hex_rgba(h, a=255):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


def texto_img(txt, f, cor, contorno=0, cor_contorno=(0, 0, 0, 255), sombra=True):
    b = f.getbbox(txt, stroke_width=contorno)
    w, h = b[2] - b[0] + 20, b[3] - b[1] + 20
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if sombra:
        d.text((10 - b[0] + 4, 10 - b[1] + 6), txt, font=f, fill=(0, 0, 0, 110),
               stroke_width=contorno, stroke_fill=(0, 0, 0, 110))
    d.text((10 - b[0], 10 - b[1]), txt, font=f, fill=cor, stroke_width=contorno, stroke_fill=cor_contorno)
    return im


def colar(base, img, cx, cy, escala=1.0, alpha=1.0, rot=0.0):
    if escala <= 0.01 or alpha <= 0.01:
        return
    if escala != 1:
        img = img.resize((max(1, int(img.width * escala)), max(1, int(img.height * escala))), Image.BICUBIC)
    if rot:
        img = img.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 1:
        img = img.copy()  # não alterar a imagem em cache
        a = img.getchannel("A").point(lambda v: int(v * alpha))
        img.putalpha(a)
    base.alpha_composite(img, (int(cx - img.width / 2), int(cy - img.height / 2)))


# ---------- modelos ----------
def m_titulo(W, H, t, dur, a, ctx):
    im = Image.new("RGBA", (W, H))
    if "img" not in ctx:
        ctx["img"] = texto_img(a.texto, fonte(a.fonte, a.fonte_tam or int(H * 0.11)), hex_rgba(a.cor),
                               contorno=max(4, int(H * 0.007)))
    e, s = entrada_saida(t, dur, 0.5, 0.3)
    esc = ease_out_elastic(e) * (1 - ease_in_cubic(s) * 0.4)
    colar(im, ctx["img"], W / 2, H * a.pos_y, esc, 1 - s)
    return im


def m_lower(W, H, t, dur, a, ctx):
    im = Image.new("RGBA", (W, H))
    u = H / 1080
    f1, f2 = fonte(a.fonte, a.fonte_tam or int(54 * u)), fonte(a.fonte, int(32 * u))
    if "dims" not in ctx:
        w1 = f1.getbbox(a.texto)[2]; w2 = f2.getbbox(a.sub or " ")[2]
        ctx["dims"] = (max(w1, w2) + int(80 * u), w2 + int(64 * u))
    larg, larg_sub = ctx["dims"]
    x0, y0 = int(80 * u), int(H * a.pos_y)
    e, s = entrada_saida(t, dur, 0.6, 0.45)
    d = ImageDraw.Draw(im)
    # faixa de acento
    p_acc = ease_out_cubic(e / 0.6) * (1 - ease_in_cubic(s))
    d.rectangle([x0, y0, x0 + int(12 * u), y0 + int(140 * u * p_acc)], fill=hex_rgba(a.cor))
    # caixa principal
    p_box = ease_out_cubic((e - 0.25) / 0.75) * (1 - ease_in_cubic(s * 1.3))
    if p_box > 0:
        d.rectangle([x0 + int(12 * u), y0, x0 + int(12 * u) + int(larg * p_box), y0 + int(86 * u)],
                    fill=hex_rgba(a.fundo, 235))
        if a.sub:
            d.rectangle([x0 + int(12 * u), y0 + int(86 * u), x0 + int(12 * u) + int(larg_sub * p_box),
                         y0 + int(140 * u)], fill=hex_rgba(a.cor, 235))
    # textos (mascarados pela caixa)
    p_txt = ease_out_cubic((e - 0.5) / 0.5) * (1 - s)
    if p_txt > 0:
        camada = Image.new("RGBA", (W, H)); dc = ImageDraw.Draw(camada)
        dx = int((1 - p_txt) * -40 * u)
        dc.text((x0 + int(40 * u) + dx, y0 + int(14 * u)), a.texto, font=f1, fill=hex_rgba(a.cor_texto))
        if a.sub:
            dc.text((x0 + int(40 * u) + dx, y0 + int(94 * u)), a.sub, font=f2, fill=hex_rgba(a.cor_texto))
        mask = Image.new("L", (W, H))
        ImageDraw.Draw(mask).rectangle([x0 + int(12 * u), y0, x0 + int(12 * u) + int(larg * p_box),
                                        y0 + int(140 * u)], fill=int(255 * p_txt))
        camada.putalpha(Image.composite(camada.getchannel("A"), mask, mask).point(lambda v: v))
        im.alpha_composite(camada)
    return im


def m_palavras(W, H, t, dur, a, ctx):
    im = Image.new("RGBA", (W, H))
    if "linhas" not in ctx:
        f = fonte(a.fonte, a.fonte_tam or int(min(W, H) * 0.09))
        pal = a.texto.split()
        larg_max = W * 0.85
        linhas, atual = [], []
        for p in pal:
            teste = " ".join(atual + [p])
            if atual and f.getbbox(teste)[2] > larg_max:
                linhas.append(atual); atual = [p]
            else:
                atual.append(p)
        linhas.append(atual)
        esp = f.getbbox(" ")[2]
        alt = int(f.size * 1.2)
        itens, y = [], H * a.pos_y - alt * len(linhas) / 2 + alt / 2
        for ln in linhas:
            imgs = [texto_img(p, f, hex_rgba(a.cor), contorno=max(3, f.size // 14)) for p in ln]
            tot = sum(i.width - 20 for i in imgs) + esp * (len(imgs) - 1)
            x = (W - tot) / 2
            for i in imgs:
                itens.append((i, x + (i.width - 20) / 2, y)); x += i.width - 20 + esp
            y += alt
        ctx["linhas"] = itens
    itens = ctx["linhas"]
    passo = min(a.intervalo, (dur - 0.6) / max(len(itens), 1))
    _, s = entrada_saida(t, dur, 0.1, 0.3)
    for k, (img, cx, cy) in enumerate(itens):
        p = (t - k * passo) / 0.25
        if p <= 0:
            continue
        colar(im, img, cx, cy + (1 - ease_out_cubic(p)) * 30, ease_out_back(p), clamp(p * 2) * (1 - s))
    return im


def m_contador(W, H, t, dur, a, ctx):
    im = Image.new("RGBA", (W, H))
    f = ctx.setdefault("f", fonte(a.fonte, a.fonte_tam or int(H * 0.16)))
    p = ease_out_cubic(t / max(dur - 0.8, 0.1))
    v = a.de + (a.ate - a.de) * p
    num = f"{v:,.{a.decimais}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    txt = f"{a.prefixo}{num}{a.sufixo}"
    e, s = entrada_saida(t, dur, 0.3, 0.3)
    pulso = 1 + 0.08 * math.sin(clamp((t - (dur - 0.8)) / 0.3) * math.pi)
    colar(im, texto_img(txt, f, hex_rgba(a.cor), contorno=max(4, f.size // 14)), W / 2, H * a.pos_y,
          ease_out_back(e) * pulso, 1 - s)
    return im


def m_barra(W, H, t, dur, a, ctx):
    im = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(im)
    alt = max(6, int(H * 0.012))
    y = H - alt if a.pos_y >= 0.5 else 0
    d.rectangle([0, y, W, y + alt], fill=(255, 255, 255, 60))
    d.rectangle([0, y, int(W * t / dur), y + alt], fill=hex_rgba(a.cor))
    return im


def m_cta(W, H, t, dur, a, ctx):
    im = Image.new("RGBA", (W, H))
    if "img" not in ctx:
        f = fonte(a.fonte, a.fonte_tam or int(min(W, H) * 0.055))
        b = f.getbbox(a.texto)
        pw, ph = b[2] - b[0] + int(f.size * 1.6), int(f.size * 2.0)
        btn = Image.new("RGBA", (pw + 20, ph + 20))
        d = ImageDraw.Draw(btn)
        d.rounded_rectangle([14, 16, pw + 14, ph + 16], radius=ph // 2, fill=(0, 0, 0, 100))
        d.rounded_rectangle([10, 10, pw + 10, ph + 10], radius=ph // 2, fill=hex_rgba(a.fundo))
        d.text((10 + (pw - (b[2] - b[0])) / 2 - b[0], 10 + (ph - (b[3] - b[1])) / 2 - b[1]), a.texto,
               font=f, fill=hex_rgba(a.cor_texto))
        ctx["img"] = btn
    e, s = entrada_saida(t, dur, 0.5, 0.3)
    pulo = 1 + 0.06 * math.sin(max(t - 0.6, 0) * 2 * math.pi * 1.2) * (t > 0.6)
    colar(im, ctx["img"], W / 2, H * a.pos_y + (1 - ease_out_back(e)) * H * 0.15, pulo, clamp(e * 3) * (1 - s))
    return im


def m_destaque(W, H, t, dur, a, ctx):
    im = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(im)
    x, y = a.x if a.x is not None else W / 2, a.y if a.y is not None else H / 2
    r = a.raio or int(min(W, H) * 0.09)
    esp = max(5, int(min(W, H) * 0.008))
    e, s = entrada_saida(t, dur, 0.6, 0.3)
    cor = hex_rgba(a.cor, int(255 * (1 - s)))
    ang = 360 * ease_out_cubic(e)
    if ang > 1:
        d.arc([x - r * 1.1, y - r, x + r * 1.1, y + r], -100, -100 + ang, fill=cor, width=esp)
    # seta vinda de baixo-esquerda
    p = ease_out_cubic((t - 0.3) / 0.4)
    if p > 0:
        sx, sy = x - r * 2.6, y + r * 2.2
        ex, ey = x - r * 0.9, y + r * 0.8
        cx, cy = sx + (ex - sx) * p, sy + (ey - sy) * p
        d.line([sx, sy, cx, cy], fill=cor, width=esp)
        ang_s = math.atan2(ey - sy, ex - sx)
        for da in (2.6, -2.6):
            d.line([cx, cy, cx + r * 0.35 * math.cos(ang_s + da), cy + r * 0.35 * math.sin(ang_s + da)],
                   fill=cor, width=esp)
    return im


def m_emoji(W, H, t, dur, a, ctx):
    im = Image.new("RGBA", (W, H))
    if "img" not in ctx:
        if not a.imagem:
            sys.exit("--imagem arquivo.png é obrigatório para 'emoji'")
        src = Image.open(a.imagem).convert("RGBA")
        lado = a.fonte_tam or int(min(W, H) * 0.18)
        src.thumbnail((lado, lado), Image.LANCZOS)
        ctx["img"] = src
    e, s = entrada_saida(t, dur, 0.5, 0.25)
    rot = 8 * math.sin(t * 2 * math.pi * 1.5) * (t > 0.5)
    x = a.x if a.x is not None else W / 2
    colar(im, ctx["img"], x, H * a.pos_y, ease_out_elastic(e) * (1 - s), 1, rot)
    return im


MODELOS = {"titulo": m_titulo, "lower": m_lower, "palavras": m_palavras, "contador": m_contador,
           "barra": m_barra, "cta": m_cta, "destaque": m_destaque, "emoji": m_emoji}
POS_PADRAO = {"titulo": 0.5, "lower": 0.74, "palavras": 0.5, "contador": 0.5, "barra": 1.0,
              "cta": 0.8, "destaque": 0.5, "emoji": 0.3}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("modelo", choices=MODELOS)
    ap.add_argument("saida", help=".mov (transparente) ou .mp4/.webm")
    ap.add_argument("--texto", default="")
    ap.add_argument("--sub", default="")
    ap.add_argument("--duracao", type=float, default=3.0)
    ap.add_argument("--tamanho", default="1920x1080")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--cor", default="#FFE600", help="cor principal")
    ap.add_argument("--cor-texto", default="#111111", help="texto sobre caixas (lower/cta)")
    ap.add_argument("--fundo", default="#FFFFFF", help="cor de caixas/botões")
    ap.add_argument("--fonte"); ap.add_argument("--fonte-tam", type=int)
    ap.add_argument("--pos-y", type=float, help="posição vertical 0–1")
    ap.add_argument("--x", type=float); ap.add_argument("--y", type=float); ap.add_argument("--raio", type=int)
    ap.add_argument("--de", type=float, default=0); ap.add_argument("--ate", type=float, default=100)
    ap.add_argument("--decimais", type=int, default=0)
    ap.add_argument("--prefixo", default=""); ap.add_argument("--sufixo", default="")
    ap.add_argument("--intervalo", type=float, default=0.28, help="segundos entre palavras")
    ap.add_argument("--imagem", help="PNG para o modelo emoji")
    ap.add_argument("--previa", action="store_true", help="MP4 sobre fundo azul para conferir")
    a = ap.parse_args()
    if a.pos_y is None:
        a.pos_y = POS_PADRAO[a.modelo]
    if a.modelo == "destaque" and a.y is not None:
        a.pos_y = a.y
    if a.modelo in ("titulo", "lower", "palavras", "cta") and not a.texto:
        sys.exit("--texto é obrigatório para " + a.modelo)
    if a.modelo == "cta" and a.fundo == "#FFFFFF" and a.cor_texto == "#111111":
        a.fundo, a.cor_texto = a.cor, "#111111"

    W, H = map(int, a.tamanho.lower().split("x"))
    n = int(round(a.duracao * a.fps))
    if a.previa or a.saida.endswith(".mp4"):
        fundo = "-f lavfi -i color=c=0x3a6ea5:s={W}x{H}:r={fps}".format(W=W, H=H, fps=a.fps)
        cmd = (["ffmpeg", "-v", "error", "-y"] + fundo.split() +
               ["-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(a.fps), "-i", "-",
                "-filter_complex", "[0][1]overlay=shortest=1,format=yuv420p", "-c:v", "libx264", "-crf", "20",
                a.saida])
    elif a.saida.endswith(".webm"):
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
               "-r", str(a.fps), "-i", "-", "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "2M", a.saida]
    else:
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
               "-r", str(a.fps), "-i", "-", "-c:v", "prores_ks", "-profile:v", "4444",
               "-pix_fmt", "yuva444p10le", a.saida]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    ctx = {}
    fn = MODELOS[a.modelo]
    for i in range(n):
        proc.stdin.write(fn(W, H, i / a.fps, a.duracao, a, ctx).tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg falhou")
    print(f"✔ {a.saida} ({a.modelo}, {W}x{H}, {a.duracao}s @ {a.fps}fps)")


if __name__ == "__main__":
    main()
