#!/usr/bin/env python3
"""Rule-level tests for the grid engine + Zip patrol layer.

Mirrors the Cangjie types in entry/src/main/cangjie/{engine,game}.
This file is the executable spec: if a Cangjie change disagrees with these
behaviours, the Cangjie side is wrong unless this spec is updated first.
"""

from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from solve_levels import load_levels, solve, wall_key  # noqa: E402


class Cell:
    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y

    def equals(self, other: Cell) -> bool:
        return self.x == other.x and self.y == other.y


class GridLayout:
    def __init__(self, origin_x: float, origin_y: float, cell_size: float, cols: int, rows: int) -> None:
        self.origin_x = origin_x
        self.origin_y = origin_y
        self.cell_size = cell_size
        self.cols = cols
        self.rows = rows


def touch_to_cell(px: float, py: float, layout: GridLayout) -> Cell | None:
    if px < layout.origin_x or py < layout.origin_y:
        return None
    cx = int((px - layout.origin_x) / layout.cell_size)
    cy = int((py - layout.origin_y) / layout.cell_size)
    if cx < 0 or cy < 0 or cx >= layout.cols or cy >= layout.rows:
        return None
    return Cell(cx, cy)


class UndoStack:
    def __init__(self) -> None:
        self.items: list = []

    def push(self, item) -> None:
        self.items.append(item)

    def pop(self):
        if not self.items:
            return None
        return self.items.pop()

    def peek(self):
        return self.items[-1] if self.items else None

    def clear(self) -> None:
        self.items.clear()

    def size(self) -> int:
        return len(self.items)


class GridPath:
    def __init__(self) -> None:
        self.stack = UndoStack()

    def cells(self) -> list:
        return list(self.stack.items)

    def push(self, cell: Cell) -> None:
        self.stack.push(cell)

    def undo(self) -> Cell | None:
        return self.stack.pop()

    def clear(self) -> None:
        self.stack.clear()

    def last(self) -> Cell | None:
        return self.stack.peek()

    def prev(self) -> Cell | None:
        if self.stack.size() < 2:
            return None
        return self.stack.items[-2]

    def contains(self, cell: Cell) -> bool:
        return any(c.equals(cell) for c in self.stack.items)

    def size(self) -> int:
        return self.stack.size()


class GridMap:
    def __init__(self, cols: int, rows: int, walls: list[tuple[int, int, int, int]]) -> None:
        self.cols = cols
        self.rows = rows
        self.walls = {wall_key(x1, y1, x2, y2) for x1, y1, x2, y2 in walls}

    def in_bounds(self, cell: Cell) -> bool:
        return 0 <= cell.x < self.cols and 0 <= cell.y < self.rows

    def orthogonal(self, a: Cell, b: Cell) -> bool:
        return abs(a.x - b.x) + abs(a.y - b.y) == 1

    def blocked(self, a: Cell, b: Cell) -> bool:
        return wall_key(a.x, a.y, b.x, b.y) in self.walls


class PatrolGame:
    """THIS game's rules: ordered waypoints + fill-all Hamiltonian path."""

    def __init__(self, level: dict) -> None:
        self.level = level
        walls = [(int(w["x1"]), int(w["y1"]), int(w["x2"]), int(w["y2"])) for w in level.get("walls") or []]
        self.grid = GridMap(int(level["cols"]), int(level["rows"]), walls)
        self.wps = {(int(w["x"]), int(w["y"])): int(w["n"]) for w in level["waypoints"]}
        self.max_n = max(self.wps.values())
        self.path = GridPath()

    def number_at(self, x: int, y: int) -> int:
        return self.wps.get((x, y), 0)

    def next_required(self) -> int:
        seen = 0
        for c in self.path.cells():
            n = self.number_at(c.x, c.y)
            if n == seen + 1:
                seen = n
        return seen + 1

    def _can_enter(self, cell: Cell) -> bool:
        if not self.grid.in_bounds(cell):
            return False
        if self.path.contains(cell):
            return False
        last = self.path.last()
        if last is None:
            return self.number_at(cell.x, cell.y) == 1
        if not self.grid.orthogonal(last, cell):
            return False
        if self.grid.blocked(last, cell):
            return False
        num = self.number_at(cell.x, cell.y)
        nxt = self.next_required()
        if num != 0 and num != nxt:
            return False
        if num == self.max_n and self.path.size() + 1 != self.grid.cols * self.grid.rows:
            return False
        return True

    def try_step(self, cell: Cell) -> bool:
        prev = self.path.prev()
        if prev is not None and cell.equals(prev):
            self.path.undo()
            return True
        if self._can_enter(cell):
            self.path.push(cell)
            return True
        return False

    def undo(self) -> bool:
        return self.path.undo() is not None

    def clear(self) -> None:
        self.path.clear()

    def is_win(self) -> bool:
        last = self.path.last()
        if last is None:
            return False
        if self.path.size() != self.grid.cols * self.grid.rows:
            return False
        return self.number_at(last.x, last.y) == self.max_n and self.next_required() == self.max_n + 1


