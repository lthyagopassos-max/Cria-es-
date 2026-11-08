---
name: video-programatico
description: Gera vídeos a partir de código ou dados — slideshow de imagens com música, vídeo de texto/citação, vídeo com narração em áudio, animações e templates em lote com MoviePy, FFmpeg ou Remotion (React). Use quando o usuário quiser criar um vídeo do zero sem filmagem, automatizar vários vídeos parecidos ou montar vídeo a partir de imagens, textos, planilhas ou roteiro.
---

# Vídeo programático

## Escolha da ferramenta
| Caso | Ferramenta |
|---|---|
| Slideshow simples, imagens + música | **FFmpeg** (sem dependências) |
| Composição em Python, texto, lotes a partir de CSV | **MoviePy** (`pip install moviepy`) |
| Animações ricas, templates de marca, motion design | **Remotion** (React/TypeScript, Node) |

## FFmpeg — slideshow com zoom suave (Ken Burns) e música
```bash
# imagens img_01.jpg, img_02.jpg ... 4 s cada, 1080x1920
for f in img_*.jpg; do
  ffmpeg -y -loop 1 -t 4 -i "$f" -vf "scale=2160:-2,zoompan=z='min(zoom+0.0015,1.15)':d=120:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30,format=yuv420p" -c:v libx264 "clip_${f%.*}.mp4"
done
printf "file '%s'\n" clip_img_*.mp4 > lista.txt
ffmpeg -y -f concat -safe 0 -i lista.txt -i musica.mp3 -c:v copy -c:a aac -shortest slideshow.mp4
```
Para transições suaves entre clipes use `xfade`: `[0][1]xfade=transition=fade:duration=0.5:offset=3.5`.

## MoviePy (v2) — vídeo de texto com narração
```python
from moviepy import ImageClip, TextClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips

W, H = 1080, 1920
cenas = [("fundo1.jpg", "Primeira ideia"), ("fundo2.jpg", "Segunda ideia")]
narracao = AudioFileClip("narracao.mp3")
dur = narracao.duration / len(cenas)

clips = []
for img, txt in cenas:
    bg = ImageClip(img).resized(height=H).cropped(x_center=None, width=W).with_duration(dur)
    t = (TextClip(text=txt, font_size=90, color="white", stroke_color="black", stroke_width=4,
                  method="caption", size=(W - 160, None), font="DejaVuSans-Bold.ttf")
         .with_position("center").with_duration(dur))
    clips.append(CompositeVideoClip([bg, t], size=(W, H)))

final = concatenate_videoclips(clips).with_audio(narracao)
final.write_videofile("saida.mp4", fps=30, codec="libx264", audio_codec="aac")
```
Em MoviePy 1.x os métodos são `set_duration`, `resize`, `set_position`, `set_audio` e `TextClip(txt, fontsize=...)`. Verifique a versão com `pip show moviepy`.

## Vídeos em lote a partir de CSV
1. Crie um template (função Python ou composição Remotion) que recebe os campos.
2. Leia o CSV e gere um arquivo por linha: `saida/<id>_<slug>.mp4`.
3. Renderize primeiro **um** para o usuário aprovar, depois o lote.

## Remotion (React)
```bash
npx create-video@latest meu-video   # escolha o template
cd meu-video && npm run dev         # preview no navegador (Remotion Studio)
npx remotion render <CompositionId> out/video.mp4 --props='{"titulo":"Olá"}'
```
Conceitos: `<Composition>` define id, duração (`durationInFrames`), fps e tamanho; `useCurrentFrame()` + `interpolate()`/`spring()` animam; `<Sequence from={30}>` posiciona elementos no tempo; `<Audio>`, `<Img>`, `<OffthreadVideo>` para mídia. Para lotes use `--props` ou `@remotion/renderer` (`renderMedia`) em script Node.
Observação: Remotion exige licença paga para empresas acima de certo porte — avise o usuário se for uso comercial.

## Narração (TTS)
Se o usuário não tiver narração gravada, ofereça um TTS (ex.: `edge-tts`: `edge-tts --voice pt-BR-FranciscaNeural --text "..." --write-media narracao.mp3`, ou uma API que ele já use). Depois gere legendas com a skill `legendas`.

## Checklist antes de entregar
- Duração bate com o roteiro (skill `roteiro-video`)?
- Resolução/fps corretos para a plataforma, `yuv420p`, áudio normalizado (-14 LUFS)?
- Abra 2–3 frames (`ffmpeg -ss X -i saida.mp4 -frames:v 1 f.jpg`) e confira visualmente.
