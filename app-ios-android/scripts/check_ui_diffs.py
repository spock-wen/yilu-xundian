#!/usr/bin/env python3
"""Static UI diffs and rule checker for Yilu CJMP (lib/index.cj, lib/chapter.cj, etc.).

Checks:
  a) index.cj has no .borderRadius before .border (check_border_radius 0 violations)
  b) dessertIds() in chapter.cj has 10 IDs matching boards-locked, isDessert() has no '== 4'
  c) lib/*.cj has no '当前已通'; chapter.cj centralizes all-clear copy in class SummaryCopy
     (literal '驿路全通' only inside SummaryCopy); board_selftest/main.cj has required footer
     literal. Once index.cj wires the summary card (references SummaryCopy, J12b), index.cj
     must not contain the literals '驿路全通'/'十章皆通'/Text("全通") outside that wiring.
  d) index.cj has no Text("通")/Text("锁"), no rawImg("card_05".."10"), has lockIcon & checkCircleIcon
  e) index.cj Text("章节") has no .border, Text("驿程") has screen=3 onClick
  f) dessertTag builder state==1 uses Theme.paperShade without .border, h18/fs11/r3 verified
  g) modifier chains: Theme.qingDeep slip r4, rowBorderW r8, cardBorderW r10, vermillion toast r4,
     doUndo/doClear r8 with border width 1.2
  h) (e) fallback toast: index.cj references toastIsOutsideTray / rejectPlace.step == 4 and the
     '// toast fallback (e)' Text appears before the board Scroll (border before borderRadius)
  i) (B7) summary card: @Builder summaryCard wired via SummaryCopy.summaryVisible, copy routed
     through SummaryCopy (no 驿路全通/十章皆通/Text("全通") literals in index.cj), geometry via
     SummaryGeom, border before borderRadius inside the builder
  j) (J13) chapter list footer: index.cj references chapterListFooterLines, single
     Text(this.chapterListFooter()) removed
  k) (J18) Theme.sansBold / sansBoldFamily() in lib/*.cj only at home screen Text('章节')
     (exactly 1 .fontFamily(this.sansBoldFamily())), YiluSans-Bold.ttf sha256 prefix 7e46ee679e9d
  l) (J19) index.cj footer Text width avail+1 and maxLines(1), chapter.cj footerSlack
  m) (J20) StationRowGeom in chapter.cj; index.cj screen 3 references global constants,
     screen 5 references chapter constants, old r18/18pt patterns removed, border order maintained;
     (J22) locked rows place the lock icon via StationRowGeom.lockPadRight
  o) (J26) r8 primary buttons (开始传书 home / 下一驿 win popup): rendered as container rows
     (Row { Text(...) } with .borderRadius(8), Theme.primaryH, .onClick), never bare Button(
     without .type(ButtonType.Normal) — Button defaults to a capsule shape that ignores
     .borderRadius; likewise any Button( chain carrying .borderRadius( without
     .type(ButtonType.Normal) is a violation
  p) (J26b) yicheng scroll content top whitespace: SummaryGeom.gapAbove()==12 applied as the
     Scroll content Column's .padding(top: SummaryGeom.gapAbove()) (both all-clear and non-cleared
     states, per B5/B7 previews' vp_top = topbar + 12); summary card keeps only the bottom margin
     gapBelow()-8.0 (card bottom to first group header = 12 with parent Column(space: 8));
     YichengScrollGeom.contentTopPad documents that the scroll offset formula is unchanged
  w) build_body_no_let_var: func build() body has no let/var before root container
     or at top level (depth 1), modifier closures permitted; verified against
     cec0712 (PASS) and efb4503 (FAIL)
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
CJMP_DIR = os.path.dirname(SCRIPTS_DIR)
REPO_ROOT = os.path.dirname(CJMP_DIR)

# Ensure check_border_radius is importable
sys.path.insert(0, SCRIPTS_DIR)
from check_border_radius import split_chains, check_source


def _extract_brace_body(text, start_pos):
    """Extract contents inside matching { ... } starting at or after start_pos."""
    brace_open, brace_close = _brace_span(text, start_pos)
    return text[brace_open + 1:brace_close]


def _brace_span(text, start_pos):
    """Return (open, close) indices of the matching { ... } at or after start_pos."""
    brace_open = text.index('{', start_pos)
    depth = 0
    end = brace_open
    for idx in range(brace_open, len(text)):
        if text[idx] == '{':
            depth += 1
        elif text[idx] == '}':
            depth -= 1
            if depth == 0:
                end = idx
                break
    return brace_open, end


def check_a(lines, name="index.cj"):
    """a) index.cj has no borderRadius before border."""
    violations, _, _ = check_source("\n".join(lines), filename=name, check_anchors=False)
    if violations:
        return False, f"{len(violations)} violation(s):\n    " + "\n    ".join(violations)
    return True, "0 borderRadius-before-border violations in index.cj"


def check_b(chapter_cj_text, boards_locked_dir):
    """b) dessert count = 10, matches boards-locked, isDessert clean."""
    m_func = re.search(r'func\s+dessertIds\s*\([^)]*\)', chapter_cj_text)
    if not m_func:
        return False, "func dessertIds() not found in chapter.cj"
    body = _extract_brace_body(chapter_cj_text, m_func.end())

    m_arr = re.search(r'\[([\s\S]*?)\]', body)
    if not m_arr:
        return False, "no array literal [...] found in dessertIds() body"
    extracted_ids = [int(x) for x in re.findall(r'\b\d+\b', m_arr.group(1))]

    if len(extracted_ids) != 10:
        return False, f"dessertIds() returned {len(extracted_ids)} ids, expected 10: {extracted_ids}"

    if not os.path.isdir(boards_locked_dir):
        return False, f"boards-locked directory not found at {boards_locked_dir}"

    def sort_key(fn):
        m = re.match(r"^ch(\d+)_", fn)
        return int(m.group(1)) if m else 999

    locked_files = sorted(
        [f for f in os.listdir(boards_locked_dir) if f.startswith("ch") and f.endswith(".json")],
        key=sort_key,
    )
    if len(locked_files) != 10:
        return False, f"expected 10 chapter files in boards-locked, found {len(locked_files)}"

    expected_ids = []
    total_locked = 0
    for ch_idx, fn in enumerate(locked_files):
        fpath = os.path.join(boards_locked_dir, fn)
        with open(fpath, "r", encoding="utf-8") as jf:
            data = json.load(jf)
        boards = data.get("boards", [])
        for i, b in enumerate(boards):
            if b.get("dessert") is True:
                total_locked += 1
                expected_ids.append(ch_idx * 10 + i)

    if total_locked != 10:
        return False, f"boards-locked total dessert=true count is {total_locked}, expected 10"

    if set(extracted_ids) != set(expected_ids):
        return False, f"dessertIds {extracted_ids} != expected {expected_ids}"

    m_is_dessert = re.search(r'func\s+isDessert\s*\([^)]*\)', chapter_cj_text)
    if not m_is_dessert:
        return False, "func isDessert() not found in chapter.cj"
    is_dessert_body = _extract_brace_body(chapter_cj_text, m_is_dessert.end())
    if "== 4" in is_dessert_body:
        return False, "isDessert() still contains hardcoded '== 4'"

    return True, f"10 dessert levels match boards-locked {expected_ids}, isDessert clean"


def check_c(lib_dir, board_selftest_main_path, chapter_cj_path=None, index_cj_path=None):
    """c) No '当前已通' in lib/*.cj; all-clear copy centralized in SummaryCopy; literals present."""
    found_violations = []
    if os.path.isdir(lib_dir):
        for fn in sorted(os.listdir(lib_dir)):
            if fn.endswith(".cj"):
                p = os.path.join(lib_dir, fn)
                with open(p, "r", encoding="utf-8") as f:
                    content = f.read()
                if "当前已通" in content:
                    found_violations.append(f"{fn} contains prohibited substring '当前已通'")

    if found_violations:
        return False, "; ".join(found_violations)

    ch_path = chapter_cj_path or os.path.join(lib_dir, "chapter.cj")
    if not os.path.exists(ch_path):
        return False, f"chapter.cj not found at {ch_path}"
    with open(ch_path, "r", encoding="utf-8") as f:
        chapter_content = f.read()

    # All-clear summary copy (B7) must live in class SummaryCopy; the title literal
    # '驿路全通' may appear only inside SummaryCopy (yichengFooter routes through it).
    m_class = re.search(r'class\s+SummaryCopy\b', chapter_content)
    if not m_class:
        return False, "chapter.cj missing 'class SummaryCopy' (summary card copy must be centralized)"
    brace_open, brace_close = _brace_span(chapter_content, m_class.end())
    summary_body = chapter_content[brace_open:brace_close + 1]
    outside = chapter_content[:brace_open] + chapter_content[brace_close + 1:]
    if 'return "驿路全通"' not in summary_body:
        return False, "SummaryCopy must define title() returning literal '驿路全通'"
    if "驿路全通" in outside:
        return False, "literal '驿路全通' appears outside SummaryCopy in chapter.cj (copy must be centralized)"

    if not os.path.exists(board_selftest_main_path):
        return False, f"board_selftest/main.cj not found at {board_selftest_main_path}"
    with open(board_selftest_main_path, "r", encoding="utf-8") as f:
        selftest_content = f.read()
    if "已通 100 · 驿路全通" not in selftest_content:
        return False, "board_selftest/main.cj missing literal '已通 100 · 驿路全通'"

    # index.cj literal ban: enforced once the summary card is wired into index.cj
    # (J12b landed: index.cj references SummaryCopy, so the ban is active).
    if index_cj_path and os.path.exists(index_cj_path):
        with open(index_cj_path, "r", encoding="utf-8") as f:
            index_content = f.read()
        if "SummaryCopy" in index_content:
            index_issues = []
            if "驿路全通" in index_content:
                index_issues.append("contains literal '驿路全通' (use SummaryCopy.title())")
            if "十章皆通" in index_content:
                index_issues.append("contains literal '十章皆通' (use SummaryCopy.subtitle())")
            if 'Text("全通")' in index_content:
                index_issues.append('contains Text("全通")')
            if index_issues:
                return False, "index.cj: " + "; ".join(index_issues)

    return True, "no '当前已通' in lib, SummaryCopy centralizes all-clear copy, footer literal present"


def check_d(index_cj_text):
    """d) No Text('通')/Text('锁'), no rawImg('card_05'..'10'), lockIcon/checkCircleIcon present."""
    issues = []
    if 'Text("通")' in index_cj_text:
        issues.append('contains Text("通")')
    if 'Text("锁")' in index_cj_text:
        issues.append('contains Text("锁")')
    if re.search(r'rawImg\("card_(0[5-9]|10)_', index_cj_text):
        issues.append('contains rawImg("card_05".."card_10")')
    if 'lockIcon(' not in index_cj_text:
        issues.append('missing lockIcon( call')
    if 'checkCircleIcon(' not in index_cj_text:
        issues.append('missing checkCircleIcon( call')

    if issues:
        return False, "; ".join(issues)
    return True, "no text icons or large cards, lockIcon and checkCircleIcon present"


def check_e(lines):
    """e) Text('章节') chain has no .border, Text('驿程') opens via this.openYicheng() and
    func openYicheng sets this.screen = 3 (J21/J23: click goes through the entry hook)."""
    found_zhangjie = False
    for i, line in enumerate(lines):
        if 'Text("章节")' in line:
            found_zhangjie = True
            chain = []
            for j in range(i + 1, len(lines)):
                if lines[j].strip().startswith("."):
                    chain.append(lines[j])
                else:
                    break
            chain_str = "\n".join(chain)
            if ".border(" in chain_str:
                return False, f'Text("章节") on line {i + 1} has .border( in its modifier chain'

    if not found_zhangjie:
        return False, 'Text("章节") not found in index.cj'

    found_yicheng_click = False
    onclick_pattern = re.compile(r'\.onClick\s*\(\s*\{\s*event\s*=>\s*this\.openYicheng\(\)\s*\}\s*\)')
    for i, line in enumerate(lines):
        if 'Text("驿程")' in line:
            chain = []
            for j in range(i + 1, len(lines)):
                if lines[j].strip().startswith("."):
                    chain.append(lines[j])
                else:
                    break
            chain_str = "\n".join(chain)
            if onclick_pattern.search(chain_str):
                found_yicheng_click = True
                break

    if not found_yicheng_click:
        return False, 'Text("驿程") with .onClick({event => this.openYicheng()}) modifier not found'

    # func openYicheng body must set this.screen = 3
    func_start = None
    for i, line in enumerate(lines):
        if re.search(r'func\s+openYicheng\s*\(', line):
            func_start = i
            break
    if func_start is None:
        return False, 'func openYicheng not found in index.cj'

    depth = 0
    opened = False
    body_lines = []
    for j in range(func_start, len(lines)):
        depth += lines[j].count("{") - lines[j].count("}")
        if "{" in lines[j]:
            opened = True
        if opened:
            body_lines.append(lines[j])
        if opened and depth <= 0:
            break
    body = "\n".join(body_lines)
    if not re.search(r'this\.screen\s*=\s*3', body):
        return False, 'func openYicheng body does not set this.screen = 3'

    return True, 'Text("章节") has no .border, Text("驿程") opens via this.openYicheng() which sets screen=3'


def check_f(index_cj_text):
    """f) dessertTag state==1 uses Theme.paperShade without .border, dimensions verified."""
    m = re.search(r'(?:@Builder\s+)?func\s+dessertTag\s*\([^)]*\)', index_cj_text)
    if not m:
        return False, "dessertTag builder not found in index.cj"

    func_body = _extract_brace_body(index_cj_text, m.end())

    # (J20) badge font is a per-kind parameter (StationRowGeom.globalBadgeFont 12 /
    # chapterBadgeFont 11) passed by the call sites, no longer the fixed literal 11.
    for req in ("Theme.paperShade", ".height(18)", ".fontSize(font)", ".borderRadius(3)"):
        if req not in func_body:
            return False, f"dessertTag body missing {req}"

    m_state1 = re.search(r'(?:else\s+)?if\s*\(\s*state\s*==\s*1\s*\)', func_body)
    if not m_state1:
        return False, "state == 1 branch not found in dessertTag"

    state1_branch = _extract_brace_body(func_body, m_state1.end())

    if "Theme.paperShade" not in state1_branch:
        return False, "state == 1 branch does not contain Theme.paperShade"
    if ".border(" in state1_branch:
        return False, "state == 1 branch must not contain .border("

    return True, "dessertTag state==1 branch uses Theme.paperShade without .border, dimensions verified"


def check_g(lines):
    """g) borderRadius values for slip(4), row(8), card(10), toast(4), undo/clear(8 w1.2)."""
    qing_chains = []
    row_chains = []
    card_chains = []
    toast_chains = []
    undo_chains = []

    for start, chain in split_chains(lines):
        txt = "\n".join(chain)
        m_rad = re.search(r'\.borderRadius\s*\(\s*(\d+)', txt)
        rad = int(m_rad.group(1)) if m_rad else None

        # 1. Theme.qingDeep slip: .border(width: 1.2, color: Theme.qingDeep)
        if re.search(r'\.border\s*\([^)]*Theme\.qingDeep', txt) and "1.2" in txt:
            qing_chains.append((start, rad, txt))

        # 2. rowBorderW
        if "rowBorderW(" in txt:
            row_chains.append((start, rad, txt))

        # 3. cardBorderW
        if "cardBorderW(" in txt:
            card_chains.append((start, rad, txt))

        # 4. Theme.vermillion border toast (the summary-card seal borders use SummaryGeom
        #    seal widths and radii 4/2 by design — their order is checked in i), not g)
        if re.search(r'\.border\s*\([^)]*Theme\.vermillion', txt) and \
                not re.search(r'SummaryGeom\.seal(Frame|Inner)W', txt):
            toast_chains.append((start, rad, txt))

        # 5. doUndo() / doClear()
        if "doUndo()" in txt or "doClear()" in txt:
            has_w1_2 = bool(re.search(r'\.border\s*\([^)]*width:\s*1\.2', txt))
            undo_chains.append((start, rad, has_w1_2, txt))

    errors = []

    # Check 1: qingDeep slip
    if not qing_chains:
        errors.append("missing Theme.qingDeep slip chain with .border(width: 1.2, color: Theme.qingDeep)")
    else:
        for start, rad, _ in qing_chains:
            if rad != 4:
                errors.append(f"Theme.qingDeep slip chain (line {start}) radius is {rad}, expected 4")

    # Check 2: rowBorderW
    if not row_chains:
        errors.append("missing chain with rowBorderW(")
    else:
        for start, rad, _ in row_chains:
            if rad != 8:
                errors.append(f"rowBorderW chain (line {start}) radius is {rad}, expected 8")

    # Check 3: cardBorderW
    if not card_chains:
        errors.append("missing chain with cardBorderW(")
    else:
        for start, rad, _ in card_chains:
            if rad != 10:
                errors.append(f"cardBorderW chain (line {start}) radius is {rad}, expected 10")

    # Check 4: vermillion toast
    if not toast_chains:
        errors.append("missing Theme.vermillion toast chain")
    else:
        for start, rad, _ in toast_chains:
            if rad != 4:
                errors.append(f"vermillion toast chain (line {start}) radius is {rad}, expected 4")

    # Check 5: doUndo() / doClear()
    has_undo = any("doUndo()" in txt for _, _, _, txt in undo_chains)
    has_clear = any("doClear()" in txt for _, _, _, txt in undo_chains)
    if not has_undo or not has_clear:
        errors.append("missing doUndo() or doClear() chain")
    for start, rad, has_w1_2, _ in undo_chains:
        if rad != 8:
            errors.append(f"undo/clear chain (line {start}) radius is {rad}, expected 8")
        if not has_w1_2:
            errors.append(f"undo/clear chain (line {start}) border width is not 1.2")

    if errors:
        return False, "; ".join(errors)

    return True, "slip r4, rowBorderW r8, cardBorderW r10, toast r4, undo/clear r8 w1.2 verified"


def check_h(index_cj_text):
    """h) (e) fallback toast outside the tray: marker Text before board Scroll, border order kept."""
    if ("toastIsOutsideTray" not in index_cj_text) and ("rejectPlace.step == 4" not in index_cj_text):
        return False, "no toastIsOutsideTray / rejectPlace.step == 4 reference in index.cj"

    marker = index_cj_text.find("// toast fallback (e)")
    if marker < 0:
        return False, "fallback toast marker '// toast fallback (e)' not found in index.cj"

    # Board Scroll = the Scroll that owns the board stack. Earlier Scroll blocks exist on other
    # screens and this.boardCells is also assigned in helpers, so anchor on the last occurrence
    # (the board ForEach) and search backwards for the nearest 'Scroll {'.
    cells_pos = index_cj_text.rfind("this.boardCells")
    if cells_pos < 0:
        return False, "this.boardCells not found (board Scroll anchor missing)"
    board_scroll = index_cj_text.rfind("Scroll {", 0, cells_pos)
    if board_scroll < 0:
        return False, "board 'Scroll {' not found before this.boardCells"
    if marker > board_scroll:
        return False, "fallback toast marker must appear before the board 'Scroll {'"

    # The fallback Text chain (marker .. .position() ) must keep border before borderRadius.
    chain_end = index_cj_text.find(".position(", marker)
    if chain_end < 0 or chain_end > board_scroll:
        return False, "fallback toast Text chain (.position) not found before the board 'Scroll {'"
    chain = index_cj_text[marker:chain_end]
    b = chain.find(".border(")
    r = chain.find(".borderRadius(")
    if b < 0 or r < 0 or b > r:
        return False, "fallback toast chain must have .border( before .borderRadius("

    return True, "toastIsOutsideTray referenced, fallback (e) toast before board Scroll, border before borderRadius"


def check_i(index_cj_text):
    """i) (B7) summary card wired: summaryCard builder, SummaryCopy/SummaryGeom routing, order."""
    if "SummaryCopy.summaryVisible" not in index_cj_text:
        return False, "index.cj must gate the summary card with SummaryCopy.summaryVisible"
    if not re.search(r'@Builder\s+func\s+summaryCard\s*\(', index_cj_text):
        return False, "@Builder func summaryCard() not found in index.cj"

    m = re.search(r'@Builder\s+func\s+summaryCard\s*\([^)]*\)', index_cj_text)
    body = _extract_brace_body(index_cj_text, m.end())

    for req in (
        "SummaryCopy.title()",
        "SummaryCopy.subtitle(",
        "SummaryCopy.sealChars()",
        "SummaryGeom.cardH()",
        "SummaryGeom.sealSize()",
        "Float32(SummaryGeom.sealAngle())",
        "SummaryGeom.sealAlpha()",
    ):
        if req not in body:
            return False, f"summaryCard body missing {req}"

    for lit in ("驿路全通", "十章皆通"):
        if lit in index_cj_text:
            return False, f"index.cj contains literal '{lit}' (copy must live in SummaryCopy)"
    if 'Text("全通")' in index_cj_text:
        return False, 'index.cj contains Text("全通")'

    # border before borderRadius in every modifier chain inside the builder
    for start, chain in split_chains(body.splitlines()):
        txt = "\n".join(chain)
        b = txt.find(".border(")
        r = txt.find(".borderRadius(")
        if b >= 0 and r >= 0 and b > r:
            return False, f"summaryCard chain (line ~{start}) has .borderRadius before .border"

    return True, "summaryCard wired via SummaryCopy.summaryVisible, copy/geometry centralized, border before borderRadius"


def check_j(index_cj_text):
    """j) (J13) chapterListFooterLines in index.cj, single Text(this.chapterListFooter()) removed."""
    if "chapterListFooterLines" not in index_cj_text:
        return False, "index.cj missing 'chapterListFooterLines'"
    if "Text(this.chapterListFooter())" in index_cj_text:
        return False, "index.cj still contains single Text(this.chapterListFooter()) footer"
    return True, "chapterListFooterLines present and single Text(this.chapterListFooter()) removed"


def check_k(lib_dir, fonts_dir):
    """k) (J18/B5) Theme.sansBold / sansBoldFamily() in lib/*.cj only at home screen Text('章节')
    and win card Text('下一驿') (exactly 2 .fontFamily(this.sansBoldFamily())), YiluSans-Bold.ttf sha256 prefix 7e46ee679e9d."""
    bold_path = os.path.join(fonts_dir, "YiluSans-Bold.ttf")
    if not os.path.isfile(bold_path):
        return False, f"YiluSans-Bold.ttf not found at {bold_path}"

    h = hashlib.sha256()
    with open(bold_path, "rb") as f:
        h.update(f.read())
    digest = h.hexdigest()
    if not digest.startswith("7e46ee679e9d"):
        return False, f"YiluSans-Bold.ttf sha256={digest} does not start with 7e46ee679e9d"

    sans_bold_call_count = 0
    errors = []

    for fn in sorted(os.listdir(lib_dir)):
        if not fn.endswith(".cj"):
            continue
        fp = os.path.join(lib_dir, fn)
        with open(fp, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for idx, line in enumerate(lines):
            lineno = idx + 1
            if ".fontFamily(this.sansBoldFamily())" in line or ".fontFamily(sansBoldFamily())" in line:
                sans_bold_call_count += 1
                found_target = False
                for prev in range(idx - 1, max(-1, idx - 10), -1):
                    s = lines[prev].strip()
                    if s.startswith('Text('):
                        if 'Text("章节")' in s or 'Text("下一驿")' in s:
                            found_target = True
                        break
                    if s.startswith("Column") or s.startswith("Row") or s.startswith("}"):
                        break
                if not found_target:
                    errors.append(f"{fn}:{lineno} .fontFamily(this.sansBoldFamily()) not attached to Text(\"章节\") or Text(\"下一驿\")")

            if "Theme.sansBold" in line:
                is_allowed = False
                if fn == "theme.cj" and "public static const sansBold" in line:
                    is_allowed = True
                elif fn == "fonts.cj" and "Theme.sansBold" in line:
                    is_allowed = True
                elif fn == "index.cj" and "return Theme.sansBold" in line:
                    is_allowed = True
                if not is_allowed:
                    errors.append(f"{fn}:{lineno} unexpected Theme.sansBold occurrence: {line.strip()}")

            if "sansBoldFamily" in line:
                is_allowed = False
                if fn == "index.cj" and ("func sansBoldFamily" in line or "fontFamily" in line):
                    is_allowed = True
                if not is_allowed:
                    errors.append(f"{fn}:{lineno} unexpected sansBoldFamily occurrence: {line.strip()}")

    if sans_bold_call_count != 2:
        return False, f"expected exactly 2 .fontFamily(this.sansBoldFamily()), found {sans_bold_call_count}"

    if errors:
        return False, "Theme.sansBold / sansBoldFamily() violations:\n    " + "\n    ".join(errors)

    return True, f"YiluSans-Bold.ttf (7e46ee679e9d) OK, .fontFamily(this.sansBoldFamily()) exactly 2 on Text('章节') and Text('下一驿')"


def check_l(index_cj_text, chapter_cj_text):
    """l) (J19) index.cj footer Text width avail+1 and maxLines(1), chapter.cj footerSlack."""
    if "footerSlack" not in chapter_cj_text:
        return False, "chapter.cj missing 'footerSlack'"

    if "this.chapterListFooterLines" not in index_cj_text:
        return False, "index.cj missing 'this.chapterListFooterLines'"

    idx = index_cj_text.find("this.chapterListFooterLines")
    window = index_cj_text[idx:idx + 600]

    if not re.search(r'\.width\(\s*this\.winW\s*-\s*40(?:\.0)?\s*\+\s*1(?:\.0)?\s*\)', window):
        return False, "index.cj footer Text missing .width(this.winW - 40.0 + 1.0)"

    if not re.search(r'\.maxLines\(\s*1\s*\)', window):
        return False, "index.cj footer Text missing .maxLines(1)"

    return True, "footer Text width avail+1 and maxLines(1) verified, chapter.cj has footerSlack"


def check_m(index_cj_text, chapter_cj_text):
    """m) (J20) StationRowGeom in chapter.cj; index.cj screen 3 references global constants,
    screen 5 references chapter constants, old r18/18pt patterns removed, border before borderRadius.
    (J22) locked rows place the lock icon via StationRowGeom.lockPadRight."""
    if "class StationRowGeom" not in chapter_cj_text:
        return False, "chapter.cj missing 'class StationRowGeom'"

    for geom_field in ("globalRowH", "globalRingR", "globalNameFont", "chapterRowH", "chapterRingR", "chapterNameFont"):
        if geom_field not in chapter_cj_text:
            return False, f"chapter.cj StationRowGeom missing '{geom_field}'"

    # Build-block anchor: 'this.screen == N' also appears in onBackPress/playPaper helpers
    # before the build(); search screen blocks from 'func build()' onward so the full row
    # builders are inside the slice.
    build_idx = index_cj_text.find("func build()")
    if build_idx < 0:
        return False, "index.cj missing 'func build()' (screen block anchor)"

    # Screen 3 block (yicheng full list)
    s3_idx = index_cj_text.find("this.screen == 3", build_idx)
    if s3_idx < 0:
        return False, "index.cj missing 'this.screen == 3' block after func build()"
    s4_idx = index_cj_text.find("this.screen == 4", s3_idx)
    if s4_idx < 0:
        return False, "index.cj missing 'this.screen == 4' boundary"
    s3_text = index_cj_text[s3_idx:s4_idx]

    # Required StationRowGeom references in screen 3
    for req in ("StationRowGeom.globalRingD", "StationRowGeom.globalNumFont", "StationRowGeom.globalNameFont",
                "StationRowGeom.globalMetaFont", "StationRowGeom.globalRowH", "StationRowGeom.globalPadLeft",
                "StationRowGeom.globalNameGap", "StationRowGeom.globalBadgeFont"):
        if req not in s3_text:
            return False, f"index.cj screen 3 missing '{req}'"

    # (J22) locked rows position the lock icon via StationRowGeom.lockPadRight
    if "func lockPadRight" not in chapter_cj_text:
        return False, "chapter.cj StationRowGeom missing 'func lockPadRight'"
    if "StationRowGeom.lockPadRight(true, this.lockW())" not in s3_text:
        return False, "index.cj screen 3 locked row missing 'StationRowGeom.lockPadRight(true, this.lockW())'"

    # Old r18/18pt forbidden patterns in screen 3
    if "this.checkCircleIcon(36)" in s3_text:
        return False, "index.cj screen 3 still contains old 'this.checkCircleIcon(36)' (expected globalRingD 28)"
    if ".borderRadius(18)" in s3_text:
        return False, "index.cj screen 3 still contains old '.borderRadius(18)' (expected globalRingR 14)"
    if ".fontSize(18)" in s3_text:
        return False, "index.cj screen 3 still contains old '.fontSize(18)' (expected globalNameFont 20)"
    if ".margin(left: 12)" in s3_text:
        return False, "index.cj screen 3 still contains old '.margin(left: 12)' (expected globalNameGap 16)"

    # Screen 5 block (chapter levels)
    s5_idx = index_cj_text.find("this.screen == 5", build_idx)
    if s5_idx < 0:
        return False, "index.cj missing 'this.screen == 5' block after func build()"
    s6_idx = index_cj_text.find("this.screen == 6", s5_idx)
    s5_end = s6_idx if s6_idx >= 0 else len(index_cj_text)
    s5_text = index_cj_text[s5_idx:s5_end]

    # Required StationRowGeom references in screen 5
    for req in ("StationRowGeom.chapterRingD", "StationRowGeom.chapterNumFont", "StationRowGeom.chapterNameFont",
                "StationRowGeom.chapterMetaFont", "StationRowGeom.chapterRowH", "StationRowGeom.chapterPadLeft",
                "StationRowGeom.chapterNameGap", "StationRowGeom.chapterBadgeFont"):
        if req not in s5_text:
            return False, f"index.cj screen 5 missing '{req}'"

    if "StationRowGeom.lockPadRight(false, this.lockW())" not in s5_text:
        return False, "index.cj screen 5 locked row missing 'StationRowGeom.lockPadRight(false, this.lockW())'"

    if "this.checkCircleIcon(32)" in s5_text:
        return False, "index.cj screen 5 still contains old 'this.checkCircleIcon(32)' (expected chapterRingD 26)"
    if ".borderRadius(16)" in s5_text:
        return False, "index.cj screen 5 still contains old '.borderRadius(16)' (expected chapterRingR 13)"
    if ".margin(left: 10)" in s5_text:
        return False, "index.cj screen 5 still contains old '.margin(left: 10)' (expected chapterNameGap 13)"

    # Check border before borderRadius in both screen blocks
    for label, blk in (("screen 3", s3_text), ("screen 5", s5_text)):
        for start, chain in split_chains(blk.splitlines()):
            txt = "\n".join(chain)
            b = txt.find(".border(")
            r = txt.find(".borderRadius(")
            if b >= 0 and r >= 0 and b > r:
                return False, f"index.cj {label} chain has .borderRadius before .border:\n    {txt}"

    return True, "index.cj references StationRowGeom global/chapter constants, locked rows use lockPadRight, old r18/18pt patterns removed, border order maintained"


def check_n(index_cj_text, chapter_cj_text):
    """n) (J21) yicheng full-list initial scroll position: pure geometry (YichengScrollGeom +
    ChapterCatalog.yichengScrollOffset) in chapter.cj; index.cj wires a Scroller member into
    Scroll(this.yichengScroller) and calls scrollTo once on entering screen 3."""
    if "class YichengScrollGeom" not in chapter_cj_text:
        return False, "chapter.cj missing 'class YichengScrollGeom'"
    if "func yichengScrollOffset" not in chapter_cj_text:
        return False, "chapter.cj missing 'func yichengScrollOffset'"
    if "groupGap" not in chapter_cj_text:
        return False, "chapter.cj YichengScrollGeom missing 'groupGap'"

    if "let yichengScroller: Scroller = Scroller()" not in index_cj_text:
        return False, "index.cj missing 'let yichengScroller: Scroller = Scroller()'"
    if "Scroll(this.yichengScroller)" not in index_cj_text:
        return False, "index.cj missing 'Scroll(this.yichengScroller)'"
    if "yichengScroller.scrollTo(" not in index_cj_text:
        return False, "index.cj missing 'yichengScroller.scrollTo('"
    if "ChapterCatalog.yichengScrollOffset(" not in index_cj_text:
        return False, "index.cj missing 'ChapterCatalog.yichengScrollOffset('"

    # Entry hook: scrollTo must be wired to entering screen 3, not dead code
    if "this.openYicheng()" not in index_cj_text:
        return False, "index.cj missing 'this.openYicheng()' entry hook"
    if ".onClick({event => this.screen = 3})" in index_cj_text:
        return False, "index.cj still opens screen 3 directly (expected this.openYicheng())"

    return True, "yicheng scroll-to-current-chapter wired via Scroller/scrollTo, geometry in YichengScrollGeom/yichengScrollOffset"


def _button_chain(lines, i):
    """Lines of the Button( at index i plus its modifier chain (dot lines)."""
    chain = [lines[i]]
    j = i + 1
    while j < len(lines) and lines[j].strip().startswith("."):
        chain.append(lines[j])
        j += 1
    return chain, j


def _container_chain_after(index_cj_text, anchor, skip_closes=1):
    """Return the modifier chain (dot lines) of the container whose body closes right after
    the first `}` line following anchor (the container's own chain, not the anchor Text's)."""
    idx = index_cj_text.find(anchor)
    if idx < 0:
        return ""
    lines = index_cj_text[idx:].splitlines()[1:]
    chain = []
    seen_closes = 0
    for ln in lines:
        s = ln.strip()
        if seen_closes < skip_closes:
            if s == "}" or s.endswith("}"):
                seen_closes += 1
            continue
        if s.startswith("//"):
            continue
        if s.startswith("."):
            chain.append(s)
        elif chain:
            break
    return "\n".join(chain)


def check_o(index_cj_text):
    """o) (J26) r8 primary buttons must not be bare Button( (capsule ignores .borderRadius)."""
    errors = []
    lines = index_cj_text.splitlines()

    # General rule: any Button( whose modifier chain has .borderRadius( but no
    # .type(ButtonType.Normal) — borderRadius has no effect on Button's capsule shape.
    # For the two r8 primary buttons even a bare Button( without .borderRadius( is a
    # violation (spec r8; they must use the container form asserted below).
    primary_labels = {"开始传书", "下一驿"}
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith("Button("):
            chain, j = _button_chain(lines, i)
            txt = "\n".join(chain)
            has_type = ".type(ButtonType.Normal)" in txt
            m = re.match(r'Button\("([^"]+)"\)', lines[i].strip())
            is_primary = bool(m and m.group(1) in primary_labels)
            if ".borderRadius(" in txt and not has_type:
                errors.append(f"line {i + 1}: Button(...) chain has .borderRadius( but no "
                              f".type(ButtonType.Normal) — borderRadius is ineffective on Button "
                              f"(default capsule):\n    {txt}")
            elif is_primary and not has_type:
                errors.append(f'line {i + 1}: bare Button("{m.group(1)}") — Button renders a '
                              f"capsule by default, spec requires r8 container form")
            i = j
        else:
            i += 1

    # Specific rule: the two r8 primary buttons use the verified container form.
    for label, onclick in (("开始传书", "this.startPlay()"), ("下一驿", "this.nextLevel()")):
        if f'Text("{label}")' not in index_cj_text:
            errors.append(f'Text("{label}") not found (expected container-row button form)')
            continue
        chain_txt = _container_chain_after(index_cj_text, f'Text("{label}")')
        width_options = [".width(100.percent)"] if label == "开始传书" else [".width(WinGeom.btnW(this.winW))", ".width(100.percent)"]
        if not any(w in chain_txt for w in width_options):
            errors.append(f'"{label}" container chain missing {" or ".join(width_options)}')
        for req in (".height(Theme.primaryH)",
                    ".backgroundColor(Theme.qingDeep)", ".borderRadius(8)",
                    ".justifyContent(FlexAlign.Center)", f".onClick({{event => {onclick}}}"):
            if req not in chain_txt:
                errors.append(f'"{label}" container chain missing {req}')

    if errors:
        return False, "\n    ".join(errors)
    return True, ("r8 primary buttons (开始传书/下一驿) are container rows with .borderRadius(8); "
                  "no Button(...) with .borderRadius( and no .type(ButtonType.Normal)")


def _summary_geom_value(chapter_cj_text, func_name):
    """Return the Float64 literal returned by SummaryGeom.<func_name>(), or None."""
    m = re.search(r'class\s+SummaryGeom\b(?!\s*\w)', chapter_cj_text)
    if not m:
        return None
    body = _extract_brace_body(chapter_cj_text, m.end())
    fm = re.search(r'func\s+' + func_name + r'\(\)\s*:\s*Float64\s*\{\s*return\s+([0-9.]+)', body)
    return float(fm.group(1)) if fm else None


def check_p(index_cj_text, chapter_cj_text):
    """p) (J26b) yicheng scroll content top whitespace 12u to the divider (SummaryGeom.gapAbove,
    applied as padding(top:) on the Scroll content Column so both the all-clear summary card and
    the non-cleared first group header sit 12u below the divider, per B5/B7 previews); card bottom
    to the first group header stays 12 (gapBelow, parent Column(space: 8) + margin bottom
    gapBelow()-8.0); scroll offset formula unchanged (YichengScrollGeom.contentTopPad)."""
    errors = []

    # chapter.cj: gapAbove (top whitespace) and gapBelow (card -> first group header) both 12
    for name in ("gapAbove", "gapBelow"):
        v = _summary_geom_value(chapter_cj_text, name)
        if v is None:
            errors.append(f"chapter.cj SummaryGeom missing 'func {name}(): Float64' with a literal return")
        elif abs(v - 12.0) > 1e-9:
            errors.append(f"chapter.cj SummaryGeom.{name}() = {v}, expected 12.0")
    if "func contentTopPad(): Float64 { return SummaryGeom.gapAbove() }" not in chapter_cj_text:
        errors.append("chapter.cj YichengScrollGeom missing 'contentTopPad(): Float64 { return SummaryGeom.gapAbove() }'")

    # index.cj screen 3: the Scroll content Column carries the 12u top padding
    build_idx = index_cj_text.find("func build()")
    s3_idx = index_cj_text.find("this.screen == 3", build_idx if build_idx >= 0 else 0)
    s4_idx = index_cj_text.find("this.screen == 4", s3_idx)
    s3_text = index_cj_text[s3_idx:s4_idx if s4_idx > 0 else len(index_cj_text)] if s3_idx >= 0 else ""
    pad = ".padding(top: SummaryGeom.gapAbove())"
    n_pad = s3_text.count(pad)
    if n_pad != 1:
        errors.append(f"index.cj screen 3 must carry the top whitespace exactly once as '{pad}' "
                      f"on the Scroll content Column (found {n_pad})")
    if "Column(space: 8)" not in s3_text:
        errors.append("yicheng Scroll content is not 'Column(space: 8)' — "
                      "margin bottom gapBelow()-8.0 would not total 12")

    # summaryCard: card keeps the bottom margin only (the 12u above comes from the content padding)
    m = re.search(r'@Builder\s+func\s+summaryCard\s*\(', index_cj_text)
    if not m:
        errors.append("@Builder func summaryCard() not found in index.cj")
    else:
        body = _extract_brace_body(index_cj_text, m.end())
        if ".margin(bottom: SummaryGeom.gapBelow() - 8.0)" not in body:
            errors.append("summaryCard body missing '.margin(bottom: SummaryGeom.gapBelow() - 8.0)' "
                          "(card bottom to first group header = 8 Column space + 4 margin = 12)")
        body_code = "\n".join(ln for ln in body.splitlines() if not ln.strip().startswith("//"))
        if "gapAbove" in body_code:
            errors.append("summaryCard body must not reference gapAbove — the 12u top whitespace "
                          "lives on the Scroll content Column padding, not on the card (would double to 24)")
        if ".height(SummaryGeom.cardH())" not in body:
            errors.append("summaryCard body missing '.height(SummaryGeom.cardH())'")

    if errors:
        return False, "\n    ".join(errors)
    return True, ("yicheng scroll content top whitespace 12 (gapAbove, content Column padding, both states); "
                  "summary card bottom to first group header stays 12 (gapBelow, Column space 8 + margin 4); "
                  "offset formula unchanged via YichengScrollGeom.contentTopPad")


def _yicheng_geom_value(chapter_cj_text, func_name):
    """Return the Float64 literal returned by YichengScrollGeom.<func_name>(), or None."""
    m = re.search(r'class\s+YichengScrollGeom\b', chapter_cj_text)
    if not m:
        return None
    body = _extract_brace_body(chapter_cj_text, m.end())
    fm = re.search(r'func\s+' + func_name + r'\(\)\s*:\s*Float64\s*\{\s*return\s+([0-9.]+)', body)
    if fm:
        return float(fm.group(1))
    if func_name == "rowH":
        if "StationRowGeom.globalRowH" in body:
            return 64.0
    return None


def check_q(index_cj_text, chapter_cj_text):
    """q) (J32) yicheng scroll geometry alignment with designer ruling (SPEC.md B5):
    ① chapterH formula includes headerH + rowGap (8u below header) and levelCount * (rowH + rowGap);
    ② period constant 780 derived from YichengScrollGeom (40 + 8 + 10*72 + 12 = 780);
    ③ group header Row carries 4u top padding (headerPadTop 4 / headerTextShift 2) with block height 40;
    ④ old 'chapterH ... - rowGap' (levelCount - 1) formula removed."""
    errors = []

    m_geom = re.search(r'class\s+YichengScrollGeom\b', chapter_cj_text)
    if not m_geom:
        return False, "chapter.cj missing 'class YichengScrollGeom'"
    geom_body = _extract_brace_body(chapter_cj_text, m_geom.end())

    # 1. chapterH formula
    m_ch_h = re.search(r'func\s+chapterH\s*\([^)]*\)\s*:\s*Float64', geom_body)
    if not m_ch_h:
        errors.append("chapter.cj YichengScrollGeom missing 'func chapterH(levelCount: Int64): Float64'")
    else:
        ch_body = _extract_brace_body(geom_body, m_ch_h.end())
        # ④ Check that old (levelCount - 1) or - rowGap pattern is absent
        if re.search(r'levelCount\s*-\s*1', ch_body) or "- rowGap" in ch_body or "- YichengScrollGeom.rowGap" in ch_body:
            errors.append("chapterH formula still uses old 'levelCount - 1' / '- rowGap' pattern (must be levelCount * (rowH + rowGap))")
        # ① Check that chapterH contains headerH + rowGap
        if not re.search(r'headerH\s*\(\s*\)\s*\+\s*(?:YichengScrollGeom\.)?rowGap\s*\(\s*\)', ch_body):
            errors.append("chapterH formula missing 'headerH + rowGap' (8u gap below header block)")
        # ① Check that levelCount is multiplied by (rowH + rowGap)
        if not re.search(r'(?:levelCount|Float64\s*\(\s*levelCount\s*\))\s*\*\s*\(\s*(?:YichengScrollGeom\.)?rowH\s*\(\s*\)\s*\+\s*(?:YichengScrollGeom\.)?rowGap\s*\(\s*\)\s*\)', ch_body):
            errors.append("chapterH formula missing 'levelCount * (rowH + rowGap)' (each row includes 8u trailing gap)")

    # 2. Derive period 780 from YichengScrollGeom constants
    hdr_h = _yicheng_geom_value(chapter_cj_text, "headerH")
    row_h = _yicheng_geom_value(chapter_cj_text, "rowH")
    row_gap = _yicheng_geom_value(chapter_cj_text, "rowGap")
    group_gap = _yicheng_geom_value(chapter_cj_text, "groupGap")

    if hdr_h is None or abs(hdr_h - 40.0) > 1e-6:
        errors.append(f"YichengScrollGeom.headerH() expected 40.0, got {hdr_h}")
    if row_h is None or abs(row_h - 64.0) > 1e-6:
        errors.append(f"YichengScrollGeom.rowH() expected 64.0, got {row_h}")
    if row_gap is None or abs(row_gap - 8.0) > 1e-6:
        errors.append(f"YichengScrollGeom.rowGap() expected 8.0, got {row_gap}")
    if group_gap is None or abs(group_gap - 12.0) > 1e-6:
        errors.append(f"YichengScrollGeom.groupGap() expected 12.0, got {group_gap}")

    if hdr_h is not None and row_h is not None and row_gap is not None and group_gap is not None:
        chapter_10_h = hdr_h + row_gap + 10.0 * (row_h + row_gap)
        if abs(chapter_10_h - 768.0) > 1e-6:
            errors.append(f"Derived chapterH(10) {chapter_10_h} != 768.0")
        derived_period = chapter_10_h + group_gap
        if abs(derived_period - 780.0) > 1e-6:
            errors.append(f"Derived chapter period {derived_period} != 780.0")

    # Header text shift constants
    pad_top = _yicheng_geom_value(chapter_cj_text, "headerPadTop")
    if pad_top is None or abs(pad_top - 4.0) > 1e-6:
        errors.append(f"YichengScrollGeom.headerPadTop() expected 4.0, got {pad_top}")
    text_shift = _yicheng_geom_value(chapter_cj_text, "headerTextShift")
    if text_shift is None or abs(text_shift - 2.0) > 1e-6:
        errors.append(f"YichengScrollGeom.headerTextShift() expected 2.0, got {text_shift}")

    # 3. Group header block in index.cj screen 3
    build_idx = index_cj_text.find("func build()")
    s3_idx = index_cj_text.find("this.screen == 3", build_idx if build_idx >= 0 else 0)
    s4_idx = index_cj_text.find("this.screen == 4", s3_idx)
    s3_text = index_cj_text[s3_idx:s4_idx if s4_idx > 0 else len(index_cj_text)] if s3_idx >= 0 else ""

    if "this.groupIsFirst(index)" not in s3_text:
        errors.append("index.cj screen 3 missing 'this.groupIsFirst(index)' group header block")
    else:
        # Check header Row has 4u top padding (headerPadTop or literal 4)
        if not re.search(r'\.padding\s*\(\s*top\s*:\s*(?:YichengScrollGeom\.headerPadTop\(\)|4(?:\.0)?)\s*\)', s3_text):
            errors.append("group header Row missing 4u top padding (.padding(top: YichengScrollGeom.headerPadTop()) or 4)")
        # Check header block has height 40
        if not re.search(r'Column\s*\{\s*Row\b.*?\.height\s*\(\s*40\s*\)', s3_text, re.DOTALL):
            errors.append("group header container block missing '.height(40)'")
        # Check hairline is 1u at bottom
        if "Column() {}.width(100.percent).height(1).backgroundColor(" not in s3_text:
            errors.append("group header missing 1u hairline Column at bottom of block")
        # Check margin top 12 (groupGap) and bottom 8 (rowGap) on header block
        if not re.search(r'\.margin\s*\(\s*top\s*:\s*if\s*\(\s*index\s*==\s*0\s*\)\s*\{\s*0\s*\}\s*else\s*\{\s*12\s*\}\s*,\s*bottom\s*:\s*8\s*\)', s3_text):
            errors.append("group header container missing '.margin(top: if (index == 0) { 0 } else { 12 }, bottom: 8)'")

    if errors:
        return False, "\n    ".join(errors)
    return True, ("yicheng scroll geometry aligned with designer ruling: chapterH formula has headerH+rowGap "
                  "and levelCount*(rowH+rowGap); period 780 derived from YichengScrollGeom (40+8+10*72+12); "
                  "group header Row has 4u top padding (text shift 2u) and height 40 block; old (levelCount - 1) removed")


def check_r(index_cj_text):
    """r) Root padding & safe area: build() outer container is Stack, first child is root Column;
    root Column modifier chain has .padding(top: this.padTop, bottom: this.padBottom, left: this.playInset(), right: this.playInset());
    @State var padTop/padBottom initialized from Theme.safeTop()/Theme.safeBottom();
    root background is this.playPaper(); onAreaChange re-reads safeTop/safeBottom."""
    errors = []
    if not re.search(r'@State\s+var\s+padTop\s*:\s*Float64\s*=\s*Theme\.safeTop\(\)', index_cj_text):
        errors.append("padTop @State var missing or not initialized with Theme.safeTop()")
    if not re.search(r'@State\s+var\s+padBottom\s*:\s*Float64\s*=\s*Theme\.safeBottom\(\)', index_cj_text):
        errors.append("padBottom @State var missing or not initialized with Theme.safeBottom()")

    m_build = re.search(r'func\s+build\s*\(\s*\)', index_cj_text)
    if not m_build:
        return False, "func build() not found in index.cj"
    build_body = _extract_brace_body(index_cj_text, m_build.end())
    cleaned_build = "\n".join(l for l in build_body.splitlines() if not l.strip().startswith("//"))
    m_stack = re.search(r'\bStack\s*(\([^)]*\))?\s*\{', cleaned_build)
    if not m_stack:
        return False, "build() outermost container is not Stack"

    stack_content = _extract_brace_body(cleaned_build, m_stack.start())
    m_col = re.search(r'^\s*Column\s*\{', stack_content, re.MULTILINE)
    if not m_col:
        return False, "first child of outer Stack is not root Column"

    col_open, col_close = _brace_span(stack_content, m_col.start())
    root_col_chain = stack_content[col_close + 1:].split("if (this.screen == 2)")[0]

    m_pad = re.search(r'\.padding\s*\((.+?)\)\s*(?:\.|\n|\Z)', root_col_chain)
    if not m_pad:
        errors.append("root Column missing .padding(...) modifier")
    else:
        pad_args = m_pad.group(1)
        for req in ("top: this.padTop", "bottom: this.padBottom", "left: this.playInset()", "right: this.playInset()"):
            if req not in pad_args:
                errors.append(f"root Column .padding missing '{req}'")

    if ".backgroundColor(this.playPaper())" not in root_col_chain:
        errors.append("root Column missing .backgroundColor(this.playPaper())")

    if ".onAreaChange(" not in root_col_chain:
        errors.append("root Column missing .onAreaChange(...) modifier")
    else:
        if "Theme.safeTop()" not in root_col_chain or "this.padTop" not in root_col_chain:
            errors.append("onAreaChange does not re-read Theme.safeTop() into this.padTop")
        if "Theme.safeBottom()" not in root_col_chain or "this.padBottom" not in root_col_chain:
            errors.append("onAreaChange does not re-read Theme.safeBottom() into this.padBottom")

    if errors:
        return False, "; ".join(errors)
    return True, ("build() outermost Stack with root Column padding (padTop/padBottom/playInset), "
                  "@State safeTop/safeBottom, playPaper background, onAreaChange re-read verified")


def check_s(index_cj_text, theme_cj_text=None):
    """s) 5 bottom margins use Theme.bottomMargin/chipMargin:
    1. Home screen '章节·驿程' Row has Theme.bottomMargin(8.0, 0.0)
    2. Chapter screen Text(this.chapterOpenFooter()) has Theme.bottomMargin(16.0, 8.0)
    3. Yicheng full list ChapterCatalog.yichengFooter has Theme.bottomMargin(16.0, 8.0)
    4. In-chapter yicheng chapterListFooterLines footer Column has Theme.bottomMargin(16.0, 8.0)
    5. Board chips '撤销' and '重绘驿道' Rows have Theme.chipMargin()
    6. Board bottom bar Row has Theme.chipBarHeight() and not legacy Theme.bottomBar
    None of these 5 locations may use legacy 'bottom: 8' (or unadapted constants).
    theme.cj contains hasHundredths, safeBottomSet, bottomMarginOrLegacy, chipMarginOrLegacy,
    chipBarHeightOrLegacy, and Theme.bottomMargin/chipMargin/chipBarHeight route through *OrLegacy."""
    errors = []

    # 1. Home '章节·驿程' Row
    home_chain = _container_chain_after(index_cj_text, 'Text("驿程")', skip_closes=1)
    if not home_chain:
        errors.append("home '章节·驿程' Row modifier chain not found")
    else:
        if "Theme.bottomMargin(8.0, 0.0)" not in home_chain:
            errors.append("home '章节·驿程' Row missing Theme.bottomMargin(8.0, 0.0)")
        if re.search(r'bottom:\s*8(?!\.0)\b', home_chain):
            errors.append("home '章节·驿程' Row still contains legacy bottom: 8")

    # 2. Chapter page chapterOpenFooter
    ch_chain = _container_chain_after(index_cj_text, "Text(this.chapterOpenFooter())", skip_closes=0)
    if not ch_chain:
        errors.append("Text(this.chapterOpenFooter()) modifier chain not found")
    else:
        if "Theme.bottomMargin(16.0, 8.0)" not in ch_chain:
            errors.append("Text(this.chapterOpenFooter()) missing Theme.bottomMargin(16.0, 8.0)")
        if re.search(r'bottom:\s*8\b', ch_chain):
            errors.append("Text(this.chapterOpenFooter()) still contains legacy bottom: 8")

    # 3. Yicheng full list yichengFooter
    yc_chain = _container_chain_after(index_cj_text, "ChapterCatalog.yichengFooter", skip_closes=0)
    if not yc_chain:
        errors.append("Text(ChapterCatalog.yichengFooter(...)) modifier chain not found")
    else:
        if "Theme.bottomMargin(16.0, 8.0)" not in yc_chain:
            errors.append("Text(ChapterCatalog.yichengFooter(...)) missing Theme.bottomMargin(16.0, 8.0)")
        if re.search(r'bottom:\s*8\b', yc_chain):
            errors.append("Text(ChapterCatalog.yichengFooter(...)) still contains legacy bottom: 8")

    # 4. In-chapter yicheng chapterListFooterLines footer Column
    cl_chain = _container_chain_after(index_cj_text, "this.chapterListFooterLines()", skip_closes=2)
    if not cl_chain:
        errors.append("chapterListFooterLines footer Column modifier chain not found")
    else:
        if "Theme.bottomMargin(16.0, 8.0)" not in cl_chain:
            errors.append("chapterListFooterLines footer Column missing Theme.bottomMargin(16.0, 8.0)")
        if re.search(r'bottom:\s*8\b', cl_chain):
            errors.append("chapterListFooterLines footer Column still contains legacy bottom: 8")

    # 5. Board chips: '撤销' and '重绘驿道'
    for chip in ("撤销", "重绘驿道"):
        chip_chain = _container_chain_after(index_cj_text, f'Text("{chip}")', skip_closes=1)
        if not chip_chain:
            errors.append(f"chip '{chip}' Row modifier chain not found")
        else:
            if "Theme.chipMargin()" not in chip_chain:
                errors.append(f"chip '{chip}' Row missing Theme.chipMargin()")
            if re.search(r'bottom:\s*8\b', chip_chain):
                errors.append(f"chip '{chip}' Row still contains legacy bottom: 8")

    # 5b. Board bottom bar Row height
    bar_chain = _container_chain_after(index_cj_text, 'Text("重绘驿道")', skip_closes=2)
    if not bar_chain:
        errors.append("bottom bar Row modifier chain not found")
    else:
        if "Theme.chipBarHeight()" not in bar_chain:
            errors.append("bottom bar Row missing Theme.chipBarHeight()")
        if "Theme.bottomBar" in bar_chain:
            errors.append("bottom bar Row still uses legacy Theme.bottomBar")

    # 6. theme.cj assertions
    if theme_cj_text is None:
        default_theme_path = os.path.join(CJMP_DIR, "lib", "theme.cj")
        if os.path.isfile(default_theme_path):
            with open(default_theme_path, "r", encoding="utf-8") as f:
                theme_cj_text = f.read()

    if theme_cj_text is not None:
        if not re.search(r'func\s+hasHundredths\b', theme_cj_text):
            errors.append("theme.cj missing func hasHundredths")
        if not re.search(r'func\s+safeBottomSet\b', theme_cj_text):
            errors.append("theme.cj missing Theme.safeBottomSet")
        if not re.search(r'func\s+bottomMarginOrLegacy\b', theme_cj_text):
            errors.append("theme.cj missing func bottomMarginOrLegacy")
        if not re.search(r'func\s+chipMarginOrLegacy\b', theme_cj_text):
            errors.append("theme.cj missing func chipMarginOrLegacy")
        if not re.search(r'func\s+chipBarHeightOrLegacy\b', theme_cj_text):
            errors.append("theme.cj missing func chipBarHeightOrLegacy")

        m_bm = re.search(r'public\s+static\s+func\s+bottomMargin\s*\([^)]*\)[^{]*\{([\s\S]*?)\}', theme_cj_text)
        if not m_bm or "bottomMarginOrLegacy" not in m_bm.group(1):
            errors.append("Theme.bottomMargin does not route via bottomMarginOrLegacy")

        m_cm = re.search(r'public\s+static\s+func\s+chipMargin\s*\([^)]*\)[^{]*\{([\s\S]*?)\}', theme_cj_text)
        if not m_cm or "chipMarginOrLegacy" not in m_cm.group(1):
            errors.append("Theme.chipMargin does not route via chipMarginOrLegacy")

        m_cbh = re.search(r'public\s+static\s+func\s+chipBarHeight\s*\([^)]*\)[^{]*\{([\s\S]*?)\}', theme_cj_text)
        if not m_cbh or "chipBarHeightOrLegacy" not in m_cbh.group(1):
            errors.append("Theme.chipBarHeight does not route via chipBarHeightOrLegacy")
    else:
        errors.append("theme.cj not found or provided")

    if errors:
        return False, "; ".join(errors)
    return True, ("5 bottom margins use Theme.bottomMargin(8.0, 0.0)/(16.0, 8.0), Theme.chipMargin() and Theme.chipBarHeight(), "
                  "theme.cj has hasHundredths/safeBottomSet/*OrLegacy routing, legacy bottom: 8 removed")


def check_t(index_cj_text, theme_cj_text):
    """t) Win popup scrim/card layers and styling: theme.cj contains winScrim (0x802C2A26)
    and sealInk (0xEB9B3A2F); screen == 2 branch removed from root Column; outer Stack order:
    root Column -> mask (winScrim, maskTop) -> shadow (paperShade, dx/dy) -> card (Stack, WinGeom
    geometry, border before borderRadius(4)) -> hairline overlay; mask has NO onClick; board Column
    visibility contains screen == 1 || screen == 2; leaveBoard() intact; gold line width comes from
    WinGeom.roadTitleWidth; seal has transparent background (no Theme.vermillion), double frames with
    WinGeom outer/inner constants and border before borderRadius, sealInk, sealGlyphFont(),
    sealGlyphPitch(); card uses WinGeom.* (no bare magic numbers 28/360/62/124/154/288/17/19/6.9/16.3/4.8/29/48/67/0.55
    in code); shadow avoids .shadow(); seal rotate explicit Float32; 下一驿 uses sansBoldFamily."""
    errors = []

    # 1. theme.cj winScrim and sealInk
    if not re.search(r'winScrim\s*:\s*Int64\s*=\s*0x802C2A26\b', theme_cj_text):
        errors.append("theme.cj missing winScrim = 0x802C2A26")
    if not re.search(r'sealInk\s*:\s*Int64\s*=\s*0xEB9B3A2F\b', theme_cj_text):
        errors.append("theme.cj missing sealInk = 0xEB9B3A2F")

    # 2. index.cj build() root Column vs win block
    m_build = re.search(r'func\s+build\s*\(\s*\)', index_cj_text)
    if not m_build:
        return False, "func build() not found in index.cj"
    build_body = _extract_brace_body(index_cj_text, m_build.end())
    cleaned_build = "\n".join(l for l in build_body.splitlines() if not l.strip().startswith("//"))
    m_stack = re.search(r'\bStack\s*(\([^)]*\))?\s*\{', cleaned_build)
    if not m_stack:
        return False, "build() outermost container is not Stack"
    stack_content = _extract_brace_body(cleaned_build, m_stack.start())

    m_col = re.search(r'^\s*Column\s*\{', stack_content, re.MULTILINE)
    if not m_col:
        return False, "root Column not found in outer Stack"
    col_open, col_close = _brace_span(stack_content, m_col.start())
    root_col_body = stack_content[col_open + 1:col_close]

    if "else if (this.screen == 2)" in root_col_body or "else if (screen == 2)" in root_col_body or "if (this.screen == 2)" in root_col_body:
        errors.append("root Column still contains screen == 2 branch (must be outside root Column)")

    # Outer stack remainder after root Column
    outer_after_root = stack_content[col_close + 1:]
    m_win_block = re.search(r'if\s*\((?:this\.)?screen\s*==\s*2\)\s*\{', outer_after_root)
    if not m_win_block:
        errors.append("outer Stack missing if (this.screen == 2) block outside root Column")
        return False, "; ".join(errors)

    win_body = _extract_brace_body(outer_after_root, m_win_block.start())

    # Layer order: mask -> shadow -> card -> hairline
    # Mask
    pos_mask = win_body.find("Theme.winScrim")
    if pos_mask < 0 or "WinGeom.maskTop" not in win_body:
        errors.append("win block missing mask with Theme.winScrim and WinGeom.maskTop")
    # Check mask has no onClick
    mask_chain = win_body[pos_mask:pos_mask + 300]
    if ".onClick(" in mask_chain:
        errors.append("mask has unexpected .onClick(...)")

    # Shadow
    pos_shadow = win_body.find("WinGeom.cardShadowDx")
    if pos_shadow < 0 or "Theme.paperShade" not in win_body:
        errors.append("win block missing card shadow with Theme.paperShade")
    if ".shadow(" in win_body:
        errors.append("win block uses .shadow() (hard shadow required)")

    # Card
    pos_card = win_body.find("WinGeom.cardTop")
    if pos_card < 0 or "WinGeom.cardW" not in win_body or "WinGeom.cardH" not in win_body:
        errors.append("win block missing card with WinGeom geometry")

    # Hairline
    pos_hairline = win_body.find("WinGeom.hairlineY")
    if pos_hairline < 0 or "Theme.paperLine" not in win_body:
        errors.append("win block missing hairline overlay at WinGeom.hairlineY")

    if not (pos_mask < pos_shadow < pos_card < pos_hairline):
        errors.append("outer Stack layers not in expected order (mask < shadow < card < hairline)")

    # Board column visibility: screen == 1 || this.screen == 2
    if not re.search(r'\.visibility\s*\(\s*if\s*\((?:this\.)?screen\s*==\s*1\s*\|\|\s*(?:this\.)?screen\s*==\s*2\)', index_cj_text):
        errors.append("board Column visibility missing screen == 1 || this.screen == 2")

    # Board leaveBoard()
    if "this.leaveBoard()" not in index_cj_text:
        errors.append("board topbar back button missing this.leaveBoard()")

    # Gold line width comes from WinGeom.roadTitleWidth(
    if "WinGeom.roadTitleWidth(" not in win_body:
        errors.append("gold line width must come from WinGeom.roadTitleWidth(...)")

    # Card border before borderRadius(4)
    idx_card_w = win_body.find(".width(WinGeom.cardW(this.winW))\n            .height(WinGeom.cardH())\n            .backgroundColor(Theme.whitePaper)")
    if idx_card_w < 0:
        idx_card_w = win_body.find(".backgroundColor(Theme.whitePaper)")
    if idx_card_w >= 0:
        card_chain = win_body[idx_card_w:idx_card_w + 300]
        pos_b = card_chain.find(".border(")
        pos_r = card_chain.find(".borderRadius(4)")
        if pos_b < 0 or pos_r < 0 or pos_b > pos_r:
            errors.append("card modifier chain must place .border before .borderRadius(4)")
    else:
        errors.append("card modifier chain not identified in win body")

    # Seal transparent background: must NOT have backgroundColor(Theme.vermillion)
    if "backgroundColor(Theme.vermillion)" in win_body:
        errors.append("seal must have transparent background, found backgroundColor(Theme.vermillion)")

    # Seal outer and inner frames WinGeom constants and border before borderRadius
    if "WinGeom.sealOuterStroke" not in win_body or "WinGeom.sealOuterRadius" not in win_body:
        errors.append("seal missing outer frame WinGeom.sealOuterStroke/sealOuterRadius")
    if "WinGeom.sealInnerStroke" not in win_body or "WinGeom.sealInnerRadius" not in win_body:
        errors.append("seal missing inner frame WinGeom.sealInnerStroke/sealInnerRadius")

    for stroke_call, radius_call in [
        ("WinGeom.sealOuterStroke", "WinGeom.sealOuterRadius"),
        ("WinGeom.sealInnerStroke", "WinGeom.sealInnerRadius"),
    ]:
        pos_s = win_body.find(stroke_call)
        pos_r = win_body.find(radius_call)
        if pos_s >= 0 and pos_r >= 0 and pos_s > pos_r:
            errors.append(f"seal frame with {stroke_call} must place .border before .borderRadius")

    # Seal glyphs font, pitch, color
    if "WinGeom.sealGlyphFont()" not in win_body:
        errors.append("seal glyphs missing WinGeom.sealGlyphFont()")
    if "WinGeom.sealGlyphPitch()" not in win_body:
        errors.append("seal glyphs missing WinGeom.sealGlyphPitch()")
    if "Theme.sealInk" not in win_body:
        errors.append("seal missing Theme.sealInk")

    # Seal explicit Float32
    if not re.search(r'\.rotate\s*\(\s*angle\s*:\s*Float32\s*\(\s*WinGeom\.sealAngle\(\)\s*\)\s*\)', win_body):
        errors.append("seal rotate angle missing explicit Float32(WinGeom.sealAngle())")

    # 下一驿 sansBoldFamily
    if 'Text("下一驿")' not in win_body or "sansBoldFamily" not in win_body:
        errors.append('Text("下一驿") missing sansBoldFamily()')

    # Magic numbers in win block (excluding comments)
    win_code = "\n".join(l.split("//")[0] for l in win_body.splitlines())
    win_code = re.sub(r'/\*[\s\S]*?\*/', "", win_code)
    m_magic = re.findall(r'\b(28|360|62|124|154|288|17|19|29|48|67|6\.9|16\.3|4\.8|0\.55)\b', win_code)
    if m_magic:
        errors.append(f"magic numbers {m_magic} found in win block code")

    if errors:
        return False, "; ".join(errors)
    return True, "win scrim, card stack, layers, geometry, and styling OK"


