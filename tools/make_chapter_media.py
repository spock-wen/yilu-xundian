#!/usr/bin/env python3
"""Generate chapter-flow v1.3 bust / flag / skin PNGs for base/media.

Ink-line portraits + vertical flags. High-res sources so 14×36 vp thumbs
stay readable (no blur). Does not invent levels.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "entry/src/main/resources/base/media"
FONT = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
INK = (44, 42, 38, 255)
PAPER = (251, 246, 236, 255)
MUTED = (92, 87, 78, 255)

FLAGS = {
    "flag_p01_han": ((179, 60, 50), "汉"),
    "flag_p02_huang": ((228, 195, 90), "黄"),
    "flag_p03_gongsun": ((154, 167, 176), "公孙"),
    "flag_p04_yuan": ((122, 107, 50), "袁"),
    "flag_p05_liu": ((90, 108, 122), "刘"),
    "flag_p06_cao": ((72, 72, 72), "曹"),
    "flag_p07_lv": ((122, 90, 58), "吕"),
}

# role, hat style: official / cloth / helm / robe / warrior / cao / lv
BUSTS = {
    "bust_p01_cangguan": "official",
    "bust_p02_huangjin": "cloth",
    "bust_p03_gongsun": "helm",
    "bust_p04_yuanshao": "robe",
    "bust_p05_liubei": "official",
    "bust_p06_caocao": "cao",
    "bust_p07_lvbu": "lv",
}


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT, size=size)


def draw_flag(name: str, color: tuple[int, int, int], text: str) -> None:
    w, h = 56, 144
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((2, 2, w - 3, h - 3), radius=6, fill=color + (255,), outline=INK, width=3)
    fnt = font(28 if len(text) == 1 else 22)
    y = 18
    for ch in text:
        bbox = d.textbbox((0, 0), ch, font=fnt)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        d.text(((w - tw) / 2, y), ch, font=fnt, fill=INK)
        y += th + 6
    im.save(OUT / f"{name}.png")


def _face(d: ImageDraw.ImageDraw, cx: int, cy: int, r: int) -> None:
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=INK, width=4)
    d.ellipse((cx - 8, cy - 4, cx - 2, cy + 4), fill=INK)
    d.ellipse((cx + 2, cy - 4, cx + 8, cy + 4), fill=INK)
    d.arc((cx - 10, cy + 2, cx + 10, cy + 16), 20, 160, fill=INK, width=3)


def draw_bust(name: str, style: str) -> None:
    w, h = 216, 288
    im = Image.new("RGBA", (w, h), PAPER)
    d = ImageDraw.Draw(im)
    cx, cy, r = 108, 128, 46
    # shoulders
    d.arc((20, 168, 196, 300), 200, 340, fill=INK, width=5)
    d.line((36, 230, 180, 230), fill=INK, width=4)
    if style == "official":
        d.polygon([(cx - 40, cy - 44), (cx, cy - 88), (cx + 40, cy - 44)], outline=INK, width=4)
        d.rectangle((cx - 18, cy - 56, cx + 18, cy - 44), outline=INK, width=3)
    elif style == "cloth":
        d.arc((cx - 42, cy - 70, cx + 42, cy - 10), 180, 360, fill=INK, width=5)
        d.line((cx - 36, cy - 36, cx - 50, cy - 8), fill=INK, width=4)
        d.line((cx + 36, cy - 36, cx + 50, cy - 8), fill=INK, width=4)
    elif style == "helm":
        d.polygon([(cx - 48, cy - 28), (cx - 36, cy - 78), (cx + 36, cy - 78), (cx + 48, cy - 28)], outline=INK, width=4)
        d.line((cx, cy - 78, cx, cy - 96), fill=INK, width=4)
        d.ellipse((cx - 6, cy - 104, cx + 6, cy - 92), outline=INK, width=3)
    elif style == "robe":
        d.arc((cx - 44, cy - 72, cx + 44, cy - 8), 200, 340, fill=INK, width=4)
        d.line((cx - 20, 40, cx + 20, 40), fill=INK, width=4)
    elif style == "cao":
        d.rectangle((cx - 42, cy - 70, cx + 42, cy - 28), outline=INK, width=4)
        d.line((cx - 42, cy - 50, cx + 42, cy - 50), fill=INK, width=3)
    elif style == "lv":
        d.polygon([(cx - 20, cy - 44), (cx, cy - 100), (cx + 20, cy - 44)], outline=INK, width=4)
        d.line((cx - 48, cy - 20, cx + 48, cy - 20), fill=INK, width=4)
    _face(d, cx, cy, r)
    # collar
    d.line((cx - 16, cy + r - 4, cx, cy + r + 22), fill=INK, width=3)
    d.line((cx + 16, cy + r - 4, cx, cy + r + 22), fill=INK, width=3)
    im.save(OUT / f"{name}.png")


def draw_zhuo_skin() -> None:
    w, h = 720, 192
    im = Image.new("RGBA", (w, h), (243, 232, 214, 255))
    d = ImageDraw.Draw(im)
    d.arc((40, 90, 260, 260), 200, 340, fill=MUTED, width=3)
    d.arc((220, 70, 520, 260), 200, 340, fill=MUTED, width=3)
    d.arc((480, 100, 700, 260), 200, 340, fill=MUTED, width=3)
    # city gate
    d.rectangle((300, 70, 420, 160), outline=INK, width=4)
    d.polygon([(290, 70), (360, 28), (430, 70)], outline=INK, width=4)
    d.arc((330, 110, 390, 170), 180, 360, fill=INK, width=4)
    d.line((360, 70, 360, 110), fill=INK, width=3)
    im.save(OUT / "skin_01_zhuojun_v91.png")


def draw_ping_skin() -> None:
    w, h = 720, 192
    im = Image.new("RGBA", (w, h), (231, 235, 216, 255))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((180, 28, 540, 164), radius=10, outline=INK, width=4)
    d.line((360, 28, 360, 164), fill=INK, width=3)
    d.arc((200, 48, 340, 144), 210, 330, fill=MUTED, width=3)
    d.arc((380, 48, 520, 144), 210, 330, fill=MUTED, width=3)
    d.polygon([(348, 88), (360, 48), (372, 88)], fill=INK)
    d.line((360, 88, 360, 128), fill=INK, width=4)
    im.save(OUT / "skin_02_pingyuan_v91.png")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (color, text) in FLAGS.items():
        draw_flag(name, color, text)
    for name, style in BUSTS.items():
        draw_bust(name, style)
    draw_zhuo_skin()
    draw_ping_skin()
    print(f"wrote {len(FLAGS) + len(BUSTS) + 2} media files under {OUT}")


if __name__ == "__main__":
    main()
