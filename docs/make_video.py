"""Render launch/video/warrant-demo.mp4 (1920x1080) and a high-quality GIF from the same scripts.

Reuses the terminal renderer in make_demo_gif.py at 2x scale; ffmpeg comes from the
imageio-ffmpeg pip package. Content is the same real outputs as the README GIFs.
    pip install imageio-ffmpeg && python docs/make_video.py
"""
import subprocess
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

import make_demo_gif as R
from make_feature_gifs import REVIEW, WATCH

S = 2  # scale: 960x540 logical -> 1920x1080
R.W, R.H, R.PAD, R.LH = 960 * S, 540 * S, 28 * S, 22 * S
R.MONO = ImageFont.truetype(str(R.FONT_DIR / "consola.ttf"), 16 * S)
R.MONO_B = ImageFont.truetype(str(R.FONT_DIR / "consolab.ttf"), 16 * S)
R.CAP = ImageFont.truetype(str(R.FONT_DIR / "seguisb.ttf"), 19 * S)
FPS = 30
OUT = Path(__file__).resolve().parent.parent / "launch" / "video"


def card(title: str, sub: str, foot: str = "") -> Image.Image:
    im = Image.new("RGB", (R.W, R.H), R.BG)
    d = ImageDraw.Draw(im)
    big = ImageFont.truetype(str(R.FONT_DIR / "seguisb.ttf"), 64 * S // 2 * 2)
    mid = ImageFont.truetype(str(R.FONT_DIR / "segoeui.ttf"), 30 * S)
    d.text((R.W // 2, R.H // 2 - 70 * S), title, font=big, fill=R.FG, anchor="mm")
    d.text((R.W // 2, R.H // 2 + 10 * S), sub, font=mid, fill=R.MUT, anchor="mm")
    if foot:
        d.text((R.W // 2, R.H // 2 + 90 * S), foot, font=R.MONO_B, fill=R.GREEN, anchor="mm")
    return im


def main():
    seq: list[tuple[Image.Image, int]] = []
    seq.append((card("warrant", "The referee that reads every paper you cite.",
                     "Claude Code  ·  Codex  ·  OpenCode"), 2600))
    seq.append((card("1. Numbers need a source", "Every number in the agent's reply must trace to a real run."), 1800))
    for script in (R.SCRIPT,):
        f, d = R.render(script)
        seq += list(zip(f, d))
    seq.append((card("2. Papers get read", "Cited papers checked. Quotes verified. p-values recomputed."), 1800))
    f, d = R.render(REVIEW)
    seq += list(zip(f, d))
    seq.append((card("3. Live runs get watched", "Zero-token sentinels on your training logs."), 1800))
    f, d = R.render(WATCH)
    seq += list(zip(f, d))
    seq.append((card("no source, no number.", "github.com/ItsShreyamHere/warrant",
                     "/plugin marketplace add ItsShreyamHere/warrant"), 3500))

    OUT.mkdir(parents=True, exist_ok=True)
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    mp4 = OUT / "warrant-demo.mp4"
    p = subprocess.Popen([ff, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{R.W}x{R.H}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "slow",
                          "-movflags", "+faststart", str(mp4)], stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    for im, ms in seq:
        raw = im.convert("RGB").tobytes()
        for _ in range(max(1, round(ms / 1000 * FPS))):
            p.stdin.write(raw)
    p.stdin.close()
    p.wait()
    gif = OUT / "warrant-demo-hq.gif"
    subprocess.run([ff, "-y", "-i", str(mp4), "-vf",
                    "fps=12,scale=1280:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=none",
                    str(gif)], stderr=subprocess.DEVNULL, check=True)
    secs = sum(ms for _, ms in seq) / 1000
    print(f"wrote {mp4} ({mp4.stat().st_size // 1024} KB, {secs:.0f}s) and {gif} ({gif.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