class TouchToCellTests(unittest.TestCase):
    def setUp(self) -> None:
        self.layout = GridLayout(8.0, 8.0, 64.0, 5, 5)

    def test_maps_center_of_cell(self) -> None:
        cell = touch_to_cell(8 + 64 * 2 + 32, 8 + 64 * 3 + 10, self.layout)
        self.assertIsNotNone(cell)
        self.assertEqual((cell.x, cell.y), (2, 3))

    def test_rejects_outside(self) -> None:
        self.assertIsNone(touch_to_cell(7, 40, self.layout))
        self.assertIsNone(touch_to_cell(8 + 64 * 5 + 1, 40, self.layout))


class UndoStackTests(unittest.TestCase):
    def test_push_pop_clear(self) -> None:
        s = UndoStack()
        s.push("a")
        s.push("b")
        self.assertEqual(s.peek(), "b")
        self.assertEqual(s.pop(), "b")
        self.assertEqual(s.pop(), "a")
        self.assertIsNone(s.pop())
        s.push("c")
        s.clear()
        self.assertEqual(s.size(), 0)


class PatrolRuleTests(unittest.TestCase):
    def level(self) -> dict:
        return {
            "id": 99,
            "name": "试驿",
            "cols": 3,
            "rows": 3,
            "waypoints": [{"n": 1, "x": 0, "y": 0}, {"n": 2, "x": 2, "y": 2}],
            "walls": [{"x1": 0, "y1": 0, "x2": 1, "y2": 0}],
        }

    def test_must_start_on_one(self) -> None:
        g = PatrolGame(self.level())
        self.assertFalse(g.try_step(Cell(1, 1)))
        self.assertTrue(g.try_step(Cell(0, 0)))

    def test_rejects_diagonal(self) -> None:
        g = PatrolGame(self.level())
        g.try_step(Cell(0, 0))
        self.assertFalse(g.try_step(Cell(1, 1)))

    def test_rejects_wall(self) -> None:
        g = PatrolGame(self.level())
        g.try_step(Cell(0, 0))
        self.assertFalse(g.try_step(Cell(1, 0)))
        self.assertTrue(g.try_step(Cell(0, 1)))

    def test_drag_back_undo(self) -> None:
        g = PatrolGame(self.level())
        g.try_step(Cell(0, 0))
        g.try_step(Cell(0, 1))
        self.assertTrue(g.try_step(Cell(0, 0)))
        self.assertEqual(g.path.size(), 1)
        self.assertTrue(g.path.last().equals(Cell(0, 0)))

    def test_button_undo_and_clear(self) -> None:
        g = PatrolGame(self.level())
        g.try_step(Cell(0, 0))
        g.try_step(Cell(0, 1))
        self.assertTrue(g.undo())
        self.assertEqual(g.path.size(), 1)
        g.clear()
        self.assertEqual(g.path.size(), 0)

    def test_rejects_revisit(self) -> None:
        g = PatrolGame(self.level())
        g.try_step(Cell(0, 0))
        g.try_step(Cell(0, 1))
        g.try_step(Cell(0, 2))
        g.try_step(Cell(1, 2))
        g.try_step(Cell(1, 1))
        self.assertFalse(g.try_step(Cell(0, 1)))

    def test_cannot_enter_two_early(self) -> None:
        g = PatrolGame(self.level())
        g.try_step(Cell(0, 0))
        g.try_step(Cell(0, 1))
        g.try_step(Cell(0, 2))
        g.try_step(Cell(1, 2))
        self.assertFalse(g.try_step(Cell(2, 2)))
        self.assertEqual(g.path.size(), 4)
        self.assertFalse(g.is_win())


