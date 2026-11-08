#!/usr/bin/env python3
"""Renderiza uma timeline JSON (vídeo + cor + transições + B-roll/motion + legendas + música + SFX).

Uso:
  python render.py timeline.json                  # renderiza
  python render.py timeline.json --mapa           # só mostra o mapa da timeline (tempos de cada clipe)
  python render.py timeline.json --rascunho       # render rápido em meia resolução para conferir
  python render.py timeline.json --edl final.edl  # também exporta EDL (DaVinci Resolve / Premiere)

Formato da timeline: veja ../SKILL.md e ../modelo_timeline.json
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parents[1] / "correcao-cor" / "scripts"))
try:
    from presets import filtro as filtro_cor
except ImportError:  # skill correcao-cor ausente: aceita só filtros brutos
    def filtro_cor(x):
        return x or ""

ESTILOS_LEGENDA = {
    "padrao": "FontName=Arial,FontSize=14,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
              "BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=30",
    "reels": "FontName=Arial Black,FontSize=20,Bold=1,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,"
             "BorderStyle=1,Outline=3,Shadow=0,Alignment=10",
    "caixa": "FontName=Arial,FontSize=14,PrimaryColour=&H00FFFFFF,BackColour=&H80000000,"
             "BorderStyle=3,Outline=1,Shadow=0,Alignment=2,MarginV=30",
}


# ---------------- utilidades ----------------
def run(cmd, rotulo):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"✘ Erro em: {rotulo}\n" + " ".join(map(str, cmd)) + "\n" + r.stderr[-3000:], file=sys.stderr)
        sys.exit(1)


def probe(arq, campo, stream=None):
    cmd = ["ffprobe", "-v", "error"]
    if stream:
        cmd += ["-select_streams", stream]
    cmd += ["-show_entries", campo, "-of", "csv=p=0", str(arq)]
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


def duracao(arq):
    return float(probe(arq, "format=duration") or 0)


def tem_audio(arq):
    return bool(probe(arq, "stream=index", "a"))


def esc(caminho):
    """Escapa caminho para uso dentro de filtros (subtitles, lut3d...)."""
    return str(caminho).replace("\\", "/").replace(":", "\\:").replace("'", "\\'").replace(",", "\\,")


def tc(seg, fps):
    f = int(round(seg * fps))
    return f"{f // (3600 * fps):02}:{f // (60 * fps) % 60:02}:{f // fps % 60:02}:{f % fps:02}"


def atempo(v):
    partes = []
    while v > 2.0:
        partes.append("atempo=2.0"); v /= 2.0
    while v < 0.5:
        partes.append("atempo=0.5"); v /= 0.5
    partes.append(f"atempo={v:.4f}")
    return ",".join(partes)


# ---------------- etapa 1: clipes normalizados ----------------
def preparar_clipe(c, i, W, H, fps, base, tmp):
    saida = tmp / f"clipe_{i:03}.mp4"
    vel = float(c.get("velocidade", 1.0))
    ajuste = c.get("ajuste", "preencher")  # preencher (corta bordas) | conter (barras)
    if "imagem" in c:
        src = base / c["imagem"]
        dur_src = float(c.get("duracao", 3))
        entrada = ["-loop", "1", "-framerate", str(fps), "-t", f"{dur_src}", "-i", str(src)]
        audio_src = False
    else:
        src = base / c["arquivo"]
        ini = float(c.get("inicio", 0))
        fim = float(c.get("fim", duracao(src)))
        dur_src = fim - ini
        entrada = ["-ss", f"{ini}", "-t", f"{dur_src}", "-i", str(src)]
        audio_src = tem_audio(src) and not c.get("mudo", False)
    if not src.exists():
        sys.exit(f"✘ Arquivo não encontrado: {src}")
    dur = dur_src / vel

    if ajuste == "conter":
        vf = [f"scale={W}:{H}:force_original_aspect_ratio=decrease",
              f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={c.get('fundo', 'black')}"]
    else:
        vf = [f"scale={W}:{H}:force_original_aspect_ratio=increase", f"crop={W}:{H}"]
    vf += ["setsar=1"]
    if vel != 1:
        vf.append(f"setpts=PTS/{vel}")
    vf.append(f"fps={fps}")
    z = c.get("zoom")
    if isinstance(z, (int, float)) and z != 1:
        vf += [f"scale={int(W * z) // 2 * 2}:{int(H * z) // 2 * 2}", f"crop={W}:{H}"]
    elif isinstance(z, list):
        z0, z1 = float(z[0]), float(z[1])
        n = max(int(round(dur * fps)), 1)
        vf += [f"scale={W * 2}:{H * 2}",
               f"zoompan=z='{z0}+({z1 - z0})*on/{n}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
               f":s={W}x{H}:fps={fps}"]
    if c.get("cor"):
        vf.append(filtro_cor(c["cor"]))
    vf.append("format=yuv420p")

    cmd = ["ffmpeg", "-v", "error", "-y"] + entrada
    if audio_src:
        af = [f"volume={c.get('volume', 1.0)}"]
        if vel != 1:
            af.append(atempo(vel))
        af += ["aresample=48000", "aformat=sample_fmts=fltp:channel_layouts=stereo"]
        fc = f"[0:v]{','.join(vf)}[v];[0:a]{','.join(af)},apad[a]"
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
        fc = f"[0:v]{','.join(vf)}[v];[1:a]aformat=sample_fmts=fltp:channel_layouts=stereo[a]"
    cmd += ["-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", f"{dur:.4f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-c:a", "pcm_s16le",
            "-f", "matroska", str(saida.with_suffix(".mkv"))]
    run(cmd, f"clipe {i + 1} ({c.get('arquivo') or c.get('imagem')})")
    real = duracao(saida.with_suffix(".mkv"))
    return saida.with_suffix(".mkv"), real


# ---------------- etapa 2: juntar com transições ----------------
def juntar(clipes, transicoes, tmp):
    """clipes: [(arquivo, dur)], transicoes[i] = (tipo, d) da entrada do clipe i. Retorna (arquivo, inicios, total)."""
    inicios, total = [], 0.0
    for i, (_, d) in enumerate(clipes):
        tr = transicoes[i][1] if i > 0 and transicoes[i] else 0.0
        inicio = total - tr
        inicios.append(inicio)
        total = inicio + d
    saida = tmp / "base.mkv"
    if len(clipes) == 1:
        shutil.copy(clipes[0][0], saida)
        return saida, inicios, total
    if not any(transicoes[1:]):
        lista = tmp / "lista.txt"
        lista.write_text("".join(f"file '{p.as_posix()}'\n" for p, _ in clipes))
        run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(saida)],
            "concatenação")
        return saida, inicios, total
    entradas, fc = [], []
    for p, _ in clipes:
        entradas += ["-i", str(p)]
    for i in range(len(clipes)):  # mesma base de tempo em tudo (xfade exige)
        fc.append(f"[{i}:v]settb=AVTB,setpts=PTS-STARTPTS[pv{i}]")
        fc.append(f"[{i}:a]asetpts=PTS-STARTPTS[pa{i}]")
    v, a = "[pv0]", "[pa0]"
    for i in range(1, len(clipes)):
        nv, na = f"[v{i}]", f"[a{i}]"
        if transicoes[i]:
            tipo, d = transicoes[i]
            fc.append(f"{v}[pv{i}]xfade=transition={tipo}:duration={d}:offset={inicios[i]:.4f}{nv}")
            fc.append(f"{a}[pa{i}]acrossfade=d={d}:c1=tri:c2=tri{na}")
        else:
            fc.append(f"{v}{a}[pv{i}][pa{i}]concat=n=2:v=1:a=1[cv{i}]{na}")
            fc.append(f"[cv{i}]settb=AVTB{nv}")
        v, a = nv, na
    run(["ffmpeg", "-v", "error", "-y"] + entradas + ["-filter_complex", ";".join(fc), "-map", v, "-map", a,
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-c:a", "pcm_s16le", str(saida)], "transições")
    return saida, inicios, total


# ---------------- etapa 3: camadas, áudio e exportação ----------------
def finalizar(tl, base_dir, base, total, W, H, fps, saida, rascunho):
    entradas = ["-i", str(base)]
    fc, idx = [], 1
    v = "[0:v]"
    if tl.get("cor"):
        fc.append(f"{v}{filtro_cor(tl['cor'])}[vc]"); v = "[vc]"

    # overlays (motion, B-roll, logo, imagens)
    sfx = list(tl.get("sfx", []))
    for k, o in enumerate(tl.get("overlays", [])):
        arq = base_dir / o["arquivo"]
        em = float(o.get("em", 0))
        imagem = arq.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
        if imagem:
            entradas += ["-loop", "1", "-framerate", str(fps), "-t", str(o.get("duracao", 3)), "-i", str(arq)]
        else:
            if o.get("de") is not None:
                entradas += ["-ss", str(o["de"])]
            if o.get("duracao") is not None:
                entradas += ["-t", str(o["duracao"])]
            entradas += ["-i", str(arq)]
        f = [f"fps={fps}"]
        if o.get("tela_cheia"):
            f += [f"scale={W}:{H}:force_original_aspect_ratio=increase", f"crop={W}:{H}"]
        elif o.get("largura"):
            f.append(f"scale={int(o['largura'])}:-2")
        elif o.get("escala"):
            f.append(f"scale=iw*{o['escala']}:-2")
        if o.get("cor"):
            f.append(filtro_cor(o["cor"]))
        f += ["format=yuva420p"]
        if o.get("fade", 0):
            d = float(o["fade"]); dur_o = float(o.get("duracao") or duracao(arq) - float(o.get("de") or 0))
            f += [f"fade=t=in:d={d}:alpha=1", f"fade=t=out:st={max(dur_o - d, 0):.3f}:d={d}:alpha=1"]
        f.append(f"setpts=PTS-STARTPTS+{em}/TB")
        x = o.get("x", "(W-w)/2" if o.get("tela_cheia") or o.get("centro") else 0)
        y = o.get("y", "(H-h)/2" if o.get("tela_cheia") or o.get("centro") else 0)
        fc.append(f"[{idx}:v]{','.join(f)}[o{k}]")
        fc.append(f"{v}[o{k}]overlay=x={x}:y={y}:eof_action=pass[vo{k}]")
        v = f"[vo{k}]"; idx += 1
        if o.get("sfx"):
            sfx.append({"arquivo": o["sfx"], "em": em + float(o.get("sfx_atraso", 0)),
                        "volume": o.get("sfx_volume", 0.5)})

    leg = tl.get("legendas")
    if leg:
        estilo = ESTILOS_LEGENDA.get(leg.get("estilo", "padrao"), leg.get("estilo"))
        fc.append(f"{v}subtitles='{esc(base_dir / leg['arquivo'])}':force_style='{estilo}'[vl]"); v = "[vl]"
    if rascunho:
        fc.append(f"{v}scale={W // 2 // 2 * 2}:-2[vr]"); v = "[vr]"
    fc.append(f"{v}format=yuv420p[vfinal]")

    # ---- áudio ----
    musicas = tl.get("musica", [])
    sc = tl.get("sfx_cortes")
    if sc:
        for t in tl["_inicios"][1:]:
            sfx.append({"arquivo": sc["arquivo"], "em": max(t - float(sc.get("antecipar", 0.15)), 0),
                        "volume": sc.get("volume", 0.35)})
    n_duck = sum(1 for m in musicas if m.get("ducking", True))
    voz = "[0:a]"
    if n_duck:
        saidas = "".join(f"[sc{j}]" for j in range(n_duck))
        fc.append(f"[0:a]asplit={n_duck + 1}[voz]{saidas}"); voz = "[voz]"
    mix, j = [voz], 0
    for k, m in enumerate(musicas):
        arq = base_dir / m["arquivo"]
        if m.get("loop"):
            entradas += ["-stream_loop", "-1"]
        entradas += ["-i", str(arq)]
        ini = float(m.get("inicio", 0)); fim = float(m.get("fim", total))
        dur_m = fim - ini
        if not m.get("loop"):
            dur_m = min(dur_m, duracao(arq) - float(m.get("de", 0)))
        f = [f"atrim=start={m.get('de', 0)}:duration={dur_m:.3f}", "asetpts=PTS-STARTPTS",
             "aresample=48000", "aformat=sample_fmts=fltp:channel_layouts=stereo", f"volume={m.get('volume', 0.25)}"]
        if m.get("fade_in", 1):
            f.append(f"afade=t=in:d={m.get('fade_in', 1)}")
        if m.get("fade_out", 2):
            fo = float(m.get("fade_out", 2))
            f.append(f"afade=t=out:st={max(dur_m - fo, 0):.3f}:d={fo}")
        ms = int(ini * 1000)
        f.append(f"adelay={ms}|{ms}")
        fc.append(f"[{idx}:a]{','.join(f)}[m{k}]")
        rot = f"[m{k}]"
        if m.get("ducking", True):
            fc.append(f"[m{k}][sc{j}]sidechaincompress=threshold={m.get('ducking_limiar', 0.02)}:ratio=10:"
                      f"attack=15:release=400:makeup=1[md{k}]")
            rot = f"[md{k}]"; j += 1
        mix.append(rot); idx += 1
    for k, s in enumerate(sfx):
        entradas += ["-i", str(base_dir / s["arquivo"])]
        ms = int(float(s["em"]) * 1000)
        fc.append(f"[{idx}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                  f"volume={s.get('volume', 0.5)},adelay={ms}|{ms}[s{k}]")
        mix.append(f"[s{k}]"); idx += 1
    if len(mix) > 1:
        fc.append(f"{''.join(mix)}amix=inputs={len(mix)}:duration=first:dropout_transition=0:normalize=0[mx]")
        a = "[mx]"
    else:
        a = voz
    lufs = tl.get("loudness", -14)
    if lufs is not None:
        fc.append(f"{a}loudnorm=I={lufs}:TP=-1.5:LRA=11,aresample=48000[afinal]")
    else:
        fc.append(f"{a}alimiter=limit=0.89,aresample=48000[afinal]")

    cmd = (["ffmpeg", "-v", "error", "-y"] + entradas +
           ["-filter_complex", ";".join(fc), "-map", "[vfinal]", "-map", "[afinal]", "-t", f"{total:.4f}",
            "-c:v", "libx264", "-preset", "ultrafast" if rascunho else tl.get("preset", "medium"),
            "-crf", "28" if rascunho else str(tl.get("crf", 20)), "-r", str(fps),
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(saida)])
    run(cmd, "exportação final")
    if lufs is not None:
        ajustar_loudness(saida, float(lufs))


def ajustar_loudness(arq, alvo):
    """O loudnorm de 1 passada erra em arquivos curtos: mede e corrige o ganho (só o áudio é recodificado)."""
    import re
    log = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(arq), "-vn", "-af", "ebur128",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", log)
    if not m:
        return
    medido = float(m[-1]); ganho = alvo - medido
    if abs(ganho) < 0.5:
        return
    tmp = arq.with_name(arq.stem + "_tmp" + arq.suffix)
    run(["ffmpeg", "-v", "error", "-y", "-i", str(arq), "-c:v", "copy", "-af",
         f"volume={ganho:.2f}dB,alimiter=limit=0.84:level=false", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", str(tmp)], "ajuste de loudness")
    tmp.replace(arq)
    print(f"  loudness: {medido:.1f} → {alvo:.0f} LUFS (ganho {ganho:+.1f} dB)")


def exportar_edl(tl, clipes, inicios, duracoes, fps, caminho):
    linhas = [f"TITLE: {Path(tl.get('saida', 'final')).stem}", "FCM: NON-DROP FRAME", ""]
    for i, (c, ini_rec) in enumerate(zip(clipes, inicios), 1):
        nome = c.get("arquivo") or c.get("imagem")
        s_in = float(c.get("inicio", 0))
        dur = duracoes[i - 1]
        s_out = s_in + dur * float(c.get("velocidade", 1.0))
        r_in, r_out = 3600 + ini_rec, 3600 + ini_rec + dur
        linhas.append(f"{i:03}  AX       B     C        {tc(s_in, fps)} {tc(s_out, fps)} {tc(r_in, fps)} {tc(r_out, fps)}")
        linhas.append(f"* FROM CLIP NAME: {Path(nome).name}")
        if c.get("transicao"):
            linhas.append(f"* TRANSICAO: {c['transicao'].get('tipo', 'fade')} {c['transicao'].get('duracao', 0.5)}s")
        linhas.append("")
    Path(caminho).write_text("\n".join(linhas))
    print(f"✔ EDL: {caminho} (abra no DaVinci: File > Import > Timeline; Premiere: File > Import)")



def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("timeline")
    ap.add_argument("--mapa", action="store_true", help="só mostra os tempos, sem renderizar")
    ap.add_argument("--rascunho", action="store_true", help="render rápido em meia resolução")
    ap.add_argument("--edl", help="exporta também um EDL CMX3600")
    ap.add_argument("--saida", help="sobrescreve o campo 'saida'")
    a = ap.parse_args()

    tl_path = Path(a.timeline).resolve()
    tl = json.loads(tl_path.read_text(encoding="utf-8"))
    base_dir = tl_path.parent
    W, H = tl.get("resolucao", [1920, 1080])
    fps = int(tl.get("fps", 30))
    saida = base_dir / (a.saida or tl.get("saida", "final.mp4"))
    if a.rascunho and not a.saida:
        saida = saida.with_name(saida.stem + "_rascunho" + saida.suffix)
    clipes = tl["video"]

    # durações previstas (para o mapa e o EDL)
    prev = []
    for c in clipes:
        if "imagem" in c:
            d = float(c.get("duracao", 3))
        else:
            src = base_dir / c["arquivo"]
            d = float(c.get("fim", duracao(src))) - float(c.get("inicio", 0))
        prev.append(d / float(c.get("velocidade", 1.0)))
    trans = [None] + [((c["transicao"].get("tipo", "fade"), float(c["transicao"].get("duracao", 0.5)))
                       if c.get("transicao") else None) for c in clipes[1:]]
    inicios, total = [], 0.0
    for i, d in enumerate(prev):
        ini = total - (trans[i][1] if trans[i] else 0)
        inicios.append(ini); total = ini + d
    print(f"Timeline: {len(clipes)} clipes, {total:.2f}s, {W}x{H} @ {fps}fps")
    for i, (c, ini, d) in enumerate(zip(clipes, inicios, prev), 1):
        nome = c.get("arquivo") or c.get("imagem")
        extra = " ".join(f"{k}={c[k]}" for k in ("cor", "zoom", "velocidade") if c.get(k))
        if c.get("transicao"):
            extra += f" transição={c['transicao'].get('tipo', 'fade')} {c['transicao'].get('duracao', 0.5)}s"
        print(f"  {i:>3}. {ini:7.2f}s → {ini + d:7.2f}s  {nome} [{c.get('inicio', 0)}–{c.get('fim', '')}] {extra}")
    if a.mapa:
        return

    tmp = Path(tempfile.mkdtemp(prefix="montagem_"))
    try:
        prontos = []
        for i, c in enumerate(clipes):
            print(f"  preparando clipe {i + 1}/{len(clipes)}…", end="\r")
            prontos.append(preparar_clipe(c, i, W, H, fps, base_dir, tmp))
        print()
        base, inicios, total = juntar(prontos, trans, tmp)
        tl["_inicios"] = inicios
        print("  finalizando (camadas, legendas, áudio)…")
        finalizar(tl, base_dir, base, total, W, H, fps, saida, a.rascunho)
        if a.edl:
            exportar_edl(tl, clipes, inicios, [d for _, d in prontos], fps, base_dir / a.edl)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"✔ {saida} ({duracao(saida):.2f}s)")


if __name__ == "__main__":
    main()
