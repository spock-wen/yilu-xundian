#!/usr/bin/env python3
"""Lint dynamic board-label literals (board_mech.cj / board.cj) against font cmaps.

check_fonts.py only covers the static charset; index.cj renders boardNextLabels etc. via
ForEach Text(...) with sansFamily()/serif, so literals inside BoardLabel/centerLabel calls
are invisible to it. This script extracts them and verifies every char is in the cmaps of
all fonts of the assigned family (sans -> YiluSans-*, serif -> YiluSerif-*).
"""
import os
import re
import sys

CJMP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(CJMP, "lib")
FONTS = os.path.join(CJMP, "fonts")
FAMILIES = {
    "sans": ["YiluSans-Regular.ttf", "YiluSans-Medium.ttf"],
    "serif": ["YiluSerif-Regular.otf", "YiluSerif-Bold.otf"],
}
STR_RE = re.compile(r'"((?:[^"\\\n]|\\.)*)"')
CALL_RE = re.compile(r'\b(?:BoardLabel|centerLabel)\s*\(')


def _scan_string(text, j):
    """j at opening quote; return index just past closing quote."""
    j += 1
    while j < len(text) and text[j] != '"':
        j += 2 if text[j] == '\\' else 1
    return j + 1


def call_literals(text):
    """(lineno, literal) for every "..." inside a BoardLabel(...)/centerLabel(...) call."""
    out = []
    for m in CALL_RE.finditer(text):
        i, depth = m.end() - 1, 0
        while i < len(text):
            if text[i] == '"':
                i = _scan_string(text, i)
                continue
            if text[i] == '(':
                depth += 1
            elif text[i] == ')':
                depth -= 1
                if depth == 0:
                    break
            i += 1
        seg = text[m.start():i]
        for sm in STR_RE.finditer(seg):
            if '${' in sm.group(1):
                continue
            out.append((text.count('\n', 0, m.start() + sm.start()) + 1, sm.group(1)))
    return out


def func_literals(text, name):
    """(lineno, literal) for all "..." in the body of func <name>(...)."""
    m = re.search(r'func\s+%s\s*\(' % re.escape(name), text)
    if not m or '{' not in text[m.end():]:
        sys.exit("check_board_labels: func %s not found" % name)
    i, depth = text.index('{', m.end()), 0
    while i < len(text):
        if text[i] == '"':
            i = _scan_string(text, i)
            continue
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                break
        i += 1
    seg = text[m.start():i]
    return [(text.count('\n', 0, m.start() + sm.start()) + 1, sm.group(1))
            for sm in STR_RE.finditer(seg) if '${' not in sm.group(1)]


def main():
    mech = open(os.path.join(LIB, "board_mech.cj"), encoding="utf-8").read()
    board = open(os.path.join(LIB, "board.cj"), encoding="utf-8").read()
    labels = []  # (family, file, lineno, literal)
    for lineno, lit in call_literals(mech):
        labels.append(("sans", "board_mech.cj", lineno, lit))
    for lineno, lit in func_literals(board, "buildBoardNextLabels"):
        labels.append(("sans", "board.cj", lineno, lit))
    for lineno, lit in func_literals(board, "buildBoardParityLabels"):
        labels.append(("serif", "board.cj", lineno, lit))

    cmaps = {}
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        sys.exit("check_board_labels: fontTools not importable via python3 (set YILU_PY)")
    for fam, files in FAMILIES.items():
        for fn in files:
            cmaps[(fam, fn)] = TTFont(os.path.join(FONTS, fn)).getBestCmap() or {}

    failed, seen, n = [], set(), 0
    for fam, src, lineno, lit in labels:
        for ch in lit:
            if ch.isspace() or (fam, ch) in seen:
                continue
            seen.add((fam, ch))
            n += 1
            missing = [fn for fn in FAMILIES[fam] if ord(ch) not in cmaps[(fam, fn)]]
            if missing:
                failed.append((fam, ch, src, lineno))
                print("FAIL %s %r from %s:%d" % (fam, ch, src, lineno))
            else:
                print("PASS %s %r" % (fam, ch))
    for fam, ch, src, lineno in failed:
        print("MISSING %s %s from %s:%d" % (fam, ch, src, lineno))
    if failed:
        sys.exit(1)
    print("check_board_labels: PASS (%d chars)" % n)


if __name__ == "__main__":
    main()