class ShippedLevelPlaythroughTests(unittest.TestCase):
    def test_solver_path_wins_every_solvable_shipped_level(self) -> None:
        levels = load_levels(ROOT / "entry/src/main/resources/rawfile/levels.json")
        self.assertEqual(len(levels), 20)
        for level in levels:
            found = solve(level, timeout_s=8.0)
            path = found[0]
            game = PatrolGame(level)
            for x, y in path:
                self.assertTrue(
                    game.try_step(Cell(x, y)),
                    f"{level['name']} rejected ({x},{y}) at size={game.path.size()}",
                )
            self.assertTrue(game.is_win(), f"{level['name']} did not win after solver path")

    def test_first_two_have_unique_solutions(self) -> None:
        levels = load_levels(ROOT / "entry/src/main/resources/rawfile/levels.json")
        for level in levels[:2]:
            found = solve(level, find_all=True, limit=2, timeout_s=8.0)
            self.assertEqual(len(found), 1, f"{level['name']} should have a unique solution")


class VerifiedCatalogTests(unittest.TestCase):
    """Lock the 20-board 涿郡+平原 catalog (ids 0..19)."""

    def test_json_is_the_verified_table(self) -> None:
        from build_levels import EXPECTED_NAMES, ST02_WALLS, emit, load_verified

        levels = load_verified()
        self.assertEqual(len(levels), 20)
        self.assertEqual([int(lv["id"]) for lv in levels], list(range(20)))
        self.assertEqual([lv["name"] for lv in levels], list(EXPECTED_NAMES))
        self.assertNotIn("长安", [lv["name"] for lv in levels])
        self.assertNotIn("洛阳", [lv["name"] for lv in levels])
        self.assertNotIn("汽梁", [lv["name"] for lv in levels])
        self.assertTrue(all("_src" not in lv for lv in levels))

        st01 = levels[0]
        self.assertEqual(st01["name"], "涿郡·涿")
        self.assertEqual((st01["cols"], st01["rows"]), (6, 6))
        self.assertEqual(len(st01["waypoints"]), 6)
        self.assertEqual(st01.get("walls") or [], [])

        st02 = levels[1]
        self.assertEqual(st02["name"], "涿郡·范阳")
        self.assertEqual(st02["walls"], ST02_WALLS)

        generated = emit(levels)
        shipped = (ROOT / "entry/src/main/cangjie/levels.cj").read_text(encoding="utf-8")
        self.assertEqual(shipped, generated, "levels.cj must be emitted from levels.json")

    def test_mock_copy_is_in_ui(self) -> None:
        ui = (ROOT / "entry/src/main/cangjie/index.cj").read_text(encoding="utf-8")
        for phrase in (
            "传书过驿",
            "开始传书",
            "驿程",
            "关防",
            "重绘驿道",
            "文书到",
            "驿道已通",
            "文书递达本驿",
            "下一驿",
        ):
            self.assertIn(phrase, ui)
        self.assertNotIn("文书达驿", ui)

    def test_theme_tokens_match_handoff(self) -> None:
        theme = (ROOT / "entry/src/main/cangjie/theme.cj").read_text(encoding="utf-8")
        for token in (
            "0XF3E8D6",
            "0XE6D5B8",
            "0XD4C4A8",
            "0X2C2A26",
            "0X5C574E",
            "0X6B7A78",
            "0X3D4A47",
            "0X3F4F4C",
            "0XC4A35A",
            "0X9B3A2F",
            "0XC9BBA6",
            "0X5E7A6A",
            "0XFBF6EC",
        ):
            self.assertIn(token, theme)


# Selectable chapters this round: 涿郡 + 平原 only (10 boards each).
# 徐州 / 吕布 may exist as comments in Cangjie, never in the selectable list.
CHAPTERS = (
    {"id": 0, "name": "涿郡", "levelStart": 0, "levelCount": 10},
    {"id": 1, "name": "平原", "levelStart": 10, "levelCount": 10},
)


def chapter_by_id(chapter_id: int) -> dict:
    return next(ch for ch in CHAPTERS if ch["id"] == chapter_id)


def chapter_unlocked(chapter_id: int, cleared: int) -> bool:
    """Chapter 0 always unlocked; later chapters need the previous 10 cleared."""
    if chapter_id <= 0:
        return True
    prev = chapter_by_id(chapter_id - 1)
    return cleared >= prev["levelStart"] + prev["levelCount"]


def chapter_cleared_count(chapter_id: int, cleared: int) -> int:
    ch = chapter_by_id(chapter_id)
    start = ch["levelStart"]
    count = ch["levelCount"]
    if cleared <= start:
        return 0
    return min(count, cleared - start)


def chapter_levels(levels: list, chapter_id: int) -> list:
    ch = chapter_by_id(chapter_id)
    start = ch["levelStart"]
    return levels[start : start + ch["levelCount"]]


def continue_level_index(cleared: int, total: int) -> int:
    """Home「开始传书」: current unlocked station, or last board if all cleared."""
    if cleared >= total:
        return total - 1
    return cleared


