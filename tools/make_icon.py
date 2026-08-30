#!/usr/bin/env python3
"""Write a placeholder post-road app icon (paper / ink / muted path)."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
W = H = 192
PAPER = (0xF3, 0xEB, 0xDD, 255)
INK = (0x2B, 0x2A, 0x27, 255)
PATH = (0x4A, 0x66, 0x70, 255)


def png_rgba(pixels: list[list[tuple[int, int, int, int]]]) -> bytes:
    raw = b""
    for row in pixels:
        raw += b"\x00" + b"".join(bytes(px) for px in row)
    compressed = zlib.compress(raw, 9)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")


def disk(px: list, cx: int, cy: int, r: int, fill: tuple[int, int, int, int], ring: tuple[int, int, int, int]) -> None:
    for y in range(max(0, cy - r - 2), min(H, cy + r + 3)):
        for x in range(max(0, cx - r - 2), min(W, cx + r + 3)):
            d2 = (x - cx) * (x - cx) + (y - cy) * (y - cy)
            if d2 <= (r - 3) * (r - 3):
                px[y][x] = fill
            elif d2 <= r * r:
                px[y][x] = ring


def stroke_line(px: list, x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int, int], width: int) -> None:
    steps = max(abs(x1 - x0), abs(y1 - y0), 1)
    for i in range(steps + 1):
        x = x0 + (x1 - x0) * i // steps
        y = y0 + (y1 - y0) * i // steps
        for dy in range(-width, width + 1):
            for dx in range(-width, width + 1):
                if dx * dx + dy * dy <= width * width:
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < W and 0 <= yy < H:
                        px[yy][xx] = color


def main() -> None:
    px = [[PAPER for _ in range(W)] for _ in range(H)]
    stroke_line(px, 36, 150, 70, 110, PATH, 5)
    stroke_line(px, 70, 110, 120, 88, PATH, 5)
    stroke_line(px, 120, 88, 156, 48, PATH, 5)
    disk(px, 40, 148, 18, PAPER, INK)
    disk(px, 154, 46, 18, PAPER, INK)
    paths = [
        ROOT / "AppScope/resources/base/media/app_icon.png",
        ROOT / "entry/src/main/resources/base/media/app_icon.png",
    ]
    data = png_rgba(px)
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
