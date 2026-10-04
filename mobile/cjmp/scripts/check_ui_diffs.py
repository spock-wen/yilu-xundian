#!/usr/bin/env python3
"""Static UI diffs and rule checker for Yilu CJMP (lib/index.cj, lib/chapter.cj, etc.).

Checks:
  a) index.cj has no .borderRadius before .border (check_border_radius 0 violations)
  b) dessertIds() in chapter.cj has 10 IDs matching boards-locked, isDessert() has no '== 4'
  c) lib/*.cj has no '当前已通'; chapter.cj and board_selftest/main.cj have required footer strings
  d) index.cj has no Text("通")/Text("锁"), no rawImg("card_05".."10"), has lockIcon & checkCircleIcon
  e) index.cj Text("章节") has no .border, Text("驿程") has screen=3 onClick
  f) dessertTag builder state==1 uses Theme.paperShade without .border, h18/fs11/r3 verified
  g) modifier chains: Theme.qingDeep slip r4, rowBorderW r8, cardBorderW r10, vermillion toast r4,
     doUndo/doClear r8 with border width 1.2
  h) (e) fallback toast: index.cj references toastIsOutsideTray / rejectPlace.step == 4 and the
     '// toast fallback (e)' Text appears before the board Scroll (border before borderRadius)
"""
import argparse
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
    return text[brace_open + 1:end]


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


def check_c(lib_dir, board_selftest_main_path, chapter_cj_path=None):
    """c) No '当前已通' in lib/*.cj, footer templates present."""
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
    if "已通 ${total} · 驿路全通" not in chapter_content:
        return False, "chapter.cj missing template '已通 ${total} · 驿路全通'"

    if not os.path.exists(board_selftest_main_path):
        return False, f"board_selftest/main.cj not found at {board_selftest_main_path}"
    with open(board_selftest_main_path, "r", encoding="utf-8") as f:
        selftest_content = f.read()
    if "已通 100 · 驿路全通" not in selftest_content:
        return False, "board_selftest/main.cj missing literal '已通 100 · 驿路全通'"

    return True, "no '当前已通' in lib, required footer templates/literals present"


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
    """e) Text('章节') chain has no .border, Text('驿程') has screen=3 onClick."""
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
    onclick_pattern = re.compile(r'\.onClick\s*\(\s*\{\s*event\s*=>\s*this\.screen\s*=\s*3\s*\}\s*\)')
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
        return False, 'Text("驿程") with .onClick({event => this.screen = 3}) modifier not found'

    return True, 'Text("章节") has no .border, Text("驿程") with screen=3 onClick present'


def check_f(index_cj_text):
    """f) dessertTag state==1 uses Theme.paperShade without .border, dimensions verified."""
    m = re.search(r'(?:@Builder\s+)?func\s+dessertTag\s*\([^)]*\)', index_cj_text)
    if not m:
        return False, "dessertTag builder not found in index.cj"

    func_body = _extract_brace_body(index_cj_text, m.end())

    for req in ("Theme.paperShade", ".height(18)", ".fontSize(11)", ".borderRadius(3)"):
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

        # 4. Theme.vermillion border toast
        if re.search(r'\.border\s*\([^)]*Theme\.vermillion', txt):
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
            f.write('func yichengFooter() { return "已通 ${total} · 驿路全通" }')
        st_f = os.path.join(tmpdir, "main.cj")
        with open(st_f, "w", encoding="utf-8") as f:
            f.write('func test() { ctx.ck(s == "已通 100 · 驿路全通") }')

        ok_c_good, msg = check_c(tmpdir, st_f, ch_f)
        assert ok_c_good, f"selftest c: expected pass, got {ok_c_good}, {msg}"

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
        ("c) prohibited_strings", lambda: check_c(lib_dir, selftest_main_path, chapter_cj_path)),
        ("d) icons_and_cards", lambda: check_d(index_cj_text)),
        ("e) home_screen_nav", lambda: check_e(index_cj_lines)),
        ("f) dessert_tag_builder", lambda: check_f(index_cj_text)),
        ("g) border_radius_values", lambda: check_g(index_cj_lines)),
        ("h) toast_fallback_outside_scroll", lambda: check_h(index_cj_text)),
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
