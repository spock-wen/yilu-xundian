#!/usr/bin/env python3
"""check_fonts.py — strict per-family glyph coverage check for CJMP (Keels 0.2.2).

Families:
  serif     → fonts/YiluSerif-Regular.otf + fonts/YiluSerif-Bold.otf
  sans      → fonts/YiluSans-Regular.ttf  + fonts/YiluSans-Medium.ttf
  sans-bold → fonts/YiluSans-Bold.ttf

Font family markers parsed from mobile/cjmp/lib/*.cj:
  serif     ← serifFamily()    / serifBoldFamily()  / Theme.serif  / Theme.serifBold
  sans      ← sansFamily()     / sansMediumFamily() / Theme.sansRegular / Theme.sansMedium
              / Theme.sans     (alias for sansRegular)
  sans-bold ← sansBoldFamily() / Theme.sansBold

For each Text(<arg>) or Button(<arg>) call, the chained .fontFamily(...) that
follows (before the next component call) determines which family that text
belongs to.  Text/Button without a fontFamily → "NO_FAMILY file:line" error.

If <arg> is a plain string literal, its literal characters are collected.
If it contains ${...} interpolations or is a non-literal expression, the
"dynamic data charset" is added to that family:
  • every character in every string literal in mobile/cjmp/lib/chapter.cj
  • every "name" value in mobile/shared/levels/levels.json
  • digits 0-9 + all printable ASCII (0x20-0x7E)

Writes charset files:
  mobile/cjmp/fonts/charset_serif.txt
  mobile/cjmp/fonts/charset_sans.txt

Exit codes:
  0 — all checks pass
  1 — one or more failures (missing file, missing glyph, NO_FAMILY)
  3 — --pending-sans-ok and BOTH sans files are missing (serif still must pass)
"""

import argparse
import json
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Repo root discovery
# ---------------------------------------------------------------------------

def get_repo_root() -> Path:
    script_dir = Path(__file__).resolve().parent
    for p in script_dir.parents:
        if (p / "entry").is_dir():
            return p
    return script_dir.parents[2]


REPO = get_repo_root()
LIB_DIR = REPO / "mobile" / "cjmp" / "lib"
FONTS_DIR = REPO / "mobile" / "cjmp" / "fonts"
LEVELS_JSON = REPO / "mobile" / "shared" / "levels" / "levels.json"
CHAPTER_CJ = LIB_DIR / "chapter.cj"

SERIF_FILES = [
    FONTS_DIR / "YiluSerif-Regular.otf",
    FONTS_DIR / "YiluSerif-Bold.otf",
]
SANS_FILES = [
    FONTS_DIR / "YiluSans-Regular.ttf",
    FONTS_DIR / "YiluSans-Medium.ttf",
]
SANS_BOLD_FILE = FONTS_DIR / "YiluSans-Bold.ttf"

# ---------------------------------------------------------------------------
# Dynamic data charset
# ---------------------------------------------------------------------------

def build_dynamic_charset() -> set:
    """Characters that must be covered by any family that renders dynamic data."""
    chars = set()

    # All string literals in chapter.cj
    if CHAPTER_CJ.exists():
        text = CHAPTER_CJ.read_text(encoding="utf-8")
        for literal in re.findall(r'"([^"]*)"', text):
            chars.update(literal)

    # All "name" values in levels.json
    if LEVELS_JSON.exists():
        levels = json.loads(LEVELS_JSON.read_text(encoding="utf-8"))
        for lv in levels:
            chars.update(lv.get("name", ""))

    # Digits 0-9
    chars.update("0123456789")

    # Printable ASCII 0x20-0x7E
    for code in range(0x20, 0x7F):
        chars.add(chr(code))

    return chars


# ---------------------------------------------------------------------------
# Font family classification
# ---------------------------------------------------------------------------