def road_title(name: str, catalog_index: int) -> str:
    """Board / win header: locked 盘名原文, already includes chapter·station."""
    return name


def _road_title_func_body(ui: str) -> str:
    start = ui.index("func roadTitle()")
    brace = ui.index("{", start)
    depth = 0
    i = brace
    while i < len(ui):
        if ui[i] == "{":
            depth += 1
        elif ui[i] == "}":
            depth -= 1
            if depth == 0:
                return ui[start : i + 1]
        i += 1
    raise AssertionError("roadTitle() body not closed")


class RoadTitleCopyTests(unittest.TestCase):
    """Header is the locked board name as-is (already chapter·station)."""

    def test_first_board_title_is_raw_name(self) -> None:
        levels = load_levels(ROOT / "entry/src/main/resources/rawfile/levels.json")
        first = levels[0]
        self.assertEqual(first["name"], "涿郡·涿")
        self.assertEqual((int(first["cols"]), int(first["rows"])), (6, 6))
        self.assertEqual(len(first["waypoints"]), 6)
        self.assertEqual(first.get("walls") or [], [])
        self.assertEqual(road_title(first["name"], 0), "涿郡·涿")
        self.assertNotIn("第 1 驿", road_title(first["name"], 0))

    def test_second_board_title_is_raw_name(self) -> None:
        levels = load_levels(ROOT / "entry/src/main/resources/rawfile/levels.json")
        second = levels[1]
        self.assertEqual(second["name"], "涿郡·范阳")
        self.assertEqual(len(second.get("walls") or []), 2)
        self.assertEqual(road_title(second["name"], 1), "涿郡·范阳")

    def test_second_station_name_already_includes_ordinal(self) -> None:
        levels = load_levels(ROOT / "entry/src/main/resources/rawfile/levels.json")
        named = next(lv for lv in levels if lv["name"] == "平原·祝阿·第 2 驿")
        self.assertEqual(road_title(named["name"], int(named["id"])), "平原·祝阿·第 2 驿")

    def test_ui_road_title_uses_raw_board_name(self) -> None:
        ui = (ROOT / "entry/src/main/cangjie/index.cj").read_text(encoding="utf-8")
        body = _road_title_func_body(ui)
        self.assertIn("this.game.level.name", body)
        self.assertNotIn("this.levelIndex + 1", body)
        self.assertNotIn("maxNumber()", body)
        self.assertEqual(ui.count("func roadTitle()"), 1)
        self.assertEqual(ui.count("this.roadTitle()"), 2)


class ChapterCatalogTests(unittest.TestCase):
    """Selectable chapters are 涿郡 + 平原; LevelCatalog stays the board SoT."""

    def test_selectable_chapters_are_zhuojun_and_pingyuan(self) -> None:
        self.assertEqual([ch["name"] for ch in CHAPTERS], ["涿郡", "平原"])
        self.assertEqual([ch["id"] for ch in CHAPTERS], [0, 1])
        self.assertTrue(all(ch["levelCount"] == 10 for ch in CHAPTERS))
        self.assertEqual(CHAPTERS[0]["levelStart"], 0)
        self.assertEqual(CHAPTERS[1]["levelStart"], 10)
        self.assertNotIn("徐州", [ch["name"] for ch in CHAPTERS])
        self.assertNotIn("吕布", [ch["name"] for ch in CHAPTERS])

    def test_zhuojun_always_unlocked_pingyuan_needs_ten_cleared(self) -> None:
        self.assertTrue(chapter_unlocked(0, 0))
        self.assertTrue(chapter_unlocked(0, 9))
        self.assertFalse(chapter_unlocked(1, 0))
        self.assertFalse(chapter_unlocked(1, 9))
        self.assertTrue(chapter_unlocked(1, 10))
        self.assertTrue(chapter_unlocked(1, 19))

    def test_cleared_count_is_clamped_to_the_chapter_window(self) -> None:
        self.assertEqual(chapter_cleared_count(0, 0), 0)
        self.assertEqual(chapter_cleared_count(0, 3), 3)
        self.assertEqual(chapter_cleared_count(0, 10), 10)
        self.assertEqual(chapter_cleared_count(0, 15), 10)
        self.assertEqual(chapter_cleared_count(1, 9), 0)
        self.assertEqual(chapter_cleared_count(1, 10), 0)
        self.assertEqual(chapter_cleared_count(1, 14), 4)
        self.assertEqual(chapter_cleared_count(1, 20), 10)

    def test_chapter_slices_ten_global_boards(self) -> None:
        levels = load_levels(ROOT / "entry/src/main/resources/rawfile/levels.json")
        zhuo = chapter_levels(levels, 0)
        ping = chapter_levels(levels, 1)
        self.assertEqual(len(zhuo), 10)
        self.assertEqual(len(ping), 10)
        self.assertEqual([int(lv["id"]) for lv in zhuo], list(range(0, 10)))
        self.assertEqual([int(lv["id"]) for lv in ping], list(range(10, 20)))
        self.assertTrue(all(lv["name"].startswith("涿郡") for lv in zhuo))
        self.assertTrue(all(lv["name"].startswith("平原") for lv in ping))

    def test_continue_opens_current_station(self) -> None:
        self.assertEqual(continue_level_index(0, 20), 0)
        self.assertEqual(continue_level_index(7, 20), 7)
        self.assertEqual(continue_level_index(10, 20), 10)
        self.assertEqual(continue_level_index(20, 20), 19)

    def test_cangjie_catalog_matches_python_spec(self) -> None:
        src = (ROOT / "entry/src/main/cangjie/chapter.cj").read_text(encoding="utf-8")
        self.assertIn("class ChapterCatalog", src)
        self.assertIn('ChapterDef(0, "涿郡", 0, 10)', src)
        self.assertIn('ChapterDef(1, "平原", 10, 10)', src)
        adds = [line for line in src.splitlines() if "ChapterDef(" in line and "chapters.add" in line]
        self.assertEqual(len(adds), 2, "only 涿郡 + 平原 may be selectable")
        all_fn = _func_body(src, "all")
        self.assertNotIn("徐州", all_fn)
        self.assertNotIn("吕布", all_fn)
        self.assertIn("levelStart", src)
        self.assertIn("levelCount", src)


