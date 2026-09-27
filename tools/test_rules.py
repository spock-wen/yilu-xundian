#!/usr/bin/env python3
"""Rule-level tests for the grid engine + Zip patrol layer.

Mirrors the Cangjie types in entry/src/main/cangjie/{engine,game}.
This file is the executable spec: if a Cangjie change disagrees with these
behaviours, the Cangjie side is wrong unless this spec is updated first.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from solve_levels import (  # noqa: E402
    load_levels,
    load_locked_levels,
    report_solve_exit,
    solve,
    verify_path,
    wall_key,
)


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
        """Mirrors Cangjie GridMap.blocked: non-orthogonal counts as blocked."""
        return not self.orthogonal(a, b) or wall_key(a.x, a.y, b.x, b.y) in self.walls


class ParityEdge:
    """Mirrors Cangjie ParityEdge: parity gate on one orthogonal edge."""

    def __init__(self, x1: int, y1: int, x2: int, y2: int, require_odd: bool, require_even: bool) -> None:
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.require_odd = require_odd
        self.require_even = require_even

    def matches(self, a: Cell, b: Cell) -> bool:
        same = self.x1 == a.x and self.y1 == a.y and self.x2 == b.x and self.y2 == b.y
        rev = self.x1 == b.x and self.y1 == b.y and self.x2 == a.x and self.y2 == a.y
        return same or rev


class PatrolGame:
    """THIS game's rules: ordered waypoints + fill-all Hamiltonian path."""

    def __init__(self, level: dict) -> None:
        self.level = level
        walls = [(int(w["x1"]), int(w["y1"]), int(w["x2"]), int(w["y2"])) for w in level.get("walls") or []]
        self.grid = GridMap(int(level["cols"]), int(level["rows"]), walls)
        self.wps = {(int(w["x"]), int(w["y"])): int(w["n"]) for w in level["waypoints"]}
        self.max_n = max(self.wps.values())
        self.parity_edges = [
            ParityEdge(
                int(e["x1"]),
                int(e["y1"]),
                int(e["x2"]),
                int(e["y2"]),
                bool(e["requireOdd"]),
                bool(e["requireEven"]),
            )
            for e in level.get("parityEdges") or []
        ]
        self.path = GridPath()
        self.last_reject_parity = 0

    def number_at(self, x: int, y: int) -> int:
        return self.wps.get((x, y), 0)

    def filled(self) -> int:
        """Mirrors Cangjie PatrolGame.filled: laid cells incl. the standing cell."""
        return self.path.size()

    def next_required(self) -> int:
        seen = 0
        for c in self.path.cells():
            n = self.number_at(c.x, c.y)
            if n == seen + 1:
                seen = n
        return seen + 1

    def _check_parity(self, last: Cell, cell: Cell) -> bool:
        """Mirrors Cangjie PatrolGame.checkParity.

        SoT: filled odd → require_odd; even → require_even (filled = cells laid,
        standing cell counted, before push).
        """
        filled = self.filled()
        for pe in self.parity_edges:
            if pe.matches(last, cell):
                if pe.require_odd and filled % 2 == 0:
                    self.last_reject_parity = 1
                    return False
                if pe.require_even and filled % 2 == 1:
                    self.last_reject_parity = 2
                    return False
        return True

    def _can_enter(self, cell: Cell) -> bool:
        self.last_reject_parity = 0
        if not self.grid.in_bounds(cell):
            return False
        if self.path.contains(cell):
            return False
        last = self.path.last()
        if last is None:
            return self.number_at(cell.x, cell.y) == 1
        if self.grid.blocked(last, cell):
            return False
        if not self._check_parity(last, cell):
            return False
        num = self.number_at(cell.x, cell.y)
        nxt = self.next_required()
        if num != 0 and num != nxt:
            return False
        if num == self.max_n and self.path.size() + 1 != self.grid.cols * self.grid.rows:
            return False
        return True

    def try_step(self, cell: Cell) -> bool:
        self.last_reject_parity = 0
        prev = self.path.prev()
        if prev is not None and cell.equals(prev):
            self.path.undo()
            return True
        if self._can_enter(cell):
            self.path.push(cell)
            return True
        return False

    def undo(self) -> bool:
        self.last_reject_parity = 0
        return self.path.undo() is not None

    def clear(self) -> None:
        self.path.clear()
        self.last_reject_parity = 0

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

    def test_blocked_matches_cangjie_non_orthogonal(self) -> None:
        grid = GridMap(3, 3, [])
        self.assertTrue(grid.blocked(Cell(0, 0), Cell(1, 1)))
        self.assertTrue(grid.blocked(Cell(0, 0), Cell(2, 0)))
        self.assertFalse(grid.blocked(Cell(0, 0), Cell(1, 0)))

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


class ParityRuleTests(unittest.TestCase):
    """奇偶闸: filled odd → require_odd; even → require_even (filled before push)."""

    def level(self, edges: list[dict]) -> dict:
        return {
            "id": 98,
            "name": "奇偶试驿",
            "cols": 3,
            "rows": 3,
            "waypoints": [{"n": 1, "x": 0, "y": 0}, {"n": 2, "x": 2, "y": 2}],
            "walls": [],
            "parityEdges": edges,
            "stepLimit": 0,
        }

    @staticmethod
    def edge(x1: int, y1: int, x2: int, y2: int, odd: bool) -> dict:
        return {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "requireOdd": odd, "requireEven": not odd}

    def test_filled_is_laid_cells_including_standing(self) -> None:
        g = PatrolGame(self.level([]))
        self.assertEqual(g.filled(), 0)
        g.try_step(Cell(0, 0))
        self.assertEqual(g.filled(), 1)
        g.try_step(Cell(0, 1))
        self.assertEqual(g.filled(), 2)

    def test_odd_edge_passes_on_odd_filled(self) -> None:
        g = PatrolGame(self.level([self.edge(0, 0, 0, 1, True)]))
        g.try_step(Cell(0, 0))
        self.assertEqual(g.filled(), 1)
        self.assertTrue(g.try_step(Cell(0, 1)))
        self.assertEqual(g.last_reject_parity, 0)

    def test_even_edge_rejects_odd_filled(self) -> None:
        g = PatrolGame(self.level([self.edge(0, 0, 0, 1, False)]))
        g.try_step(Cell(0, 0))
        self.assertFalse(g.try_step(Cell(0, 1)))
        self.assertEqual(g.last_reject_parity, 2)
        self.assertEqual(g.filled(), 1)

    def test_odd_edge_rejects_even_filled(self) -> None:
        g = PatrolGame(self.level([self.edge(0, 1, 0, 2, True)]))
        g.try_step(Cell(0, 0))
        g.try_step(Cell(0, 1))
        self.assertEqual(g.filled(), 2)
        self.assertFalse(g.try_step(Cell(0, 2)))
        self.assertEqual(g.last_reject_parity, 1)
        self.assertEqual(g.filled(), 2)

    def test_edge_matches_in_both_directions(self) -> None:
        """(0,0) and (0,2) are the same chessboard color, so a simple path arrives with odd filled.

        require_odd therefore allows the reverse step (0,2) -> (0,1). The edge
        was stored as (0,1)-(0,2); acceptance shows ParityEdge.matches both orders.
        """
        g = PatrolGame(self.level([self.edge(0, 1, 0, 2, True)]))
        for cell in (Cell(0, 0), Cell(1, 0), Cell(1, 1), Cell(1, 2), Cell(0, 2)):
            self.assertTrue(g.try_step(cell))
        self.assertEqual(g.filled(), 5)
        self.assertTrue(g.try_step(Cell(0, 1)))
        self.assertEqual(g.last_reject_parity, 0)

    def test_reject_code_clears_after_undo_clear_and_success(self) -> None:
        g = PatrolGame(self.level([self.edge(0, 0, 0, 1, False)]))
        g.try_step(Cell(0, 0))
        self.assertFalse(g.try_step(Cell(0, 1)))
        self.assertEqual(g.last_reject_parity, 2)
        self.assertTrue(g.undo())
        self.assertEqual(g.last_reject_parity, 0)
        g.try_step(Cell(0, 0))
        self.assertFalse(g.try_step(Cell(0, 1)))
        g.clear()
        self.assertEqual(g.last_reject_parity, 0)

    def test_locked_shipped_paths_obey_parity(self) -> None:
        """Stored locked paths, including ferry jumps, still satisfy parity edges."""
        checked = 0
        for level in load_locked_levels():
            if not level.get("parityEdges"):
                continue
            ok, why = verify_path(level, level["storedPath"])
            self.assertTrue(ok, f"{level['name']} {why}")
            checked += 1
        self.assertGreaterEqual(checked, 5)


