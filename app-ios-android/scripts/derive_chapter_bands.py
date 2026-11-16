#!/usr/bin/env python3
"""derive_chapter_bands.py — derive chapter band composite PNGs from chapter-skins-v9 mocks.

Crop box: (0, 246, 1080, 546) -> 1080x300 RGBA PNG.
Mapping:
  03-xuzhou-v91.png   -> band_xuzhou_v91.png
  04-lvbu-v91.png     -> band_lvbu_v91.png
  05-touyuan-v91.png  -> band_touyuan_v91.png
  06-jingzhou-v91.png -> band_jingzhou_v91.png
  07-chibi-v91.png    -> band_chibi_v91.png
  08-rushu-v91.png    -> band_rushu_v91.png
  09-hanzhong-v91.png -> band_hanzhong_v91.png
  10-beifa-v91.png    -> band_beifa_v91.png

Chapters 0 (band_zhuojun_v91) and 1 (band_pingyuan_v91) are kept untouched.
"""

import argparse
import os
import sys
from pathlib import Path
from PIL import Image

CROP_BOX = (0, 246, 1080, 546)

CHAPTER_BANDS = [
    ("03-xuzhou-v91.png", "band_xuzhou_v91.png"),
    ("04-lvbu-v91.png", "band_lvbu_v91.png"),
    ("05-touyuan-v91.png", "band_touyuan_v91.png"),
    ("06-jingzhou-v91.png", "band_jingzhou_v91.png"),
    ("07-chibi-v91.png", "band_chibi_v91.png"),
    ("08-rushu-v91.png", "band_rushu_v91.png"),
    ("09-hanzhong-v91.png", "band_hanzhong_v91.png"),
    ("10-beifa-v91.png", "band_beifa_v91.png"),
]


def derive_bands(source_dir: Path, out_dir: Path) -> None:
    if not source_dir.is_dir():
        raise FileNotFoundError(f"Source directory does not exist: {source_dir}")

    out_dir.mkdir(parents=True, exist_ok=True)

    for src_name, dst_name in CHAPTER_BANDS:
        src_path = source_dir / src_name
        if not src_path.is_file():
            raise FileNotFoundError(f"Missing source mockup: {src_path}")

        with Image.open(src_path) as im:
            crop = im.crop(CROP_BOX).convert("RGBA")
            dst_path = out_dir / dst_name
            crop.save(dst_path, format="PNG")
            print(f"Derived {dst_name} ({crop.size[0]}x{crop.size[1]} {crop.mode}) from {src_name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Derive chapter band PNGs from chapter-skins-v9 mocks.")
    parser.add_argument(
        "source_dir",
        type=Path,
        help="Path to source mockups directory containing 03-xuzhou-v91.png .. 10-beifa-v91.png",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Output media directory (default: entry/src/main/resources/base/media)",
    )

    args = parser.parse_args()

    if args.out_dir is None:
        repo_root = Path(__file__).resolve().parents[2]
        out_dir = repo_root / "entry" / "src" / "main" / "resources" / "base" / "media"
    else:
        out_dir = args.out_dir

    try:
        derive_bands(args.source_dir, out_dir)
        print("All bands derived successfully.")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