class ChapterNavUiTests(unittest.TestCase):
    """Home → chapter list → chapter's 10 → board. Structural screens only."""

    def test_home_browse_opens_chapter_list_not_flat_catalog(self) -> None:
        ui = (ROOT / "entry/src/main/cangjie/index.cj").read_text(encoding="utf-8")
        home = ui[ui.index("if (this.screen == 0)") : ui.index("} else if (this.screen ==")]
        self.assertIn('this.screen = 3', home)
        self.assertIn("开始传书", home)
        self.assertIn("this.startPlay()", home)
        self.assertIn("驿程", home)
        self.assertNotIn("LevelCatalog.all()", home)

    def test_screen_3_is_chapter_cards_only(self) -> None:
        ui = (ROOT / "entry/src/main/cangjie/index.cj").read_text(encoding="utf-8")
        chapter_list = _screen_branch(ui, 3)
        self.assertIn("ChapterCatalog.all()", chapter_list)
        self.assertIn("涿郡", (ROOT / "entry/src/main/cangjie/chapter.cj").read_text(encoding="utf-8"))
        self.assertIn("平原", (ROOT / "entry/src/main/cangjie/chapter.cj").read_text(encoding="utf-8"))
        self.assertNotIn("LevelCatalog.all()", chapter_list)
        self.assertNotIn("Image(", chapter_list)
        self.assertNotIn(".png", chapter_list)
        self.assertNotIn("徐州", chapter_list)
        self.assertNotIn("吕布", chapter_list)
        self.assertIn("this.screen = 0", chapter_list)
        self.assertIn("Theme.whitePaper", chapter_list)
        self.assertIn("Theme.ink", chapter_list)

    def test_screen_4_lists_one_chapter_ten_and_returns_to_chapters(self) -> None:
        ui = (ROOT / "entry/src/main/cangjie/index.cj").read_text(encoding="utf-8")
        level_list = _screen_branch(ui, 4)
        self.assertIn("ChapterCatalog", level_list)
        self.assertNotIn("LevelCatalog.all()", level_list)
        self.assertIn("this.screen = 3", level_list)
        self.assertIn("openFromList", level_list)
        self.assertIn("item.id", level_list)

    def test_start_play_continues_cleared_station(self) -> None:
        ui = (ROOT / "entry/src/main/cangjie/index.cj").read_text(encoding="utf-8")
        body = _func_body(ui, "startPlay")
        self.assertIn("this.cleared", body)
        self.assertIn("this.openLevel", body)
        self.assertNotIn("this.screen = 3", body)

    def test_no_chapter_skin_assets_shipped(self) -> None:
        media = ROOT / "entry/src/main/resources"
        skins = []
        for pattern in ("**/*chapter*", "**/*zhuojun*", "**/*pingyuan*", "**/*涿郡*", "**/*平原*"):
            skins.extend(p for p in media.glob(pattern) if p.suffix.lower() in {".png", ".jpg", ".webp"})
        self.assertEqual(skins, [], "do not ship placeholder chapter skins")