class SolverContractTests(unittest.TestCase):
    def test_timeout_and_unverified_mechanics_fail_the_gate(self) -> None:
        """Timeout keeps the board file, but it is not a pass. Unsupported mechanics are not a pass."""
        with redirect_stdout(io.StringIO()):
            self.assertEqual(report_solve_exit(0, 0), 0)
            self.assertEqual(report_solve_exit(0, 1), 1)
            self.assertEqual(report_solve_exit(1, 0), 1)
            self.assertEqual(report_solve_exit(0, 0, non_unique=1), 1)
            self.assertEqual(report_solve_exit(0, 0, unsupported=1), 1)
            self.assertEqual(report_solve_exit(0, 0, stored_invalid=1), 1)


class ShippedLevelPlaythroughTests(unittest.TestCase):
    def test_catalog_is_the_full_locked_set(self) -> None:
        from build_levels import EXPECTED_NAMES

        levels = load_levels(ROOT / "entry/src/main/resources/rawfile/levels.json")
        locked = load_locked_levels()
        self.assertEqual(len(levels), len(EXPECTED_NAMES))
        self.assertEqual(len(levels), len(locked))
        self.assertGreater(len(levels), 20)
        self.assertEqual([int(lv["id"]) for lv in levels], list(range(len(levels))))
        self.assertEqual([lv["name"] for lv in levels], [lv["name"] for lv in locked])

    def test_supported_locked_paths_replay(self) -> None:
        checked = 0
        for level in load_locked_levels():
            ok, why = verify_path(level, level["storedPath"])
            self.assertTrue(ok, f"#{level['id']} {level['name']} {why}")
            checked += 1
        self.assertEqual(checked, 100)

    def test_first_two_have_unique_solutions(self) -> None:
        levels = load_levels(ROOT / "entry/src/main/resources/rawfile/levels.json")
        for level in levels[:2]:
            found = solve(level, find_all=True, limit=2, timeout_s=8.0)
            self.assertEqual(len(found), 1, f"{level['name']} should have a unique solution")


class FerryMechanicTests(unittest.TestCase):
    """Ferry is a forced one-way jump: stepping on 甲 must continue on 乙."""

    def test_locked_52_stored_path_is_the_unique_solution_shipped_has_none(self) -> None:
        locked = next(level for level in load_locked_levels() if int(level["id"]) == 52)
        self.assertEqual(locked["name"], "荆州·樊城·第 1 驿")
        self.assertIsNotNone(locked["ferry"])
        self.assertEqual(locked["droppedFields"], ["ferry"])
        ok, why = verify_path(locked, locked["storedPath"])
        self.assertTrue(ok, why)
        found = solve(locked, find_all=True, limit=2, timeout_s=30)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0], locked["storedPath"])

        shipped = load_levels(ROOT / "entry/src/main/resources/rawfile/levels.json")
        ship = next(level for level in shipped if int(level["id"]) == 52)
        self.assertEqual(ship["name"], locked["name"])
        self.assertFalse(ship.get("ferry"))
        self.assertEqual(solve(ship, find_all=True, limit=2, timeout_s=30), [])
        shipped_ok, shipped_why = verify_path(ship, locked["storedPath"])
        self.assertFalse(shipped_ok)
        self.assertIn("illegal step", shipped_why)


class SealBurdenCollapseTests(unittest.TestCase):
    """Locked seal, burden, and collapse: the stored path is the unique solution.

    Rules match boards-locked seal_rule / burden_rule / collapse_rule:
    a seal edge opens only after a token cell, load/unload toggles laden,
    and the collapse edge becomes a wall after the trigger cell.
    """

    def test_locked_boards_stored_path_is_the_unique_solution(self) -> None:
        wanted = (70, 79, 90, 93, 95, 97, 99)
        locked = {int(level["id"]): level for level in load_locked_levels()}
        for lid in wanted:
            level = locked[lid]
            self.assertTrue(
                level.get("sealGates") or level.get("burden") or level.get("collapse"),
                lid,
            )
            ok, why = verify_path(level, level["storedPath"])
            self.assertTrue(ok, f"#{lid} {level['name']} {why}")
            found = solve(level, find_all=True, limit=2, timeout_s=30)
            self.assertEqual(len(found), 1, f"#{lid} {level['name']}")
            self.assertEqual(found[0], level["storedPath"], lid)


class VerifiedCatalogTests(unittest.TestCase):
    """Lock the full ch1..ch10 catalog (ids follow boards-locked, not a hard-coded 20)."""

    def test_json_is_the_verified_table(self) -> None:
        from build_levels import EXPECTED_NAMES, ST02_WALLS, emit, load_verified

        levels = load_verified()
        self.assertEqual(len(levels), len(EXPECTED_NAMES))
        self.assertEqual([int(lv["id"]) for lv in levels], list(range(len(levels))))
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
            "章节",
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

    def test_readme_tracks_locked_catalog(self) -> None:
        """README names the full-catalog gate failure, not a 20/20 pass."""
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("涿郡·涿", readme)
        self.assertIn("平原·祝阿·第 2 驿", readme)
        self.assertIn("cleared >= 10", readme)
        self.assertNotIn("20/20", readme)
        self.assertNotIn("12/12", readme)
        self.assertNotIn("13/13", readme)
        self.assertNotIn("{驿名}·第 N 驿", readme)
        self.assertNotIn("| 0 | 长安（教程） |", readme)
        self.assertNotIn("汽梁", readme)
        self.assertIn("52,59,60,63,67,89", readme)
        self.assertIn("30,33,35,37,40,43,45,47,49,50,55,57,65,73,77,83,87,93,95,97,99", readme)
        self.assertIn("39,70,75,79,85,90", readme)
        self.assertIn("LOCKED_UNIQUE_EQ_STORED: 100/100", readme)
        self.assertNotIn("UNSUPPORTED mechanic — not verified", readme)
        self.assertIn("sols_no_ferry", readme)

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
        self.assertIn("0XE7EBD8", theme)
        self.assertIn("0XE8E4DC", theme)
        self.assertIn("0XE8EDE8", theme)
        self.assertIn("0XE2E4EA", theme)
        self.assertIn("0XE6E8E2", theme)
        self.assertIn("0XE4E8E6", theme)
        self.assertIn("0XEDE6D8", theme)
        self.assertIn("0XB33C32", theme)
        self.assertIn("chapterCardH: Int64 = 104", theme)
        self.assertIn("chapterSkinCardH: Int64 = 176", theme)
        self.assertIn("chapterThumbRowW: Int64 = 128", theme)
        self.assertIn("flagThumbW: Int64 = 24", theme)
        self.assertIn("flagThumbH: Int64 = 30", theme)
        self.assertIn("bustThumbW: Int64 = 36", theme)
        self.assertIn("bustThumbH: Int64 = 48", theme)
        self.assertIn("chromeStripH: Int64 = 64", theme)
        # BANDS.md: 1080×300 px = 360×100 vp at SCALE 3; 30px clear = 10 vp.
        self.assertIn("designW: Int64 = 360", theme)
        self.assertIn("bandH: Int64 = 100", theme)
        self.assertIn("bandClear: Int64 = 10", theme)


