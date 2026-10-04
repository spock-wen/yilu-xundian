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
"""
import argparse
import hashlib
import json
import os
import re
import sys

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
CJMP_DIR = os.path.dirname(SCRIPTS_DIR)
REPO_ROOT = os.path.dirname(os.path.dirname(CJMP_DIR))

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
    """k) (J18) Theme.sansBold / sansBoldFamily() in lib/*.cj only at home screen Text('章节')
    (exactly 1 .fontFamily(this.sansBoldFamily())), YiluSans-Bold.ttf sha256 prefix 7e46ee679e9d."""
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
                    if 'Text("章节")' in lines[prev]:
                        found_target = True
                        break
                    if lines[prev].strip().startswith("Column") or lines[prev].strip().startswith("Row"):
                        break
                if not found_target:
                    errors.append(f"{fn}:{lineno} .fontFamily(this.sansBoldFamily()) not attached to Text(\"章节\")")

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

    if sans_bold_call_count != 1:
        return False, f"expected exactly 1 .fontFamily(this.sansBoldFamily()), found {sans_bold_call_count}"

    if errors:
        return False, "Theme.sansBold / sansBoldFamily() violations:\n    " + "\n    ".join(errors)

    return True, f"YiluSans-Bold.ttf (7e46ee679e9d) OK, .fontFamily(this.sansBoldFamily()) exactly 1 on Text('章节')"


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

        # Negative 3: extra fontFamily call
        with open(os.path.join(tmp_lib, "index.cj"), "a", encoding="utf-8") as f:
            f.write('Text("章节").fontFamily(this.sansBoldFamily())\n')
        ok_k_extra, msg = check_k(tmp_lib, tmp_fonts)
        assert not ok_k_extra and "expected exactly 1" in msg, f"selftest k: expected extra call failure, got {msg}"

        # Negative 4: used on non-"章节" Text
        with open(os.path.join(tmp_lib, "index.cj"), "w", encoding="utf-8") as f:
            f.write('func sansBoldFamily(): String { return Theme.sansBold }\n'
                    'Column {\n'
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

    print("selftest OK")
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--selftest", action="store_true", help="Run self-tests on memory samples and exit")
    parser.add_argument("--repo-root", default=REPO_ROOT, help="Path to repository root")
    parser.add_argument("--cjmp", default=CJMP_DIR, help="Path to mobile/cjmp directory")
    args = parser.parse_args()

    if args.selftest:
        selftest()

    repo_root = os.path.abspath(args.repo_root)
    cjmp_dir = os.path.abspath(args.cjmp)
    lib_dir = os.path.join(cjmp_dir, "lib")
    fonts_dir = os.path.join(cjmp_dir, "fonts")
    index_cj_path = os.path.join(lib_dir, "index.cj")
    chapter_cj_path = os.path.join(lib_dir, "chapter.cj")
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