def _screen_branch(ui: str, screen: int) -> str:
    token = f"this.screen == {screen}"
    start = ui.index(token)
    brace = ui.index("{", start)
    depth = 0
    i = brace
    while i < len(ui):
        if ui[i] == "{":
            depth += 1
        elif ui[i] == "}":
            depth -= 1
            if depth == 0:
                return ui[start : i + 1]
        i += 1
    raise AssertionError(f"screen {screen} branch not closed")


def _play_bottom_bar(ui: str) -> str:
    """Slice the play-screen 撤销 / 重绘驿道 bar (last Row that contains both labels)."""
    start = ui.rfind("Row(space: 12)")
    if start < 0:
        raise AssertionError("play bottom bar Row(space: 12) missing")
    return ui[start:]


def _func_body(src: str, name: str) -> str:
    start = src.index(f"func {name}(")
    brace = src.index("{", start)
    depth = 0
    i = brace
    while i < len(src):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[start : i + 1]
        i += 1
    raise AssertionError(f"{name}() body not closed")


class BottomBarIconTests(unittest.TestCase):
    """Approved 24vp stroke-only open-chevron icons, not filled tips or tofu."""

    def test_undo_clear_are_not_harmony_buttons(self) -> None:
        ui = (ROOT / "entry/src/main/cangjie/index.cj").read_text(encoding="utf-8")
        bar = _play_bottom_bar(ui)
        self.assertNotIn('Button("撤销")', ui)
        self.assertNotIn('Button("重绘驿道")', ui)
        self.assertNotIn("SymbolGlyph", ui)
        self.assertNotIn("startIcon", bar)
        self.assertIn("撤销", bar)
        self.assertIn("重绘驿道", bar)
        self.assertIn("this.doUndo()", bar)
        self.assertIn("this.doClear()", bar)

    def test_undo_clear_use_24vp_canvas_path_arrows(self) -> None:
        ui = (ROOT / "entry/src/main/cangjie/index.cj").read_text(encoding="utf-8")
        theme = (ROOT / "entry/src/main/cangjie/theme.cj").read_text(encoding="utf-8")
        self.assertIn("public static let iconVp: Int64 = 24", theme)
        undo = _func_body(ui, "drawUndoIcon")
        redraw = _func_body(ui, "drawRedrawIcon")
        self.assertIn("counterclockwise: true", undo)
        self.assertIn("counterclockwise: false", redraw)
        self.assertIn("lineWidth", undo)
        self.assertIn("lineWidth = 1.5", undo)
        self.assertIn("lineWidth = 1.5", redraw)
        self.assertNotIn("Theme.hairline", undo)
        self.assertNotIn("Theme.hairline", redraw)
        self.assertIn("Theme.ink", undo)
        self.assertIn("Theme.ink", redraw)
        self.assertIn("Path2D()", undo)
        self.assertIn("Path2D()", redraw)
        self.assertIn(".arc(", undo.replace(" ", ""))
        self.assertIn(".stroke(", undo)
        self.assertIn(".arc(", redraw.replace(" ", ""))
        self.assertIn(".stroke(", redraw)
        self.assertNotIn("fillRect", undo)
        self.assertNotIn("fillRect", redraw)
        bar = _play_bottom_bar(ui)
        self.assertIn("Theme.iconVp", bar)
        self.assertIn("Canvas(this.undoContext)", bar)
        self.assertIn("Canvas(this.redrawContext)", bar)

    def test_icons_are_stroke_only_open_chevron(self) -> None:
        ui = (ROOT / "entry/src/main/cangjie/index.cj").read_text(encoding="utf-8")
        undo = _func_body(ui, "drawUndoIcon")
        redraw = _func_body(ui, "drawRedrawIcon")
        for body in (undo, redraw):
            self.assertNotIn("closePath", body)
            self.assertNotIn("fill(", body)
            self.assertNotIn("fillStyle", body)
            self.assertIn("moveTo", body)
            self.assertIn("lineTo", body)
            self.assertEqual(body.count("stroke("), 3)
            self.assertEqual(body.count("lineTo("), 2)
        # Old filled-triangle vertices from the 24vp blob.
        blob = undo + redraw
        for token in ("10.8", "8.7", "12.9", "19.5", "15.4", "18.4"):
            self.assertNotIn(token, blob)

    def test_icon_geometry_matches_svg(self) -> None:
        from bar_icons import (  # noqa: E402
            ICON_VP,
            REDRAW,
            STROKE,
            UNDO,
            assert_inside_icon,
            assert_open_chevron,
        )

        self.assertEqual(ICON_VP, 24)
        self.assertEqual(STROKE, 1.5)
        self.assertTrue(UNDO.counterclockwise())
        self.assertFalse(REDRAW.counterclockwise())
        self.assertGreater(UNDO.sweep_rad(), 4.2)
        self.assertLess(UNDO.sweep_rad(), 4.6)
        self.assertGreater(REDRAW.sweep_rad(), 4.2)
        self.assertLess(REDRAW.sweep_rad(), 4.6)
        for spec in (UNDO, REDRAW):
            assert_open_chevron(spec)
            assert_inside_icon((spec.arc_x0, spec.arc_y0))
            assert_inside_icon((spec.arc_x1, spec.arc_y1))
            for arm in (spec.arm_a, spec.arm_b):
                for pt in arm.points():
                    assert_inside_icon(pt)
            cx, cy, r, start, end, _ccw = spec.canvas_arc()
            self.assertAlmostEqual(cx + r * math.cos(start), spec.arc_x0, places=2)
            self.assertAlmostEqual(cy + r * math.sin(start), spec.arc_y0, places=2)
            self.assertAlmostEqual(cx + r * math.cos(end), spec.arc_x1, places=2)
            self.assertAlmostEqual(cy + r * math.sin(end), spec.arc_y1, places=2)
        ui = (ROOT / "entry/src/main/cangjie/index.cj").read_text(encoding="utf-8")
        undo = _func_body(ui, "drawUndoIcon")
        redraw = _func_body(ui, "drawRedrawIcon")
        for token in UNDO.cj_tokens():
            self.assertIn(token, undo, f"missing undo token {token}")
        for token in REDRAW.cj_tokens():
            self.assertIn(token, redraw, f"missing redraw token {token}")

    def test_committed_svgs_match_spec(self) -> None:
        from bar_icons import REDRAW, UNDO  # noqa: E402

        undo_svg = (ROOT / "icons/icon-undo.svg").read_text(encoding="utf-8")
        reset_svg = (ROOT / "icons/icon-reset.svg").read_text(encoding="utf-8")
        self.assertEqual(undo_svg, UNDO.icon_svg())
        self.assertEqual(reset_svg, REDRAW.icon_svg())
        for raw in (undo_svg, reset_svg):
            self.assertIn('stroke-width="1.5"', raw)
            self.assertIn("stroke-linecap=\"round\"", raw)
            self.assertNotIn("<polygon", raw)
            self.assertNotIn("closePath", raw)
            self.assertEqual(raw.count('fill="none"'), 1)
            self.assertEqual(raw.count("fill="), 1)


