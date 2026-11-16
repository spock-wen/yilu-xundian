#!/usr/bin/env python3
"""Subset Noto Serif SC fonts for Yilu Xundian CJMP app."""

import argparse
import json
import sys
from pathlib import Path
from fontTools import subset
from fontTools.ttLib import TTFont

EXTRA_SYMBOLS = "·、，。：；！？「」『』（）《》〈〉—…×✓·０１２３４５６７８９"


def get_repo_root() -> Path:
    script_dir = Path(__file__).resolve().parent
    for p in script_dir.parents:
        if (p / "entry").is_dir():
            return p
    return script_dir.parents[1]


def collect_charset(repo: Path) -> set[str]:
    chars: set[str] = set()

    # 1) Non-ASCII characters in $REPO/app-ios-android/lib/**/*.cj
    lib_dir = repo / "app-ios-android/lib"
    if lib_dir.exists():
        for cj_file in sorted(lib_dir.rglob("*.cj")):
            try:
                text = cj_file.read_text(encoding="utf-8")
                for ch in text:
                    if ord(ch) > 127:
                        chars.add(ch)
            except Exception as e:
                print(f"Warning reading {cj_file}: {e}", file=sys.stderr)

    # 2) Every character of every "name" in engine/shared/levels/levels.json
    levels_file = repo / "engine/shared/levels/levels.json"
    if levels_file.exists():
        with open(levels_file, "r", encoding="utf-8") as f:
            levels_data = json.load(f)
        for lv in levels_data:
            name = lv.get("name", "")
            for ch in name:
                chars.add(ch)
    else:
        print(f"Warning: {levels_file} not found", file=sys.stderr)

    # 3) All printable ASCII 0x20-0x7E
    for code in range(0x20, 0x7F):
        chars.add(chr(code))

    # 4) Extra punctuation and symbols
    for ch in EXTRA_SYMBOLS:
        chars.add(ch)

    return chars


def subset_one_font(input_path: Path, output_path: Path, text: str) -> None:
    options = subset.Options()
    options.glyph_names = False
    options.hinting = False

    font = subset.load_font(str(input_path), options)
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(text=text)
    subsetter.subset(font)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subset.save_font(font, str(output_path), options)


def run_check(repo: Path, chars: set[str]) -> int:
    fonts_dir = repo / "app-ios-android/fonts"
    regular_path = fonts_dir / "YiluSerif-Regular.otf"
    bold_path = fonts_dir / "YiluSerif-Bold.otf"

    missing_files = []
    if not regular_path.exists():
        missing_files.append(str(regular_path.relative_to(repo)))
    if not bold_path.exists():
        missing_files.append(str(bold_path.relative_to(repo)))

    if missing_files:
        print(f"FAIL: Subset font file(s) missing: {', '.join(missing_files)}", file=sys.stderr)
        return 1

    regular_font = TTFont(str(regular_path))
    bold_font = TTFont(str(bold_path))
    cmap_reg = regular_font.getBestCmap()
    cmap_bold = bold_font.getBestCmap()

    missing_reg = [ch for ch in sorted(chars) if ord(ch) not in cmap_reg]
    missing_bold = [ch for ch in sorted(chars) if ord(ch) not in cmap_bold]

    has_error = False
    if missing_reg:
        has_error = True
        print(f"FAIL: YiluSerif-Regular.otf missing {len(missing_reg)} characters: {''.join(missing_reg)}", file=sys.stderr)
    if missing_bold:
        has_error = True
        print(f"FAIL: YiluSerif-Bold.otf missing {len(missing_bold)} characters: {''.join(missing_bold)}", file=sys.stderr)

    if has_error:
        return 1

    print(f"PASS: All {len(chars)} characters present in subset fonts.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Subset Noto Serif SC fonts for Yilu Xundian.")
    parser.add_argument("--regular", help="Path to NotoSerifSC-Regular.otf")
    parser.add_argument("--bold", help="Path to NotoSerifSC-Bold.otf")
    parser.add_argument("--check", action="store_true", help="Check existing subset fonts against charset")

    args = parser.parse_args()

    repo = get_repo_root()
    charset = collect_charset(repo)
    sorted_chars = sorted(charset)
    charset_text = "".join(sorted_chars)

    if args.check:
        return run_check(repo, charset)

    if not args.regular or not args.bold:
        parser.error("Both --regular and --bold are required when not using --check")

    reg_in = Path(args.regular)
    bold_in = Path(args.bold)
    if not reg_in.is_file():
        print(f"Error: regular font file not found: {reg_in}", file=sys.stderr)
        return 1
    if not bold_in.is_file():
        print(f"Error: bold font file not found: {bold_in}", file=sys.stderr)
        return 1

    fonts_dir = repo / "app-ios-android/fonts"
    fonts_dir.mkdir(parents=True, exist_ok=True)

    reg_out = fonts_dir / "YiluSerif-Regular.otf"
    bold_out = fonts_dir / "YiluSerif-Bold.otf"
    charset_out = fonts_dir / "charset.txt"

    subset_one_font(reg_in, reg_out, charset_text)
    subset_one_font(bold_in, bold_out, charset_text)
    charset_out.write_text(charset_text + "\n", encoding="utf-8")

    print(f"Charset count: {len(sorted_chars)} characters")
    print(f"Wrote {charset_out.relative_to(repo)}")
    print(f"Wrote {reg_out.relative_to(repo)} ({reg_out.stat().st_size} bytes)")
    print(f"Wrote {bold_out.relative_to(repo)} ({bold_out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