# Mirror of chapter.cj ChapterCatalog. Every chapter is open with 10 boards:
# levelStart = id * 10, levelCount = 10. isOpen is cleared >= levelStart.
# Chapters 4–9 also have a skin preview (hasSkinPreview); that is separate from unlock.
SHIP_CHAPTERS = (
    {
        "id": 0,
        "name": "涿郡",
        "label": "第1章 涿郡",
        "title": "涿郡·安喜",
        "subtitle": "仓官×渠帅 · 汉×黄 · 黄巾乱世出粮",
        "listSubtitle": "仓官×渠帅 · 汉×黄 · 安喜",
        "boardSubtitle": "仓官×渠帅 · 汉×黄 · 安喜",
        "friend": "汉廷官仓",
        "tension": "黄巾乱世出粮",
        "city": "涿·安喜",
        "open": True,
        "levelStart": 0,
        "levelCount": 10,
        "leftBust": "bust_p01_cangguan",
        "leftFlag": "flag_p01_han",
        "rightBust": "bust_p02_huangjin",
        "rightFlag": "flag_p02_huang",
        "skin": "skin_01_zhuojun_v91",
        "band": "band_zhuojun_v91",
        "preview": False,
    },
    {
        "id": 1,
        "name": "平原",
        "label": "第2章 平原",
        "title": "平原·郡治",
        "subtitle": "公孙×袁绍 · 袁绍为敌",
        "listSubtitle": "公孙×袁绍 · 公孙×袁 · 郡治",
        "boardSubtitle": "公孙×袁绍 · 公孙×袁 · 郡治",
        "friend": "公孙瓒",
        "tension": "袁绍为敌",
        "city": "高唐·郡治",
        "open": True,
        "levelStart": 10,
        "levelCount": 10,
        "leftBust": "bust_p03_gongsun",
        "leftFlag": "flag_p03_gongsun",
        "rightBust": "bust_p04_yuanshao",
        "rightFlag": "flag_p04_yuan",
        "skin": "skin_02_pingyuan_v91",
        "band": "band_pingyuan_v91",
        "preview": False,
    },
    {
        "id": 2,
        "name": "徐州",
        "label": "第3章 徐州",
        "title": "徐州·下邳",
        "subtitle": "刘×曹 · 淮泗争粮",
        "listSubtitle": "刘×曹 · 淮泗争粮",
        "boardSubtitle": "刘×曹 · 淮泗争粮",
        "friend": "刘备",
        "tension": "淮泗争粮",
        "city": "徐州·下邳",
        "open": True,
        "levelStart": 20,
        "levelCount": 10,
        "leftBust": "bust_p05_liubei",
        "leftFlag": "flag_p05_liu",
        "rightBust": "bust_p06_caocao",
        "rightFlag": "flag_p06_cao",
        "skin": "",
        "preview": False,
    },
    {
        "id": 3,
        "name": "吕布",
        "label": "第4章 吕布",
        "title": "吕布章",
        "subtitle": "吕×曹 · 下邳同仓",
        "listSubtitle": "吕×曹 · 下邳同仓",
        "boardSubtitle": "吕×曹 · 下邳同仓",
        "friend": "吕布",
        "tension": "下邳同仓",
        "city": "下邳",
        "open": True,
        "levelStart": 30,
        "levelCount": 10,
        "leftBust": "bust_p07_lvbu",
        "leftFlag": "flag_p07_lv",
        "rightBust": "bust_p06_caocao",
        "rightFlag": "flag_p06_cao",
        "skin": "",
        "preview": False,
    },
    {
        "id": 4,
        "name": "投袁",
        "label": "第5章 投袁",
        "title": "投袁·邺",
        "subtitle": "乌巢仓破、半印失散；北不可回",
        "listSubtitle": "袁绍×曹操 · 袁×曹 · 邺",
        "boardSubtitle": "袁绍×曹操 · 袁×曹 · 邺",
        "friend": "袁→备",
        "tension": "乌巢仓破、半印失散；北不可回",
        "city": "邺（乌巢仓影可辅）",
        "open": True,
        "levelStart": 40,
        "levelCount": 10,
        "leftBust": "bust_p04_yuanshao",
        "leftFlag": "flag_p04_yuan",
        "rightBust": "bust_p06_caocao",
        "rightFlag": "flag_p06_cao",
        "skin": "skin_05_touyuan_v91",
        "card": "card_05_touyuan_v91",
        "paper": "0XE8E4DC",
        "preview": True,
    },
    {
        "id": 5,
        "name": "荆州",
        "label": "第6章 荆州",
        "title": "荆州·襄阳",
        "subtitle": "刘表辖下友道；不给曹营送",
        "listSubtitle": "刘备×曹操 · 刘×曹 · 襄阳",
        "boardSubtitle": "刘备×曹操 · 刘×曹 · 襄阳",
        "friend": "刘表",
        "tension": "刘表辖下友道；不给曹营送",
        "city": "襄阳",
        "open": True,
        "levelStart": 50,
        "levelCount": 10,
        "leftBust": "bust_p05_liubei",
        "leftFlag": "flag_p05_liu",
        "rightBust": "bust_p06_caocao",
        "rightFlag": "flag_p06_cao",
        "skin": "skin_06_jingzhou_v91",
        "card": "card_06_jingzhou_v91",
        "paper": "0XE8EDE8",
        "preview": True,
    },
    {
        "id": 6,
        "name": "赤壁",
        "label": "第7章 赤壁",
        "title": "赤壁·柴桑",
        "subtitle": "孙刘联军岸；不往乌林送曹营",
        "listSubtitle": "孙权×曹操 · 孙×曹 · 柴桑",
        "boardSubtitle": "孙权×曹操 · 孙×曹 · 柴桑",
        "friend": "孙刘",
        "tension": "孙刘联军岸；不往乌林送曹营",
        "city": "柴桑",
        "open": True,
        "levelStart": 60,
        "levelCount": 10,
        "leftBust": "bust_p08_sunquan",
        "leftFlag": "flag_p08_sun",
        "rightBust": "bust_p06_caocao",
        "rightFlag": "flag_p06_cao",
        "skin": "skin_07_chibi_v91",
        "card": "card_07_chibi_v91",
        "paper": "0XE2E4EA",
        "preview": True,
    },
    {
        "id": 7,
        "name": "入蜀",
        "label": "第8章 入蜀",
        "title": "入蜀·白水关",
        "subtitle": "峡江入川关隘递进；非曹粮道，勿挂曹脸",
        "listSubtitle": "刘备×关隘影 · 刘×纹样 · 白水关",
        "boardSubtitle": "刘备×关隘影 · 刘×纹样 · 白水关",
        "friend": "蜀",
        "tension": "峡江入川关隘递进；非曹粮道，勿挂曹脸",
        "city": "白水关（辅成都）",
        "open": True,
        "levelStart": 70,
        "levelCount": 10,
        "leftBust": "bust_p05_liubei",
        "leftFlag": "flag_p05_liu",
        "rightBust": "bust_s01_guanai",
        "rightFlag": "flag_gate_pattern",
        "skin": "skin_08_rushu_v91",
        "card": "card_08_rushu_v91",
        "paper": "0XE6E8E2",
        "preview": True,
    },
    {
        "id": 8,
        "name": "汉中南中",
        "label": "第9章 汉中南中",
        "title": "汉中南中·阳平关",
        "subtitle": "两道分运：汉中关城 vs 南中北运",
        "listSubtitle": "诸葛×曹操 · 诸葛×曹 · 阳平关",
        "boardSubtitle": "诸葛×曹操 · 诸葛×曹 · 阳平关",
        "friend": "诸葛",
        "tension": "两道分运：汉中关城 vs 南中北运",
        "city": "阳平关",
        "open": True,
        "levelStart": 80,
        "levelCount": 10,
        "leftBust": "bust_p09_zhugeliang",
        "leftFlag": "flag_p09_zhuge",
        "rightBust": "bust_p06_caocao",
        "rightFlag": "flag_p06_cao",
        "skin": "skin_09_hanzhong_v91",
        "card": "card_09_hanzhong_v91",
        "paper": "0XE4E8E6",
        "preview": True,
    },
    {
        "id": 9,
        "name": "北伐",
        "label": "第10章 北伐",
        "title": "北伐·五丈原",
        "subtitle": "对魏远征；街亭/空仓余韵",
        "listSubtitle": "诸葛×司马 · 诸葛×司马 · 五丈原",
        "boardSubtitle": "诸葛×司马 · 诸葛×司马 · 五丈原",
        "friend": "诸葛",
        "tension": "对魏远征；街亭/空仓余韵",
        "city": "五丈原",
        "open": True,
        "levelStart": 90,
        "levelCount": 10,
        "leftBust": "bust_p09_zhugeliang",
        "leftFlag": "flag_p09_zhuge",
        "rightBust": "bust_p10_simayi",
        "rightFlag": "flag_p10_sima",
        "skin": "skin_10_beifa_v91",
        "card": "card_10_beifa_v91",
        "paper": "0XEDE6D8",
        "preview": True,
    },
)