def station_number_vp(cell_size: float) -> int:
    """Designer mock: tutorial cell 48 → 24vp; scale cs/48; floor is 22vp."""
    vp = int(24.0 * cell_size / 48.0 + 0.5)
    return max(22, vp)


def station_diameter(cell_size: float) -> float:
    """Designer mock: tutorial cell 48 → diameter 40; scale with cs/48."""
    return 40.0 * cell_size / 48.0


def station_glyph_height(cell_size: float) -> float:
    """Path2D glyph height in vp: 0.60 of diameter (24 in a 40 circle)."""
    h = station_diameter(cell_size) * 0.60
    return max(22.0, h)


class StationNumberSkinTests(unittest.TestCase):
    """Board waypoint digits: Path2D in vp, same unit as the station circle.

    fillText / font px and vp2px already shipped twice; a 180×180 crop of
    tutorial station-1 was pixel-identical to e90cacf (0 px diff). Digits
    must be Path2D moveTo/lineTo/arc in vp, height 0.55–0.65 of diameter.
    """

    def test_spec_tutorial_is_24vp_in_40_circle(self) -> None:
        self.assertEqual(station_number_vp(48), 24)
        self.assertEqual(station_diameter(48), 40.0)
        self.assertAlmostEqual(station_glyph_height(48), 24.0)
        self.assertGreaterEqual(station_glyph_height(48) / 40.0, 0.55)
        self.assertLessEqual(station_glyph_height(48) / 40.0, 0.65)

    def test_spec_later_boards_scale_with_cell(self) -> None:
        self.assertEqual(station_number_vp(96), 48)
        self.assertEqual(station_diameter(96), 80.0)
        self.assertEqual(station_number_vp(72), 36)
        self.assertEqual(station_diameter(72), 60.0)
        self.assertEqual(station_number_vp(57.6), 29)
        self.assertGreaterEqual(station_number_vp(20), 22)
        self.assertAlmostEqual(station_glyph_height(96), 48.0)

    def test_spec_five_by_five_is_readable(self) -> None:
        cell = 288 / 5
        self.assertGreaterEqual(station_number_vp(cell), 22)
        self.assertAlmostEqual(station_number_vp(cell), 29)
        self.assertGreater(station_diameter(cell), 40.0)

    def test_index_drops_hardcoded_px_serif_for_waypoint_digits(self) -> None:
        ui = (ROOT / "entry/src/main/cangjie/index.cj").read_text(encoding="utf-8")
        board = _func_body(ui, "drawBoard")
        self.assertNotIn("18px serif", board)
        self.assertNotIn('"24px"', board)
        self.assertNotIn('"22px"', board)

    def test_index_waypoint_digits_use_path2d_not_font(self) -> None:
        """Digits are Path2D in vp. font/fillText must not paint wp.n."""
        ui = (ROOT / "entry/src/main/cangjie/index.cj").read_text(encoding="utf-8")
        theme = (ROOT / "entry/src/main/cangjie/theme.cj").read_text(encoding="utf-8")
        board = _func_body(ui, "drawBoard")
        self.assertIn("func drawStationDigit(", ui)
        self.assertIn("func drawStationNumber(", ui)
        digits = _func_body(ui, "drawStationDigit")
        numbers = _func_body(ui, "drawStationNumber")
        self.assertNotIn('fillText("${wp.n}", cx, cy)', board)
        self.assertNotIn("${numPx}px", board)
        self.assertNotIn("${numVp}vp", board)
        self.assertNotIn("vp Noto", board)
        self.assertNotIn("canvasDensity", board)
        self.assertIn("drawStationNumber", board)
        self.assertIn("Path2D()", digits)
        self.assertIn("moveTo", digits)
        self.assertIn("lineTo", digits)
        self.assertIn(".arc(", digits)
        self.assertIn("func strokeStationPath(", ui)
        self.assertIn("stroke(path)", _func_body(ui, "strokeStationPath"))
        self.assertIn("n >= 10", numbers)
        for d in range(0, 10):
            self.assertIn(f"d == {d}", digits)
        self.assertRegex(board, r"cs\s*/\s*48")
        self.assertIn("stationD", board)
        self.assertIn("stationD: Float64 = 40.0", theme)
        self.assertIn("tutorialCell: Int64 = 48", theme)
        self.assertIn("iconVp: Int64 = 24", theme)
        self.assertIn("stationNumber: Int64 = 24", theme)
        self.assertIn("stationNumberMin: Int64 = 22", theme)
        self.assertIn("0.60", board + numbers + digits)
    def test_index_contrast_ink_on_paper_and_paper_on_qing(self) -> None:
        ui = (ROOT / "entry/src/main/cangjie/index.cj").read_text(encoding="utf-8")
        theme = (ROOT / "entry/src/main/cangjie/theme.cj").read_text(encoding="utf-8")
        board = _func_body(ui, "drawBoard")
        self.assertIn("ink: Int64 = 0X2C2A26", theme)
        self.assertIn("whitePaper: Int64 = 0XFBF6EC", theme)
        self.assertIn("qing: Int64 = 0X6B7A78", theme)
        self.assertIn("fillStyle = Theme.qing", board)
        self.assertIn("fillStyle = Theme.whitePaper", board)
        self.assertIn("fillStyle = Theme.ink", board)
        wp = board[board.index("for (wp in this.game.level.waypoints)") :]
        visited = wp[wp.index("if (st == 2)") : wp.index("} else {")]
        self.assertIn("Theme.qing", visited)
        self.assertIn("Theme.whitePaper", visited)
        idle = wp[wp.index("} else {") :]
        self.assertIn("Theme.ink", idle)

    def test_bundled_noto_bold_subset_has_ofl(self) -> None:
        fonts = list((ROOT / "entry/src/main/resources/rawfile").glob("**/*NotoSerifSC*"))
        fonts += list((ROOT / "entry/src/main/resources/base/media").glob("**/*NotoSerifSC*"))
        self.assertTrue(fonts, "Noto Serif SC Bold subset TTF/OTF must be bundled")
        names = " ".join(p.name for p in fonts)
        self.assertRegex(names, r"Bold|SemiBold", "thin Regular/ExtraLight is not enough contrast")
        ofl = list(ROOT.rglob("OFL.txt")) + list(ROOT.rglob("**/OFL-NotoSerifSC*"))
        self.assertTrue(ofl, "SIL Open Font License file must be in the repo")


if __name__ == "__main__":
    unittest.main(verbosity=2)