def check_u(theme_cj_text, lib_dir):
    """u) safeTop/safeBottom implementation constraints: theme.cj section does not use
    .toString(), Int64.parse, .parse(), or \"${ on Ints; YILU_SAFE_TOP and YILU_SAFE_BOTTOM
    are each read inside a try-catch block; Theme.safeAreaTop does not appear in any lib file."""
    errors = []
    idx_parse = theme_cj_text.find("func parseHundredths")
    idx_has = theme_cj_text.find("func hasHundredths")
    candidates = [i for i in (idx_parse, idx_has) if i >= 0]
    idx_end = theme_cj_text.find("public static const inset")
    if not candidates or idx_end < 0:
        return False, "parseHundredths or Theme.safeTop/Bottom segment not found in theme.cj"
    seg = theme_cj_text[min(candidates):idx_end]
    for banned in (".toString(", "Int64.parse", ".parse(", '"${'):
        if banned in seg:
            errors.append(f"theme.cj safeTop/safeBottom contains banned construct: {banned}")

    if not re.search(r'try\s*\{[\s\S]*?getVariable\("YILU_SAFE_TOP"\)[\s\S]*?\}\s*catch', theme_cj_text):
        errors.append('getVariable("YILU_SAFE_TOP") missing or not enclosed in try { ... } catch')
    if not re.search(r'try\s*\{[\s\S]*?getVariable\("YILU_SAFE_BOTTOM"\)[\s\S]*?\}\s*catch', theme_cj_text):
        errors.append('getVariable("YILU_SAFE_BOTTOM") missing or not enclosed in try { ... } catch')

    for fn in os.listdir(lib_dir):
        if fn.endswith(".cj"):
            with open(os.path.join(lib_dir, fn), "r", encoding="utf-8") as f:
                content = f.read()
            if "safeAreaTop" in content:
                errors.append(f"{fn} contains deprecated safeAreaTop")

    if errors:
        return False, "; ".join(errors)
    return True, "safeTop/safeBottom safe implementation, getVariable in try-catch, 0 safeAreaTop references"


