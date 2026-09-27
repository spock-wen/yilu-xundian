#!/usr/bin/env python3
"""Independent solver for 「驿路巡点」 levels.

Rules (LinkedIn Zip / Hamiltonian path with ordered waypoints), plus the
mechanics that boards-locked actually stores and this solver can check:

- Orthogonal 4-direction steps only, except a ferry jump
- Visit every cell exactly once
- Visit numbered waypoints in increasing order 1..N
- Start on cell 1; end on the highest number
- Path cannot cross walls or itself
- parity edges: filled = cells already laid, including the standing cell,
  before the step. Odd filled may cross require_odd; even filled may cross
  require_even. Source: boards-locked parity_rule (ch9 / ch10).
- one_ways: the reverse of each from→to edge is blocked. Forward stays optional.
- ferry: forced one-way jump. Stepping onto 甲 by a walk marks 甲 visited and
  the only continuation is a jump to 乙 (乙 visited). Cells between 甲 and 乙
  are not skipped. Source: boards-locked ferry_rule.
- slide cells: entering a slide cell by a walk continues in the entry direction
  through contiguous slide cells, stopping before a non-slide cell, wall, edge,
  filled cell, or numbered cell. Every slid cell counts toward the fill.
  Source: boards-locked slide_rule ("Stop before wall/edge/filled/numbered").
  Straight-line sliding onto non-slide cells rejects the stored paths of
  locked boards 43 and 49, so the continuation stays on the slide strip.
- seal_gates / token_cells / burden / collapse have prose in the locked files
  but no implementation in the engine or this solver. Those levels are reported
  as "UNSUPPORTED mechanic — not verified" and never counted as a pass.

Coordinates: boards-locked cells are [row, col]. This solver and levels.json
use x=col, y=row.

The default CLI checks every locked board against the shipped levels.json.
It does not hard-code a level count. It exits non-zero when a shipped level
has 0 solutions, when uniqueness is lost against the locked board, when a
mechanic is unsupported, when a stored path is illegal, or when a search
times out. It does not rewrite boards.

Usage (from repo root):
    python3 tools/solve_levels.py
    python3 tools/solve_levels.py --timeout 30
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Iterable


DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))
UNSUPPORTED_FIELDS = ("seal_gates", "token_cells", "burden", "collapse")


def cell_key(x: int, y: int) -> int:
    return y * 64 + x


def wall_key(x1: int, y1: int, x2: int, y2: int) -> tuple[int, int]:
    a = cell_key(x1, y1)
    b = cell_key(x2, y2)
    return (a, b) if a < b else (b, a)


def load_levels(path: Path) -> list[dict]:
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "levels" in data:
        return data["levels"]
    if isinstance(data, list):
        return data
    raise ValueError("levels.json must be a list or {\"levels\": [...]}")


def validate_schema(level: dict) -> None:
    required = ("id", "name", "cols", "rows", "waypoints")
    for key in required:
        if key not in level:
            raise ValueError(f"level missing '{key}': {level}")
    cols, rows = int(level["cols"]), int(level["rows"])
    if cols < 2 or rows < 2:
        raise ValueError(f"level {level['id']}: grid too small")
    wps = sorted(level["waypoints"], key=lambda w: int(w["n"]))
    nums = [int(w["n"]) for w in wps]
    if nums != list(range(1, len(nums) + 1)):
        raise ValueError(f"level {level['id']}: waypoints must be 1..N contiguous, got {nums}")
    seen = set()
    for w in wps:
        x, y = int(w["x"]), int(w["y"])
        if not (0 <= x < cols and 0 <= y < rows):
            raise ValueError(f"level {level['id']}: waypoint {w} out of bounds")
        if (x, y) in seen:
            raise ValueError(f"level {level['id']}: duplicate waypoint cell {(x, y)}")
        seen.add((x, y))
    for wall in level.get("walls") or []:
        x1, y1, x2, y2 = (int(wall[k]) for k in ("x1", "y1", "x2", "y2"))
        if abs(x1 - x2) + abs(y1 - y2) != 1:
            raise ValueError(f"level {level['id']}: wall not orthogonal: {wall}")
        for x, y in ((x1, y1), (x2, y2)):
            if not (0 <= x < cols and 0 <= y < rows):
                raise ValueError(f"level {level['id']}: wall out of bounds: {wall}")


class SolverTimeout(Exception):
    """Search exceeded the per-level budget. The board is not rewritten."""


class Compiled:
    """Static geometry for one level, in (x, y) coordinates."""

    def __init__(self, level: dict) -> None:
        self.cols = int(level["cols"])
        self.rows = int(level["rows"])
        self.total = self.cols * self.rows
        self.full_mask = (1 << self.total) - 1
        self.wps = {(int(w["x"]), int(w["y"])): int(w["n"]) for w in level["waypoints"]}
        self.max_n = max(self.wps.values())
        self.start = next(xy for xy, n in self.wps.items() if n == 1)
        self.end = next(xy for xy, n in self.wps.items() if n == self.max_n)
        walls: set[tuple[int, int]] = set()
        for wall in level.get("walls") or []:
            walls.add(wall_key(int(wall["x1"]), int(wall["y1"]), int(wall["x2"]), int(wall["y2"])))
        blocked_reverse: set[tuple[tuple[int, int], tuple[int, int]]] = set()
        for edge in level.get("oneWays") or []:
            src = (int(edge["x1"]), int(edge["y1"]))
            dst = (int(edge["x2"]), int(edge["y2"]))
            blocked_reverse.add((dst, src))
        self.parity: dict[tuple[int, int], str] = {}
        for edge in level.get("parityEdges") or []:
            kind = "odd" if edge.get("requireOdd") else "even"
            self.parity[wall_key(int(edge["x1"]), int(edge["y1"]), int(edge["x2"]), int(edge["y2"]))] = kind
        self.slides = {(int(c["x"]), int(c["y"])) for c in (level.get("slideCells") or [])}
        ferry = level.get("ferry")
        if ferry:
            jia = ferry["jia"]
            yi = ferry["yi"]
            self.jia: tuple[int, int] | None = (int(jia["x"]), int(jia["y"]))
            self.yi: tuple[int, int] | None = (int(yi["x"]), int(yi["y"]))
        else:
            self.jia = None
            self.yi = None
        self.yi_bit = 0 if self.yi is None else self.bit(self.yi[0], self.yi[1])
        self.jia_idx = None if self.jia is None else self.index(self.jia[0], self.jia[1])
        self.neigh: list[list[tuple[int, int, int, int, int]]] = [[] for _ in range(self.total)]
        self.neigh_mask = [0] * self.total
        for y in range(self.rows):
            for x in range(self.cols):
                idx = self.index(x, y)
                for dx, dy in DIRS:
                    nx, ny = x + dx, y + dy
                    if not (0 <= nx < self.cols and 0 <= ny < self.rows):
                        continue
                    if wall_key(x, y, nx, ny) in walls:
                        continue
                    if ((x, y), (nx, ny)) in blocked_reverse:
                        continue
                    bit = self.bit(nx, ny)
                    self.neigh[idx].append((nx, ny, bit, dx, dy))
                    self.neigh_mask[idx] |= bit

    def index(self, x: int, y: int) -> int:
        return y * self.cols + x

    def bit(self, x: int, y: int) -> int:
        return 1 << self.index(x, y)

    def can_step(self, x: int, y: int, nx: int, ny: int, nbit: int, filled: int) -> bool:
        if (self.neigh_mask[self.index(x, y)] & nbit) == 0:
            return False
        if not self.parity:
            return True
        kind = self.parity.get(wall_key(x, y, nx, ny))
        if kind == "odd" and filled % 2 == 0:
            return False
        if kind == "even" and filled % 2 == 1:
            return False
        return True

    def slide_extra(
        self,
        x: int,
        y: int,
        dx: int,
        dy: int,
        visited: int,
        filled0: int,
    ) -> list[tuple[int, int]]:
        """Cells after the slide cell (x, y). filled0 is the path length before (x, y)."""
        extras: list[tuple[int, int]] = []
        cx, cy = x, y
        seen = visited | self.bit(x, y)
        filled = filled0 + 1
        while True:
            nx, ny = cx + dx, cy + dy
            if not (0 <= nx < self.cols and 0 <= ny < self.rows):
                break
            nbit = self.bit(nx, ny)
            if seen & nbit:
                break
            if (nx, ny) in self.wps:
                break
            if not self.can_step(cx, cy, nx, ny, nbit, filled):
                break
            if (nx, ny) not in self.slides:
                break
            extras.append((nx, ny))
            seen |= nbit
            filled += 1
            cx, cy = nx, ny
        return extras

    def legal_moves(
        self,
        x: int,
        y: int,
        visited: int,
        next_n: int,
        arrived_by_walk: bool,
        path_len: int,
    ) -> list[tuple[list[tuple[int, int]], bool]]:
        """Return (cells, next_arrived_by_walk) options from the standing cell.

        next_arrived_by_walk is true only for a one-cell orthogonal step. A ferry
        jump and a multi-cell slide both land with it false.
        """
        if self.jia is not None and arrived_by_walk and (x, y) == self.jia:
            assert self.yi is not None
            yx, yy = self.yi
            if visited & self.yi_bit:
                return []
            num = self.wps.get((yx, yy), 0)
            if num != 0 and num != next_n:
                return []
            if (yx, yy) == self.end and path_len + 1 != self.total:
                return []
            return [([(yx, yy)], False)]

        moves: list[tuple[int, int, int, list[tuple[int, int]], bool]] = []
        idx = self.index(x, y)
        for nx, ny, nbit, dx, dy in self.neigh[idx]:
            if visited & nbit:
                continue
            if not self.can_step(x, y, nx, ny, nbit, path_len):
                continue
            num = self.wps.get((nx, ny), 0)
            if num != 0 and num != next_n:
                continue
            cells = [(nx, ny)]
            if (nx, ny) in self.slides:
                cells.extend(self.slide_extra(nx, ny, dx, dy, visited, path_len))
            if any(cell == self.end for cell in cells[:-1]):
                continue
            if cells[-1] == self.end and path_len + len(cells) != self.total:
                continue
            if any(self.wps.get(cell, 0) for cell in cells[1:]):
                continue
            extra_bits = 0
            blocked = False
            for cell in cells[1:]:
                bit = self.bit(cell[0], cell[1])
                if visited & bit or extra_bits & bit:
                    blocked = True
                    break
                extra_bits |= bit
            if blocked:
                continue
            deg = (self.neigh_mask[self.index(nx, ny)] & ~visited).bit_count()
            arrived = len(cells) == 1
            moves.append((deg, ny, nx, cells, arrived))
        moves.sort()
        return [(cells, arrived) for _, _, _, cells, arrived in moves]

    def reachable(self, visited: int, x: int, y: int, must_jump: bool) -> bool:
        unvisited = self.full_mask ^ visited
        if unvisited == 0:
            return True
        seen = 0
        if must_jump:
            if self.yi is None or (visited & self.yi_bit):
                return False
            frontier = self.yi_bit & unvisited
        else:
            frontier = self.neigh_mask[self.index(x, y)] & unvisited
        while frontier:
            bit = frontier & -frontier
            frontier ^= bit
            if seen & bit:
                continue
            seen |= bit
            j = bit.bit_length() - 1
            frontier |= self.neigh_mask[j] & unvisited & ~seen
            if self.jia_idx is not None and j == self.jia_idx and self.yi_bit:
                if (visited & self.yi_bit) == 0 and (seen & self.yi_bit) == 0:
                    frontier |= self.yi_bit & unvisited
        return seen == unvisited


def compile_level(level: dict) -> Compiled:
    return Compiled(level)


def solve(
    level: dict,
    find_all: bool = False,
    limit: int = 1,
    timeout_s: float | None = None,
    *,
    connectivity: bool = True,
) -> list[list[tuple[int, int]]]:
    """DFS Hamiltonian path with waypoint order, ferry, one-ways, slides, parity.

    find_all=False stops at the first solution. limit caps how many are kept.
    connectivity prunes positions that cannot reach every unvisited cell
    (walls, one-ways, and the forced ferry jump; parity and slides stay
    conservative so a legal path is not discarded).
    """
    comp = Compiled(level)
    solutions: list[list[tuple[int, int]]] = []
    start = comp.start
    path = [start]
    start_mask = comp.bit(start[0], start[1])
    deadline = None if timeout_s is None else time.monotonic() + timeout_s
    ticks = 0

    def dfs(x: int, y: int, visited: int, next_n: int, arrived_by_walk: bool) -> None:
        nonlocal ticks
        if solutions and not find_all:
            return
        if len(solutions) >= limit:
            return
        path_len = len(path)
        if path_len == comp.total:
            if (x, y) == comp.end and next_n == comp.max_n + 1:
                solutions.append(list(path))
            return
        ticks += 1
        if deadline is not None and ticks % 4096 == 0 and time.monotonic() > deadline:
            raise SolverTimeout()
        must_jump = comp.jia is not None and arrived_by_walk and (x, y) == comp.jia
        if connectivity and not comp.reachable(visited, x, y, must_jump):
            return
        for cells, arrived in comp.legal_moves(x, y, visited, next_n, arrived_by_walk, path_len):
            new_visited = visited
            nn = next_n
            for cx, cy in cells:
                path.append((cx, cy))
                new_visited |= comp.bit(cx, cy)
                num = comp.wps.get((cx, cy), 0)
                if num == nn:
                    nn += 1
            dfs(cells[-1][0], cells[-1][1], new_visited, nn, arrived)
            del path[-len(cells) :]
            if solutions and not find_all:
                return
            if len(solutions) >= limit:
                return

    dfs(start[0], start[1], start_mask, 2, False)
    return solutions


def verify_path(level: dict, path: list[tuple[int, int]]) -> tuple[bool, str]:
    """Replay a path under the same move rules solve() uses."""
    comp = Compiled(level)
    if len(path) != comp.total or len(set(path)) != comp.total:
        return False, f"coverage len={len(path)} uniq={len(set(path))} grid={comp.total}"
    if path[0] != comp.start:
        return False, f"start {path[0]} != {comp.start}"
    visited = comp.bit(path[0][0], path[0][1])
    next_n = 2
    arrived = False
    index = 0
    while index < comp.total - 1:
        x, y = path[index]
        options = comp.legal_moves(x, y, visited, next_n, arrived, index + 1)
        matched: tuple[list[tuple[int, int]], bool] | None = None
        for cells, next_arrived in options:
            if path[index + 1 : index + 1 + len(cells)] == cells:
                matched = (cells, next_arrived)
                break
        if matched is None:
            nxt = path[index + 1] if index + 1 < len(path) else None
            return False, f"illegal step at index {index}: {path[index]} -> {nxt}"
        cells, arrived = matched
        for cx, cy in cells:
            num = comp.wps.get((cx, cy), 0)
            if num and num != next_n:
                return False, f"waypoint {num} out of order at {cx, cy}"
            if num == next_n:
                next_n += 1
            visited |= comp.bit(cx, cy)
        index += len(cells)
    if index != comp.total - 1:
        return False, f"path consumed to index {index}"
    if path[-1] != comp.end:
        return False, "does not end on the highest waypoint"
    if next_n != comp.max_n + 1:
        return False, "not all waypoints"
    return True, "ok"


def format_path(path: list[tuple[int, int]]) -> str:
    return " -> ".join(f"({x},{y})" for x, y in path)


def report_solve_exit(
    unsolvable: int = 0,
    timed_out: int = 0,
    *,
    non_unique: int = 0,
    unsupported: int = 0,
    stored_invalid: int = 0,
    total: int | None = None,
) -> int:
    """Non-zero unless every level was solved, unique where the locked board is, and fully verified.

    A timeout is not a pass: the board is left untouched, but solvability was not shown.
    `total` is accepted so older call sites can still name the catalog size; it does not
    change the exit decision.
    """
    del total
    problems = []
    if unsolvable:
        problems.append(f"{unsolvable} unsolvable")
    if non_unique:
        problems.append(f"{non_unique} lost uniqueness")
    if unsupported:
        problems.append(f"{unsupported} unsupported mechanic")
    if stored_invalid:
        problems.append(f"{stored_invalid} stored path invalid")
    if timed_out:
        problems.append(f"{timed_out} timed out")
    if problems:
        print("RESULT: FAIL (" + "; ".join(problems) + "). Do not ship.")
        return 1
    print("RESULT: PASS")
    return 0


def _mechanic_present(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, tuple, dict)) and len(value) == 0:
        return False
    return True


def load_locked_levels() -> list[dict]:
    """Locked boards as solver levels, including mechanics levels.json drops.

    Uses convert_board only as the lossy waypoint/wall/parity projection, then
    reattaches one_ways, ferry, and slide cells. Seal, burden, and collapse are
    recorded as unsupported and are not given invented rules.
    """
    from build_levels import convert_board, dropped_mechanic_fields, iter_locked_boards

    levels: list[dict] = []
    for global_id, board in iter_locked_boards():
        level = convert_board(board, global_id, allow_dropped_mechanics=True)
        one_ways = []
        for edge in board.get("one_ways") or []:
            r1, c1 = edge["from"]
            r2, c2 = edge["to"]
            one_ways.append({"x1": int(c1), "y1": int(r1), "x2": int(c2), "y2": int(r2)})
        level["oneWays"] = one_ways
        ferry = board.get("ferry")
        if ferry:
            jr, jc = ferry["jia"]
            yr, yc = ferry["yi"]
            level["ferry"] = {
                "jia": {"x": int(jc), "y": int(jr)},
                "yi": {"x": int(yc), "y": int(yr)},
            }
        else:
            level["ferry"] = None
        level["slideCells"] = [
            {"x": int(c), "y": int(r)} for r, c in (board.get("slide_cells") or [])
        ]
        level["storedPath"] = [(int(c), int(r)) for r, c in (board.get("path") or [])]
        raw_meta = board.get("sols_no_ferry")
        level["solsNoFerry"] = int(raw_meta) if isinstance(raw_meta, int) else None
        level["droppedFields"] = dropped_mechanic_fields(board)
        level["unsupported"] = [name for name in UNSUPPORTED_FIELDS if name in level["droppedFields"]]
        levels.append(level)
    return levels


def _id_list(ids: Iterable[int]) -> str:
    return ",".join(str(i) for i in ids) if ids else "(none)"


def _solve_capped(level: dict, limit: int, timeout_s: float) -> tuple[list[list[tuple[int, int]]] | None, str]:
    try:
        return solve(level, find_all=True, limit=limit, timeout_s=timeout_s), "done"
    except SolverTimeout:
        return None, "TIMEOUT"


def run_gate(shipped_path: Path, *, timeout_s: float, cap: int = 2) -> int:
    """Compare every locked board with the shipped catalog. cap is the solution ceiling (2 = unique vs not)."""
    shipped = load_levels(shipped_path)
    locked = load_locked_levels()
    for level in shipped:
        validate_schema(level)
    if [int(level["id"]) for level in locked] != [int(level["id"]) for level in shipped]:
        print(
            "FAIL: locked board ids and shipped levels.json ids differ "
            f"(locked {len(locked)}, shipped {len(shipped)})",
            file=sys.stderr,
        )
        return 2

    print(f"GATE locked+shipped levels={len(locked)} cap={cap} timeout={timeout_s}s")
    print("Rules: ferry=forced one-way jump 甲→乙; one_ways reverse blocked; "
          "slide=contiguous slide cells in the entry direction; parity on filled-before-step.")
    print("-" * 72)

    unsolvable: list[int] = []
    non_unique: list[int] = []
    still_unique: list[int] = []
    unsupported_ids: list[int] = []
    stored_invalid: list[int] = []
    timed_out: list[int] = []
    meta_notes: list[str] = []

    shipped_by_id = {int(level["id"]): level for level in shipped}
    for locked_level in locked:
        lid = int(locked_level["id"])
        shipped_level = shipped_by_id[lid]
        name = locked_level["name"]
        unsupported = list(locked_level.get("unsupported") or [])
        dropped = list(locked_level.get("droppedFields") or [])
        stored = list(locked_level.get("storedPath") or [])

        if unsupported:
            unsupported_ids.append(lid)

        stored_ok, stored_reason = verify_path(locked_level, stored) if stored else (False, "missing stored path")
        if not stored_ok and not unsupported:
            stored_invalid.append(lid)
        stored_label = "OK" if stored_ok else "INVALID"
        if unsupported:
            stored_label = ("PARTIAL:" + stored_label)

        locked_sols, locked_state = _solve_capped(locked_level, cap, timeout_s)
        ship_sols, ship_state = _solve_capped(shipped_level, cap, timeout_s)

        if locked_state == "TIMEOUT" or ship_state == "TIMEOUT":
            timed_out.append(lid)
            bucket = "TIMEOUT"
            locked_n = "TIMEOUT" if locked_sols is None else len(locked_sols)
            ship_n = "TIMEOUT" if ship_sols is None else len(ship_sols)
        else:
            assert locked_sols is not None and ship_sols is not None
            locked_n = len(locked_sols)
            ship_n = len(ship_sols)
            if stored_ok and locked_n == 1 and locked_sols[0] != stored:
                locked_n = 2
            if ship_n == 0:
                bucket = "UNSOLVABLE"
                unsolvable.append(lid)
            elif ship_n >= cap:
                bucket = "NON-UNIQUE"
                non_unique.append(lid)
            else:
                bucket = "UNIQUE"
                still_unique.append(lid)

        flags = [bucket]
        if unsupported:
            flags.append(
                "UNSUPPORTED mechanic — not verified: " + ",".join(unsupported)
            )
        if not stored_ok and not unsupported:
            flags.append(f"stored {stored_reason}")
        dropped_text = ",".join(dropped) if dropped else "-"
        locked_text = f"{locked_n}" + (" partial" if unsupported else "")
        print(
            f"#{lid} {name}  locked={locked_text} shipped={ship_n} "
            f"stored={stored_label}  {'  '.join(flags)}  dropped={dropped_text}",
            flush=True,
        )

        meta = locked_level.get("solsNoFerry")
        if isinstance(meta, int):
            stripped = dict(locked_level)
            stripped["ferry"] = None
            # Same supported rules with the ferry removed. Cap above the metadata
            # value so a completed search can disagree with sols_no_ferry.
            meta_cap = max(meta + 1, cap)
            meta_sols, meta_state = _solve_capped(stripped, meta_cap, timeout_s)
            if meta_state == "TIMEOUT" or meta_sols is None:
                meta_notes.append(
                    f"#{lid} sols_no_ferry metadata={meta} exhaustive_without_ferry=TIMEOUT (not rewritten)"
                )
            else:
                found = len(meta_sols)
                exact = found < meta_cap
                shown = str(found) if exact else f">={found}"
                if (exact and found != meta) or (not exact and found > meta):
                    meta_notes.append(
                        f"#{lid} sols_no_ferry metadata={meta} exhaustive_without_ferry={shown}"
                    )

    print("-" * 72)
    print(f"UNSOLVABLE: {_id_list(unsolvable)}")
    print(f"NON_UNIQUE: {_id_list(non_unique)}")
    print(f"STILL_UNIQUE: {_id_list(still_unique)}")
    print(f"UNSUPPORTED: {_id_list(unsupported_ids)}")
    if meta_notes:
        print("META sols_no_ferry mismatches (reported, boards not modified):")
        for note in meta_notes:
            print(f"  {note}")
    else:
        print("META sols_no_ferry: no mismatch in completed searches")
    if stored_invalid:
        print(f"STORED_INVALID: {_id_list(stored_invalid)}")
    if timed_out:
        print(f"TIMEOUT: {_id_list(timed_out)}")
    return report_solve_exit(
        unsolvable=len(unsolvable),
        timed_out=len(timed_out),
        non_unique=len(non_unique),
        unsupported=len(unsupported_ids),
        stored_invalid=len(stored_invalid),
        total=len(locked),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check every locked board against shipped levels.json (no hard-coded level count)."
    )
    parser.add_argument(
        "--json",
        default="entry/src/main/resources/rawfile/levels.json",
        help="Shipped levels.json to compare with boards-locked/",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Seconds per solve. Timeout fails the gate and does not rewrite the board.",
    )
    parser.add_argument(
        "--cap",
        type=int,
        default=2,
        help="Stop after this many solutions. 2 distinguishes unique from not unique.",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    json_path = Path(args.json)
    if not json_path.is_absolute():
        json_path = root / json_path
    if not json_path.exists():
        print(f"FAIL: missing {json_path}", file=sys.stderr)
        return 2
    if args.cap < 2:
        print("FAIL: --cap must be at least 2 to detect a second solution", file=sys.stderr)
        return 2
    return run_gate(json_path, timeout_s=args.timeout, cap=args.cap)


if __name__ == "__main__":
    sys.exit(main())