SHIP_MEDIA = (
    "bust_p01_cangguan",
    "bust_p02_huangjin",
    "bust_p03_gongsun",
    "bust_p04_yuanshao",
    "bust_p05_liubei",
    "bust_p06_caocao",
    "bust_p07_lvbu",
    "bust_p08_sunquan",
    "bust_p09_zhugeliang",
    "bust_p10_simayi",
    "bust_s01_guanai",
    "flag_p01_han",
    "flag_p02_huang",
    "flag_p03_gongsun",
    "flag_p04_yuan",
    "flag_p05_liu",
    "flag_p06_cao",
    "flag_p07_lv",
    "flag_p08_sun",
    "flag_p09_zhuge",
    "flag_p10_sima",
    "flag_gate_pattern",
    "skin_01_zhuojun_v91",
    "skin_02_pingyuan_v91",
    "skin_05_touyuan_v91",
    "skin_06_jingzhou_v91",
    "skin_07_chibi_v91",
    "skin_08_rushu_v91",
    "skin_09_hanzhong_v91",
    "skin_10_beifa_v91",
    "card_05_touyuan_v91",
    "card_06_jingzhou_v91",
    "card_07_chibi_v91",
    "card_08_rushu_v91",
    "card_09_hanzhong_v91",
    "card_10_beifa_v91",
    "band_zhuojun_v91",
    "band_pingyuan_v91",
)


def chapter_has_skin_preview(chapter_id: int) -> bool:
    return bool(chapter_by_id(chapter_id).get("preview"))

# BANDS.md locked geometry on the 1080×1920 / SCALE 3 design canvas.
BAND_SCALE = 3
BAND_ORIGIN_PX = (0, 246)
BAND_SIZE_PX = (1080, 300)
BAND_SIZE_VP = (360, 100)
BOARD_TOP_PX = 576
BOARD_CLEAR_PX = 30


def board_band_name(level_index: int) -> str:
    """Composite landscape band: 涿郡 0–9, 平原 10–19."""
    if level_index < 10:
        return "band_zhuojun_v91"
    return "band_pingyuan_v91"


def band_bottom_px() -> int:
    return BAND_ORIGIN_PX[1] + BAND_SIZE_PX[1]


def band_clears_board() -> bool:
    """Hard rule: band.bottom ≤ board.top − 30 so bust/flags never enter the grid."""
    return band_bottom_px() <= BOARD_TOP_PX - BOARD_CLEAR_PX


def chapter_by_id(chapter_id: int) -> dict:
    return next(ch for ch in SHIP_CHAPTERS if ch["id"] == chapter_id)


def chapter_is_open(chapter_id: int, cleared: int) -> bool:
    """Runtime unlock: catalog.open is 'has boards', not 'currently unlocked'."""
    ch = chapter_by_id(chapter_id)
    if not ch["open"] or ch["levelCount"] <= 0:
        return False
    return cleared >= ch["levelStart"]


def chapter_selectable(chapter_id: int, cleared: int) -> bool:
    return chapter_is_open(chapter_id, cleared)


def chapter_open_count(cleared: int) -> int:
    return sum(1 for ch in SHIP_CHAPTERS if chapter_is_open(ch["id"], cleared))


def chapter_open_footer(cleared: int) -> str:
    opened = chapter_open_count(cleared)
    locked = len(SHIP_CHAPTERS) - opened
    return f"已开 {opened} · 未启 {locked} · 点开章入驿程"


def chapter_current_label(chapter_id: int, cleared: int, levels: list[dict]) -> str:
    """驿程 footer / 当前章: locked 平原 must not be presented as current."""
    if not chapter_is_open(chapter_id, cleared):
        return "未开"
    ch = chapter_by_id(chapter_id)
    end = ch["levelStart"] + ch["levelCount"]
    if cleared >= end:
        return "已通"
    idx = cleared if cleared >= ch["levelStart"] else ch["levelStart"]
    return next(lv["name"] for lv in levels if int(lv["id"]) == idx)


def chapter_cleared_count(chapter_id: int, cleared: int) -> int:
    ch = chapter_by_id(chapter_id)
    if ch["levelCount"] <= 0:
        return 0
    if cleared <= ch["levelStart"]:
        return 0
    return min(cleared - ch["levelStart"], ch["levelCount"])


def chapter_levels(levels: list[dict], chapter_id: int) -> list[dict]:
    ch = chapter_by_id(chapter_id)
    start = ch["levelStart"]
    return [lv for lv in levels if start <= int(lv["id"]) < start + ch["levelCount"]]


def continue_level_index(cleared: int, count: int) -> int:
    if cleared >= count:
        return count - 1
    return cleared


def is_dessert_level(level: dict) -> bool:
    """SHIP 点心: 涿郡·中山. Mock 第5驿 = JSON id 4 (not 中山·第 2 驿 id 5)."""
    return int(level["id"]) == 4 and level["name"] == "涿郡·中山"