def check_v(index_cj_text):
    """v) Play paper colors: playPaper() returns Theme.paperOf( only for screen == 6,
    all other screens return Theme.paper; paperOf( called exactly once in index.cj."""
    errors = []
    m = re.search(r'func\s+playPaper\s*\(\s*\)\s*:\s*Int64\s*\{([\s\S]*?)\}', index_cj_text)
    if not m:
        return False, "func playPaper() not found in index.cj"
    body = m.group(1)
    if "this.screen == 6" not in body:
        errors.append("playPaper() missing screen == 6 check")
    if "return Theme.paperOf(" not in body:
        errors.append("playPaper() missing Theme.paperOf for screen 6")
    if "return Theme.paper" not in body:
        errors.append("playPaper() default return must be Theme.paper")

    screens_with_paper_of = re.findall(r'if\s*\(([^)]+)\)\s*\{[^}]*?paperOf', body)
    for cond in screens_with_paper_of:
        if "6" not in cond:
            errors.append(f"playPaper() returns paperOf on non-screen-6 condition: {cond.strip()}")

    call_count = len(re.findall(r'\bpaperOf\(', index_cj_text))
    if call_count != 1:
        errors.append(f"expected exactly 1 paperOf( call in index.cj, found {call_count}")

    if errors:
        return False, "; ".join(errors)
    return True, "playPaper() uses Theme.paperOf only for screen 6, paperOf() called exactly once in index.cj"