def classify_family(marker: str) -> str:
    """Return 'serif', 'sans', or 'sans-bold' for a recognised fontFamily marker, else ''.

    Marker may be a bare method call ('serifFamily()', possibly prefixed
    with 'this.') or a Theme constant ('Theme.serif' etc.).
    """
    marker = re.sub(r'\s+', '', marker)
    marker = re.sub(r'^this\.', '', marker)

    method = re.fullmatch(r'([A-Za-z]+)\(\)', marker)
    if method:
        name = method.group(1)
        if name in ("serifFamily", "serifBoldFamily"):
            return "serif"
        if name in ("sansFamily", "sansMediumFamily"):
            return "sans"
        if name == "sansBoldFamily":
            return "sans-bold"
        return ""

    if marker in ("Theme.serif", "Theme.serifBold"):
        return "serif"
    if marker in ("Theme.sansRegular", "Theme.sansMedium", "Theme.sans"):
        return "sans"
    if marker == "Theme.sansBold":
        return "sans-bold"
    return ""


# ---------------------------------------------------------------------------
# Parse .cj source files
# ---------------------------------------------------------------------------

# Pattern for component calls: Text(...) or Button(...)
# We look for the opening call and then scan for .fontFamily(...) before the next
# top-level component call.
#
# Strategy: line-by-line state machine.
#   State: looking for Text/Button call.
#   When found, record the arg and the location, then scan subsequent lines for
#   .fontFamily(..) before encountering a new component-level call.
#
# "Component-level call": a line whose first non-whitespace chars form an
#   identifier immediately followed by `(` or `{`, at indentation <= the
#   Text/Button line's indentation.

# Regex pieces
RE_TEXT_OR_BUTTON = re.compile(
    r'^(?P<indent>\s*)(?P<comp>Text|Button)\s*\((?P<arg>.*)\)\s*$'
)
RE_FONT_FAMILY_OPEN = re.compile(r'\.fontFamily\s*\(')


def extract_font_family_marker(line: str) -> str:
    """Return the argument of .fontFamily(...) (paren-balanced) on this line, else ''."""
    m = RE_FONT_FAMILY_OPEN.search(line)
    if not m:
        return ""
    i = m.end()
    depth = 1
    start = i
    while i < len(line) and depth > 0:
        ch = line[i]
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        i += 1
    if depth != 0:
        return ""
    return line[start:i - 1].strip()
RE_COMPONENT_CALL = re.compile(r'^\s*[A-Za-z_][A-Za-z0-9_]*\s*[\({]')

# String literal: starts and ends with ", no unescaped "
RE_STRING_LITERAL = re.compile(r'^"(?P<body>[^"]*)"$')
RE_HAS_INTERPOLATION = re.compile(r'\$\{')


