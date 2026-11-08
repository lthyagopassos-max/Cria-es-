"""Looks de cor prontos, como cadeias de filtros do FFmpeg.

Usado por cor.py e pelo render.py da skill `montagem`.
"""

PRESETS = {
    # correções neutras
    "neutro": "eq=contrast=1.05:saturation=1.05",
    "clarear": "eq=brightness=0.04:gamma=1.12:contrast=1.03",
    "escurecer": "eq=brightness=-0.03:gamma=0.92",
    "mais-contraste": "curves=master='0/0 0.25/0.20 0.75/0.82 1/1'",
    "menos-contraste": "curves=master='0/0.04 0.5/0.5 1/0.96'",
    "mais-saturacao": "eq=saturation=1.25",
    "pele": "colorbalance=rm=0.03:gm=0.0:bm=-0.03,eq=saturation=1.05",
    # looks criativos
    "quente": "colortemperature=temperature=5000:mix=0.6,eq=saturation=1.08:contrast=1.04",
    "frio": "colortemperature=temperature=8000:mix=0.6,eq=saturation=0.95:contrast=1.05",
    "cinema": "curves=master='0/0.03 0.25/0.21 0.75/0.80 1/0.97',"
              "colorbalance=rs=-0.06:gs=0.0:bs=0.08:rh=0.06:gh=0.02:bh=-0.06,eq=saturation=0.92",
    "teal-orange": "colorbalance=rs=-0.12:bs=0.12:rm=-0.04:bm=0.04:rh=0.10:bh=-0.10,eq=saturation=1.1:contrast=1.06",
    "vlog": "eq=brightness=0.02:contrast=1.06:saturation=1.18:gamma=1.04,unsharp=5:5:0.4",
    "vintage": "curves=preset=vintage,eq=saturation=0.85",
    "desbotado": "curves=master='0/0.08 0.5/0.5 1/0.92',eq=saturation=0.8",
    "pb": "hue=s=0,eq=contrast=1.15",
    "pb-suave": "hue=s=0,curves=master='0/0.05 1/0.95'",
    "noturno": "colortemperature=temperature=9500:mix=0.7,eq=brightness=-0.06:saturation=0.75:contrast=1.1",
}


def filtro(nome_ou_filtro: str) -> str:
    """Retorna o filtro do preset, 'lut:<arquivo.cube>' vira lut3d, senão devolve como filtro bruto."""
    if not nome_ou_filtro:
        return ""
    if nome_ou_filtro in PRESETS:
        return PRESETS[nome_ou_filtro]
    if nome_ou_filtro.startswith("lut:"):
        caminho = nome_ou_filtro[4:].replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
        return f"lut3d=file='{caminho}'"
    return nome_ou_filtro