def check_w(index_cj_text):
    """w) build_body_no_let_var: func build() body contains no let/var before root container
    and no let/var at top level (depth 1, outside component braces/modifier closures)."""
    m_build = re.search(r'\bfunc\s+build\s*\(\s*\)', index_cj_text)
    if not m_build:
        return False, "func build() not found in index.cj"

    s = index_cj_text
    n = len(s)
    build_start = m_build.end()

    # Strip comments and strings while preserving offsets and newlines
    chars = []
    i = 0
    while i < n:
        if s[i:i+2] == "//":
            chars.append("  ")
            i += 2
            while i < n and s[i] != "\n":
                chars.append(" ")
                i += 1
        elif s[i:i+2] == "/*":
            chars.append("  ")
            i += 2
            while i < n and s[i:i+2] != "*/":
                chars.append("\n" if s[i] == "\n" else " ")
                i += 1
            if i < n:
                chars.append("  ")
                i += 2
        elif s[i] == '"':
            chars.append(" ")
            i += 1
            while i < n and s[i] != '"':
                if s[i] == "\\":
                    chars.append("  ")
                    i += 2
                else:
                    chars.append("\n" if s[i] == "\n" else " ")
                    i += 1
            if i < n:
                chars.append(" ")
                i += 1
        else:
            chars.append(s[i])
            i += 1
    cleaned = "".join(chars)

    open_brace_idx = cleaned.find("{", build_start)
    if open_brace_idx < 0:
        return False, "opening brace of func build() not found"

    body_start = open_brace_idx + 1
    i = body_start
    depth = 1
    paren_depth = 0
    violations = []

    while i < n and depth > 0:
        ch = cleaned[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                break
        elif ch == "(":
            paren_depth += 1
        elif ch == ")":
            paren_depth = max(0, paren_depth - 1)

        # Depth 1: top-level of build(), outside any component container or modifier closure
        if depth == 1 and paren_depth == 0:
            for kw in ("let", "var"):
                klen = len(kw)
                if cleaned[i:i+klen] == kw:
                    prev_c = cleaned[i-1] if i > 0 else "\n"
                    next_c = cleaned[i+klen] if i + klen < n else "\n"
                    if not (prev_c.isalnum() or prev_c == "_") and not (next_c.isalnum() or next_c == "_"):
                        ls = s.rfind("\n", 0, i) + 1
                        le = s.find("\n", i)
                        line = s[ls:le].strip() if le >= 0 else s[ls:].strip()
                        violations.append(f"top-level {kw} in build(): {line}")
        i += 1

    if violations:
        return False, f"build() contains {len(violations)} forbidden let/var statement(s):\n    " + "\n    ".join(violations)

    return True, "func build() body contains no let/var at top level or before root container"


def selftest():
    # 1. Test check_a violation detection
    bad_a_lines = [
        'Text("sample")',
        '    .borderRadius(4)',
        '    .border(width: 1, color: Theme.paperLine)',
    ]
    ok_a_bad, _ = check_a(bad_a_lines, name="<test_bad>")
    assert not ok_a_bad, "selftest a: expected violation detected"

    good_a_lines = [
        'Text("sample")',
        '    .border(width: 1, color: Theme.paperLine)',
        '    .borderRadius(4)',
    ]
    ok_a_good, _ = check_a(good_a_lines, name="<test_good>")
    assert ok_a_good, "selftest a: expected good chain to pass"

    # 2. Test check_c prohibited string detection
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        bad_f = os.path.join(tmpdir, "bad.cj")
        with open(bad_f, "w", encoding="utf-8") as f:
            f.write('func foo() { let s = "当前已通" }')

        ok_c_bad, msg = check_c(tmpdir, "nonexistent", None)
        assert not ok_c_bad and "当前已通" in msg, f"selftest c: expected failure, got {ok_c_bad}, {msg}"

        os.remove(bad_f)
        ch_f = os.path.join(tmpdir, "chapter.cj")
        with open(ch_f, "w", encoding="utf-8") as f:
            f.write('class SummaryCopy { static func title(): String { return "驿路全通" } }\n'
                    'func yichengFooter() { return SummaryCopy.footer(1) }')
        st_f = os.path.join(tmpdir, "main.cj")
        with open(st_f, "w", encoding="utf-8") as f:
            f.write('func test() { ctx.ck(s == "已通 100 · 驿路全通") }')

        ok_c_good, msg = check_c(tmpdir, st_f, ch_f)
        assert ok_c_good, f"selftest c: expected pass, got {ok_c_good}, {msg}"

        # literal '驿路全通' outside SummaryCopy must fail
        with open(ch_f, "w", encoding="utf-8") as f:
            f.write('func yichengFooter() { return "已通 ${total} · 驿路全通" }\n'
                    'class SummaryCopy { static func title(): String { return "驿路全通" } }')
        ok_c_outside, msg = check_c(tmpdir, st_f, ch_f)
        assert not ok_c_outside and "outside" in msg, f"selftest c: expected outside failure, got {msg}"

        # missing SummaryCopy must fail
        with open(ch_f, "w", encoding="utf-8") as f:
            f.write('func yichengFooter() { return "x" }')
        ok_c_noclass, msg = check_c(tmpdir, st_f, ch_f)
        assert not ok_c_noclass and "SummaryCopy" in msg, f"selftest c: expected missing-class failure, got {msg}"

        # index.cj literal ban, gated on summary wiring (SummaryCopy reference)
        with open(ch_f, "w", encoding="utf-8") as f:
            f.write('class SummaryCopy { static func title(): String { return "驿路全通" } }')
        idx_f = os.path.join(tmpdir, "index.cj")

        with open(idx_f, "w", encoding="utf-8") as f:
            f.write('let s = SummaryCopy.title()')
        ok_c_idx_wired, msg = check_c(tmpdir, st_f, ch_f, idx_f)
        assert ok_c_idx_wired, f"selftest c: expected wired-clean index pass, got {msg}"

        with open(idx_f, "w", encoding="utf-8") as f:
            f.write('let s = SummaryCopy.title()\nText("驿路全通")')
        ok_c_idx_lit, msg = check_c(tmpdir, st_f, ch_f, idx_f)
        assert not ok_c_idx_lit and "index.cj" in msg, f"selftest c: expected index literal failure, got {msg}"

        # unwired index (no SummaryCopy reference) with literals is skipped until J12b
        with open(idx_f, "w", encoding="utf-8") as f:
            f.write('Text("全通")')
        ok_c_idx_unwired, msg = check_c(tmpdir, st_f, ch_f, idx_f)
        assert ok_c_idx_unwired, f"selftest c: expected unwired index skip, got {msg}"

    # 3. Test check_h fallback toast placement
    good_h = (
        "if (txt.size > 0 && p.shown && toastIsOutsideTray(p)) {\n"
        "    // toast fallback (e)\n"
        "    Text(txt).border(width: 1, color: Theme.vermillion)\n"
        "    .borderRadius(4)\n"
        "    .position(x: 1.0, y: 2.0)\n"
        "}\n"
        "Scroll { ForEach(this.boardCells) }\n"
    )
    ok_h_good, msg = check_h(good_h)
    assert ok_h_good, f"selftest h: expected pass, got {ok_h_good}, {msg}"

    ok_h_no_marker, msg = check_h(good_h.replace("    // toast fallback (e)\n", ""))
    assert not ok_h_no_marker and "marker" in msg, f"selftest h: expected marker failure, got {msg}"

    bad_order = good_h.replace(
        ".border(width: 1, color: Theme.vermillion)\n    .borderRadius(4)",
        ".borderRadius(4)\n    .border(width: 1, color: Theme.vermillion)",
    )
    ok_h_bad_order, msg = check_h(bad_order)
    assert not ok_h_bad_order and "border" in msg, f"selftest h: expected order failure, got {msg}"

    after_scroll = "Scroll { ForEach(this.boardCells) }\n" + good_h.replace(
        "Scroll { ForEach(this.boardCells) }\n", ""
    )
    ok_h_after, msg = check_h(after_scroll)
    assert not ok_h_after and "before" in msg, f"selftest h: expected before-Scroll failure, got {msg}"

    ok_h_no_ref, msg = check_h(good_h.replace("toastIsOutsideTray(p)", "foo(p)"))
    assert not ok_h_no_ref and "toastIsOutsideTray" in msg, f"selftest h: expected reference failure, got {msg}"

    # 4. Test check_i summary card wiring
    good_i = (
        "if (SummaryCopy.summaryVisible(this.cleared, this.levels.size)) {\n"
        "    this.summaryCard()\n"
        "}\n"
        "@Builder func summaryCard() {\n"
        "    Column {\n"
        "        Text(SummaryCopy.title())\n"
        "        Text(SummaryCopy.subtitle(this.levels.size))\n"
        "        ForEach(SummaryCopy.sealChars(), itemGenerator: {ch: String, index: Int64 => Text(ch) })\n"
        "    }\n"
        "    .height(SummaryGeom.cardH())\n"
        "    .width(SummaryGeom.sealSize())\n"
        "    .border(width: 1, color: Theme.paperLine)\n"
        "    .borderRadius(SummaryGeom.radius())\n"
        "    .rotate(angle: Float32(SummaryGeom.sealAngle()))\n"
        "    .opacity(SummaryGeom.sealAlpha())\n"
        "}\n"
    )
    ok_i_good, msg = check_i(good_i)
    assert ok_i_good, f"selftest i: expected pass, got {msg}"

    ok_i_no_vis, msg = check_i(good_i.replace("SummaryCopy.summaryVisible", "foo"))
    assert not ok_i_no_vis and "summaryVisible" in msg, f"selftest i: expected gate failure, got {msg}"

    ok_i_lit, msg = check_i(good_i + '\nText("驿路全通")\n')
    assert not ok_i_lit and "驿路全通" in msg, f"selftest i: expected literal failure, got {msg}"

    ok_i_missing, msg = check_i(good_i.replace("SummaryGeom.sealAlpha()", "0.9"))
    assert not ok_i_missing and "SummaryGeom.sealAlpha()" in msg, f"selftest i: expected geometry failure, got {msg}"

    ok_i_order, msg = check_i(good_i.replace(
        ".border(width: 1, color: Theme.paperLine)\n    .borderRadius(SummaryGeom.radius())",
        ".borderRadius(SummaryGeom.radius())\n    .border(width: 1, color: Theme.paperLine)",
    ))
    assert not ok_i_order and "before" in msg, f"selftest i: expected order failure, got {msg}"

    # 5. Test check_j chapter list footer lines
    good_j = "func chapterListFooterLines(): Array<String> {}\nColumn { ForEach(this.chapterListFooterLines()) }"
    ok_j_good, msg = check_j(good_j)
    assert ok_j_good, f"selftest j: expected pass, got {msg}"

    bad_j_missing = "func other() {}"
    ok_j_missing, msg = check_j(bad_j_missing)
    assert not ok_j_missing and "missing" in msg, f"selftest j: expected missing failure, got {msg}"

    bad_j_single = "func chapterListFooterLines(): Array<String> {}\nText(this.chapterListFooter())"
    ok_j_single, msg = check_j(bad_j_single)
    assert not ok_j_single and "single Text" in msg, f"selftest j: expected single Text failure, got {msg}"

    # 6. Test check_k sans-bold font and usage
    import shutil
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_lib = os.path.join(tmpdir, "lib")
        tmp_fonts = os.path.join(tmpdir, "fonts")
        os.makedirs(tmp_lib)
        os.makedirs(tmp_fonts)

        real_bold = os.path.join(CJMP_DIR, "fonts", "YiluSans-Bold.ttf")
        dummy_bold = os.path.join(tmp_fonts, "YiluSans-Bold.ttf")
        shutil.copyfile(real_bold, dummy_bold)

        with open(os.path.join(tmp_lib, "theme.cj"), "w", encoding="utf-8") as f:
            f.write('public static const sansBold: String = "YiluSansBold"\n')
        with open(os.path.join(tmp_lib, "fonts.cj"), "w", encoding="utf-8") as f:
            f.write('let nameE = LibC.mallocCString(Theme.sansBold)\n')
        with open(os.path.join(tmp_lib, "index.cj"), "w", encoding="utf-8") as f:
            f.write('func sansBoldFamily(): String { return Theme.sansBold }\n'
                    'Column {\n'
                    '    Text("章节")\n'
                    '        .fontFamily(this.sansBoldFamily())\n'
                    '    Text("下一驿")\n'
                    '        .fontFamily(this.sansBoldFamily())\n'
                    '}\n')

        ok_k_good, msg = check_k(tmp_lib, tmp_fonts)
        assert ok_k_good, f"selftest k: expected pass, got {msg}"

        # Negative 1: font file missing
        ok_k_nofont, msg = check_k(tmp_lib, os.path.join(tmpdir, "nonexistent"))
        assert not ok_k_nofont and "not found" in msg, f"selftest k: expected font missing failure, got {msg}"

        # Negative 2: wrong sha256
        with open(dummy_bold, "wb") as f:
            f.write(b"bad font data")
        ok_k_badsha, msg = check_k(tmp_lib, tmp_fonts)
        assert not ok_k_badsha and "sha256" in msg, f"selftest k: expected bad sha failure, got {msg}"
        shutil.copyfile(real_bold, dummy_bold)

        # Negative 3: extra fontFamily call (3 calls, expected 2)
        with open(os.path.join(tmp_lib, "index.cj"), "a", encoding="utf-8") as f:
            f.write('Text("章节").fontFamily(this.sansBoldFamily())\n')
        ok_k_extra, msg = check_k(tmp_lib, tmp_fonts)
        assert not ok_k_extra and "expected exactly 2" in msg, f"selftest k: expected extra call failure, got {msg}"

        # Negative 3b: only 1 call (missing 下一驿)
        with open(os.path.join(tmp_lib, "index.cj"), "w", encoding="utf-8") as f:
            f.write('func sansBoldFamily(): String { return Theme.sansBold }\n'
                    'Column {\n'
                    '    Text("章节")\n'
                    '        .fontFamily(this.sansBoldFamily())\n'
                    '}\n')
        ok_k_under, msg = check_k(tmp_lib, tmp_fonts)
        assert not ok_k_under and "expected exactly 2" in msg, f"selftest k: expected under call failure, got {msg}"

        # Negative 4: used on non-authorized Text
        with open(os.path.join(tmp_lib, "index.cj"), "w", encoding="utf-8") as f:
            f.write('func sansBoldFamily(): String { return Theme.sansBold }\n'
                    'Column {\n'
                    '    Text("章节")\n'
                    '        .fontFamily(this.sansBoldFamily())\n'
                    '    Text("其他")\n'
                    '        .fontFamily(this.sansBoldFamily())\n'
                    '}\n')
        ok_k_wrong_text, msg = check_k(tmp_lib, tmp_fonts)
        assert not ok_k_wrong_text and "not attached to Text" in msg, f"selftest k: expected wrong text failure, got {msg}"

        # Negative 5: unexpected Theme.sansBold in other file
        with open(os.path.join(tmp_lib, "index.cj"), "w", encoding="utf-8") as f:
            f.write('func sansBoldFamily(): String { return Theme.sansBold }\n'
                    'Column {\n'
                    '    Text("章节")\n'
                    '        .fontFamily(this.sansBoldFamily())\n'
                    '    Text("下一驿")\n'
                    '        .fontFamily(this.sansBoldFamily())\n'
                    '}\n')
        with open(os.path.join(tmp_lib, "other.cj"), "w", encoding="utf-8") as f:
            f.write('let x = Theme.sansBold\n')
        ok_k_other, msg = check_k(tmp_lib, tmp_fonts)
        assert not ok_k_other and "unexpected Theme.sansBold" in msg, f"selftest k: expected other file failure, got {msg}"

    # 7. Test check_l footer slack and avail+1 width
    good_l_index = (
        "Column {\n"
        "    ForEach(\n"
        "        this.chapterListFooterLines(),\n"
        "        itemGenerator: {line: String, index: Int64 =>\n"
        "            Text(line)\n"
        "                .fontSize(12)\n"
        "                .lineHeight(16)\n"
        "                .height(16)\n"
        "                .fontColor(Theme.inkMuted)\n"
        "                .fontFamily(this.sansFamily())\n"
        "                .maxLines(1)\n"
        "                .width(this.winW - 40.0 + 1.0)\n"
        "        }\n"
        "    )\n"
        "}\n"
    )
    good_l_chapter = "public func footerSlack(): Float64 { return 0.5 }\n"

    ok_l, msg = check_l(good_l_index, good_l_chapter)
    assert ok_l, f"selftest l: expected pass, got {msg}"

    # Negative 1: missing footerSlack in chapter.cj
    bad_l_chapter = "public func footerNeedsTwoLines(): Bool { return false }\n"
    ok_l_noslack, msg = check_l(good_l_index, bad_l_chapter)
    assert not ok_l_noslack and "footerSlack" in msg, f"selftest l: expected footerSlack failure, got {msg}"

    # Negative 2: missing width(this.winW - 40.0 + 1.0) in index.cj
    bad_l_index_width = good_l_index.replace(".width(this.winW - 40.0 + 1.0)", ".width(100.percent)")
    ok_l_nowidth, msg = check_l(bad_l_index_width, good_l_chapter)
    assert not ok_l_nowidth and "width" in msg, f"selftest l: expected width failure, got {msg}"

    # Negative 3: missing maxLines(1) in index.cj
    bad_l_index_maxlines = good_l_index.replace(".maxLines(1)\n", "")
    ok_l_nomaxlines, msg = check_l(bad_l_index_maxlines, good_l_chapter)
    assert not ok_l_nomaxlines and "maxLines" in msg, f"selftest l: expected maxLines failure, got {msg}"

    # Negative 4: missing this.chapterListFooterLines in index.cj
    bad_l_index_noblock = "Text(\"x\").width(this.winW - 40.0 + 1.0).maxLines(1)\n"
    ok_l_noblock, msg = check_l(bad_l_index_noblock, good_l_chapter)
    assert not ok_l_noblock and "chapterListFooterLines" in msg, f"selftest l: expected block failure, got {msg}"

    # 8. Test check_m station row geometry wiring (J20)
    good_m_chapter = (
        "public class StationRowGeom {\n"
        "    public static const globalRowH: Int64 = 64\n"
        "    public static const globalRingR: Int64 = 14\n"
        "    public static const globalNameFont: Int64 = 20\n"
        "    public static const chapterRowH: Int64 = 52\n"
        "    public static const chapterRingR: Int64 = 13\n"
        "    public static const chapterNameFont: Int64 = 16\n"
        "    public static func lockPadRight(isGlobal: Bool, lockBoxW: Float64): Float64 { return 1.0 }\n"
        "}\n"
    )
    good_m_index = (
        "func build() {\n"
        "    Column {\n"
        "        if (this.screen == 3) {\n"
        "            this.checkCircleIcon(StationRowGeom.globalRingD)\n"
        "            Text(\"${index + 1}\").fontSize(StationRowGeom.globalNumFont)\n"
        "            Text(item.name).fontSize(StationRowGeom.globalNameFont)\n"
        "            Text(\"x\").fontSize(StationRowGeom.globalMetaFont)\n"
        "            this.dessertTag(0, StationRowGeom.globalBadgeFont)\n"
        "            .height(StationRowGeom.globalRowH)\n"
        "            .padding(left: StationRowGeom.globalPadLeft, right: StationRowGeom.lockPadRight(true, this.lockW()))\n"
        "            .margin(left: StationRowGeom.globalNameGap)\n"
        "        } else if (this.screen == 4) {\n"
        "        } else if (this.screen == 5) {\n"
        "            this.checkCircleIcon(StationRowGeom.chapterRingD)\n"
        "            Text(\"${index + 1}\").fontSize(StationRowGeom.chapterNumFont)\n"
        "            Text(item.name).fontSize(StationRowGeom.chapterNameFont)\n"
        "            Text(\"x\").fontSize(StationRowGeom.chapterMetaFont)\n"
        "            this.dessertTag(0, StationRowGeom.chapterBadgeFont)\n"
        "            .height(StationRowGeom.chapterRowH)\n"
        "            .padding(left: StationRowGeom.chapterPadLeft, right: StationRowGeom.lockPadRight(false, this.lockW()))\n"
        "            .margin(left: StationRowGeom.chapterNameGap)\n"
        "        }\n"
        "    }\n"
        "}\n"
    )

    ok_m, msg = check_m(good_m_index, good_m_chapter)
    assert ok_m, f"selftest m: expected pass, got {msg}"

    # Negative 1: chapter.cj missing StationRowGeom class
    ok_m_noclass, msg = check_m(good_m_index, "public func foo(): Int64 { return 1 }\n")
    assert not ok_m_noclass and "StationRowGeom" in msg, f"selftest m: expected class failure, got {msg}"

    # Negative 2: screen 3 reverts to old r18 ring (.borderRadius(18) literal)
    bad_m_index_r18 = good_m_index.replace(
        ".height(StationRowGeom.globalRowH)",
        ".height(StationRowGeom.globalRowH).borderRadius(18)")
    ok_m_r18, msg = check_m(bad_m_index_r18, good_m_chapter)
    assert not ok_m_r18 and "borderRadius(18)" in msg, f"selftest m: expected r18 failure, got {msg}"

    # Negative 3: screen 5 drops chapterNameGap reference (back to literal margin)
    bad_m_index_gap = good_m_index.replace(".margin(left: StationRowGeom.chapterNameGap)", ".margin(left: 10)")
    ok_m_gap, msg = check_m(bad_m_index_gap, good_m_chapter)
    assert not ok_m_gap and "chapterNameGap" in msg, f"selftest m: expected nameGap failure, got {msg}"

    # Negative 4: .borderRadius before .border inside screen 3 chain
    bad_m_index_order = good_m_index.replace(
        ".height(StationRowGeom.globalRowH)",
        ".height(StationRowGeom.globalRowH).borderRadius(8).border(width: 1, color: Theme.paperLine)")
    ok_m_order, msg = check_m(bad_m_index_order, good_m_chapter)
    assert not ok_m_order and ".borderRadius before .border" in msg, f"selftest m: expected order failure, got {msg}"

    # Negative 5: (J22) screen 3 locked row drops lockPadRight (back to fixed 16 padding)
    bad_m_index_lock = good_m_index.replace(
        ".padding(left: StationRowGeom.globalPadLeft, right: StationRowGeom.lockPadRight(true, this.lockW()))",
        ".padding(left: StationRowGeom.globalPadLeft, right: 16)")
    ok_m_lock, msg = check_m(bad_m_index_lock, good_m_chapter)
    assert not ok_m_lock and "lockPadRight(true, this.lockW())" in msg, f"selftest m: expected lockPadRight failure, got {msg}"

    # 15. Test check_e (home screen nav wiring, J23: click goes through openYicheng)
    good_e_lines = (
        'Text("章节")\n'
        '    .fontFamily(this.sansFamily())\n'
        '    .onClick({event => this.screen = 2})\n'
        'Text("驿程")\n'
        '    .fontFamily(this.sansFamily())\n'
        '    .onClick({event => this.openYicheng()})\n'
        'func openYicheng(): Unit {\n'
        '    this.screen = 3\n'
        '    this.positionYichengScroll()\n'
        '}\n'
    ).splitlines()
    ok_e, msg = check_e(good_e_lines)
    assert ok_e, f"selftest e: expected pass, got {ok_e}, {msg}"

    bad_e_border = [l for l in good_e_lines]
    bad_e_border.insert(2, '    .border(width: 1, color: Theme.paperLine)')
    ok_e_border, msg = check_e(bad_e_border)
    assert not ok_e_border and ".border" in msg, f"selftest e: expected border failure, got {ok_e_border}, {msg}"

    bad_e_click = [l.replace(".onClick({event => this.openYicheng()})", ".onClick({event => this.screen = 5})")
                   for l in good_e_lines]
    ok_e_click, msg = check_e(bad_e_click)
    assert not ok_e_click and "openYicheng()" in msg, f"selftest e: expected onClick failure, got {ok_e_click}, {msg}"

    bad_e_body = [l.replace("this.screen = 3", "this.screen = 4") for l in good_e_lines]
    ok_e_body, msg = check_e(bad_e_body)
    assert not ok_e_body and "screen = 3" in msg, f"selftest e: expected body failure, got {ok_e_body}, {msg}"

    bad_e_nofunc = "\n".join(good_e_lines).replace(
        "func openYicheng(): Unit {\n"
        "    this.screen = 3\n"
        "    this.positionYichengScroll()\n"
        "}", "").splitlines()
    ok_e_nofunc, msg = check_e(bad_e_nofunc)
    assert not ok_e_nofunc and "func openYicheng" in msg, f"selftest e: expected missing-func failure, got {ok_e_nofunc}, {msg}"

    # 16. Test check_n (yicheng scroll position wiring)
    good_n_chapter = (
        "public class ChapterCatalog {\n"
        "    public static func yichengScrollOffset(currentChapter: Int64, cleared: Int64, total: Int64): Float64 { return 0.0 }\n"
        "}\n"
        "public class YichengScrollGeom {\n"
        "    public static func groupGap(): Float64 { return 12.0 }\n"
        "}\n"
    )
    good_n_index = (
        "class EntryView {\n"
        "    let yichengScroller: Scroller = Scroller()\n"
        "    func openYicheng(): Unit {\n"
        "        this.screen = 3\n"
        "        let t = ChapterCatalog.yichengScrollOffset(0, this.cleared, this.levels.size)\n"
        "        this.yichengScroller.scrollTo(xOffset: 0.0, yOffset: t)\n"
        "    }\n"
        "}\n"
        "Scroll(this.yichengScroller) { Column(space: 8) { } }\n"
        ".onClick({event => this.openYicheng()})\n"
    )
    ok_n, msg = check_n(good_n_index, good_n_chapter)
    assert ok_n, f"selftest n: expected pass, got {msg}"

    ok_n_nochapter, msg = check_n(good_n_index, "public func foo(): Int64 { return 1 }\n")
    assert not ok_n_nochapter and "YichengScrollGeom" in msg, f"selftest n: expected chapter geom failure, got {msg}"

    bad_n_index_noscroll = good_n_index.replace("Scroll(this.yichengScroller)", "Scroll")
    ok_n_noscroll, msg = check_n(bad_n_index_noscroll, good_n_chapter)
    assert not ok_n_noscroll and "Scroll(this.yichengScroller)" in msg, f"selftest n: expected Scroll wiring failure, got {msg}"

    bad_n_index_deadcode = good_n_index.replace(".onClick({event => this.openYicheng()})", ".onClick({event => this.screen = 3})")
    ok_n_deadcode, msg = check_n(bad_n_index_deadcode, good_n_chapter)
    assert not ok_n_deadcode and "openYicheng" in msg, f"selftest n: expected entry-hook failure, got {msg}"

    bad_n_index_noscrollto = good_n_index.replace("this.yichengScroller.scrollTo(xOffset: 0.0, yOffset: t)", "()")
    ok_n_noscrollto, msg = check_n(bad_n_index_noscrollto, good_n_chapter)
    assert not ok_n_noscrollto and "scrollTo" in msg, f"selftest n: expected scrollTo failure, got {msg}"

    # 15. Test check_o: bare Button + borderRadius(8) is detected, container form passes
    def _o_button(label, onclick):
        return (f'Button("{label}")\n'
                '    .width(100.percent)\n'
                '    .height(Theme.primaryH)\n'
                '    .backgroundColor(Theme.qingDeep)\n'
                '    .borderRadius(8)\n'
                f'    .onClick({{event => {onclick}}})\n')

    def _o_container(label, onclick):
        return (f'Row {{\n'
                f'    Text("{label}")\n'
                '        .fontSize(16)\n'
                '        .fontColor(Theme.whitePaper)\n'
                '        .fontFamily(this.sansMediumFamily())\n'
                '}\n'
                '    .width(100.percent)\n'
                '    .height(Theme.primaryH)\n'
                '    .backgroundColor(Theme.qingDeep)\n'
                '    .borderRadius(8)\n'
                '    .justifyContent(FlexAlign.Center)\n'
                '    .alignItems(VerticalAlign.Center)\n'
                f'    .onClick({{event => {onclick}}})\n')

    good_o = _o_container("开始传书", "this.startPlay()") + _o_container("下一驿", "this.nextLevel()")
    ok_o_good, msg = check_o(good_o)
    assert ok_o_good, f"selftest o: expected container form to pass, got {msg}"

    bad_o = _o_button("开始传书", "this.startPlay()") + _o_container("下一驿", "this.nextLevel()")
    ok_o_bad, msg = check_o(bad_o)
    assert not ok_o_bad and "borderRadius is ineffective" in msg, \
        f"selftest o: expected bare Button+borderRadius violation, got {ok_o_bad}, {msg}"

    bad_o_bare = _o_container("开始传书", "this.startPlay()") + _o_button("下一驿", "this.nextLevel()").replace(
        "    .borderRadius(8)\n", "")
    ok_o_bare, msg = check_o(bad_o_bare)
    assert not ok_o_bare and "capsule" in msg, \
        f"selftest o: expected bare primary Button violation, got {ok_o_bare}, {msg}"

    bad_o_missing = good_o.replace("    .borderRadius(8)\n    .justifyContent(FlexAlign.Center)\n    .alignItems(VerticalAlign.Center)\n    .onClick({event => this.startPlay()})",
                                   "    .borderRadius(8)\n    .onClick({event => this.startPlay()})")
    ok_o_missing, msg = check_o(bad_o_missing)
    assert not ok_o_missing and "missing" in msg, \
        f"selftest o: expected missing-modifier violation, got {ok_o_missing}, {msg}"

    # 16. Test check_p: 12u scroll-content top padding + 12u card-below via gapAbove/gapBelow
    def _p_chapter(gap_above="12.0", gap_below="12.0", with_toppad=True):
        txt = ('public class SummaryGeom {\n'
               '    public static func cardH(): Float64 { return 88.0 }\n'
               f'    public static func gapAbove(): Float64 {{ return {gap_above} }}\n'
               f'    public static func gapBelow(): Float64 {{ return {gap_below} }}\n'
               '}\n'
               'public class YichengScrollGeom {\n')
        if with_toppad:
            txt += '    public static func contentTopPad(): Float64 { return SummaryGeom.gapAbove() }\n'
        txt += '}\n'
        return txt

    def _p_index(pad_line="    .padding(top: SummaryGeom.gapAbove())", card_margin=True):
        card = ('@Builder func summaryCard() {\n'
                '    Row {\n'
                '        Text(SummaryCopy.title())\n'
                '    }\n'
                '    .width(100.percent)\n'
                '    .height(SummaryGeom.cardH())\n')
        if card_margin:
            card += '    .margin(bottom: SummaryGeom.gapBelow() - 8.0)\n'
        card += '}\n'
        return (card +
                '} else if (this.screen == 3) {\n'
                'Scroll(this.yichengScroller) {\n'
                '    Column(space: 8) {\n'
                '        if (SummaryCopy.summaryVisible(this.cleared, this.levels.size)) {\n'
                '            this.summaryCard()\n'
                '        }\n'
                '    }\n'
                '    .width(100.percent)\n'
                f'{pad_line}\n'
                '}\n'
                '} else if (this.screen == 4) {\n')

    ok_p_good, msg = check_p(_p_index(), _p_chapter())
    assert ok_p_good, f"selftest p: expected wired form to pass, got {msg}"

    # c711f3e form: no content top padding (content flush against the divider) -> violation
    ok_p_bad, msg = check_p(_p_index(pad_line="    .width(100.percent)"), _p_chapter())
    assert not ok_p_bad and "gapAbove" in msg, \
        f"selftest p: expected missing-top-padding violation, got {ok_p_bad}, {msg}"

    # whitespace on the card instead of the content Column -> violation (double-count guard)
    ok_p_card, msg = check_p(_p_index(pad_line="    .width(100.percent)").replace(
        ".margin(bottom: SummaryGeom.gapBelow() - 8.0)",
        ".margin(top: SummaryGeom.gapAbove(), bottom: SummaryGeom.gapBelow() - 8.0)"), _p_chapter())
    assert not ok_p_card and "must not reference gapAbove" in msg, \
        f"selftest p: expected gapAbove-on-card violation, got {ok_p_card}, {msg}"

    # wrong constants: gapAbove 11 / missing gapBelow / missing contentTopPad
    ok_p_val, msg = check_p(_p_index(), _p_chapter(gap_above="11.0"))
    assert not ok_p_val and "gapAbove() = 11.0" in msg, \
        f"selftest p: expected gapAbove value violation, got {ok_p_val}, {msg}"
    ok_p_none, msg = check_p(_p_index(),
                             _p_chapter().replace("    public static func gapBelow(): Float64 { return 12.0 }\n", ""))
    assert not ok_p_none and "gapBelow" in msg, \
        f"selftest p: expected missing-gapBelow violation, got {ok_p_none}, {msg}"
    ok_p_toppad, msg = check_p(_p_index(), _p_chapter(with_toppad=False))
    assert not ok_p_toppad and "contentTopPad" in msg, \
        f"selftest p: expected missing-contentTopPad violation, got {ok_p_toppad}, {msg}"

    # parent Column space no longer 8 -> below-gap arithmetic breaks
    ok_p_space, msg = check_p(_p_index().replace("Column(space: 8)", "Column(space: 12)"), _p_chapter())
    assert not ok_p_space and "Column(space: 8)" in msg, \
        f"selftest p: expected Column(space: 8) violation, got {ok_p_space}, {msg}"

    # 17. Test check_q: yicheng scroll ruling geometry (780 cycle, 768 chapterH, text shift 2u)
    good_q_chapter = (
        'public class StationRowGeom {\n'
        '    public static let globalRowH: Int64 = 64\n'
        '}\n'
        'public class YichengScrollGeom {\n'
        '    public static func headerH(): Float64 { return 40.0 }\n'
        '    public static func headerPadTop(): Float64 { return 4.0 }\n'
        '    public static func headerTextShift(): Float64 { return 2.0 }\n'
        '    public static func rowH(): Float64 { return Float64(StationRowGeom.globalRowH) }\n'
        '    public static func rowGap(): Float64 { return 8.0 }\n'
        '    public static func headerTopMargin(): Float64 { return 12.0 }\n'
        '    public static func groupGap(): Float64 { return 12.0 }\n'
        '    public static func chapterH(levelCount: Int64): Float64 {\n'
        '        if (levelCount <= 0) { return 0.0 }\n'
        '        return YichengScrollGeom.headerH() + YichengScrollGeom.rowGap() +\n'
        '            Float64(levelCount) * (YichengScrollGeom.rowH() + YichengScrollGeom.rowGap())\n'
        '    }\n'
        '    public static func period(): Float64 {\n'
        '        return YichengScrollGeom.chapterH(10) + YichengScrollGeom.groupGap()\n'
        '    }\n'
        '}\n'
    )
    good_q_index = (
        '} else if (this.screen == 3) {\n'
        '    Scroll(this.yichengScroller) {\n'
        '        Column(space: 8) {\n'
        '            ForEach(this.levels, itemGenerator: {item: LevelDef, index: Int64 =>\n'
        '                Column {\n'
        '                    if (this.groupIsFirst(index)) {\n'
        '                        Column {\n'
        '                            Row {\n'
        '                                Text("label")\n'
        '                            }\n'
        '                            .width(100.percent)\n'
        '                            .height(39)\n'
        '                            .padding(top: YichengScrollGeom.headerPadTop())\n'
        '                            .alignItems(VerticalAlign.Center)\n'
        '                            Column() {}.width(100.percent).height(1).backgroundColor(Theme.ink)\n'
        '                        }\n'
        '                        .width(100.percent)\n'
        '                        .height(40)\n'
        '                        .margin(top: if (index == 0) { 0 } else { 12 }, bottom: 8)\n'
        '                    }\n'
        '                }\n'
        '            })\n'
        '        }\n'
        '    }\n'
        '} else if (this.screen == 4) {\n'
    )

    ok_q_good, msg = check_q(good_q_index, good_q_chapter)
    assert ok_q_good, f"selftest q: expected valid q to pass, got {msg}"

    # Historical commits c711f3e and cec0712 must fail check_q
    for commit in ("c711f3e", "cec0712"):
        try:
            res = subprocess.run(["git", "show", f"{commit}:mobile/cjmp/lib/chapter.cj"  # historical path (pre-restructure commits)],
                                 capture_output=True, text=True, check=True)
            ok_q_old, msg = check_q(good_q_index, res.stdout)
            assert not ok_q_old, f"selftest q: expected historical commit {commit} to fail check_q"
            assert "levelCount - 1" in msg or "headerH + rowGap" in msg, \
                f"selftest q: expected formula failure in commit {commit}, got: {msg}"
        except subprocess.CalledProcessError:
            pass

    # Old formula pattern: Float64(levelCount - 1) * rowGap
    bad_q_old_formula = good_q_chapter.replace(
        "return YichengScrollGeom.headerH() + YichengScrollGeom.rowGap() +\n            Float64(levelCount) * (YichengScrollGeom.rowH() + YichengScrollGeom.rowGap())",
        "return YichengScrollGeom.headerH() + Float64(levelCount) * YichengScrollGeom.rowH() +\n            Float64(levelCount - 1) * YichengScrollGeom.rowGap()"
    )
    ok_q_bad_form, msg = check_q(good_q_index, bad_q_old_formula)
    assert not ok_q_bad_form and "levelCount - 1" in msg, f"selftest q: expected old formula violation, got {msg}"

    # Missing header bottom gap in formula (40 + n*72 without the 8)
    bad_q_no_hdr_gap = good_q_chapter.replace(
        "YichengScrollGeom.headerH() + YichengScrollGeom.rowGap()",
        "YichengScrollGeom.headerH()"
    )
    ok_q_no_hdr_gap, msg = check_q(good_q_index, bad_q_no_hdr_gap)
    assert not ok_q_no_hdr_gap and "headerH + rowGap" in msg, f"selftest q: expected header gap violation, got {msg}"

    # Missing 4u top padding on group header Row
    bad_q_no_pad = good_q_index.replace(".padding(top: YichengScrollGeom.headerPadTop())", "")
    ok_q_no_pad, msg = check_q(bad_q_no_pad, good_q_chapter)
    assert not ok_q_no_pad and "4u top padding" in msg, f"selftest q: expected top padding violation, got {msg}"

    # Wrong header block margin (e.g. old 4 / 0)
    bad_q_margin = good_q_index.replace("margin(top: if (index == 0) { 0 } else { 12 }, bottom: 8)", "margin(top: if (index == 0) { 0 } else { 4 }, bottom: 0)")
    ok_q_margin, msg = check_q(bad_q_margin, good_q_chapter)
    assert not ok_q_margin and "margin" in msg, f"selftest q: expected margin violation, got {msg}"

    # 18. Test check_r: root padding & safe area
    good_r_index = (
        '@State var padTop: Float64 = Theme.safeTop()\n'
        '@State var padBottom: Float64 = Theme.safeBottom()\n'
        'func build() {\n'
        '    Stack(alignContent: Alignment.TopStart) {\n'
        '        Column {\n'
        '            Text("content")\n'
        '        }\n'
        '        .width(100.percent)\n'
        '        .height(100.percent)\n'
        '        .padding(top: this.padTop, bottom: this.padBottom, left: this.playInset(), right: this.playInset())\n'
        '        .backgroundColor(this.playPaper())\n'
        '        .onAreaChange({ old, new =>\n'
        '            let st = Theme.safeTop()\n'
        '            let sb = Theme.safeBottom()\n'
        '            this.padTop = st\n'
        '            this.padBottom = sb\n'
        '        })\n'
        '    }\n'
        '}\n'
    )
    ok_r, msg = check_r(good_r_index)
    assert ok_r, f"selftest r: expected pass, got {msg}"

    bad_r_nobottom = good_r_index.replace("bottom: this.padBottom, ", "")
    ok_r_nobot, msg = check_r(bad_r_nobottom)
    assert not ok_r_nobot and "bottom: this.padBottom" in msg, f"selftest r: expected missing bottom, got {msg}"

    bad_r_nostate = good_r_index.replace("@State var padBottom: Float64 = Theme.safeBottom()\n", "")
    ok_r_nostate, msg = check_r(bad_r_nostate)
    assert not ok_r_nostate and "padBottom @State" in msg, f"selftest r: expected missing state, got {msg}"

    bad_r_nostack = (
        '@State var padTop: Float64 = Theme.safeTop()\n'
        '@State var padBottom: Float64 = Theme.safeBottom()\n'
        'func build() {\n'
        '    Column {\n'
        '        Text("content")\n'
        '    }\n'
        '    .padding(top: this.padTop, bottom: this.padBottom, left: this.playInset(), right: this.playInset())\n'
        '    .backgroundColor(this.playPaper())\n'
        '    .onAreaChange({ old, new =>\n'
        '        this.padTop = Theme.safeTop()\n'
        '        this.padBottom = Theme.safeBottom()\n'
        '    })\n'
        '}\n'
    )
    ok_r_nostack, msg = check_r(bad_r_nostack)
    assert not ok_r_nostack and "Stack" in msg, f"selftest r: expected missing Stack, got {msg}"

    # 19. Test check_s: 5 bottom margins
    good_s_theme = (
        'public func hasHundredths(s: ?String): Bool { return true }\n'
        'public func bottomMarginOrLegacy(c: Float64, legacy: Float64, sbSet: Bool, sb: Float64): Float64 { return 0.0 }\n'
        'public func chipMarginOrLegacy(sbSet: Bool, sb: Float64): Float64 { return 0.0 }\n'
        'public func chipBarHeightOrLegacy(sbSet: Bool, sb: Float64): Float64 { return 72.0 }\n'
        'class Theme {\n'
        '    public static func safeBottomSet(): Bool { return false }\n'
        '    public static func safeBottom(): Float64 { return 0.0 }\n'
        '    public static func bottomMargin(c: Float64, legacy: Float64): Float64 {\n'
        '        return bottomMarginOrLegacy(c, legacy, Theme.safeBottomSet(), Theme.safeBottom())\n'
        '    }\n'
        '    public static func chipMargin(): Float64 {\n'
        '        return chipMarginOrLegacy(Theme.safeBottomSet(), Theme.safeBottom())\n'
        '    }\n'
        '    public static func chipBarHeight(): Float64 {\n'
        '        return chipBarHeightOrLegacy(Theme.safeBottomSet(), Theme.safeBottom())\n'
        '    }\n'
        '}\n'
    )
    good_s_index = (
        'Row {\n'
        '    Text("章节")\n'
        '    Text("驿程")\n'
        '        .onClick({event => this.openYicheng()})\n'
        '}\n'
        '.height(HomeLinkGeom.blockH)\n'
        '.margin(top: HomeLinkGeom.rowMarginTop, bottom: Theme.bottomMargin(8.0, 0.0), left: HomeLinkGeom.rowMarginLeft)\n'
        'Text(ChapterCatalog.yichengFooter(this.cleared, 10, "名"))\n'
        '    .margin(top: 12, bottom: Theme.bottomMargin(16.0, 8.0))\n'
        'Text(this.chapterOpenFooter())\n'
        '    .margin(top: 8, bottom: Theme.bottomMargin(16.0, 8.0))\n'
        'Column {\n'
        '    ForEach(\n'
        '        this.chapterListFooterLines(),\n'
        '        itemGenerator: {line: String =>\n'
        '            Text(line)\n'
        '        }\n'
        '    )\n'
        '}\n'
        '.margin(top: 8, bottom: Theme.bottomMargin(16.0, 8.0))\n'
        'Row(space: 12) {\n'
        'Row {\n'
        '    Text("撤销")\n'
        '}\n'
        '.borderRadius(8)\n'
        '.margin(bottom: Theme.chipMargin())\n'
        '.onClick({event => this.doUndo()})\n'
        'Row {\n'
        '    Text("重绘驿道")\n'
        '}\n'
        '.borderRadius(8)\n'
        '.margin(bottom: Theme.chipMargin())\n'
        '.onClick({event => this.doClear()})\n'
        '}\n'
        '.width(100.percent)\n'
        '.height(Theme.chipBarHeight())\n'
    )
    ok_s, msg = check_s(good_s_index, good_s_theme)
    assert ok_s, f"selftest s: expected pass, got {msg}"

    bad_s_legacy = good_s_index.replace("bottom: Theme.bottomMargin(16.0, 8.0)", "bottom: 8", 1)
    ok_s_leg, msg = check_s(bad_s_legacy, good_s_theme)
    assert not ok_s_leg and "bottom: 8" in msg, f"selftest s: expected legacy bottom:8 failure, got {msg}"

    bad_s_single = good_s_index.replace("bottom: Theme.bottomMargin(16.0, 8.0)", "bottom: Theme.bottomMargin(16.0)", 1)
    ok_s_sin, msg = check_s(bad_s_single, good_s_theme)
    assert not ok_s_sin and "bottomMargin(16.0, 8.0)" in msg, f"selftest s: expected single-param failure, got {msg}"

    bad_s_legacy_p = good_s_index.replace("Theme.bottomMargin(8.0, 0.0)", "Theme.bottomMargin(8.0, 8.0)")
    ok_s_leg_p, msg = check_s(bad_s_legacy_p, good_s_theme)
    assert not ok_s_leg_p and "bottomMargin(8.0, 0.0)" in msg, f"selftest s: expected wrong legacy parameter failure, got {msg}"

    bad_s_chip = good_s_index.replace(".margin(bottom: Theme.chipMargin())\n.onClick({event => this.doUndo()})",
                                     ".onClick({event => this.doUndo()})")
    ok_s_chip, msg = check_s(bad_s_chip, good_s_theme)
    assert not ok_s_chip and "Theme.chipMargin()" in msg, f"selftest s: expected missing chip margin, got {msg}"

    bad_s_bar = good_s_index.replace(".height(Theme.chipBarHeight())", ".height(Theme.bottomBar)")
    ok_s_bar, msg = check_s(bad_s_bar, good_s_theme)
    assert not ok_s_bar and "Theme.bottomBar" in msg, f"selftest s: expected bottom bar failure, got {msg}"

    bad_s_notheme = good_s_theme.replace("func hasHundredths", "func hasSomething")
    ok_s_nth, msg = check_s(good_s_index, bad_s_notheme)
    assert not ok_s_nth and "hasHundredths" in msg, f"selftest s: expected missing hasHundredths failure, got {msg}"

    bad_s_noroute = good_s_theme.replace("bottomMarginOrLegacy", "bottomMarginFor")
    ok_s_nr, msg = check_s(good_s_index, bad_s_noroute)
    assert not ok_s_nr and "bottomMarginOrLegacy" in msg, f"selftest s: expected missing routing failure, got {msg}"

    bad_s_nobarroute = good_s_theme.replace("chipBarHeightOrLegacy", "chipBarHeightFor")
    ok_s_nbr, msg = check_s(good_s_index, bad_s_nobarroute)
    assert not ok_s_nbr and "chipBarHeightOrLegacy" in msg, f"selftest s: expected missing chipBarHeight routing failure, got {msg}"

    # 20. Test check_t: win popup scrim/card
    good_t_theme = (
        "public static const winScrim: Int64 = 0x802C2A26\n"
        "public static const sealInk: Int64 = 0xEB9B3A2F\n"
    )
    good_t_index = (
        'func build() {\n'
        '    Stack(alignContent: Alignment.TopStart) {\n'
        '        Column {\n'
        '            Column() {}\n'
        '                .visibility(if (this.screen == 1 || this.screen == 2) { Visibility.Visible } else { Visibility.None })\n'
        '            this.backButton({ => this.leaveBoard() }, true)\n'
        '        }\n'
        '        .width(100.percent)\n'
        '        if (this.screen == 2) {\n'
        '            Column() {}\n'
        '                .backgroundColor(Theme.winScrim)\n'
        '                .position(x: 0.0, y: WinGeom.maskTop(this.padTop))\n'
        '            Column() {}\n'
        '                .backgroundColor(Theme.paperShade)\n'
        '                .borderRadius(4)\n'
        '                .position(x: WinGeom.cardX() + WinGeom.cardShadowDx(), y: WinGeom.cardTop(currentH, this.padTop, this.padBottom) + WinGeom.cardShadowDy())\n'
        '            Stack(alignContent: Alignment.TopStart) {\n'
        '                Column() {}\n'
        '                    .width(WinGeom.roadTitleWidth(this.roadTitle()))\n'
        '                Stack(alignContent: Alignment.TopStart) {\n'
        '                    Column() {}\n'
        '                        .border(width: WinGeom.sealOuterStroke(), color: Theme.sealInk)\n'
        '                        .borderRadius(WinGeom.sealOuterRadius())\n'
        '                    Column() {}\n'
        '                        .border(width: WinGeom.sealInnerStroke(), color: Theme.sealInk)\n'
        '                        .borderRadius(WinGeom.sealInnerRadius())\n'
        '                    Text("文")\n'
        '                        .fontSize(WinGeom.sealGlyphFont())\n'
        '                        .height(WinGeom.sealGlyphPitch())\n'
        '                        .fontColor(Theme.sealInk)\n'
        '                }\n'
        '                .rotate(angle: Float32(WinGeom.sealAngle()))\n'
        '                Row {\n'
        '                    Text("下一驿")\n'
        '                        .fontFamily(this.sansBoldFamily())\n'
        '                }\n'
        '            }\n'
        '            .width(WinGeom.cardW(this.winW))\n'
        '            .height(WinGeom.cardH())\n'
        '            .backgroundColor(Theme.whitePaper)\n'
        '            .border(width: 1, color: Theme.paperLine)\n'
        '            .borderRadius(4)\n'
        '            .position(x: WinGeom.cardX(), y: WinGeom.cardTop(currentH, this.padTop, this.padBottom))\n'
        '            Column() {}\n'
        '                .backgroundColor(Theme.paperLine)\n'
        '                .position(x: 20.0, y: WinGeom.hairlineY(this.padTop))\n'
        '        }\n'
        '    }\n'
        '}\n'
    )
    ok_t, msg = check_t(good_t_index, good_t_theme)
    assert ok_t, f"selftest t: expected pass, got {msg}"

    bad_t_incol = (
        'func build() {\n'
        '    Stack {\n'
        '        Column {\n'
        '            if (this.screen == 0) {}\n'
        '            else if (this.screen == 2) {\n'
        '                Text("win")\n'
        '            }\n'
        '        }\n'
        '    }\n'
        '}\n'
    )
    ok_t_incol, msg = check_t(bad_t_incol, good_t_theme)
    assert not ok_t_incol and "root Column still contains screen == 2 branch" in msg, f"selftest t: expected in-column failure, got {msg}"

    bad_t_onclick = good_t_index.replace(".position(x: 0.0, y: WinGeom.maskTop(this.padTop))\n",
                                         ".position(x: 0.0, y: WinGeom.maskTop(this.padTop))\n                .onClick({event => ()})\n")
    ok_t_click, msg = check_t(bad_t_onclick, good_t_theme)
    assert not ok_t_click and ".onClick" in msg, f"selftest t: expected mask onClick failure, got {msg}"

    bad_t_theme = "public static const winScrim: Int64 = 0xFF000000\npublic static const sealInk: Int64 = 0xEB9B3A2F\n"
    ok_t_theme, msg = check_t(good_t_index, bad_t_theme)
    assert not ok_t_theme and "winScrim = 0x802C2A26" in msg, f"selftest t: expected winScrim failure, got {msg}"

    bad_t_noseal = "public static const winScrim: Int64 = 0x802C2A26\n"
    ok_t_noseal, msg = check_t(good_t_index, bad_t_noseal)
    assert not ok_t_noseal and "sealInk = 0xEB9B3A2F" in msg, f"selftest t: expected sealInk failure, got {msg}"

    bad_t_vermillion = good_t_index.replace(
        "Stack(alignContent: Alignment.TopStart) {\n                    Column() {}",
        "Stack(alignContent: Alignment.TopStart) {\n                    Column() {}\n                        .backgroundColor(Theme.vermillion)"
    )
    ok_t_verm, msg = check_t(bad_t_vermillion, good_t_theme)
    assert not ok_t_verm and "backgroundColor(Theme.vermillion)" in msg, f"selftest t: expected vermillion failure, got {msg}"

    bad_t_const_gold = good_t_index.replace(
        ".width(WinGeom.roadTitleWidth(this.roadTitle()))",
        ".width(95.4)"
    )
    ok_t_gold, msg = check_t(bad_t_const_gold, good_t_theme)
    assert not ok_t_gold and "WinGeom.roadTitleWidth" in msg, f"selftest t: expected const gold width failure, got {msg}"

    bad_t_magic = good_t_index.replace('Text("下一驿")', 'Text("下一驿")\n                    .fontSize(17)')
    ok_t_magic, msg = check_t(bad_t_magic, good_t_theme)
    assert not ok_t_magic and "magic numbers" in msg, f"selftest t: expected magic number failure, got {msg}"

    # 21. Test check_u: safeTop/safeBottom implementation
    good_u_theme = (
        'func parseHundredths(s: ?String): Int64 {\n'
        '    return 0\n'
        '}\n'
        'func hasHundredths(s: ?String): Bool {\n'
        '    return false\n'
        '}\n'
        'class Theme {\n'
        '    public static func safeTop(): Float64 {\n'
        '        var opt: ?String = None\n'
        '        try { opt = getVariable("YILU_SAFE_TOP") } catch (e: Exception) { opt = None }\n'
        '        return Float64(parseHundredths(opt)) / 100.0\n'
        '    }\n'
        '    public static func safeBottom(): Float64 {\n'
        '        var opt: ?String = None\n'
        '        try { opt = getVariable("YILU_SAFE_BOTTOM") } catch (e: Exception) { opt = None }\n'
        '        return Float64(parseHundredths(opt)) / 100.0\n'
        '    }\n'
        '    public static const inset: Int64 = 20\n'
        '}\n'
    )
    with tempfile.TemporaryDirectory() as tmp_lib:
        with open(os.path.join(tmp_lib, "theme.cj"), "w", encoding="utf-8") as f:
            f.write(good_u_theme)
        ok_u, msg = check_u(good_u_theme, tmp_lib)
        assert ok_u, f"selftest u: expected pass, got {msg}"

        bad_u_tostring = good_u_theme.replace("return 0\n", "return 0.toString()\n")
        ok_u_str, msg = check_u(bad_u_tostring, tmp_lib)
        assert not ok_u_str and "toString" in msg, f"selftest u: expected toString failure, got {msg}"

        bad_u_hstr = good_u_theme.replace("return false\n", "return false.toString()\n")
        ok_u_hstr, msg = check_u(bad_u_hstr, tmp_lib)
        assert not ok_u_hstr and "toString" in msg, f"selftest u: expected toString in hasHundredths failure, got {msg}"

        bad_u_notry = good_u_theme.replace('try { opt = getVariable("YILU_SAFE_TOP") } catch (e: Exception) { opt = None }',
                                           'opt = getVariable("YILU_SAFE_TOP")')
        ok_u_try, msg = check_u(bad_u_notry, tmp_lib)
        assert not ok_u_try and "try" in msg, f"selftest u: expected try-catch failure, got {msg}"

        with open(os.path.join(tmp_lib, "other.cj"), "w", encoding="utf-8") as f:
            f.write("let x = Theme.safeAreaTop\n")
        ok_u_dep, msg = check_u(good_u_theme, tmp_lib)
        assert not ok_u_dep and "safeAreaTop" in msg, f"selftest u: expected safeAreaTop failure, got {msg}"

    # 22. Test check_v: playPaper
    good_v_index = (
        'func playPaper(): Int64 {\n'
        '    if (this.screen == 6) {\n'
        '        return Theme.paperOf(this.chapterIndex)\n'
        '    }\n'
        '    return Theme.paper\n'
        '}\n'
    )
    ok_v, msg = check_v(good_v_index)
    assert ok_v, f"selftest v: expected pass, got {msg}"

    bad_v_screen2 = (
        'func playPaper(): Int64 {\n'
        '    if (this.screen == 6) {\n'
        '        return Theme.paperOf(this.chapterIndex)\n'
        '    }\n'
        '    if (this.screen == 2) {\n'
        '        return Theme.paperOf(this.chapterIndex)\n'
        '    }\n'
        '    return Theme.paper\n'
        '}\n'
    )
    ok_v_s2, msg = check_v(bad_v_screen2)
    assert not ok_v_s2, f"selftest v: expected screen 2 paperOf failure, got {msg}"

    bad_v_extra = good_v_index + 'let p = Theme.paperOf(0)\n'
    ok_v_ext, msg = check_v(bad_v_extra)
    assert not ok_v_ext and "expected exactly 1" in msg, f"selftest v: expected extra call failure, got {msg}"

    # 24. Test check_w: build_body_no_let_var
    good_w_index = (
        'func build() {\n'
        '    Stack(alignContent: Alignment.TopStart) {\n'
        '        Column {\n'
        '            Text("hello")\n'
        '        }\n'
        '        .onAreaChange({ old, new =>\n'
        '            let h = new.height.value\n'
        '            var targetH = 800.0\n'
        '        })\n'
        '    }\n'
        '}\n'
    )
    ok_w_good, msg = check_w(good_w_index)
    assert ok_w_good, f"selftest w: expected pass, got {msg}"

    bad_w_top = (
        'func build() {\n'
        '    let x = 1\n'
        '    Column {\n'
        '        Text("hello")\n'
        '    }\n'
        '}\n'
    )
    ok_w_bad, msg = check_w(bad_w_top)
    assert not ok_w_bad and "let" in msg, f"selftest w: expected top-level let failure, got {msg}"

    bad_w_var = (
        'func build() {\n'
        '    var y = 2\n'
        '    Column {\n'
        '        Text("hello")\n'
        '    }\n'
        '}\n'
    )
    ok_w_var, msg = check_w(bad_w_var)
    assert not ok_w_var and "var" in msg, f"selftest w: expected top-level var failure, got {msg}"

    # 25. Baseline regression assertions: cec0712 must fail (r), (s), (t), (v) and pass (w); efb4503 must fail (w)
    try:
        cec_text = subprocess.check_output(
            ["git", "-C", REPO_ROOT, "show", "cec0712:mobile/cjmp/lib/index.cj"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except Exception:
        cec_text = None

    if cec_text is not None:
        r_pass, r_err = check_r(cec_text)
        assert not r_pass, f"selftest regression: cec0712 must fail check_r, but passed: {r_err}"
        s_pass, s_err = check_s(cec_text)
        assert not s_pass, f"selftest regression: cec0712 must fail check_s, but passed: {s_err}"
        t_pass, t_err = check_t(cec_text, good_t_theme)
        assert not t_pass, f"selftest regression: cec0712 must fail check_t, but passed: {t_err}"
        v_pass, v_err = check_v(cec_text)
        assert not v_pass, f"selftest regression: cec0712 must fail check_v, but passed: {v_err}"
        w_pass, w_msg = check_w(cec_text)
        assert w_pass, f"selftest regression: cec0712 must pass check_w, but failed: {w_msg}"
    else:
        print("SKIP baseline regression check (cannot read cec0712)")

    try:
        efb_text = subprocess.check_output(
            ["git", "-C", REPO_ROOT, "show", "efb4503:mobile/cjmp/lib/index.cj"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except Exception:
        efb_text = None

    if efb_text is not None:
        w_efb_pass, w_efb_msg = check_w(efb_text)
        assert not w_efb_pass, f"selftest regression: efb4503 must fail check_w, but passed: {w_efb_msg}"
    else:
        print("SKIP efb4503 regression check (cannot read efb4503)")

    print("selftest OK")
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--selftest", action="store_true", help="Run self-tests on memory samples and exit")
    parser.add_argument("--repo-root", default=REPO_ROOT, help="Path to repository root")
    parser.add_argument("--cjmp", default=CJMP_DIR, help="Path to app-ios-android directory")
    args = parser.parse_args()

    if args.selftest:
        selftest()

    repo_root = os.path.abspath(args.repo_root)
    cjmp_dir = os.path.abspath(args.cjmp)
    lib_dir = os.path.join(cjmp_dir, "lib")
    fonts_dir = os.path.join(cjmp_dir, "fonts")
    index_cj_path = os.path.join(lib_dir, "index.cj")
    chapter_cj_path = os.path.join(lib_dir, "chapter.cj")
    theme_cj_path = os.path.join(lib_dir, "theme.cj")
    boards_locked_dir = os.path.join(repo_root, "boards-locked")
    selftest_main_path = os.path.join(cjmp_dir, "scripts", "board_selftest", "main.cj")

    if not os.path.exists(index_cj_path):
        sys.exit(f"check_ui_diffs: index.cj not found at {index_cj_path}")

    with open(index_cj_path, "r", encoding="utf-8") as f:
        index_cj_text = f.read()
    index_cj_lines = index_cj_text.splitlines()

    chapter_cj_text = ""
    if os.path.exists(chapter_cj_path):
        with open(chapter_cj_path, "r", encoding="utf-8") as f:
            chapter_cj_text = f.read()

    theme_cj_text = ""
    if os.path.exists(theme_cj_path):
        with open(theme_cj_path, "r", encoding="utf-8") as f:
            theme_cj_text = f.read()

    checks = [
        ("a) border_radius_order", lambda: check_a(index_cj_lines, name="index.cj")),
        ("b) dessert_count_and_ids", lambda: check_b(chapter_cj_text, boards_locked_dir)),
        ("c) prohibited_strings", lambda: check_c(lib_dir, selftest_main_path, chapter_cj_path, index_cj_path)),
        ("d) icons_and_cards", lambda: check_d(index_cj_text)),
        ("e) home_screen_nav", lambda: check_e(index_cj_lines)),
        ("f) dessert_tag_builder", lambda: check_f(index_cj_text)),
        ("g) border_radius_values", lambda: check_g(index_cj_lines)),
        ("h) toast_fallback_outside_scroll", lambda: check_h(index_cj_text)),
        ("i) summary_card_wiring", lambda: check_i(index_cj_text)),
        ("j) chapter_list_footer_lines", lambda: check_j(index_cj_text)),
        ("k) sans_bold_font_and_usage", lambda: check_k(lib_dir, fonts_dir)),
        ("l) footer_slack_and_avail_width", lambda: check_l(index_cj_text, chapter_cj_text)),
        ("m) station_row_geom", lambda: check_m(index_cj_text, chapter_cj_text)),
        ("n) yicheng_scroll_position", lambda: check_n(index_cj_text, chapter_cj_text)),
        ("o) primary_button_r8_containers", lambda: check_o(index_cj_text)),
        ("p) summary_card_top_whitespace", lambda: check_p(index_cj_text, chapter_cj_text)),
        ("q) yicheng_scroll_ruling_geom", lambda: check_q(index_cj_text, chapter_cj_text)),
        ("r) root_padding_and_safe_area", lambda: check_r(index_cj_text)),
        ("s) bottom_margins_use_theme", lambda: check_s(index_cj_text, theme_cj_text)),
        ("t) win_scrim_and_card_stack", lambda: check_t(index_cj_text, theme_cj_text)),
        ("u) safe_area_implementation", lambda: check_u(theme_cj_text, lib_dir)),
        ("v) play_paper_colors", lambda: check_v(index_cj_text)),
        ("w) build_body_no_let_var", lambda: check_w(index_cj_text)),
    ]

    all_passed = True
    for name, check_fn in checks:
        passed, msg = check_fn()
        if passed:
            print(f"PASS {name}: {msg}")
        else:
            print(f"FAIL {name}: {msg}")
            all_passed = False

    if not all_passed:
        sys.exit(1)
    print("check_ui_diffs: ALL PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
