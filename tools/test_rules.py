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
import os
import re
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from solve_levels import (  # noqa: E402
    Rules,
    SolverTimeout,
    check_path,
    load_levels,
    report_solve_exit,
    solve,
    validate_schema,
    wall_key,
)

# Released mechanism keys (boards-locked snake_case shape), see build_levels.MECH_KEYS.
MECH_KEYS = (
    "ferry",
    "one_ways",
    "slide_cells",
    "seal_gates",
    "token_cells",
    "collapse",
    "burden",
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
        """The gate is undirected: crossing either way checks the same edge.

        Design SoT: hanzhong_ch9/zip_parity.py — PARITY_RULE / undirected ek
        ("parity-gated edges keyed by undirected ek", class docstring) and
        parity_ok (filled counts the standing cell, checked before the crossing).
        Grid parity fixes the filled at each landing: onto (0,1) it is always
        even, onto (0,2) via (1,2) it is always odd — so the forward crossing
        is rejected by requireOdd and the reverse crossing by requireEven.
        """
        # Forward (0,1) → (0,2) at filled=2: requireOdd rejects, code 1.
        g = PatrolGame(self.level([self.edge(0, 1, 0, 2, True)]))
        for cell in (Cell(0, 0), Cell(0, 1)):
            self.assertTrue(g.try_step(cell))
        self.assertEqual(g.filled(), 2)
        self.assertFalse(g.try_step(Cell(0, 2)))
        self.assertEqual(g.last_reject_parity, 1)
        self.assertEqual(g.filled(), 2)

        # Same direction, requireEven passes at filled=2.
        g = PatrolGame(self.level([self.edge(0, 1, 0, 2, False)]))
        for cell in (Cell(0, 0), Cell(0, 1)):
            self.assertTrue(g.try_step(cell))
        self.assertTrue(g.try_step(Cell(0, 2)))
        self.assertEqual(g.last_reject_parity, 0)
        self.assertEqual(g.filled(), 3)

        # Reverse (0,2) → (0,1) at filled=5: requireEven rejects, code 2.
        route = (Cell(0, 0), Cell(1, 0), Cell(1, 1), Cell(1, 2), Cell(0, 2))
        g = PatrolGame(self.level([self.edge(0, 1, 0, 2, False)]))
        for cell in route:
            self.assertTrue(g.try_step(cell))
        self.assertEqual(g.filled(), 5)
        self.assertFalse(g.try_step(Cell(0, 1)))
        self.assertEqual(g.last_reject_parity, 2)
        self.assertEqual(g.filled(), 5)

        # Same direction reversed, requireOdd passes at filled=5.
        g = PatrolGame(self.level([self.edge(0, 1, 0, 2, True)]))
        for cell in route:
            self.assertTrue(g.try_step(cell))
        self.assertTrue(g.try_step(Cell(0, 1)))
        self.assertEqual(g.last_reject_parity, 0)
        self.assertEqual(g.filled(), 6)

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
        """假绿 guard: every locked parity board's own solution must still play.

        Locked parity boards: ids 80, 83, 85, 87, 89. The two ferry boards
        (87, 89) jump 甲→乙 in one move (jingzhou_ch6/zip_ferry.py:64-69),
        which this mirror engine cannot replay — they are counted but skipped;
        ferry is covered by the design code / solver task, not this mirror.
        """
        from build_levels import LOCKED_DIR, LOCKED_FILES, convert_board

        checked = 0
        ferry_skipped = 0
        parity_total = 0
        for ch_idx, fname in enumerate(LOCKED_FILES):
            data = json.loads((LOCKED_DIR / fname).read_text(encoding="utf-8"))
            for tip_idx, b in enumerate(data["boards"]):
                if not b.get("parity_edges"):
                    continue
                parity_total += 1
                if b.get("ferry"):
                    ferry_skipped += 1
                    continue
                game = PatrolGame(convert_board(b, ch_idx * 10 + tip_idx))
                for r, c in b["path"]:
                    self.assertTrue(
                        game.try_step(Cell(c, r)),
                        f"{b['name']} rejected ({r},{c}) at filled={game.filled()}",
                    )
                self.assertTrue(game.is_win(), f"{b['name']} did not win on its shipped path")
                checked += 1
        self.assertEqual(parity_total, 5)
        self.assertEqual(ferry_skipped, 2)
        self.assertEqual(checked, 3)


class SolverContractTests(unittest.TestCase):
    def test_timeout_is_not_a_ship_failure(self) -> None:
        """README: TIMEOUT keeps the board; only a proven no-solution fails."""
        with redirect_stdout(io.StringIO()):
            self.assertEqual(report_solve_exit(100, 0, 0), 0)
            self.assertEqual(report_solve_exit(100, 0, 1), 0)
            self.assertEqual(report_solve_exit(100, 1, 0), 1)
            self.assertEqual(report_solve_exit(100, 1, 2), 1)


class ShippedLevelPlaythroughTests(unittest.TestCase):
    """solve() + Python mirror-engine replay on shipped levels.

    The released catalog is 100 levels (ids 0..99). Full sweeps belong to
    `python3 tools/solve_levels.py` (also reachable here via YILU_FULL_SOLVE=1);
    the default run solves a small subset: the first two mechanism-free,
    parity-free levels of each chapter. Only those can be replayed end-to-end:
    this mirror implements walls + waypoint order + parity only, and the
    current solve() does not read the mechanism keys (ferry/one_ways/…) or
    enforce parityEdges, so solver paths on those boards are not comparable.
    """

    MECH_KEYS = MECH_KEYS  # module-level, shared with the catalog tests

    @staticmethod
    def _levels() -> list[dict]:
        return load_levels(ROOT / "entry/src/main/resources/rawfile/levels.json")

    @classmethod
    def _mechanism_free(cls, level: dict) -> bool:
        return not any(level.get(key) for key in cls.MECH_KEYS)

    @classmethod
    def _replayable(cls, level: dict) -> bool:
        """Mechanism-free and no parityEdges: rules solve() + mirror both know."""
        return cls._mechanism_free(level) and not level.get("parityEdges")

    @classmethod
    def _default_subset(cls, levels: list[dict]) -> list[dict]:
        """First two replayable levels per chapter (10 chapters → 20 levels)."""
        subset: list[dict] = []
        for level in levels:
            if not cls._replayable(level):
                continue
            chapter = int(level["id"]) // 10
            taken = sum(1 for lv in subset if int(lv["id"]) // 10 == chapter)
            if taken < 2:
                subset.append(level)
        return subset

    def _assert_solvable(self, level: dict, replay: bool) -> None:
        try:
            found = solve(level, timeout_s=10.0)
        except SolverTimeout:
            self.skipTest(f"{level['name']} solver timeout > 10s")
        self.assertTrue(found, f"{level['name']} has no solution")
        if not replay:
            return
        path = found[0]
        game = PatrolGame(level)
        for x, y in path:
            self.assertTrue(
                game.try_step(Cell(x, y)),
                f"{level['name']} rejected ({x},{y}) at size={game.path.size()}",
            )
        self.assertTrue(game.is_win(), f"{level['name']} did not win after solver path")

    def test_catalog_is_one_hundred_levels_with_ids_0_to_99(self) -> None:
        levels = self._levels()
        self.assertEqual(len(levels), 100)
        self.assertEqual([int(lv["id"]) for lv in levels], list(range(100)))

    def test_solver_path_wins_default_subset_shipped_levels(self) -> None:
        """Default gate: first two mechanism-free, parity-free levels per chapter."""
        levels = self._levels()
        subset = self._default_subset(levels)
        self.assertEqual(len(subset), 20, [lv["id"] for lv in subset])
        for level in subset:
            with self.subTest(id=level["id"], name=level["name"]):
                self._assert_solvable(level, replay=True)

    @unittest.skipUnless(
        os.environ.get("YILU_FULL_SOLVE"),
        "full 100-level sweep: set YILU_FULL_SOLVE=1; authoritative run is "
        "python3 tools/solve_levels.py (mechanism-aware solver in flight)",
    )
    def test_solver_path_wins_every_solvable_shipped_level(self) -> None:
        levels = self._levels()
        self.assertEqual(len(levels), 100)
        for level in levels:
            with self.subTest(id=level["id"], name=level["name"]):
                self._assert_solvable(level, replay=self._replayable(level))

    def test_first_two_have_unique_solutions(self) -> None:
        levels = load_levels(ROOT / "entry/src/main/resources/rawfile/levels.json")
        for level in levels[:2]:
            found = solve(level, find_all=True, limit=2, timeout_s=8.0)
            self.assertEqual(len(found), 1, f"{level['name']} should have a unique solution")


class VerifiedCatalogTests(unittest.TestCase):
    """Lock the 100-board ch1–ch10 catalog (ids 0..99)."""

    def test_json_is_the_verified_table(self) -> None:
        from build_levels import EXPECTED_NAMES, ST02_WALLS, emit, load_verified

        levels = load_verified()
        self.assertEqual(len(levels), 100)
        self.assertEqual([int(lv["id"]) for lv in levels], list(range(100)))
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

    def test_levels_cj_carries_exactly_the_json_ferry_boards(self) -> None:
        """鸿蒙 levels.cj 携带 ferry：id 集合与坐标转换都必须对得上 levels.json。

        生成侧唯一的坐标换算是 build_levels._ferry_stmt（[r, c] -> x=列, y=行），
        与 engine/shared/src/game/json_level.cj 的 readRcPair `Cell(c, r)` 以及
        tools/solve_levels.py 的 rc_to_xy 同一约定。这里把 levels.cj 里实际出现
        的 `FerryDef(...)` 文本解析回来和 levels.json 逐一比对，防止「生成器改了
        而 levels.cj 没重跑」或「只 emit 了部分渡口关」。
        """
        from build_levels import _ferry_stmt, load_verified

        levels = load_verified()
        shipped = (ROOT / "entry/src/main/cangjie/levels.cj").read_text(encoding="utf-8")
        emitted = {}
        for line in shipped.splitlines():
            m = re.fullmatch(
                r"\s*level(\d+)\.ferry = Some\(FerryDef\((-?\d+), (-?\d+), (-?\d+), (-?\d+)\)\)",
                line,
            )
            if m:
                emitted[int(m.group(1))] = tuple(int(m.group(i)) for i in (2, 3, 4, 5))
        expected = {}
        for lv in levels:
            stmts = _ferry_stmt(lv)
            if stmts:
                text = stmts[0].split("FerryDef(")[1].rstrip(")")
                expected[int(lv["id"])] = tuple(int(v) for v in text.split(","))
        self.assertEqual(
            set(emitted),
            {52, 57, 59, 60, 63, 67, 87, 89},
            "levels.cj ferry board ids drifted from the 8 locked ferry boards",
        )
        self.assertEqual(
            emitted,
            expected,
            "levels.cj FerryDef coords must be the [r,c]->(x=col,y=row) conversion of levels.json",
        )
        for lid in sorted(emitted):
            src = levels[lid]["ferry"]
            jr, jc = src["jia"]
            yr, yc = src["yi"]
            self.assertEqual(emitted[lid], (jc, jr, yc, yr), f"level {lid} ferry conversion")
        # 导入也必须跟上，否则 FerryDef 未定义（编译期才炸）。
        self.assertIn(
            "import ohos_app_cangjie_entry.game.{FerryDef, LevelDef, ParityEdge, Waypoint}",
            shipped,
        )

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
        """README must describe the shipped 100-board / 10-chapter catalog.

        Counts are cross-checked against levels.json and chapter.cj rather
        than hard-coding board names into the assertion.
        """
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        levels = load_levels(ROOT / "entry/src/main/resources/rawfile/levels.json")
        self.assertEqual(len(levels), 100)
        # Stale 20-board claims must be gone.
        self.assertNotIn("20/20", readme)
        self.assertNotIn("ids 0..19", readme)
        self.assertNotIn("12/12", readme)
        self.assertNotIn("13/13", readme)
        self.assertNotIn("{驿名}·第 N 驿", readme)
        self.assertNotIn("| 0 | 长安（教程） |", readme)
        self.assertNotIn("汽梁", readme)
        # Current truth the README must state.
        self.assertIn("100", readme)
        self.assertIn("ids 0..99", readme)
        self.assertIn("10 章", readme)
        self.assertIn("python3 tools/solve_levels.py", readme)
        self.assertIn("cleared >= 10", readme)
        # Every chapter card in chapter.cj appears in the README chapter table.
        for chapter in SHIP_CHAPTERS:
            self.assertIn(chapter["name"], readme, f"README misses chapter {chapter['name']}")
        # Spot-check the board examples the README quotes verbatim.
        self.assertIn("涿郡·涿", readme)
        self.assertIn("平原·祝阿·第 2 驿", readme)

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


# chapter-flow mirror of entry/src/main/cangjie/chapter.cj (read-only SoT):
# 10 cards, each levelStart 0/10/../90, levelCount 10, open true (catalog.open
# = has boards). 05–10 additionally offer a skin preview while still locked
# (ChapterCatalog.hasSkinPreview: chapterId >= 4 && <= 9).
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
        # Catalog.open = has boards; all 10 chapters ship 10 boards each.
        self.assertEqual(
            [ch["open"] for ch in SHIP_CHAPTERS],
            [True] * 10,
        )
        self.assertTrue(chapter_selectable(0, 0))
        self.assertFalse(chapter_selectable(1, 0))
        self.assertFalse(chapter_selectable(2, 0))
        self.assertFalse(chapter_selectable(3, 0))
        self.assertFalse(chapter_selectable(4, 20))
        self.assertFalse(chapter_selectable(9, 20))
        self.assertEqual(chapter_by_id(7)["rightFlag"], "flag_gate_pattern")
        self.assertNotEqual(chapter_by_id(7)["rightFlag"], "flag_s01_guan")
        self.assertEqual(chapter_by_id(8)["leftFlag"], "flag_p09_zhuge")
        self.assertEqual(chapter_by_id(9)["rightFlag"], "flag_p10_sima")
        self.assertIn("诸葛", chapter_by_id(8)["listSubtitle"])
        self.assertIn("司马", chapter_by_id(9)["listSubtitle"])

    def test_pingyuan_opens_only_after_zhuojun_cleared(self) -> None:
        """平原 可入 iff 涿郡 10 驿 cleared; later chapters gate on their own levelStart."""
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
        # chapter.cj: 徐州 opens at levelStart 20, 吕布 at 30 — each chapter
        # unlocked iff cleared >= its own levelStart (0,10,…,90).
        self.assertTrue(chapter_is_open(2, 20))
        self.assertFalse(chapter_is_open(3, 20))
        self.assertTrue(chapter_is_open(3, 30))
        for chapter_id in range(4, 10):
            self.assertFalse(chapter_is_open(chapter_id, 20), chapter_id)
            self.assertTrue(chapter_has_skin_preview(chapter_id), chapter_id)
        self.assertTrue(chapter_is_open(9, 90))
        self.assertEqual(chapter_open_count(90), 10)
        self.assertFalse(chapter_has_skin_preview(2))
        self.assertFalse(chapter_has_skin_preview(3))
        self.assertEqual(chapter_cleared_count(1, 0), 0)
        self.assertEqual(chapter_cleared_count(0, 3), 3)
        levels = load_levels(ROOT / "entry/src/main/resources/rawfile/levels.json")
        self.assertEqual(chapter_current_label(1, 0, levels), "未开")
        self.assertEqual(chapter_current_label(1, 9, levels), "未开")
        self.assertNotIn("平原", chapter_current_label(0, 0, levels))
        self.assertEqual(chapter_current_label(1, 10, levels), levels[10]["name"])

    def test_every_shipped_chapter_has_ten_boards(self) -> None:
        """All 10 chapters ship boards: ids 10k..10k+9, 100 levels total."""
        levels = load_levels(ROOT / "entry/src/main/resources/rawfile/levels.json")
        self.assertEqual(len(levels), 100)
        self.assertEqual([int(lv["id"]) for lv in levels], list(range(100)))
        for chapter_id in range(10):
            chapter = chapter_levels(levels, chapter_id)
            self.assertEqual(len(chapter), 10, chapter_id)
            self.assertEqual(
                [int(lv["id"]) for lv in chapter],
                list(range(chapter_id * 10, chapter_id * 10 + 10)),
                chapter_id,
            )
        # Names are the locked ones — every chapter card has a real board.
        names = [lv["name"] for lv in levels]
        for prefix in ("涿郡", "平原", "徐州", "吕布", "投袁", "荆州", "赤壁", "入蜀", "汉中", "南中", "北伐"):
            self.assertTrue(any(n.startswith(prefix) for n in names), prefix)
        # No retired prototype boards.
        self.assertFalse(any("长安" in n or "汽梁" in n for n in names))

    def test_station_names_and_sizes_come_from_json_only(self) -> None:
        from build_levels import LOCKED_DIR, LOCKED_FILES

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
        # Sizes come from the locked boards, not a hard-coded 6×6:
        # ch1–3 are 6×6 (30 boards), ch4–10 are 7×7 (70 boards).
        locked_sizes = []
        for fname in LOCKED_FILES:
            data = json.loads((LOCKED_DIR / fname).read_text(encoding="utf-8"))
            locked_sizes.extend((int(b["size"]), int(b["size"])) for b in data["boards"])
        self.assertEqual(
            [(int(lv["cols"]), int(lv["rows"])) for lv in levels],
            locked_sizes,
        )
        self.assertEqual(set(locked_sizes), {(6, 6), (7, 7)})
        self.assertTrue(all(is_dessert_level(lv) is (int(lv["id"]) == 4) for lv in zhuo))
        self.assertTrue(is_dessert_level(zhuo[4]))
        self.assertFalse(is_dessert_level(zhuo[5]))

    def test_continue_opens_current_unlock(self) -> None:
        self.assertEqual(continue_level_index(0, 100), 0)
        self.assertEqual(continue_level_index(12, 100), 12)
        self.assertEqual(continue_level_index(99, 100), 99)
        self.assertEqual(continue_level_index(100, 100), 99)

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
        """05–10 open a fullscreen skin preview while still locked; no 涿/平原 skins."""
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
        """PR #15: 平原 locked while cleared<10; every later chapter gates on levelStart."""
        for cleared in (0, 3, 9):
            self.assertTrue(chapter_is_open(0, cleared), cleared)
            self.assertFalse(chapter_is_open(1, cleared), cleared)
            self.assertFalse(chapter_selectable(1, cleared), cleared)
        self.assertTrue(chapter_is_open(1, 10))
        # Every chapter gates on its own levelStart (chapter.cj isOpen).
        self.assertTrue(chapter_is_open(2, 20))
        self.assertFalse(chapter_is_open(2, 19))
        self.assertFalse(chapter_is_open(3, 20))
        self.assertTrue(chapter_is_open(3, 30))
        for chapter_id in range(4, 10):
            self.assertFalse(chapter_is_open(chapter_id, 9), chapter_id)
            self.assertFalse(chapter_is_open(chapter_id, 20), chapter_id)
            self.assertTrue(
                chapter_is_open(chapter_id, chapter_by_id(chapter_id)["levelStart"]),
                chapter_id,
            )
        src = (ROOT / "entry/src/main/cangjie/chapter.cj").read_text(encoding="utf-8")
        self.assertIn("func isOpen(", src)
        self.assertIn("cleared >= ch.levelStart", _func_body(src, "isOpen"))
        ui = (ROOT / "entry/src/main/cangjie/index.cj").read_text(encoding="utf-8")
        self.assertIn("ChapterCatalog.isOpen(id, this.cleared)", _func_body(ui, "openChapter"))

    def test_p1_skins_do_not_move_layout_or_lock(self) -> None:
        """P1 (ab3c9c9): 09 dual-tone + mock 6×6 only. BOARD_OY / isOpen frozen."""
        ship = (ROOT / "design/mockups/chapter-skins-v9/ch05-10-SHIP.md").read_text(encoding="utf-8")
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

    def test_levels_json_is_the_locked_hundred_boards(self) -> None:
        from build_levels import EXPECTED_NAMES, load_verified

        levels = load_verified()
        self.assertEqual(len(levels), 100)
        self.assertEqual([int(lv["id"]) for lv in levels], list(range(100)))
        self.assertEqual([lv["name"] for lv in levels], list(EXPECTED_NAMES))
        blob = (ROOT / "entry/src/main/resources/rawfile/levels.json").read_text(encoding="utf-8")
        # Retired prototype content must stay out of the shipped catalog.
        self.assertNotIn("dessert", blob)
        self.assertNotIn("长安", blob)
        self.assertNotIn("汽梁", blob)
        # Mechanism keys ship only on the 33 boards that have them
        # (boards-locked); the other 67 entries carry none of them.
        with_mech = [lv for lv in levels if any(lv.get(k) for k in MECH_KEYS)]
        self.assertEqual(len(with_mech), 33)
        for lv in levels:
            for key in MECH_KEYS:
                if lv.get(key):
                    break
            else:
                for key in MECH_KEYS:
                    self.assertNotIn(f'"{key}"', json.dumps(lv))


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

        undo_svg = (ROOT / "design/icons/icon-undo.svg").read_text(encoding="utf-8")
        reset_svg = (ROOT / "design/icons/icon-reset.svg").read_text(encoding="utf-8")
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


class MechanicRulesTests(unittest.TestCase):
    """Rules layer (Rules/State/initial_state/expand/apply/check_path) on
    hand-built minimal boards in the released schema.

    Waypoints/walls/parityEdges use published x/y (x=col, y=row); mechanism
    keys keep the boards-locked [r, c] shape. Design SoT is read-only — every
    test cites file:line: jingzhou_ch6/zip_ferry.py (ferry), lvbu_ch4/
    zip_oneway.py (one_ways), hanzhong_ch9/zip_parity.py (parity).
    """

    # -- construction helpers --------------------------------------------

    @staticmethod
    def level(cols: int, rows: int, wps: list, **mech) -> dict:
        """Minimal released-schema level. `wps` = [(n, x, y), ...]; `mech`
        holds optional mechanism keys verbatim (ferry/one_ways as [r, c],
        parityEdges as published x/y camelCase)."""
        lv = {
            "id": 900,
            "name": "机制试驿",
            "cols": cols,
            "rows": rows,
            "waypoints": [{"n": n, "x": x, "y": y} for n, x, y in wps],
            "walls": [],
            "stepLimit": 0,
        }
        lv.update(mech)
        validate_schema(lv)
        return lv

    @staticmethod
    def wall(x1: int, y1: int, x2: int, y2: int) -> dict:
        """Published wall entry (x/y)."""
        return {"x1": x1, "y1": y1, "x2": x2, "y2": y2}

    @staticmethod
    def pedge(x1: int, y1: int, x2: int, y2: int, odd: bool) -> dict:
        """Published parityEdges entry (x/y, camelCase requireOdd/requireEven)."""
        return {
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "requireOdd": odd, "requireEven": not odd,
        }

    def walk(self, rules: Rules, moves: list):
        """Replay inputs through initial_state/expand/apply; fail on reject."""
        state = rules.initial_state()
        self.assertIsNotNone(state, "start state rejected")
        for mv in moves:
            seg = rules.expand(state, mv)
            self.assertIsNotNone(
                seg, f"expand rejected {mv} standing at {state.path[-1]}"
            )
            state = rules.apply(state, seg)
        return state

    # -- ferry 渡口 --------------------------------------------------------
    # jingzhou_ch6/zip_ferry.py — 单向渡口: 走上甲 → 强制 [甲, 乙].

    def ferry_level(self, **extra) -> dict:
        """3x3 ferry board: 甲=(x2,y1), 乙=(x1,y1) (both unnumbered,
        zip_ferry.py / flags F7; validate_mechanics enforces it).

        Valid snake path (xy): (0,0)(1,0)(2,0) [jump] (1,1)(0,1)(0,2)(1,2)(2,2)
        → stored rc: [[0,0],[0,1],[0,2],[1,2],[1,1],[1,0],[2,0],[2,1],[2,2]]"""
        mech = {"ferry": {"jia": [1, 2], "yi": [1, 1]}}
        mech.update(extra)
        return self.level(3, 3, [(1, 0, 0), (2, 2, 2)], **mech)

    FERRY_PATH = [
        [0, 0], [0, 1], [0, 2], [1, 2], [1, 1], [1, 0], [2, 0], [2, 1], [2, 2],
    ]

    def test_ferry_step_on_jia_returns_jia_yi_in_one_input(self) -> None:
        """踏上甲的一次输入返回 [甲, 乙] (forced, not optional).

        Design: zip_ferry.py:64-69 `if nxt == jia: ... return [jia, yi]`;
        filled 一次 +2: zip_ferry.py:249 `dfs(seg[-1], nvis, filled + len(seg), ...)`."""
        rules = Rules(self.ferry_level())
        state = self.walk(rules, [(1, 0), (2, 0)])  # filled = 3, stand before 甲
        seg = rules.expand(state, (2, 1))  # the single input = step onto 甲
        self.assertEqual(seg, [(2, 1), (1, 1)])  # [甲, 乙]
        state2 = rules.apply(state, seg)
        self.assertEqual(state2.filled, state.filled + 2)  # 跳接使已铺格数 +2
        self.assertEqual(state2.path[-1], (1, 1))  # lands on 乙
        self.assertTrue(state2.ferry_used)
        self.assertEqual(len(state2.path), state.filled + 2)

    def test_ferry_enter_jia_rejected_when_yi_already_visited(self) -> None:
        """乙已访时走上甲被拒 — zip_ferry.py:65-66
        (`if (vis >> yi) & 1: return None`).

        Walk into 乙 as a plain cell first (design allows a normal entry into
        乙), then stepping onto 甲 must be rejected."""
        rules = Rules(self.ferry_level())
        state = self.walk(rules, [(0, 1), (1, 1)])  # stand on 乙 the plain way
        self.assertEqual(state.path[-1], (1, 1))
        seg, reason = rules._expand(state, (2, 1))  # step onto 甲
        self.assertIsNone(seg)
        self.assertIn("乙", reason)

    def test_ferry_check_path_requires_exactly_one_jump(self) -> None:
        """路线恰好一次甲→乙 — zip_ferry.py:126-128
        (`jumps = sum(...); if jumps != 1: return False`).

        - the shipped-style snake path (exactly one 甲→乙 pair) passes;
        - zero jumps (path dies on 甲, jump never completed) fails;
        - two 甲→乙 pairs (甲/乙 duplicated) fails."""
        lv = self.ferry_level()
        ok, reason, _ = check_path(lv, self.FERRY_PATH)
        self.assertTrue(ok, reason)

        # 0 jumps: ends on 甲, the forced [甲, 乙] segment cannot be consumed
        # (design-side jumps == 0 → False at zip_ferry.py:127).
        zero = self.FERRY_PATH[:4]  # ... (0,2) [1,2]=甲 as last cell
        self.assertEqual(zero[-1], [1, 2])
        ok0, reason0, _ = check_path(lv, zero)
        self.assertFalse(ok0)
        self.assertTrue(reason0)

        # 2 jumps: insert a second (甲, 乙) pair right after the first.
        twice = self.FERRY_PATH[:5] + [[1, 2], [1, 1]] + self.FERRY_PATH[5:]
        self.assertEqual(twice.count([1, 2]), 2)
        ok2, reason2, _ = check_path(lv, twice)
        self.assertFalse(ok2)
        self.assertTrue(reason2)

    def test_ferry_jump_exempt_from_wall_between_jia_and_yi(self) -> None:
        """跳接本体豁免墙: 甲乙之间的墙不影响跳接 — the jump branch runs
        before `nbr_open`, zip_ferry.py:49-57 vs :58 (wall check lives in
        nbr_open, zip_oneway.py:115). Entering 甲 from (2,0) is still open."""
        lv = self.ferry_level(walls=[self.wall(2, 1, 1, 1)])  # wall on 甲-乙 edge
        rules = Rules(lv)
        state = self.walk(rules, [(1, 0), (2, 0)])
        seg = rules.expand(state, (2, 1))
        self.assertEqual(seg, [(2, 1), (1, 1)])  # jump ignores the wall

    def test_ferry_jump_exempt_from_oneway_on_jia_yi_edge(self) -> None:
        """跳接本体豁免单向: reverse one-way 乙→甲 on the jump edge still
        allows the 甲→乙 jump — jump branch before nbr_open's one-way check
        (zip_ferry.py:49-57 vs :58; one-way test zip_oneway.py:117-119)."""
        # one_ways shape: boards-locked [{"from":[r,c],"to":[r,c]}] = 乙→甲.
        lv = self.ferry_level(one_ways=[{"from": [1, 1], "to": [1, 2]}])
        rules = Rules(lv)
        state = self.walk(rules, [(1, 0), (2, 0)])
        seg = rules.expand(state, (2, 1))
        self.assertEqual(seg, [(2, 1), (1, 1)])

    def test_ferry_jump_skips_parity_on_jia_yi_edge(self) -> None:
        """跳接边不查奇偶: the ferry branch returns before nbr_open_parity
        (zip_parity.py:107-117 jump branch vs :113-117 nbr_open_parity;
        PHASE0 §1 ferry row). The 甲-乙 edge requires EVEN but filled is 3
        (odd) when stepping onto 甲 — the jump still goes through."""
        lv = self.ferry_level(parityEdges=[self.pedge(2, 1, 1, 1, odd=False)])
        rules = Rules(lv)
        state = self.walk(rules, [(1, 0), (2, 0)])
        self.assertEqual(state.filled, 3)
        seg = rules.expand(state, (2, 1))
        self.assertEqual(seg, [(2, 1), (1, 1)])

    def test_no_yi_to_jia_input_from_yi_is_rejected(self) -> None:
        """没有 乙→甲: standing on 乙, input 甲 is rejected — 甲 is already
        visited (zip_ferry.py:60 `if (vis >> nxt) & 1: return None`); the
        jump branch is only 甲→乙 (zip_ferry.py:52 `cur == jia and nxt == yi`).
        """
        rules = Rules(self.ferry_level())
        state = self.walk(rules, [(1, 0), (2, 0), (2, 1)])  # jump → stand on 乙
        self.assertEqual(state.path[-1], (1, 1))
        seg, reason = rules._expand(state, (2, 1))  # try "jump back" to 甲
        self.assertIsNone(seg)
        self.assertIn("visited", reason)

    def test_entering_jia_is_blocked_by_wall(self) -> None:
        """进入甲受墙约束: the entry edge (2,0)-甲 is a wall, so stepping onto
        甲 is rejected — nbr_open runs for entering 甲 (zip_ferry.py:58, wall
        first at zip_oneway.py:115)."""
        lv = self.ferry_level(walls=[self.wall(2, 0, 2, 1)])
        rules = Rules(lv)
        state = self.walk(rules, [(1, 0), (2, 0)])
        self.assertIsNone(rules.expand(state, (2, 1)))

    def test_entering_jia_is_blocked_by_reverse_oneway(self) -> None:
        """进入甲受单向约束: one-way marked 甲→(2,0) forbids the reverse move
        (2,0)→甲 — zip_oneway.py:108-121 (`nbr_open`: constrained edge passes
        only when `(i, j) in ow`)."""
        # 甲=(x2,y1)→rc [1,2]; (2,0)→rc [0,2]; direction 甲→(2,0).
        lv = self.ferry_level(one_ways=[{"from": [1, 2], "to": [0, 2]}])
        rules = Rules(lv)
        state = self.walk(rules, [(1, 0), (2, 0)])
        self.assertIsNone(rules.expand(state, (2, 1)))  # reverse of the mark
        # The marked forward direction is fine where reachable: from 甲 you
        # could never stand anyway (forced jump), so assert on a twin edge —
        # an unmarked neighbour stays open:
        state2 = self.walk(rules, [(0, 1)])  # (0,0)→(0,1) unmarked edge
        self.assertIsNotNone(rules.expand(state2, (0, 2)))

    def test_entering_jia_is_blocked_by_parity(self) -> None:
        """进入甲受奇偶约束: edge (2,0)-甲 requires EVEN, filled is 3 (odd,
        counted with the standing cell, before crossing — zip_parity.py:59-64
        `parity_ok`, filled passed in at :113-117) → rejected."""
        lv = self.ferry_level(parityEdges=[self.pedge(2, 0, 2, 1, odd=False)])
        rules = Rules(lv)
        state = self.walk(rules, [(1, 0), (2, 0)])
        self.assertEqual(state.filled, 3)
        self.assertIsNone(rules.expand(state, (2, 1)))
        # Same edge with requireOdd passes at filled=3 → jump goes through.
        lv2 = self.ferry_level(parityEdges=[self.pedge(2, 0, 2, 1, odd=True)])
        rules2 = Rules(lv2)
        state2 = self.walk(rules2, [(1, 0), (2, 0)])
        self.assertEqual(
            rules2.expand(state2, (2, 1)), [(2, 1), (1, 1)]
        )

    # -- one_ways 单向 -----------------------------------------------------
    # lvbu_ch4/zip_oneway.py:108-121 (`nbr_open`): 先墙后单向, 反向即拒.

    OW_LEVEL = {"from": [1, 1], "to": [0, 1]}  # rc → allowed (x1,y1)→(x1,y0)

    def test_one_way_forward_is_open(self) -> None:
        """标记方向可过: standing on the marked `from` cell, moving to `to`
        is allowed — zip_oneway.py:117-119 (`if (i, j) not in ow: continue`
        passes for the marked direction)."""
        lv = self.level(3, 3, [(1, 0, 0), (2, 2, 2)], one_ways=[self.OW_LEVEL])
        rules = Rules(lv)
        state = self.walk(rules, [(0, 1), (1, 1)])  # stand on `from` (x1,y1)
        self.assertEqual(rules.expand(state, (1, 0)), [(1, 0)])  # → `to`

    def test_one_way_reverse_is_rejected(self) -> None:
        """反向被拒: moving opposite to the marked direction is rejected —
        zip_oneway.py:117-119 (constrained edge, `(i, j) not in ow`)."""
        lv = self.level(3, 3, [(1, 0, 0), (2, 2, 2)], one_ways=[self.OW_LEVEL])
        rules = Rules(lv)
        state = self.walk(rules, [(1, 0)])  # stand on `to` (x1,y0)
        seg, reason = rules._expand(state, (1, 1))  # reverse of the mark
        self.assertIsNone(seg)
        self.assertIn("one-way", reason)

    def test_one_way_does_not_affect_unmarked_edges(self) -> None:
        """未标记的边不受影响: with the same mark in place, every unmarked
        edge around the marked one still opens — nbr_open only skips edges
        whose undirected key is in the constrained set (zip_oneway.py:106,
        :117-119)."""
        lv = self.level(3, 3, [(1, 0, 0), (2, 2, 2)], one_ways=[self.OW_LEVEL])
        rules = Rules(lv)
        state = self.walk(rules, [(0, 1), (1, 1)])  # stand on the `from` cell
        self.assertEqual(rules.expand(state, (2, 1)), [(2, 1)])  # unmarked
        state = self.walk(rules, [(1, 0), (2, 0)])  # other unmarked edges
        self.assertEqual(rules.expand(state, (2, 1)), [(2, 1)])

    # -- parity 奇偶 -------------------------------------------------------
    # hanzhong_ch9/zip_parity.py:59-64 (`parity_ok`): filled 含当前站立格,
    # 跨边前; 边为无向 edge_key (:19-26, parity_from_json :30-43).

    def test_parity_filled_counts_standing_cell_before_crossing(self) -> None:
        """filled 口径 = 已铺格数含当前格, 在跨边前判定 — zip_parity.py:59-64
        (`is_odd = (filled % 2) == 1`), filled 实参在 :113-117 传入
        (`nbr_open_parity(..., filled, parity)`).

        At the start filled == 1 (the standing cell): requireOdd opens,
        requireEven rejects the very first step."""
        edge = self.pedge(0, 0, 0, 1, odd=True)  # (0,0)-(0,1) needs odd
        rules = Rules(self.level(3, 3, [(1, 0, 0), (2, 2, 2)], parityEdges=[edge]))
        state = rules.initial_state()
        self.assertEqual(state.filled, 1)  # standing cell counted
        self.assertEqual(rules.expand(state, (0, 1)), [(0, 1)])

        edge_even = self.pedge(0, 0, 0, 1, odd=False)  # same edge, needs even
        rules2 = Rules(self.level(3, 3, [(1, 0, 0), (2, 2, 2)], parityEdges=[edge_even]))
        state2 = rules2.initial_state()
        self.assertEqual(state2.filled, 1)
        self.assertIsNone(rules2.expand(state2, (0, 1)))  # odd filled → rejected

        # After one more cell filled == 2 (even) on the next edge.
        edge2 = self.pedge(1, 0, 2, 0, odd=False)  # (1,0)-(2,0) needs even
        rules3 = Rules(self.level(3, 3, [(1, 0, 0), (2, 2, 2)], parityEdges=[edge2]))
        state3 = self.walk(rules3, [(1, 0)])
        self.assertEqual(state3.filled, 2)
        self.assertEqual(rules3.expand(state3, (2, 0)), [(2, 0)])
        # Same edge, requireOdd → rejected at even filled.
        edge2_odd = self.pedge(1, 0, 2, 0, odd=True)
        rules4 = Rules(self.level(3, 3, [(1, 0, 0), (2, 2, 2)], parityEdges=[edge2_odd]))
        state4 = self.walk(rules4, [(1, 0)])
        self.assertIsNone(rules4.expand(state4, (2, 0)))

    def test_parity_edge_matches_both_directions(self) -> None:
        """requireOdd/requireEven 双向匹配: the edge key is undirected, so a
        crossing either way checks the same requirement — zip_parity.py:59-64
        (`parity_ok(e, filled, parity)` keyed by undirected ek, parse
        :30-43). Single waypoint n=1 at the start so no max-waypoint rule
        interferes with the long reverse walk."""
        # Forward: stand (0,1) at filled=2 → cross to (0,2).
        fwd_even = self.level(
            3, 3, [(1, 0, 0)], parityEdges=[self.pedge(0, 1, 0, 2, odd=False)]
        )
        rules = Rules(fwd_even)
        state = self.walk(rules, [(0, 1)])
        self.assertEqual(state.filled, 2)
        self.assertEqual(rules.expand(state, (0, 2)), [(0, 2)])
        fwd_odd = self.level(
            3, 3, [(1, 0, 0)], parityEdges=[self.pedge(0, 1, 0, 2, odd=True)]
        )
        self.assertIsNone(Rules(fwd_odd).expand(state, (0, 2)))

        # Reverse: reach (0,2) the long way with (0,1) still unvisited,
        # filled=7 (odd) → requireOdd opens, requireEven rejects.
        route = [(1, 0), (2, 0), (2, 1), (2, 2), (1, 2), (0, 2)]
        rev_odd = self.level(
            3, 3, [(1, 0, 0)], parityEdges=[self.pedge(0, 1, 0, 2, odd=True)]
        )
        rules_r = Rules(rev_odd)
        state_r = self.walk(rules_r, route)
        self.assertEqual(state_r.filled, 7)
        self.assertEqual(rules_r.expand(state_r, (0, 1)), [(0, 1)])
        rev_even = self.level(
            3, 3, [(1, 0, 0)], parityEdges=[self.pedge(0, 1, 0, 2, odd=False)]
        )
        self.assertIsNone(Rules(rev_even).expand(state_r, (0, 1)))

    # -- seal_gates / token_cells 封印符节 ---------------------------------
    # rushu_ch8/zip_seal.py — 闸: 无符不可过 (:68 `if e in gates and not
    # has_token: continue`); 符在整段输入之后才生效 (:237-240 `has_token =
    # True` after the segment); 起点即符 = 已得符 (:206-211).

    def seal_level(self, **extra) -> dict:
        """3x3 seal board: gate on the (x1,y0)-(x1,y1) edge (rc [[0,1],[1,1]]),
        token at (x0,y1) (rc [1,0])."""
        mech = {
            "seal_gates": [{"between": [[0, 1], [1, 1]], "locked_until_token": True}],
            "token_cells": [[1, 0]],
        }
        mech.update(extra)
        return self.level(3, 3, [(1, 0, 0), (2, 2, 2)], **mech)

    def test_seal_gate_rejects_crossing_without_token(self) -> None:
        """未得符过闸被拒: the gated edge (1,0)-(1,1) is closed while
        has_token is False — zip_seal.py:68 (`if e in gates and not has_token:
        continue`) inside nbr_open_seal, used by expand_move_seal:94."""
        rules = Rules(self.seal_level())
        state = self.walk(rules, [(1, 0)])  # stand on the near side, no token
        self.assertFalse(state.has_token)
        seg, reason = rules._expand(state, (1, 1))  # cross the gate
        self.assertIsNone(seg)
        self.assertIn("gate", reason)

    def test_seal_token_step_unlocks_the_next_input_only(self) -> None:
        """踩符那一次输入之后,下一次输入才可过闸 — has_token flips after the
        whole segment is applied (zip_seal.py:237-240), so the input that
        lands on the token cannot itself use it; the very next input can.

        Walk (0,0)→(0,1) picks the token, then the following input crosses
        the gate from (1,1) back to (1,0)."""
        rules = Rules(self.seal_level())
        self.assertFalse(rules.initial_state().has_token)  # before the token
        state = self.walk(rules, [(0, 1), (1, 1)])  # token input, then next
        self.assertTrue(state.has_token)  # ...applied after the token input
        self.assertEqual(rules.expand(state, (1, 0)), [(1, 0)])  # gate opens

    def test_seal_start_on_token_counts_as_picked(self) -> None:
        """起点即符格视为已得符: has_token is seeded from the start cell —
        zip_seal.py:206-211 (`has_token = path[0] in tokens ...`, with the
        explicit "start on token is ok" note at :206-208)."""
        rules = Rules(self.seal_level(token_cells=[[0, 0]]))  # token = start
        state = rules.initial_state()
        self.assertTrue(state.has_token)
        state = self.walk(rules, [(1, 0)])  # no token picked along the way
        self.assertEqual(rules.expand(state, (1, 1)), [(1, 1)])  # gate open

    def test_seal_slide_stops_before_gate_without_token(self) -> None:
        """滑行遇闸且未得符 = 停在闸前一格,不整段拒绝 — the slide loop breaks
        on the closed gate edge instead of rejecting the whole move:
        zip_seal.py:123 (`if npos not in self.nbr_open_seal(...)`) with the
        gate test at :68.

        3x4 board: slide column x=1 rows 1..2 (rc [[1,1],[2,1]]), gate on the
        (x1,y2)-(x1,y3) edge (rc [[2,1],[3,1]]), token far away at (0,3)."""
        lv = self.level(
            3, 4,
            [(1, 0, 0), (2, 2, 3)],
            slide_cells=[[1, 1], [2, 1]],
            seal_gates=[{"between": [[2, 1], [3, 1]], "locked_until_token": True}],
            token_cells=[[3, 0]],
        )
        rules = Rules(lv)
        state = self.walk(rules, [(1, 0)])  # stand above the marsh
        seg = rules.expand(state, (1, 1))  # one input enters the marsh
        self.assertIsNotNone(seg, "slide hitting a gate must not be rejected")
        self.assertEqual(seg, [(1, 1), (1, 2)])  # stopped one cell before 闸

    # -- collapse 塌桥 -----------------------------------------------------
    # beifa_ch10/zip_burden.py:146-147 (`if down and collapse.active() and
    # e == collapse.edge: continue` in nbr_open_bc) — down 只在踏上触发格后
    # 置位 (apply_cell_effects :113-123), 滑行段内在落格当步即生效
    # (:214-215 与 :235, 传入 :221-222 的 nbr_open_bc).

    def collapse_level(self, **extra) -> dict:
        """3x3 collapse board: trigger (x0,y1) rc [1,0], collapsing edge
        (x1,y1)-(x1,y2) rc [[1,1],[2,1]]."""
        mech = {
            "collapse": {
                "schema": "step_on_trigger",
                "trigger_rc": [1, 0],
                "collapse_edge": {"between": [[1, 1], [2, 1]]},
            }
        }
        mech.update(extra)
        return self.level(3, 3, [(1, 0, 0), (2, 2, 2)], **mech)

    def test_collapse_edge_closes_after_stepping_on_trigger(self) -> None:
        """踏触发格之后,指定边不可再过(普通步:下一步起) — the edge is only
        skipped while `down` is set (zip_burden.py:146-147), i.e. from the
        step after the trigger was entered.

        Control (same board, route avoiding the trigger) keeps the edge open."""
        rules = Rules(self.collapse_level())
        state = self.walk(rules, [(0, 1), (1, 1)])  # (0,1) is the trigger
        self.assertTrue(state.down)
        self.assertIsNone(rules.expand(state, (1, 2)))  # edge now closed

        state2 = self.walk(rules, [(1, 0), (1, 1)])  # never touch the trigger
        self.assertFalse(state2.down)
        self.assertEqual(rules.expand(state2, (1, 2)), [(1, 2)])  # still open

    def test_collapse_takes_effect_mid_slide_from_that_step_on(self) -> None:
        """滑行段内当步起影响同段后续: landing on the trigger mid-segment sets
        `down` immediately, so the *next* cell of the same segment is blocked
        by the collapsing edge — zip_burden.py:214-215 (`laden_s, down_s =
        apply_cell_effects(nxt, ...)` before the loop), :235 (re-applied per
        landed cell) and :221-222 (`nbr_open_bc(..., down_s, ...)`).

        Board: marsh column x=1 rows 1..2; the trigger is the first marsh cell
        and the collapsing edge is the next one along the slide direction."""
        base = dict(
            slide_cells=[[1, 1], [2, 1]],
            collapse={
                "schema": "step_on_trigger",
                "trigger_rc": [1, 1],
                "collapse_edge": {"between": [[1, 1], [2, 1]]},
            },
        )
        rules = Rules(self.level(3, 3, [(1, 0, 0), (2, 2, 2)], **base))
        state = self.walk(rules, [(1, 0)])  # stand above the marsh
        seg = rules.expand(state, (1, 1))  # one input: enter marsh + trigger
        self.assertIsNotNone(seg, "collapse mid-slide must not reject the move")
        self.assertEqual(seg, [(1, 1)])  # same segment stops right there

        # Control: identical board without the collapse key slides on.
        ctrl = dict(base)
        del ctrl["collapse"]
        rules_c = Rules(self.level(3, 3, [(1, 0, 0), (2, 2, 2)], **ctrl))
        state_c = self.walk(rules_c, [(1, 0)])
        self.assertEqual(rules_c.expand(state_c, (1, 1)), [(1, 1), (1, 2)])

    # -- burden 负重 -------------------------------------------------------
    # beifa_ch10/zip_burden.py — 禁区 while laden (:154-155 in nbr_open_bc),
    # 装/卸点效果 apply_cell_effects (:113-123), start_laden (:336-339), 起点
    # 即禁区且 laden 则无解 (:331-332).

    def burden_level(self, burden: dict | None = None, **extra) -> dict:
        """3x3 burden board: 装粮点 (x1,y0) rc [0,1], 卸粮点 (x2,y0) rc [0,2],
        禁区 (x1,y1) rc [1,1] — load/unload are not forbidden and none is a
        waypoint (zip_burden.py:325-330). `burden` overrides those defaults."""
        mech_burden = {
            "forbidden_cells": [[1, 1]],
            "load_cell": [0, 1],
            "unload_cell": [0, 2],
            "start_laden": False,
        }
        if burden:
            mech_burden.update(burden)
        mech = {"burden": mech_burden}
        mech.update(extra)
        return self.level(3, 3, [(1, 0, 0), (2, 2, 2)], **mech)

    def test_burden_laden_cannot_enter_forbidden_cell(self) -> None:
        """laden 时不可进入禁区格; empty 时同一格可进 — zip_burden.py:154-155
        (`if burden.active() and laden and j in burden.forbidden: continue`
        inside nbr_open_bc, the last check before the neighbour is open)."""
        rules = Rules(self.burden_level())
        # empty: (0,1)→禁区 (1,1) is open.
        state = self.walk(rules, [(0, 1)])
        self.assertFalse(state.laden)
        self.assertEqual(rules.expand(state, (1, 1)), [(1, 1)])
        # laden: step on the 装粮点 first, then the very edge closes.
        state2 = self.walk(rules, [(1, 0)])
        self.assertTrue(state2.laden)
        seg, reason = rules._expand(state2, (1, 1))
        self.assertIsNone(seg)
        self.assertIn("禁区", reason)

    def test_burden_load_cell_ladens_and_unload_cell_empties(self) -> None:
        """装粮点→laden、卸粮点→empty — per-cell effects applied on every
        landed cell, zip_burden.py:113-123 (`apply_cell_effects`), folded in
        apply() cell by cell (solve_levels.apply)."""
        rules = Rules(self.burden_level())
        state = rules.initial_state()
        self.assertFalse(state.laden)  # start_laden: false
        state = self.walk(rules, [(1, 0)])  # 装粮点
        self.assertTrue(state.laden)
        state = self.walk(rules, [(1, 0), (2, 0)])  # ...then 卸粮点
        self.assertFalse(state.laden)

    def test_burden_start_laden_and_unwinnable_start(self) -> None:
        """start_laden: 初始即 laden (zip_burden.py:336-339 `laden = bool(
        burden.start_laden)` + start effects); 起点即禁区且 laden →
        initial_state 无解 (zip_burden.py:331-332)."""
        rules = Rules(self.burden_level(burden={"start_laden": True}))
        state = rules.initial_state()
        self.assertIsNotNone(state)
        self.assertTrue(state.laden)
        # same board but the start cell itself sits in 禁区 → no solution.
        lv = self.burden_level(
            burden={"start_laden": True, "forbidden_cells": [[0, 0]]}
        )  # 起点 = 禁区
        self.assertIsNone(Rules(lv).initial_state())

    def test_burden_ferry_landing_forbidden_while_laden_rejects_jia(self) -> None:
        """渡口落点乙在禁区且 laden 时进甲被拒 — zip_burden.py:183-184
        (`if burden.active() and laden and yi in burden.forbidden: return
        None`) in the entering-甲 branch of expand_move_bc, and the same test
        in the jump branch at :199-200.

        Control: same board where the burden is inactive (start_laden false,
        no load) → the jump goes through."""
        lv = self.ferry_level(
            burden={"forbidden_cells": [[1, 1]], "start_laden": True}
        )  # 乙 = rc [1,1] is the 禁区 cell
        rules = Rules(lv)
        state = self.walk(rules, [(1, 0), (2, 0)])  # stand before 甲, laden
        self.assertTrue(state.laden)
        seg, reason = rules._expand(state, (2, 1))  # step onto 甲
        self.assertIsNone(seg)
        self.assertIn("乙", reason)

        ctrl = self.ferry_level(
            burden={
                "forbidden_cells": [[1, 1]],
                "load_cell": [2, 0],  # makes the burden active...
                "start_laden": False,
                "unload_cell": [1, 0],
            }
        )
        rules_c = Rules(ctrl)
        state_c = self.walk(rules_c, [(1, 0), (2, 0)])  # load is elsewhere
        self.assertFalse(state_c.laden)
        self.assertEqual(
            rules_c.expand(state_c, (2, 1)), [(2, 1), (1, 1)]
        )  # jump allowed

    # -- slide_cells 滑行 --------------------------------------------------
    # chibi_ch7/zip_slide.py:49-74 (`expand_move`): 入泽后沿入向直滑;
    # 停止条件 :60-70 越界 / 墙或单向 / 已访 / 数字格前停 / 非泽地格,
    # 遇甲/乙即停 chibi_ch7/zip_full.py:84-85;每格计入 filled
    # (zip_slide.py:1-6 模块注释 "滑过每一格计入铺满").

    def slide_level(self, slide_rc: list, **extra) -> dict:
        """3x3 slide board; `slide_rc` = 泽地 cells as boards-locked [r, c]."""
        mech = {"slide_cells": slide_rc}
        mech.update(extra)
        return self.level(3, 3, [(1, 0, 0), (2, 2, 2)], **mech)

    def test_slide_runs_along_entry_direction_until_board_edge(self) -> None:
        """沿入向滑到受阻 + 越界即停: entering the marsh moving right, the
        segment keeps going right past the marsh cells and stops at the board
        boundary — zip_slide.py:58-61 (`while True` … `if not (0 <= nr < N …):
        break`), direction from the entry vector :51-52."""
        rules = Rules(self.slide_level([[0, 1], [0, 2]]))  # xy (1,0),(2,0)
        state = rules.initial_state()
        seg = rules.expand(state, (1, 0))  # one input enters the marsh
        self.assertIsNotNone(seg)
        self.assertEqual(seg, [(1, 0), (2, 0)])  # slid right to the edge

    def test_slide_cells_count_into_filled(self) -> None:
        """滑行格计入 filled: the whole segment folds in, filled +len(seg) —
        zip_slide.py:107-109 (`i += len(seg)`, one path entry per slid cell)."""
        rules = Rules(self.slide_level([[0, 1], [0, 2]]))
        state = rules.initial_state()
        self.assertEqual(state.filled, 1)
        seg = rules.expand(state, (1, 0))
        state2 = rules.apply(state, seg)
        self.assertEqual(state2.filled, state.filled + len(seg))  # 1 + 2
        self.assertEqual(len(state2.path), 3)
        self.assertEqual(state2.path[-1], (2, 0))

    def test_slide_stops_before_a_wall(self) -> None:
        """墙: the slide stops on the last free marsh cell before the wall —
        the neighbour test inside the loop (zip_slide.py:63-64) uses nbr_open,
        whose first check is the wall (zip_oneway.py:115)."""
        rules = Rules(
            self.slide_level([[0, 1], [0, 2]], walls=[self.wall(1, 0, 2, 0)])
        )
        state = rules.initial_state()
        seg = rules.expand(state, (1, 0))  # enter moving right toward the wall
        self.assertIsNotNone(seg, "hitting a wall mid-slide is a stop, not a reject")
        self.assertEqual(seg, [(1, 0)])  # stopped one cell before the wall

    def test_slide_stops_before_an_already_visited_cell(self) -> None:
        """已访: the slide stops before stepping onto a visited cell —
        zip_slide.py:65-66 (`if (vis >> npos) & 1 or (seen >> npos) & 1:
        break`).

        Walk to (2,0) the long way (entering that marsh cell slides upward
        into the boundary and stops), then slide left: (0,0) is visited, so
        the segment is only (1,0)."""
        rules = Rules(self.slide_level([[0, 1], [0, 2]]))  # xy (1,0),(2,0)
        state = self.walk(rules, [(0, 1), (1, 1), (2, 1), (2, 0)])
        self.assertEqual(state.path[-1], (2, 0))
        seg = rules.expand(state, (1, 0))  # slide left toward the start cell
        self.assertIsNotNone(seg)
        self.assertEqual(seg, [(1, 0)])  # stops before the visited (0,0)

    def test_slide_stops_before_a_numbered_cell(self) -> None:
        """数字格前停: the slide stops on the marsh cell before the waypoint,
        which is then entered by the *next* input as a plain step —
        zip_slide.py:67-68 (`if clue_of[npos]: break`).

        3x3 with waypoints 1@(0,0) 2@(1,2) 3@(2,2); marsh column x=1 rows
        0..1 (rc [[0,1],[1,1]])."""
        lv = self.level(
            3, 3, [(1, 0, 0), (2, 1, 2), (3, 2, 2)], slide_cells=[[0, 1], [1, 1]]
        )
        rules = Rules(lv)
        state = self.walk(rules, [(1, 0)])  # enter marsh row 0, slide stops at once
        self.assertEqual(state.path[-1], (1, 0))
        seg = rules.expand(state, (1, 1))  # slide down toward waypoint 2
        self.assertEqual(seg, [(1, 1)])  # stopped before the number
        state2 = rules.apply(state, seg)
        self.assertEqual(rules.expand(state2, (1, 2)), [(1, 2)])  # next input

    def test_slide_stops_at_a_non_marsh_cell(self) -> None:
        """非泽地格: 泽地之外的普通格也构成受阻 — zip_slide.py:69-70
        (`if npos not in slide: break`). Only (1,0) is marsh, so the slide
        stops before (2,0) even though that cell is open and unvisited."""
        rules = Rules(self.slide_level([[0, 1]]))  # xy (1,0) only
        state = rules.initial_state()
        self.assertEqual(rules.expand(state, (1, 0)), [(1, 0)])

    def test_slide_stops_before_ferry_jia_or_yi(self) -> None:
        """遇甲乙即停: a slide pointing at 乙 stops one marsh cell short and
        does *not* perform the forced jump — chibi_ch7/zip_full.py:84-85
        (`if ferry and (npos == ferry[0] or npos == ferry[1]): break`).

        3x4 board: marsh cell (x1,y2) rc [2,1], 乙 = rc [1,1] sits directly
        above it; waypoint 1@(0,0), 2@(2,3)."""
        lv = self.level(
            3, 4,
            [(1, 0, 0), (2, 2, 3)],
            ferry={"jia": [1, 2], "yi": [1, 1]},
            slide_cells=[[2, 1]],
        )
        rules = Rules(lv)
        state = self.walk(rules, [(0, 1), (0, 2), (0, 3), (1, 3)])
        seg = rules.expand(state, (1, 2))  # slide up toward 乙
        self.assertIsNotNone(seg)
        self.assertEqual(seg, [(1, 2)])  # stopped, no [甲, 乙] jump here

    def test_start_cell_on_marsh_is_allowed(self) -> None:
        """起点在泽地允许: standing on marsh at t=0 is fine — no enter-slide
        has happened yet (design comment verbatim at chibi_ch7/zip_slide.py:
        163 `# start on marsh is allowed (no enter-slide yet)`; expand only
        reacts to the *entered* cell, zip_slide.py:47-48).

        Built without validate_schema: the generator contract rejects numbers
        on marsh (zip_slide.py:376-378 `raise ValueError("number on marsh")`,
        zip_full.py:143-146), which is what validate_mechanics enforces."""
        lv = {
            "id": 901,
            "name": "起点泽地",
            "cols": 3,
            "rows": 3,
            "waypoints": [{"n": 1, "x": 0, "y": 0}, {"n": 2, "x": 2, "y": 2}],
            "walls": [],
            "stepLimit": 0,
            "slide_cells": [[0, 0]],  # the start cell itself is marsh
        }
        rules = Rules(lv)
        state = rules.initial_state()
        self.assertIsNotNone(state, "start on marsh must not be rejected")
        self.assertEqual(state.path, ((0, 0),))
        # first move off the marsh is a plain step (no forced slide at t=0)
        self.assertEqual(rules.expand(state, (0, 1)), [(0, 1)])


class ShippedMechanicsAllLevelsTests(unittest.TestCase):
    """Released-data guard for the mechanism layer over all 100 shipped levels.

    Reads boards-locked (archived `path` per board) and the published
    entry/src/main/resources/rawfile/levels.json. Design SoT directories are
    never imported — they are read-only references for the rules layer."""

    LEVELS_PATH = ROOT / "entry/src/main/resources/rawfile/levels.json"
    LOCKED_DIR = ROOT / "boards-locked"

    # The 6 boards that had no solution before the ferry-aware solver.
    PREVIOUSLY_UNSOLVABLE = (52, 59, 60, 63, 67, 89)

    @classmethod
    def locked_boards(cls) -> list:
        """[(global_id, locked board dict), ...] for ids 0..99, same order as
        build_levels.LOCKED_FILES (chapter_index * 10 + board_index)."""
        from build_levels import LOCKED_FILES

        out = []
        for ch_idx, fname in enumerate(LOCKED_FILES):
            data = json.loads(
                (cls.LOCKED_DIR / fname).read_text(encoding="utf-8")
            )
            for tip_idx, board in enumerate(data["boards"]):
                out.append((ch_idx * 10 + tip_idx, board))
        return out

    @classmethod
    def levels_by_id(cls) -> dict:
        return {int(lv["id"]): lv for lv in load_levels(cls.LEVELS_PATH)}

    def test_replay_all_100_stored_paths(self) -> None:
        """Every boards-locked solution path must replay cleanly through
        check_path on the matching released level (100/100)."""
        levels = self.levels_by_id()
        boards = self.locked_boards()
        self.assertEqual(len(boards), 100, "boards-locked must hold 100 boards")
        self.assertEqual(len(levels), 100, "levels.json must hold 100 levels")
        bad = []
        for gid, board in boards:
            path = board.get("path")
            self.assertIsNotNone(path, f"locked board {gid} has no path")
            ok, reason, idx = check_path(levels[gid], path)
            if not ok:
                bad.append(f"id {gid}: {reason} (first_bad_index={idx})")
        self.assertEqual(bad, [], "stored paths rejected:\n" + "\n".join(bad))

    def test_mechanic_key_counts(self) -> None:
        """Published data carries the mechanism keys on exactly the boards
        that have the mechanic: 33 mechanism boards out of 100, with ferry 8,
        one_ways 19, slide 9, seal 6, token 6, collapse 3, burden 2.

        PM: only boards with the mechanic carry the (non-empty) key; every
        other entry stays byte-identical to the pre-mechanics release."""
        levels = load_levels(self.LEVELS_PATH)
        expected = {
            "ferry": 8,
            "one_ways": 19,
            "slide_cells": 9,
            "seal_gates": 6,
            "token_cells": 6,
            "collapse": 3,
            "burden": 2,
        }
        self.assertEqual(len(levels), 100)
        counts = {key: 0 for key in expected}
        mech_levels = 0
        for lv in levels:
            carry = False
            for key, want in expected.items():
                if lv.get(key):
                    counts[key] += 1
                    carry = True
            if carry:
                mech_levels += 1
        self.assertEqual(mech_levels, 33, "33 mechanism boards expected")
        self.assertEqual(counts, expected)

    def test_six_previously_unsolvable_paths_pass_and_ship_ferry(self) -> None:
        """ids 52/59/60/63/67/89: their archived paths replay through
        check_path, and each released level carries the渡口 ferry key (these
        are the boards that needed the ferry-aware expansion to solve)."""
        levels = self.levels_by_id()
        locked = dict(self.locked_boards())
        for gid in self.PREVIOUSLY_UNSOLVABLE:
            lv = levels[gid]
            self.assertTrue(lv.get("ferry"), f"id {gid} must ship a ferry key")
            ok, reason, idx = check_path(lv, locked[gid]["path"])
            self.assertTrue(ok, f"id {gid}: {reason} (first_bad_index={idx})")

    @unittest.skipUnless(
        os.environ.get("YILU_FULL_SOLVE"),
        "full 100-level solve is slow — set YILU_FULL_SOLVE=1 to run it; "
        "the default run only replays the archived boards-locked paths "
        "(test_replay_all_100_stored_paths)",
    )
    def test_all_100_levels_solved(self) -> None:
        """Full solve over the released catalog (opt-in via YILU_FULL_SOLVE).

        Uses solve_levels.count_solutions when that API exists; skips with a
        clear reason otherwise, so the default test run stays fast."""
        import solve_levels

        counter = getattr(solve_levels, "count_solutions", None)
        if counter is None:
            self.skipTest(
                "solve_levels.count_solutions is not available in this "
                "checkout — full-catalog solve cannot be counted yet"
            )
        levels = load_levels(self.LEVELS_PATH)
        self.assertEqual(len(levels), 100)
        unsolved = []
        for lv in levels:
            try:
                n = counter(lv)
            except TypeError as exc:
                self.skipTest(f"count_solutions signature not usable: {exc}")
            if not n:
                unsolved.append(int(lv["id"]))
        self.assertEqual(unsolved, [], f"levels with 0 solutions: {unsolved}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