def chrome_line(chapter_id: int) -> str:
    ch = chapter_by_id(chapter_id)
    return f"友：{ch['friend']} · 张力：{ch['tension']} · 城：{ch['city']}"


def _screen_branch(ui: str, screen: int) -> str:
    token = f"this.screen == {screen}"
    build = ui.index("func build()")
    start = ui.index(token, build)
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


class ChapterFlowV13Tests(unittest.TestCase):
    """Locked chapter-flow: 10 cards; 平原 unlocks after 涿郡 10 stations."""

    def test_ship_cards_match_locked_copy(self) -> None:
        self.assertEqual([ch["title"] for ch in SHIP_CHAPTERS], [
            "涿郡·安喜",
            "平原·郡治",
            "徐州·下邳",
            "吕布章",
            "投袁·邺",
            "荆州·襄阳",
            "赤壁·柴桑",
            "入蜀·白水关",
            "汉中南中·阳平关",
            "北伐·五丈原",
        ])
        self.assertEqual([ch["subtitle"] for ch in SHIP_CHAPTERS], [
            "仓官×渠帅 · 汉×黄 · 黄巾乱世出粮",
            "公孙×袁绍 · 袁绍为敌",
            "刘×曹 · 淮泗争粮",
            "吕×曹 · 下邳同仓",
            "乌巢仓破、半印失散；北不可回",
            "刘表辖下友道；不给曹营送",
            "孙刘联军岸；不往乌林送曹营",
            "峡江入川关隘递进；非曹粮道，勿挂曹脸",
            "两道分运：汉中关城 vs 南中北运",
            "对魏远征；街亭/空仓余韵",
        ])
        self.assertEqual([ch["label"] for ch in SHIP_CHAPTERS][4:], [
            "第5章 投袁",
            "第6章 荆州",
            "第7章 赤壁",
            "第8章 入蜀",
            "第9章 汉中南中",
            "第10章 北伐",
        ])
        # chapter.cj: every chapter is open, levelStart = id * 10, levelCount = 10.
        # isOpen is cleared >= levelStart. 平原 at 10, 徐州 at 20, 吕布 at 30, …, 北伐 at 90.
        self.assertEqual([ch["open"] for ch in SHIP_CHAPTERS], [True] * 10)
        self.assertEqual(
            [(ch["levelStart"], ch["levelCount"]) for ch in SHIP_CHAPTERS],
            [(i * 10, 10) for i in range(10)],
        )
        self.assertTrue(chapter_selectable(0, 0))
        self.assertFalse(chapter_selectable(1, 0))
        self.assertTrue(chapter_selectable(1, 10))
        self.assertFalse(chapter_selectable(2, 0))
        self.assertFalse(chapter_selectable(2, 10))
        self.assertTrue(chapter_selectable(2, 20))
        self.assertFalse(chapter_selectable(3, 0))
        self.assertFalse(chapter_selectable(3, 20))
        self.assertTrue(chapter_selectable(3, 30))
        self.assertFalse(chapter_selectable(4, 20))
        self.assertTrue(chapter_selectable(4, 40))
        self.assertFalse(chapter_selectable(9, 20))
        self.assertFalse(chapter_selectable(9, 80))
        self.assertTrue(chapter_selectable(9, 90))
        self.assertEqual(chapter_by_id(7)["rightFlag"], "flag_gate_pattern")
        self.assertNotEqual(chapter_by_id(7)["rightFlag"], "flag_s01_guan")
        self.assertEqual(chapter_by_id(8)["leftFlag"], "flag_p09_zhuge")
        self.assertEqual(chapter_by_id(9)["rightFlag"], "flag_p10_sima")
        self.assertIn("诸葛", chapter_by_id(8)["listSubtitle"])
        self.assertIn("司马", chapter_by_id(9)["listSubtitle"])

    def test_pingyuan_opens_only_after_zhuojun_cleared(self) -> None:
        """平原 opens at cleared >= 10; 徐州 at >= 20; each chapter at id * 10."""
        for cleared in (0, 3, 9):
            self.assertTrue(chapter_is_open(0, cleared), cleared)
            self.assertFalse(chapter_is_open(1, cleared), cleared)
            self.assertFalse(chapter_selectable(1, cleared), cleared)
            self.assertEqual(chapter_open_count(cleared), 1)
            self.assertEqual(chapter_open_footer(cleared), "已开 1 · 未启 9 · 点开章入驿程")
        self.assertTrue(chapter_is_open(1, 10))
        self.assertTrue(chapter_selectable(1, 10))
        self.assertEqual(chapter_open_count(10), 2)
        self.assertEqual(chapter_open_footer(10), "已开 2 · 未启 8 · 点开章入驿程")
        self.assertFalse(chapter_is_open(2, 10))
        self.assertTrue(chapter_is_open(2, 20))
        self.assertEqual(chapter_open_count(20), 3)
        self.assertFalse(chapter_is_open(3, 20))
        self.assertTrue(chapter_is_open(3, 30))
        for chapter_id in range(4, 10):
            start = chapter_id * 10
            self.assertFalse(chapter_is_open(chapter_id, 20), chapter_id)
            self.assertFalse(chapter_is_open(chapter_id, start - 1), chapter_id)
            self.assertTrue(chapter_is_open(chapter_id, start), chapter_id)
            self.assertTrue(chapter_has_skin_preview(chapter_id), chapter_id)
        self.assertFalse(chapter_has_skin_preview(2))
        self.assertFalse(chapter_has_skin_preview(3))
        self.assertEqual(chapter_cleared_count(1, 0), 0)
        self.assertEqual(chapter_cleared_count(0, 3), 3)
        levels = load_levels(ROOT / "entry/src/main/resources/rawfile/levels.json")
        self.assertEqual(chapter_current_label(1, 0, levels), "未开")
        self.assertEqual(chapter_current_label(1, 9, levels), "未开")
        self.assertNotIn("平原", chapter_current_label(0, 0, levels))
        self.assertEqual(chapter_current_label(1, 10, levels), levels[10]["name"])

    def test_each_chapter_has_ten_boards(self) -> None:
        levels = load_levels(ROOT / "entry/src/main/resources/rawfile/levels.json")
        for chapter_id in range(10):
            start = chapter_id * 10
            boards = chapter_levels(levels, chapter_id)
            self.assertEqual(
                [int(lv["id"]) for lv in boards],
                list(range(start, start + 10)),
                chapter_id,
            )
        from build_levels import EXPECTED_NAMES

        self.assertEqual(len(levels), len(EXPECTED_NAMES))
        names = [lv["name"] for lv in levels]
        for prefix in ("徐州", "吕布", "投袁", "荆州", "赤壁", "入蜀", "汉中", "北伐"):
            self.assertTrue(any(n.startswith(prefix) for n in names), prefix)

    def test_station_names_and_sizes_come_from_json_only(self) -> None:
        levels = load_levels(ROOT / "entry/src/main/resources/rawfile/levels.json")
        zhuo = chapter_levels(levels, 0)
        self.assertEqual([lv["name"] for lv in zhuo], [
            "涿郡·涿",
            "涿郡·范阳",
            "涿郡·故安",
            "涿郡·遒",
            "涿郡·中山",
            "涿郡·中山·第 2 驿",
            "涿郡·卢奴",
            "涿郡·卢奴·第 2 驿",
            "涿郡·安喜",
            "涿郡·安喜·第 2 驿",
        ])
        self.assertTrue(
            all((int(lv["cols"]), int(lv["rows"])) == (6, 6) for lv in levels if int(lv["id"]) < 30)
        )
        self.assertTrue(
            all((int(lv["cols"]), int(lv["rows"])) == (7, 7) for lv in levels if int(lv["id"]) >= 30)
        )
        self.assertTrue(all(is_dessert_level(lv) is (int(lv["id"]) == 4) for lv in zhuo))
        self.assertTrue(is_dessert_level(zhuo[4]))
        self.assertFalse(is_dessert_level(zhuo[5]))

    def test_continue_opens_current_unlock(self) -> None:
        self.assertEqual(continue_level_index(0, 20), 0)
        self.assertEqual(continue_level_index(12, 20), 12)
        self.assertEqual(continue_level_index(20, 20), 19)

    def test_board_chrome_lines(self) -> None:
        self.assertEqual(chrome_line(0), "友：汉廷官仓 · 张力：黄巾乱世出粮 · 城：涿·安喜")
        self.assertEqual(chrome_line(1), "友：公孙瓒 · 张力：袁绍为敌 · 城：高唐·郡治")

    def test_cangjie_catalog_ships_ten_cards(self) -> None:
        src = (ROOT / "entry/src/main/cangjie/chapter.cj").read_text(encoding="utf-8")
        self.assertIn("class ChapterCatalog", src)
        for phrase in (
            "涿郡·安喜",
            "平原·郡治",
            "徐州·下邳",
            "吕布章",
            "投袁·邺",
            "荆州·襄阳",
            "赤壁·柴桑",
            "入蜀·白水关",
            "汉中南中·阳平关",
            "北伐·五丈原",
            "第5章 投袁",
            "第10章 北伐",
            "仓官×渠帅 · 汉×黄 · 黄巾乱世出粮",
            "公孙×袁绍 · 袁绍为敌",
            "刘×曹 · 淮泗争粮",
            "吕×曹 · 下邳同仓",
            "乌巢仓破、半印失散；北不可回",
            "诸葛×司马",
            "汉廷官仓",
            "公孙瓒",
            "高唐·郡治",
        ):
            self.assertIn(phrase, src)
        self.assertIn("诸葛", src)
        self.assertIn("司马", src)
        self.assertNotIn("flag-s01-guan", src)
        self.assertNotIn("flag_s01_guan", src)
        self.assertIn("func isDessert(", src)
        dessert = _func_body(src, "isDessert")
        self.assertIn("levelId == 4", dessert)
        is_open = _func_body(src, "isOpen")
        self.assertIn("cleared", is_open)
        self.assertIn("levelStart", is_open)
        selectable = _func_body(src, "selectable")
        self.assertIn("cleared", selectable)
        self.assertIn("isOpen", selectable)
        preview = _func_body(src, "hasSkinPreview")
        self.assertIn("chapterId >= 4", preview)
        self.assertIn("chapterId <= 9", preview)

    def test_home_keeps_yicheng_and_adds_chapters(self) -> None:
        ui = (ROOT / "entry/src/main/cangjie/index.cj").read_text(encoding="utf-8")
        home = _screen_branch(ui, 0)
        self.assertIn("章节", home)
        self.assertIn("驿程", home)
        self.assertIn("开始传书", home)
        self.assertIn("this.screen = 4", home)
        self.assertIn("this.screen = 3", home)
        self.assertIn("this.startPlay()", home)
        start = _func_body(ui, "startPlay")
        self.assertIn("this.cleared", start)
        self.assertIn("this.openLevel", start)

    def test_screen_3_stays_flat_yicheng(self) -> None:
        ui = (ROOT / "entry/src/main/cangjie/index.cj").read_text(encoding="utf-8")
        yicheng = _screen_branch(ui, 3)
        self.assertIn("驿程", yicheng)
        self.assertIn("LevelCatalog.all()", yicheng)
        self.assertNotIn("ChapterCatalog.all()", yicheng)

    def test_screen_4_is_ten_chapter_cards(self) -> None:
        ui = (ROOT / "entry/src/main/cangjie/index.cj").read_text(encoding="utf-8")
        cards = _screen_branch(ui, 4)
        self.assertIn("ChapterCatalog.all()", cards)
        self.assertIn("选章入驿 · 开章可入 · 灰章未启", cards)
        self.assertIn("可入", cards)
        self.assertIn("未开", cards)
        self.assertNotIn("已开 2 · 未启 2 · 点开章入驿程", cards)
        self.assertIn("chapterOpenFooter", cards)
        self.assertIn("chapterOpen(", cards)
        self.assertNotIn("item.open", cards)
        self.assertIn("Theme.chapterCardH", cards)
        self.assertIn("Theme.chapterThumbRowW", cards)
        self.assertIn("Theme.flagThumbW", cards)
        self.assertIn("Theme.bustThumbW", cards)
        self.assertIn("@r(app.media.bust_p01_cangguan)", cards)
        self.assertIn("@r(app.media.flag_p01_han)", cards)
        self.assertIn("@r(app.media.bust_p03_gongsun)", cards)
        self.assertIn("@r(app.media.flag_p04_yuan)", cards)
        self.assertIn("@r(app.media.bust_p08_sunquan)", cards)
        self.assertIn("@r(app.media.flag_p08_sun)", cards)
        self.assertIn("@r(app.media.bust_p09_zhugeliang)", cards)
        self.assertIn("@r(app.media.flag_p09_zhuge)", cards)
        self.assertIn("@r(app.media.bust_p10_simayi)", cards)
        self.assertIn("@r(app.media.flag_p10_sima)", cards)
        self.assertIn("@r(app.media.bust_s01_guanai)", cards)
        self.assertIn("@r(app.media.flag_gate_pattern)", cards)
        self.assertIn("@r(app.media.card_05_touyuan_v91)", cards)
        self.assertIn("@r(app.media.card_06_jingzhou_v91)", cards)
        self.assertIn("@r(app.media.card_07_chibi_v91)", cards)
        self.assertIn("@r(app.media.card_08_rushu_v91)", cards)
        self.assertIn("@r(app.media.card_09_hanzhong_v91)", cards)
        self.assertIn("@r(app.media.card_10_beifa_v91)", cards)
        self.assertIn("Theme.chapterSkinCardH", cards)
        self.assertNotIn("flag-s01-guan", cards)
        self.assertNotIn("flag_s01_guan", cards)
        self.assertIn("this.openChapter(item.id)", cards)
        self.assertIn("this.screen = 0", cards)
        self.assertNotIn("LevelCatalog.all()", cards)

    def test_screen_5_lists_ten_json_stations(self) -> None:
        ui = (ROOT / "entry/src/main/cangjie/index.cj").read_text(encoding="utf-8")
        stations = _screen_branch(ui, 5)
        self.assertIn("ChapterCatalog.levelsOf", stations)
        self.assertIn("item.cols", stations)
        self.assertIn("item.rows", stations)
        self.assertIn("点心", stations)
        self.assertIn("isDessert", stations)
        self.assertIn("openFromList", stations)
        self.assertIn("this.screen = 4", stations)
        self.assertIn("共10驿", stations)
        self.assertNotIn("LevelCatalog.all()", stations)
        self.assertNotIn("5×5", stations)
        self.assertNotIn("5x5", stations)

    def test_screen_6_is_fullscreen_skin_preview(self) -> None:
        """Locked 05–10 open a preview screen; no boards, no 涿/平原 skins."""
        ui = (ROOT / "entry/src/main/cangjie/index.cj").read_text(encoding="utf-8")
        preview = _screen_branch(ui, 6)
        self.assertIn("@r(app.media.skin_05_touyuan_v91)", preview)
        self.assertIn("@r(app.media.skin_06_jingzhou_v91)", preview)
        self.assertIn("@r(app.media.skin_07_chibi_v91)", preview)
        self.assertIn("@r(app.media.skin_08_rushu_v91)", preview)
        self.assertIn("@r(app.media.skin_09_hanzhong_v91)", preview)
        self.assertIn("@r(app.media.skin_10_beifa_v91)", preview)
        self.assertIn("ImageFit.Contain", preview)
        self.assertIn("this.currentChapter().title", preview)
        self.assertIn("this.screen = 4", preview)
        self.assertNotIn("ChapterCatalog.levelsOf", preview)
        self.assertNotIn("Canvas(this.context)", preview)
        self.assertNotIn("@r(app.media.skin_01_zhuojun_v91)", preview)
        self.assertNotIn("@r(app.media.skin_02_pingyuan_v91)", preview)
        self.assertNotIn("flag-s01-guan", ui)
        self.assertNotIn("flag_s01_guan", ui)
        open_ch = _func_body(ui, "openChapter")
        self.assertIn("hasSkinPreview", open_ch)
        self.assertIn("this.screen = 6", open_ch)
        self.assertLess(open_ch.index("return"), open_ch.index("this.screen = 5"))
        paper = _func_body(ui, "playPaper")
        self.assertIn("this.screen == 6", paper)
        self.assertIn("Theme.paperOf", paper)
        self.assertIn("this.screen == 2", paper)
        self.assertIn("this.levelIndex >= 10", paper)
        self.assertIn("Theme.pingyuanPaper", paper)
        self.assertEqual(
            [play_paper(screen, 10, 1) for screen in (0, 1, 2, 3, 4, 5, 6)],
            ["paper", "pingyuan", "pingyuan", "paper", "paper", "paper", "paperOf"],
        )
        self.assertEqual(play_paper(2, 9, 0), "paper")
        self.assertEqual(play_paper(1, 9, 0), "paper")

    def test_board_chrome_uses_landscape_bands_and_keeps_path2d_bar(self) -> None:
        """screen==1: composite band above the grid, not bust/flag thumbs or skins."""
        ui = (ROOT / "entry/src/main/cangjie/index.cj").read_text(encoding="utf-8")
        board = _screen_branch(ui, 1)
        self.assertIn("@r(app.media.band_zhuojun_v91)", board)
        self.assertIn("@r(app.media.band_pingyuan_v91)", board)
        self.assertIn("this.levelIndex < 10", board)
        self.assertIn("100.percent", board)
        self.assertIn("Theme.bandH", board)
        self.assertIn("Theme.bandClear", board)
        self.assertIn("this.roadTitle()", board)
        self.assertIn("this.boardSubtitle()", board)
        # Composite already has bust+flag+terrain — do not restack thumbs on the board.
        self.assertNotIn("@r(app.media.bust_p01_cangguan)", board)
        self.assertNotIn("@r(app.media.flag_p01_han)", board)
        self.assertNotIn("@r(app.media.bust_p03_gongsun)", board)
        self.assertNotIn("@r(app.media.flag_p04_yuan)", board)
        # Official skins are 1080×1920 full-screen mocks. Putting them in the
        # 64vp chrome strip recreates the overflow/blur reject of PR #12.
        self.assertNotIn("@r(app.media.skin_01_zhuojun_v91)", ui)
        self.assertNotIn("@r(app.media.skin_02_pingyuan_v91)", ui)
        self.assertIn("友：", ui)
        self.assertIn("张力：", ui)
        self.assertIn("城：", ui)
        self.assertIn("chromeLine", ui)
        self.assertIn("boardSubtitle", ui)
        bar = _play_bottom_bar(ui)
        self.assertIn("撤销", bar)
        self.assertIn("重绘驿道", bar)
        self.assertIn("Path2D()", _func_body(ui, "drawUndoIcon"))
        self.assertIn("Path2D()", _func_body(ui, "drawRedrawIcon"))
        self.assertGreater(board.index("@r(app.media.band_zhuojun_v91)"), board.index("this.roadTitle()"))
        self.assertGreater(board.index("Canvas(this.context)"), board.index("Theme.bandH"))

    def test_band_geometry_clears_the_grid(self) -> None:
        """BANDS.md: origin (0,246) h=300; band.bottom ≤ board.top − 30."""
        self.assertEqual(BAND_ORIGIN_PX, (0, 246))
        self.assertEqual(BAND_SIZE_PX, (1080, 300))
        self.assertEqual(BAND_SIZE_VP, (360, 100))
        self.assertEqual(BAND_SIZE_PX[0] // BAND_SCALE, BAND_SIZE_VP[0])
        self.assertEqual(BAND_SIZE_PX[1] // BAND_SCALE, BAND_SIZE_VP[1])
        self.assertEqual(BOARD_CLEAR_PX // BAND_SCALE, 10)
        self.assertEqual(band_bottom_px(), 546)
        self.assertTrue(band_clears_board())
        self.assertEqual(BOARD_TOP_PX - band_bottom_px(), BOARD_CLEAR_PX)
        self.assertEqual([board_band_name(i) for i in range(10)], ["band_zhuojun_v91"] * 10)
        self.assertEqual([board_band_name(i) for i in range(10, 20)], ["band_pingyuan_v91"] * 10)
        self.assertEqual(chapter_by_id(0)["band"], "band_zhuojun_v91")
        self.assertEqual(chapter_by_id(1)["band"], "band_pingyuan_v91")

    def test_win_keeps_pingyuan_paper_and_ignores_trailing_drag(self) -> None:
        """平原 通关 (screen==2) stays sage; trailing Move cannot undo."""
        ui = (ROOT / "entry/src/main/cangjie/index.cj").read_text(encoding="utf-8")
        paper = _func_body(ui, "playPaper")
        self.assertIn("this.screen == 1 || this.screen == 2", paper)
        self.assertIn("this.levelIndex >= 10", paper)
        drag = _func_body(ui, "handleDrag")
        self.assertIn("this.screen != 1", drag)
        self.assertLess(drag.index("this.screen != 1"), drag.index("event.touches"))
        self.assertLess(drag.index("return"), drag.index("tryStep"))

    def test_progress_lock_intact_after_bands(self) -> None:
        """平原 opens at cleared >= 10; 徐州 at >= 20; each later chapter at id * 10."""
        for cleared in (0, 3, 9):
            self.assertTrue(chapter_is_open(0, cleared), cleared)
            self.assertFalse(chapter_is_open(1, cleared), cleared)
            self.assertFalse(chapter_selectable(1, cleared), cleared)
        self.assertTrue(chapter_is_open(1, 10))
        self.assertFalse(chapter_is_open(2, 10))
        self.assertTrue(chapter_is_open(2, 20))
        self.assertFalse(chapter_is_open(3, 20))
        self.assertTrue(chapter_is_open(3, 30))
        for chapter_id in range(4, 10):
            start = chapter_id * 10
            self.assertFalse(chapter_is_open(chapter_id, 9), chapter_id)
            self.assertFalse(chapter_is_open(chapter_id, 20), chapter_id)
            self.assertTrue(chapter_is_open(chapter_id, start), chapter_id)
        src = (ROOT / "entry/src/main/cangjie/chapter.cj").read_text(encoding="utf-8")
        self.assertIn("func isOpen(", src)
        self.assertIn("cleared >= ch.levelStart", _func_body(src, "isOpen"))
        ui = (ROOT / "entry/src/main/cangjie/index.cj").read_text(encoding="utf-8")
        self.assertIn("ChapterCatalog.isOpen(id, this.cleared)", _func_body(ui, "openChapter"))

    def test_p1_skins_do_not_move_layout_or_lock(self) -> None:
        """P1 (ab3c9c9): 09 dual-tone + mock 6×6 only. BOARD_OY / isOpen frozen."""
        ship = (ROOT / "mockups/chapter-skins-v9/ch05-10-SHIP.md").read_text(encoding="utf-8")
        self.assertIn("示意盘 **6×6**", ship)
        self.assertIn("09 双调加力", ship)
        self.assertIn("BOARD_OY_VP=**202**", ship)
        self.assertIn("改为 lock **6×6**", ship)
        theme = (ROOT / "entry/src/main/cangjie/theme.cj").read_text(encoding="utf-8")
        self.assertIn("bandH: Int64 = 100", theme)
        self.assertIn("bandClear: Int64 = 10", theme)
        self.assertIn("designW: Int64 = 360", theme)
        is_open = _func_body(
            (ROOT / "entry/src/main/cangjie/chapter.cj").read_text(encoding="utf-8"),
            "isOpen",
        )
        self.assertIn("cleared >= ch.levelStart", is_open)
        self.assertIn("!ch.open", is_open)
        self.assertIn("ch.levelCount <= 0", is_open)
        # Exact P1 tip blobs (assets/chapter-skins-05-10-v91 @ ab3c9c9).
        p1_skins = {
            "skin_05_touyuan_v91.png": "db204dc88f59757a151d0d387b6b975bd672ccb969a09e55c23fd4a1c57b93cf",
            "skin_06_jingzhou_v91.png": "b18b18528a4a1a524647a08f5d34a0d12b747dc46049aebe6c1515843233182b",
            "skin_07_chibi_v91.png": "ee0b4558b3e8fa18398aee9b673558cec00df2324f46ccbecc3107a727a3f5ec",
            "skin_08_rushu_v91.png": "2a795d5f606223f48ef2af07c02fe42df90306b5fb82727658dee3113f55cda6",
            "skin_09_hanzhong_v91.png": "340d748a0e1f0bca58a1e3c8071ab90444071e84cb252f23bc2a8761d2109682",
            "skin_10_beifa_v91.png": "002469587684464c2e51239a720255cb604e75cd6cfbdf2b3ae0030fa961b9b6",
        }
        media = ROOT / "entry/src/main/resources/base/media"
        for name, digest in p1_skins.items():
            blob = (media / name).read_bytes()
            self.assertEqual(hashlib.sha256(blob).hexdigest(), digest, name)

    def test_open_chapter_refuses_locked_cards(self) -> None:
        ui = (ROOT / "entry/src/main/cangjie/index.cj").read_text(encoding="utf-8")
        body = _func_body(ui, "openChapter")
        self.assertIn("this.cleared", body)
        self.assertTrue("isOpen" in body or "selectable" in body)
        self.assertIn("return", body)
        self.assertLess(body.index("return"), body.index("this.screen = 5"))
        self.assertIn("this.screen = 5", body)
        current = _func_body(ui, "chapterCurrentName")
        self.assertIn("isOpen", current)
        footer = _func_body(ui, "chapterOpenFooter")
        self.assertIn("openCount", footer)
        self.assertIn("已开", footer)
        self.assertIn("未启", footer)
        helper = (ROOT / "entry/src/main/cangjie/resource_helper.cj").read_text(encoding="utf-8")
        self.assertIn("__GenerateResource__", helper)

    def test_media_files_exist_under_base_media(self) -> None:
        from PIL import Image

        media = ROOT / "entry/src/main/resources/base/media"
        for name in SHIP_MEDIA:
            matches = list(media.glob(f"{name}.*"))
            self.assertTrue(matches, f"missing media {name}")
            path = matches[0]
            min_bytes = 4000 if name == "bust_s01_guanai" else 8000
            self.assertGreater(path.stat().st_size, min_bytes, f"{name} looks like a placeholder")
            with Image.open(path) as im:
                if name.startswith("bust_"):
                    self.assertEqual(im.size, (600, 800), name)
                    self.assertEqual(im.mode, "RGBA", name)
                elif name.startswith("flag_"):
                    self.assertEqual(im.size[1], 640, name)
                    self.assertIn(im.size[0], (512, 560), name)
                    self.assertEqual(im.mode, "RGBA", name)
                elif name.startswith("skin_"):
                    self.assertEqual(im.size, (1080, 1920), name)
                elif name.startswith("card_"):
                    self.assertEqual(im.size, (888, 528), name)
                elif name.startswith("band_"):
                    self.assertEqual(im.size, (1080, 300), name)
        media_names = {p.name for p in media.iterdir()}
        self.assertNotIn("flag-s01-guan.png", media_names)
        self.assertNotIn("flag_s01_guan.png", media_names)

    def test_levels_json_matches_locked_names(self) -> None:
        from build_levels import EXPECTED_NAMES, load_verified

        levels = load_verified()
        self.assertEqual([lv["name"] for lv in levels], list(EXPECTED_NAMES))
        self.assertEqual(len(levels), len(EXPECTED_NAMES))
        blob = (ROOT / "entry/src/main/resources/rawfile/levels.json").read_text(encoding="utf-8")
        self.assertNotIn("dessert", blob)
        self.assertIn("徐州·郯", blob)
        self.assertIn("北伐·五丈原", blob)


class DroppedMechanicTests(unittest.TestCase):
    def test_convert_board_refuses_ferry_unless_allowed(self) -> None:
        from build_levels import DroppedMechanicsError, convert_board, iter_locked_boards

        board = next(b for gid, b in iter_locked_boards() if gid == 52)
        with self.assertRaises(DroppedMechanicsError) as caught:
            convert_board(board, 52)
        self.assertEqual(caught.exception.rows, [(52, "荆州·樊城·第 1 驿", ["ferry"])])
        projected = convert_board(board, 52, allow_dropped_mechanics=True)
        self.assertNotIn("ferry", projected)
        self.assertNotIn("oneWays", projected)

    def test_build_cli_refuses_without_flag_and_allow_keeps_bytes(self) -> None:
        import hashlib
        import subprocess

        paths = [
            ROOT / "entry/src/main/resources/rawfile/levels.json",
            ROOT / "entry/src/main/cangjie/levels.cj",
        ]
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
        refused = subprocess.run(
            ["python3", "tools/build_levels.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(refused.returncode, 1)
        self.assertIn("id=52", refused.stderr)
        self.assertIn("dropped=ferry", refused.stderr)
        self.assertGreaterEqual(refused.stderr.count("\n  id="), 33)
        allowed = subprocess.run(
            ["python3", "tools/build_levels.py", "--allow-dropped-mechanics"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(allowed.returncode, 0, allowed.stderr)
        self.assertIn("id=52", allowed.stdout)
        after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
        self.assertEqual(before, after)


def play_paper(screen: int, level_index: int, chapter_index: int) -> str:
    """Mirrors EntryView.playPaper: 平原 sage on board + win only."""
    if screen == 6:
        return "paperOf"
    if screen in (1, 2) and level_index >= 10:
        return "pingyuan"
    return "paper"


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