def parse_text_uses(cj_text: str, filepath: str) -> list:
    """Return list of (family, chars_or_None, lineno, arg_text) tuples.

    chars_or_None is None when dynamic charset must be added.
    family is 'serif' or 'sans', or 'MISSING' when no fontFamily found.
    """
    lines = cj_text.splitlines()
    results = []
    n = len(lines)
    i = 0
    while i < n:
        line = lines[i]
        m = RE_TEXT_OR_BUTTON.match(line)
        if m:
            indent = len(m.group("indent"))
            arg_text = m.group("arg").strip()
            lineno = i + 1

            # Determine literal chars
            sm = RE_STRING_LITERAL.match(arg_text)
            if sm and not RE_HAS_INTERPOLATION.search(sm.group("body")):
                literal_chars = set(sm.group("body"))
                is_dynamic = False
            else:
                literal_chars = None
                is_dynamic = True

            # Look ahead for .fontFamily(...) before next component call
            family = "MISSING"
            j = i + 1
            while j < n:
                next_line = lines[j]
                # Is this a fontFamily modifier?
                raw_marker = extract_font_family_marker(next_line)
                if raw_marker:
                    family = classify_family(raw_marker)
                    if not family:
                        # Unknown marker — treat as unknown
                        family = "MISSING"
                    break
                # Is this a new component call at same or lower indent?
                cm = RE_COMPONENT_CALL.match(next_line)
                if cm:
                    this_indent = len(next_line) - len(next_line.lstrip())
                    if this_indent <= indent and next_line.strip():
                        # New sibling/parent component — no fontFamily found
                        break
                # Stop at closing braces at or below our indent
                stripped = next_line.strip()
                if stripped in ("}", "}{", "})") or stripped.startswith("}"):
                    this_indent = len(next_line) - len(next_line.lstrip())
                    if this_indent <= indent:
                        break
                j += 1

            results.append({
                "family": family,
                "literal_chars": literal_chars,
                "is_dynamic": is_dynamic,
                "lineno": lineno,
                "arg_text": arg_text,
                "file": filepath,
            })
        i += 1
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Strict per-family glyph coverage check for CJMP fonts."
    )
    parser.add_argument(
        "--pending-sans-ok",
        action="store_true",
        help="If BOTH sans files are missing, print a warning and exit 3 instead of 1; serif checks still run.",
    )
    args = parser.parse_args()

    # ------------------------------------------------------------------
    # Check font file existence
    # ------------------------------------------------------------------
    serif_missing = [p for p in SERIF_FILES if not p.exists()]
    sans_missing = [p for p in SANS_FILES if not p.exists()]
    sans_bold_missing = [SANS_BOLD_FILE] if not SANS_BOLD_FILE.exists() else []

    all_sans_missing = len(sans_missing) == len(SANS_FILES)
    any_sans_missing = len(sans_missing) > 0

    failures = []

    if serif_missing:
        for p in serif_missing:
            msg = f"MISSING_FONT_FILE {p.relative_to(REPO)}"
            print(msg)
            failures.append(msg)

    if any_sans_missing:
        if args.pending_sans_ok:
            print("--pending-sans-ok ignored: sans fonts are delivered")
        for p in sans_missing:
            msg = f"MISSING_FONT_FILE {p.relative_to(REPO)}"
            print(msg)
            failures.append(msg)

    if sans_bold_missing:
        for p in sans_bold_missing:
            msg = f"MISSING_FONT_FILE {p.relative_to(REPO)}"
            print(msg)
            failures.append(msg)

    # ------------------------------------------------------------------
    # Parse all .cj files for Text/Button + fontFamily
    # ------------------------------------------------------------------
    all_uses = []
    for cj_file in sorted(LIB_DIR.glob("*.cj")):
        try:
            text = cj_file.read_text(encoding="utf-8")
        except Exception as e:
            print(f"Warning: could not read {cj_file}: {e}", file=sys.stderr)
            continue
        uses = parse_text_uses(text, str(cj_file.relative_to(REPO)))
        all_uses.extend(uses)

    # ------------------------------------------------------------------
    # Build required charsets per family
    # ------------------------------------------------------------------
    dynamic_charset = None  # lazy

    def get_dynamic():
        nonlocal dynamic_charset
        if dynamic_charset is None:
            dynamic_charset = build_dynamic_charset()
        return dynamic_charset

    required = {"serif": set(), "sans": set()}
    sans_bold_chars = set()
    no_family_errors = []

    for use in all_uses:
        fam = use["family"]
        if fam == "MISSING":
            no_family_errors.append(use)
            continue
        if fam == "sans-bold":
            if use["is_dynamic"] or use["literal_chars"] is None:
                msg = f"DYNAMIC_SANS_BOLD_NOT_ALLOWED {use['file']}:{use['lineno']} — dynamic expression not allowed with sans-bold: {use['arg_text'][:60]}"
                print(msg)
                failures.append(msg)
            else:
                sans_bold_chars.update(use["literal_chars"])
            continue
        if fam not in required:
            continue
        if use["is_dynamic"] or use["literal_chars"] is None:
            required[fam].update(get_dynamic())
        else:
            # Ignore whitespace-only contributions (but keep the chars)
            required[fam].update(use["literal_chars"])

    # Report NO_FAMILY errors
    for use in no_family_errors:
        msg = f"NO_FAMILY {use['file']}:{use['lineno']} — {use['arg_text'][:60]}"
        print(msg)
        failures.append(msg)

    # ------------------------------------------------------------------
    # Write charset files (always, even on failure)
    # ------------------------------------------------------------------
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    for fam_name, charset in required.items():
        out_path = FONTS_DIR / f"charset_{fam_name}.txt"
        sorted_chars = sorted(charset)
        out_path.write_text("".join(sorted_chars) + "\n", encoding="utf-8")
        print(f"Wrote {out_path.relative_to(REPO)} ({len(sorted_chars)} chars)")

    # ------------------------------------------------------------------
    # Glyph coverage checks
    # ------------------------------------------------------------------
    try:
        from fontTools.ttLib import TTFont
        have_fonttools = True
    except ImportError:
        print("ERROR: fontTools is not installed — cannot verify glyph coverage. "
              "Install it with: python3 -m pip install fonttools")
        return 1

    def check_family_coverage(fam_name: str, font_files: list, charset: set) -> list:
        """Return list of (char, codepoint) for missing glyphs."""
        missing = []
        if not charset:
            return missing
        for font_path in font_files:
            if not font_path.exists():
                continue
            font = TTFont(str(font_path), lazy=True)
            cmap = font.getBestCmap() or {}
            font_missing = sorted(
                (ch for ch in charset if ord(ch) not in cmap),
                key=lambda c: ord(c)
            )
            if font_missing:
                rel = font_path.relative_to(REPO)
                print(f"FAIL: {rel} missing {len(font_missing)} chars: "
                      f"{''.join(font_missing[:40])}"
                      f"{'...' if len(font_missing) > 40 else ''}")
                # Print up to 3 file:line uses per missing char
                for ch in font_missing:
                    uses_for_ch = [
                        u for u in all_uses
                        if u["family"] == fam_name and (
                            (u["literal_chars"] is not None and ch in u["literal_chars"])
                            or u["is_dynamic"]
                        )
                    ][:3]
                    locs = ", ".join(f"{u['file']}:{u['lineno']}" for u in uses_for_ch)
                    print(f"  U+{ord(ch):04X} {repr(ch)} used at: {locs}")
                missing.extend((ch, ord(ch)) for ch in font_missing)
        return missing

    if have_fonttools:
        # Serif (always check if files present)
        if not serif_missing:
            serif_count = len(required["serif"])
            print(f"serif: {serif_count} required chars")
            serif_bad = check_family_coverage("serif", SERIF_FILES, required["serif"])
            if serif_bad:
                failures.append(f"serif coverage: {len(serif_bad)} missing glyphs")
            else:
                print(f"serif: PASS ({serif_count} chars covered)")
        else:
            names = ", ".join(p.name for p in serif_missing)
            print(f"serif: NOT CHECKED (missing font file: {names})")

        # Sans (check unless both missing and pending-sans-ok)
        if True:
            sans_count = len(required["sans"])
            print(f"sans: {sans_count} required chars")
            if sans_missing:
                names = ", ".join(p.name for p in sans_missing)
                print(f"sans: NOT CHECKED (missing font file: {names})")
            else:
                sans_bad = check_family_coverage("sans", SANS_FILES, required["sans"])
                if sans_bad:
                    failures.append(f"sans coverage: {len(sans_bad)} missing glyphs")
                else:
                    print(f"sans: PASS ({sans_count} chars covered)")

        # Sans-Bold (check YiluSans-Bold.ttf coverage for literal chars)
        if not sans_bold_missing:
            sans_bold_count = len(sans_bold_chars)
            print(f"sans-bold: {sans_bold_count} required chars")
            sans_bold_bad = check_family_coverage("sans-bold", [SANS_BOLD_FILE], sans_bold_chars)
            if sans_bold_bad:
                failures.append(f"sans-bold coverage: {len(sans_bold_bad)} missing glyphs")
            else:
                print(f"sans-bold: PASS ({sans_bold_count} chars covered)")
        else:
            names = SANS_BOLD_FILE.name
            print(f"sans-bold: NOT CHECKED (missing font file: {names})")

    # ------------------------------------------------------------------
    # Result
    # ------------------------------------------------------------------
    if failures:
        print(f"\nFAIL: {len(failures)} issue(s) found.", file=sys.stderr)
        return 1

    if args.pending_sans_ok:
        print("--pending-sans-ok ignored: sans fonts are delivered")

    print("\ncheck_fonts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
