"""Render docs/demo.gif: Claude invents a number and a DOI, warrant blocks, Claude runs it for real.

The block message is the real Stop-hook text for this reply. The run output matches
docs/demo/results.md. Captions (bottom bar) are narration, not tool output.

    python docs/make_demo_gif.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H, PAD, LH = 960, 400, 28, 22
FONT_DIR = Path("C:/Windows/Fonts")  # shortcut: Windows fonts; pass other paths on macOS/Linux
MONO = ImageFont.truetype(str(FONT_DIR / "consola.ttf"), 16)
MONO_B = ImageFont.truetype(str(FONT_DIR / "consolab.ttf"), 16)
CAP = ImageFont.truetype(str(FONT_DIR / "seguisb.ttf"), 19)

BG, FG, MUT = (20, 20, 19), (236, 235, 230), (150, 148, 142)
GREEN, RED, AMBER, ORANGE = (95, 198, 143), (242, 135, 124), (227, 181, 79), (217, 119, 87)
RED_BG, GREEN_BG = (58, 26, 23), (22, 50, 34)

# script: (kind, text, color) ; kinds: line (instant), type (typed), pause
SCRIPT = [
    ("cap", "Claude is asked to write up an experiment", None),
    ("line", "> How much does label smoothing help on our setup? Write it up.", MUT),
    ("blank",),
    ("type", "● Label smoothing improves accuracy to 0.874 vs 0.809 baseline,", FG),
    ("type", "  consistent with Müller et al. (doi 10.48550/arXiv.1906.99999).", FG),
    ("pause", 10),
    ("cap", "warrant checks the reply with code before it reaches you", None),
    ("box", ["[warrant] Your reply has numbers that no command output, file, or",
             "record entry produced: 0.874, 0.809 and citations that do not",
             "resolve or do not match: doi:10.48550/arXiv.1906.99999 (DOI does not",
             "exist). Run the command that produces each number, fix or remove",
             "the citation, or label a number as an estimate with '~'."], RED),
    ("pause", 26),
    ("clear",),
    ("cap", "So Claude actually runs the experiment", None),
    ("line", "● Bash(python train.py --smoothing 0.1 --seeds 3)", ORANGE),
    ("type", "  seed=0 smoothing=0.1 val_acc=0.8127", MUT),
    ("type", "  seed=1 smoothing=0.1 val_acc=0.8064", MUT),
    ("type", "  seed=2 smoothing=0.1 val_acc=0.8179", MUT),
    ("type", "  baseline seed=0..2 val_acc=0.7952 0.7988 0.7931", MUT),
    ("blank",),
    ("cap", "...and rewrites it. Every number now traces to that run.", None),
    ("rich", [("● Label smoothing reached ", FG), ("0.812", GREEN), (" mean val acc over 3 seeds", FG)]),
    ("rich", [("  vs ", FG), ("0.796", GREEN), (" baseline, a gain of ", FG), ("0.016", GREEN),
              (". Müller et al. study when this", FG)]),
    ("rich", [("  helps (", FG), ("arXiv:1906.02629", GREEN), ("); their numbers were not reproduced.", FG)]),
    ("pause", 8),
    ("cap", "no source, no number.   github.com/ItsShreyamHere/warrant", None),
    ("pause", 40),
]


def frame(lines, caption):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    # window chrome
    d.rounded_rectangle((0, 0, W - 1, H - 1), 14, outline=(44, 43, 41), width=2)
    for i, c in enumerate([(237, 106, 94), (245, 191, 79), (98, 197, 84)]):
        d.ellipse((18 + i * 22, 16, 30 + i * 22, 28), fill=c)
    d.text((W // 2, 22), "claude  ·  warrant on", font=MONO, fill=MUT, anchor="mm")
    y = 56
    for item in lines:
        if item[0] == "box":
            rows = item[1]
            h = len(rows) * LH + 16
            d.rounded_rectangle((PAD - 6, y - 4, W - PAD, y - 4 + h), 8, fill=RED_BG, outline=RED)
            for r in rows:
                d.text((PAD + 6, y + 4), r, font=MONO, fill=RED)
                y += LH
            y += 22
        elif item[0] == "rich":
            x = PAD
            for text, col in item[1]:
                f = MONO_B if col == GREEN else MONO
                if col == GREEN:
                    w = d.textlength(text, font=f)
                    d.rounded_rectangle((x - 2, y - 1, x + w + 2, y + LH - 3), 4, fill=GREEN_BG)
                d.text((x, y), text, font=f, fill=col)
                x += d.textlength(text, font=f)
            y += LH
        else:
            d.text((PAD, y), item[1], font=MONO, fill=item[2])
            y += LH
    # caption bar (narration)
    d.rectangle((0, H - 58, W, H), fill=(30, 30, 28))
    d.text((W // 2, H - 29), caption, font=CAP, fill=AMBER if "no source" not in caption else GREEN, anchor="mm")
    return im


def main(script=None, name="demo.gif"):
    script = script or SCRIPT
    frames, durations, lines, caption = [], [], [], ""

    def snap(ms):
        frames.append(frame(lines, caption))
        durations.append(ms)

    for step in script:
        kind = step[0]
        if kind == "cap":
            caption = step[1]
        elif kind == "line":
            lines.append(("t", step[1], step[2]))
            snap(450)
        elif kind == "blank":
            lines.append(("t", "", FG))
        elif kind == "type":
            text, col = step[1], step[2]
            lines.append(("t", "", col))
            for i in range(0, len(text) + 1, 4):
                lines[-1] = ("t", text[:i], col)
                snap(28)
            lines[-1] = ("t", text, col)
            snap(120)
        elif kind == "rich":
            lines.append(("rich", step[1]))
            snap(500)
        elif kind == "box":
            lines.append(("box", step[1]))
            snap(300)
        elif kind == "pause":
            snap(step[1] * 100)
        elif kind == "clear":
            lines = []
    out = Path(__file__).with_name(name)
    pal = [f.convert("P", palette=Image.ADAPTIVE, colors=64) for f in frames]
    pal[0].save(out, save_all=True, append_images=pal[1:], duration=durations, loop=0, optimize=True)
    print(f"wrote {out} ({out.stat().st_size // 1024} KB, {len(frames)} frames)")


if __name__ == "__main__":
    main()
