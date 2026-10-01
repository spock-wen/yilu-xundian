#!/usr/bin/env python3
"""Independent solver for 「驿路巡点」 levels.

Rules (LinkedIn Zip / Hamiltonian path with ordered waypoints):
- Orthogonal 4-direction steps only
- Visit every cell exactly once
- Visit numbered waypoints in increasing order 1..N
- Start on cell 1; end on the highest number
- Path cannot cross walls or itself

This script is the source of truth for ship-or-reject. It does not share
code with the Cangjie app.

Usage (from repo root):
    python3 tools/solve_levels.py
    python3 tools/solve_levels.py --json entry/src/main/resources/rawfile/levels.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def cell_key(x: int, y: int) -> int:
    return y * 64 + x


def wall_key(x1: int, y1: int, x2: int, y2: int) -> tuple[int, int]:
    a = cell_key(x1, y1)
    b = cell_key(x2, y2)
    return (a, b) if a < b else (b, a)


def load_levels(path: Path) -> list[dict]:
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
    validate_mechanics(level)


# ---------------------------------------------------------------------------
# Mechanism key readers.
#
# Released levels.json keeps two coordinate conventions (PM ruling):
#   * pre-existing keys (waypoints / walls / parityEdges) use x/y  (x=col, y=row)
#   * new mechanism keys (ferry/one_ways/slide_cells/seal_gates/token_cells/
#     collapse/burden) keep the boards-locked [r, c] shape verbatim.
# Everything below normalises to in-memory (x, y) = (col, row) cells; the file
# data itself is never rewritten.
#
# Design code is the rules authority. This module never imports it — every
# file:line below is a *comment* pointer into the read-only design sources.
# ---------------------------------------------------------------------------


def rc_to_xy(rc) -> tuple[int, int]:
    """boards-locked `[r, c]` -> in-memory `(x, y)` = `(col, row)`."""
    r, c = rc
    return (int(c), int(r))


def edge_key(a: tuple[int, int], b: tuple[int, int]) -> tuple[tuple[int, int], tuple[int, int]]:
    """Undirected cell edge, same ordering rule as design `undirected_key`
    (lvbu_ch4/zip_oneway.py:24-25)."""
    return (a, b) if a < b else (b, a)


def read_walls(level: dict) -> set:
    """Published walls: `x1,y1,x2,y2` already in x/y."""
    out = set()
    for wall in level.get("walls") or []:
        a = (int(wall["x1"]), int(wall["y1"]))
        b = (int(wall["x2"]), int(wall["y2"]))
        out.add(edge_key(a, b))
    return out


def read_parity(level: dict) -> dict:
    """Published `parityEdges`: x/y + camelCase `requireOdd`/`requireEven`.
    Design parse: hanzhong_ch9/zip_parity.py:30-43 (`parity_from_json`), test at
    hanzhong_ch9/zip_parity.py:59-64 (`parity_ok`)."""
    out: dict = {}
    for e in level.get("parityEdges") or []:
        a = (int(e["x1"]), int(e["y1"]))
        b = (int(e["x2"]), int(e["y2"]))
        req_odd = e.get("requireOdd")
        if req_odd is None:
            req_even = e.get("requireEven")
            req_odd = (not req_even) if req_even is not None else True
        out[edge_key(a, b)] = bool(req_odd)
    return out


def read_ferry(level: dict) -> tuple | None:
    """`ferry = {"jia": [r,c], "yi": [r,c]}`; design parse
    jingzhou_ch6/zip_ferry.py:27-33 (`ferry_from_json`)."""
    f = level.get("ferry")
    if not f:
        return None
    return (rc_to_xy(f["jia"]), rc_to_xy(f["yi"]))


def read_one_ways(level: dict) -> set:
    """`one_ways = [{"from": [r,c], "to": [r,c]}]` — directed; design parse
    lvbu_ch4/zip_oneway.py:84-96 (`ow_from_json`)."""
    out = set()
    for e in level.get("one_ways") or []:
        out.add((rc_to_xy(e["from"]), rc_to_xy(e["to"])))
    return out


def read_slide(level: dict) -> set:
    """`slide_cells = [[r,c], ...]` (泽地)."""
    return {rc_to_xy(rc) for rc in level.get("slide_cells") or []}


def read_gates(level: dict) -> set:
    """`seal_gates = [{"between": [[r,c],[r,c]], ...}]` — undirected edges.
    Design parse rushu_ch8/zip_seal.py:34-46 (`seal_from_json`)."""
    out = set()
    for g in level.get("seal_gates") or []:
        a, b = g["between"]
        out.add(edge_key(rc_to_xy(a), rc_to_xy(b)))
    return out


def read_tokens(level: dict) -> set:
    """`token_cells = [[r,c], ...]` (符节)."""
    return {rc_to_xy(rc) for rc in level.get("token_cells") or []}


def read_collapse(level: dict) -> tuple | None:
    """`collapse = {"schema", "trigger_rc": [r,c], "collapse_edge": {...}}`.
    Design parse beifa_ch10/zip_burden.py:78-88 (`collapse_from_json`);
    schema is fixed to `step_on_trigger` (beifa_ch10/zip_burden.py:30-31)."""
    c = level.get("collapse")
    if not c:
        return None
    trigger = rc_to_xy(c["trigger_rc"])
    a, b = c["collapse_edge"]["between"]
    return (trigger, edge_key(rc_to_xy(a), rc_to_xy(b)))


def read_burden(level: dict) -> dict | None:
    """`burden = {"forbidden_cells", "load_cell", "unload_cell", "start_laden"}`.
    Design parse beifa_ch10/zip_burden.py:65-77 (`burden_from_json`) and
    `BurdenCfg.active()` beifa_ch10/zip_burden.py:44-46."""
    b = level.get("burden")
    if not b:
        return None
    load = b.get("load_cell")
    unload = b.get("unload_cell")
    cfg = {
        "forbidden": frozenset(rc_to_xy(rc) for rc in b.get("forbidden_cells") or []),
        "load": rc_to_xy(load) if load else None,
        "unload": rc_to_xy(unload) if unload else None,
        "start_laden": bool(b.get("start_laden")),
    }
    # BurdenCfg.active(): non-empty forbidden AND (load or unload or start_laden)
    # beifa_ch10/zip_burden.py:44-46
    cfg["active"] = bool(cfg["forbidden"]) and (
        cfg["load"] is not None or cfg["unload"] is not None or cfg["start_laden"]
    )
    return cfg


def validate_mechanics(level: dict) -> None:
    """Static (data-only) mechanism contracts. Raises ValueError.

    Only checks the design code performs on the *board data* before replay.
    Checks that need a concrete path (e.g. `path[0] != 甲`, `jumps == 1`,
    "path steps on the token") are deliberately out of scope here.

    Sources:
      ferry   jingzhou_ch6/zip_ferry.py:120-130, chibi_ch7/zip_full.py:147-156
      slide   chibi_ch7/zip_slide.py:92-95, chibi_ch7/zip_full.py:143-145
      seal    rushu_ch8/zip_seal.py:199-201
      parity  hanzhong_ch9/zip_parity.py:233-238
      collapse/burden beifa_ch10/zip_burden.py:323-332
    """
    lid = level.get("id")
    nums = {(int(w["x"]), int(w["y"])) for w in level["waypoints"]}
    walls = read_walls(level)
    ferry = read_ferry(level)
    slide = read_slide(level)
    gates = read_gates(level)
    parity = read_parity(level)
    collapse = read_collapse(level)
    burden = read_burden(level)

    if ferry is not None:
        jia, yi = ferry
        # zip_ferry.py:123-124 `if jia == yi: return False`
        if jia == yi:
            raise ValueError(f"level {lid}: ferry 甲 and 乙 are the same cell")
        # zip_full.py:151 `if jia in slide or yi in slide: return False`
        for cell in (jia, yi):
            if cell in slide:
                raise ValueError(f"level {lid}: ferry cell {cell} sits on 泽地")
            # 甲乙 must not be a numbered cell (zip_ferry expand_move returns
            # [jia, yi] as one segment, which could never satisfy _seg_clue_ok
            # zip_ferry.py:102-110; observed invariant PHASE0 §1 / flags F7).
            if cell in nums:
                raise ValueError(f"level {lid}: ferry cell {cell} is a numbered cell")

    # zip_slide.py:92-95 / zip_full.py:143-145 — 泽地 must not carry numbers
    for cell in slide:
        if cell in nums:
            raise ValueError(f"level {lid}: 泽地 cell {cell} is a numbered cell")

    # zip_seal.py:199-201 — gates must not coincide with walls
    for e in gates:
        if e in walls:
            raise ValueError(f"level {lid}: seal gate {e} coincides with a wall")

    # zip_parity.py:233-238 — parity edges must not hit walls or gates
    for e in parity:
        if e in walls:
            raise ValueError(f"level {lid}: parity edge {e} coincides with a wall")
        if e in gates:
            raise ValueError(f"level {lid}: parity edge {e} coincides with a gate")

    # zip_burden.py:323-324 — the collapsing edge must not already be a wall
    if collapse is not None and collapse[1] in walls:
        raise ValueError(f"level {lid}: collapse edge {collapse[1]} is already a wall")

    if burden is not None and burden["active"]:
        forb = burden["forbidden"]
        # zip_burden.py:325-327
        if burden["load"] is not None and burden["load"] in forb:
            raise ValueError(f"level {lid}: load cell {burden['load']} is a 禁区 cell")
        # zip_burden.py:328-330
        if burden["unload"] is not None and burden["unload"] in forb:
            raise ValueError(f"level {lid}: unload cell {burden['unload']} is a 禁区 cell")
        # 装/卸 points are cell markers, never 驿号 (beifa_ch10/zip_burden.py:4-7)
        for tag, cell in (("load", burden["load"]), ("unload", burden["unload"])):
            if cell is not None and cell in nums:
                raise ValueError(f"level {lid}: {tag} cell {cell} is a numbered cell")


def compile_level(level: dict) -> tuple[int, int, dict[tuple[int, int], int], set[tuple[int, int]], tuple[int, int], tuple[int, int], int]:
    cols, rows = int(level["cols"]), int(level["rows"])
    wps = { (int(w["x"]), int(w["y"])): int(w["n"]) for w in level["waypoints"] }
    walls: set[tuple[int, int]] = set()
    for wall in level.get("walls") or []:
        walls.add(wall_key(int(wall["x1"]), int(wall["y1"]), int(wall["x2"]), int(wall["y2"])))
    start = next((xy for xy, n in wps.items() if n == 1))
    max_n = max(wps.values())
    end = next((xy for xy, n in wps.items() if n == max_n))
    return cols, rows, wps, walls, start, end, max_n


# ---------------------------------------------------------------------------
# Rules layer — mechanism-aware legality of one move, and replay of a stored
# path.  The DFS in solve()/main() below is intentionally untouched for now.
#
# Judgment order follows the most complete design implementation,
# beifa_ch10/zip_burden.py:159-238 (`expand_move_bc`), cross-checked against
# /workspace/cjmp-smoke/mech/PHASE0.md §1 and analysis/rules_raw.md §10.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class State:
    """Immutable game state. Cells are in-memory `(x, y)` = `(col, row)`."""

    path: tuple  # cells visited, in order (path[-1] = current position)
    visited: frozenset
    filled: int  # 已铺格数, always == len(path)
    need: int  # next 驿号 that must be stepped on
    has_token: bool  # 符节 already picked up
    laden: bool  # 负重载态 (false when the board has no burden)
    down: bool  # 塌桥 already triggered
    ferry_used: bool  # the 甲→乙 jump has happened


class Rules:
    """Mechanism rules for one released level entry.

    Coordinates: internal `(x, y)` = `(col, row)`. Mechanism keys arriving as
    `[r, c]` are converted on read only — the JSON file is never rewritten.
    """

    def __init__(self, level: dict) -> None:
        self.level = level
        self.cols = int(level["cols"])
        self.rows = int(level["rows"])
        self.total = self.cols * self.rows
        self.clue: dict[tuple[int, int], int] = {
            (int(w["x"]), int(w["y"])): int(w["n"]) for w in level["waypoints"]
        }
        self.max_n = max(self.clue.values())
        self.walls = read_walls(level)
        self.one_ways = read_one_ways(level)
        # `ow_edge_set` — lvbu_ch4/zip_oneway.py:103-104
        self.ow_constrained = {edge_key(a, b) for a, b in self.one_ways}
        self.ferry = read_ferry(level)
        self.slide = read_slide(level)
        self.gates = read_gates(level)
        self.tokens = read_tokens(level)
        self.parity = read_parity(level)
        self.collapse = read_collapse(level)
        self.burden = read_burden(level)
        self.burden_active = bool(self.burden) and bool(self.burden.get("active"))
        # CollapseCfg.active() — beifa_ch10/zip_burden.py:38-39
        self.collapse_active = self.collapse is not None
        self.start = next(xy for xy, n in self.clue.items() if n == 1)

    # -- helpers ----------------------------------------------------------

    def _parity_ok(self, e: tuple, filled: int) -> bool:
        """filled = 已铺格数 including the cell we stand on, counted *before*
        crossing. hanzhong_ch9/zip_parity.py:59-64 (`parity_ok`)."""
        req_odd = self.parity.get(e)
        if req_odd is None:
            return True
        is_odd = (filled % 2) == 1
        return is_odd if req_odd else (not is_odd)

    def _cell_effects(self, cell, laden: bool, down: bool) -> tuple[bool, bool]:
        """Per-cell 装/卸/塌桥 effects. beifa_ch10/zip_burden.py:113-123."""
        if self.burden_active:
            if self.burden["load"] is not None and cell == self.burden["load"]:
                laden = True
            if self.burden["unload"] is not None and cell == self.burden["unload"]:
                laden = False
        if self.collapse_active and cell == self.collapse[0]:
            down = True
        return laden, down

    def _nbr_open(
        self, cur: tuple[int, int], has_token: bool, filled: int, laden: bool, down: bool
    ) -> list:
        """Open neighbours of `cur`, in design order
        墙 → 塌桥封边 → 闸门 → 奇偶 → 单向 → 载态禁区.
        beifa_ch10/zip_burden.py:125-157 (`nbr_open_bc`):
          :144-145 wall, :146-147 collapse edge, :148-149 gate,
          :150-151 parity, :152-153 one-way, :154-155 forbidden while laden."""
        out = []
        for dx, dy in DIRS:
            nx, ny = cur[0] + dx, cur[1] + dy
            if not (0 <= nx < self.cols and 0 <= ny < self.rows):
                continue
            nxt = (nx, ny)
            e = edge_key(cur, nxt)
            if e in self.walls:
                continue
            if down and self.collapse_active and e == self.collapse[1]:
                continue
            if e in self.gates and not has_token:
                continue
            if not self._parity_ok(e, filled):
                continue
            if self.ow_constrained and e in self.ow_constrained and (cur, nxt) not in self.one_ways:
                continue
            if self.burden_active and laden and nxt in self.burden["forbidden"]:
                continue
            out.append(nxt)
        return out

    def _slide_segment(self, state: State, cur: tuple, nxt: tuple) -> list | None:
        """Forced slide along the entry direction once inside 泽地.

        beifa_ch10/zip_burden.py:205-238, stop conditions in the order
        documented at chibi_ch7/zip_slide.py:60-70:
          bounds → 墙/闸/奇偶/单向/禁区 (`nbr_open_bc`) → 已访 → 数字格
          → 甲/乙 (chibi_ch7/zip_full.py:84-85) → 非泽地.
        `has_token` is frozen at segment entry (rushu_ch8/zip_seal.py:115-120);
        `filled` and `laden`/`down` are updated per landed cell
        (beifa_ch10/zip_burden.py:213-235)."""
        dx = nxt[0] - cur[0]
        dy = nxt[1] - cur[1]
        if abs(dx) + abs(dy) != 1:
            return None
        seg = [nxt]
        pos = nxt
        seen = {nxt}
        fcur = state.filled + 1
        laden_s, down_s = self._cell_effects(nxt, state.laden, state.down)
        while True:
            nx, ny = pos[0] + dx, pos[1] + dy
            if not (0 <= nx < self.cols and 0 <= ny < self.rows):
                break
            npos = (nx, ny)
            if npos not in self._nbr_open(pos, state.has_token, fcur, laden_s, down_s):
                break
            if npos in state.visited or npos in seen:
                break
            if npos in self.clue:
                break
            if self.ferry is not None and npos in self.ferry:
                break
            if npos not in self.slide:
                break
            seg.append(npos)
            seen.add(npos)
            laden_s, down_s = self._cell_effects(npos, laden_s, down_s)
            pos = npos
            fcur += 1
        return seg

    def _seg_clue_ok(self, seg, need: int) -> tuple[bool, int]:
        """Waypoints inside a segment must be consumed in order.

        Design: jingzhou_ch6/zip_ferry.py:102-110 (`_seg_clue_ok`), same at
        chibi_ch7/zip_full.py:93-101. Returns (ok, next_need)."""
        n = need
        for cell in seg:
            cv = self.clue.get(cell, 0)
            if cv and cv != n:
                return False, need
            if cv == n:
                n += 1
        return True, n

    # -- public API -------------------------------------------------------

    def initial_state(self) -> State | None:
        """Start = 驿号 1. Start-cell effects apply immediately.

        起点即符格 → has_token (rushu_ch8/zip_seal.py:206-208);
        起点是装/卸点 → laden changes, 起点是塌桥触发格 → down
        (beifa_ch10/zip_burden.py:336-339).
        Returns None when the board is unwinnable from the start
        (laden start inside 禁区 — beifa_ch10/zip_burden.py:331-332)."""
        start = self.start
        laden = bool(self.burden["start_laden"]) if self.burden_active else False
        down = False
        # beifa_ch10/zip_burden.py:331-332 (checked before start effects, as
        # design does at :331 vs :339)
        if self.burden_active and laden and start in self.burden["forbidden"]:
            return None
        laden, down = self._cell_effects(start, laden, down)
        return State(
            path=(start,),
            visited=frozenset({start}),
            filled=1,
            need=self.clue[start] + 1,
            has_token=start in self.tokens,
            laden=laden,
            down=down,
            ferry_used=False,
        )

    def expand(self, state: State, nxt: tuple[int, int]) -> list | None:
        """Cells visited by one input `nxt`, or None when illegal."""
        return self._expand(state, nxt)[0]

    def _expand(self, state: State, nxt: tuple[int, int]) -> tuple[list | None, str]:
        """Same as expand() but also returns a human-readable rejection reason.

        Order is beifa_ch10/zip_burden.py:159-238:
          1. 渡口跳接分支 (:178-185) — 豁免墙/单向/闸/奇偶/塌桥
          2. `nbr_open_bc` (:186-192)
          3. 已访 (:193-194)
          4. 进入甲 (:195-202)
          5. 非泽地 → [nxt] (:203-204)
          6. 泽地 → 逐格滑行 (:205-238)
        then the rules-layer numeric constraints (zip_ferry.py:102-110)."""
        cur = state.path[-1]

        # 1. ferry jump branch — zip_burden.py:178-185
        if self.ferry is not None:
            jia, yi = self.ferry
            if cur == jia and nxt == yi:
                if cur in state.visited or nxt in state.visited:
                    return None, "ferry jump onto an already visited cell"
                if self.burden_active and state.laden and yi in self.burden["forbidden"]:
                    return None, "ferry landing 乙 is a 禁区 cell while laden"
                return [jia, yi], ""

        # 2. neighbour constraints — zip_burden.py:186-192
        if nxt not in self._nbr_open(
            cur, state.has_token, state.filled, state.laden, state.down
        ):
            return None, "neighbour closed (wall / collapse / gate / parity / one-way / 禁区)"

        # 3. already visited — zip_burden.py:193-194
        if nxt in state.visited:
            return None, "cell already visited"

        # 4. entering 甲 forces the jump to 乙 — zip_burden.py:195-202
        if self.ferry is not None:
            jia, yi = self.ferry
            if nxt == jia:
                if yi in state.visited or yi == jia:
                    return None, "ferry landing 乙 already visited"
                if self.burden_active and state.laden and yi in self.burden["forbidden"]:
                    return None, "ferry landing 乙 is a 禁区 cell while laden"
                return [jia, yi], ""

        # 5/6. plain cell vs forced slide — zip_burden.py:203-238
        if nxt not in self.slide:
            seg = [nxt]
        else:
            seg = self._slide_segment(state, cur, nxt)
            if seg is None:
                return None, "illegal slide direction"

        # numeric constraints on the produced segment
        ok, _ = self._seg_clue_ok(seg, state.need)
        if not ok:
            return None, f"segment steps on waypoint {self.clue.get(nxt)} while need={state.need}"
        # the largest waypoint may only ever be the final cell of the whole path
        # (design enforces it in the DFS, solve_levels.solve(): end == max only
        # when len(path)+1 == total)
        if self.clue.get(nxt) == self.max_n and state.filled + len(seg) != self.total:
            return None, "largest waypoint can only be entered on the final fill"
        return seg, ""

    def apply(self, state: State, seg) -> State:
        """Fold an already-validated segment into the state.

        visited/filled take the whole segment (渡口 +2, 滑行 +k);
        `need` advances over waypoints inside the segment;
        `has_token` is updated after the whole segment
        (rushu_ch8/zip_seal.py:115-120);
        `laden`/`down` are updated cell by cell (beifa_ch10/zip_burden.py:365-378)."""
        path = list(state.path)
        visited = set(state.visited)
        filled = state.filled
        laden = state.laden
        down = state.down
        for cell in seg:
            path.append(cell)
            visited.add(cell)
            filled += 1
            laden, down = self._cell_effects(cell, laden, down)
        ok, need = self._seg_clue_ok(seg, state.need)
        if not ok:  # expand() already rejected this; keep apply() total
            raise ValueError(f"segment {seg} violates waypoint order at need={state.need}")
        ferry_used = state.ferry_used
        if self.ferry is not None and tuple(seg) == self.ferry:
            ferry_used = True
        return State(
            path=tuple(path),
            visited=frozenset(visited),
            filled=filled,
            need=need,
            has_token=state.has_token or any(c in self.tokens for c in seg),
            laden=laden,
            down=down,
            ferry_used=ferry_used,
        )

    def is_win(self, state: State) -> bool:
        """Board fully filled, last cell is the largest waypoint, need == max+1,
        the ferry jump happened (if any), and the token was stepped on (if any)."""
        if state.filled != self.total or len(state.path) != self.total:
            return False
        if self.clue.get(state.path[-1]) != self.max_n:
            return False
        if state.need != self.max_n + 1:
            return False
        if self.ferry is not None and not state.ferry_used:
            return False
        if self.tokens and not state.has_token:
            return False
        return True


def check_path(level: dict, path) -> tuple[bool, str, int]:
    """Replay a stored solution path against the rules layer.

    `path` is the boards-locked sequence of `[r, c]` cells; it is converted to
    in-memory `(x, y)` on read. Returns (ok, reason, first_bad_index) where
    first_bad_index is the 0-based index in the stored path of the first cell
    that does not fit a legal expansion (-1 for whole-path failures)."""
    rules = Rules(level)
    cells = [rc_to_xy(rc) for rc in path]
    if not cells:
        return False, "empty path", -1
    state = rules.initial_state()
    if state is None:
        return False, "start cell is a 禁区 cell while laden — no solution", 0
    if cells[0] != state.path[0]:
        return False, f"path[0] {cells[0]} is not the start cell {state.path[0]}", 0
    i = 0
    while i < len(cells) - 1:
        nxt = cells[i + 1]
        seg, reason = rules._expand(state, nxt)
        if seg is None:
            return False, reason or "illegal move", i + 1
        for j, cell in enumerate(seg):
            idx = i + 1 + j
            if idx >= len(cells) or cells[idx] != cell:
                got = cells[i + 1 : i + 1 + len(seg)]
                return False, f"segment mismatch: expand says {seg}, path has {got}", idx
        state = rules.apply(state, seg)
        i += len(seg)
    if i != len(cells) - 1:
        return False, f"path length not consumed exactly (stopped at index {i})", i + 1
    if not rules.is_win(state):
        return False, "final state is not a win (fill / largest waypoint / ferry / token)", -1
    return True, "", -1


def neighbors(x: int, y: int, cols: int, rows: int, walls: set[tuple[int, int]]) -> Iterable[tuple[int, int]]:
    for dx, dy in DIRS:
        nx, ny = x + dx, y + dy
        if 0 <= nx < cols and 0 <= ny < rows:
            if wall_key(x, y, nx, ny) not in walls:
                yield nx, ny


class SolverTimeout(Exception):
    """Large grids may exceed a practical DFS budget."""


def solve(
    level: dict,
    find_all: bool = False,
    limit: int = 1,
    timeout_s: float | None = None,
) -> list[list[tuple[int, int]]]:
    """DFS Hamiltonian path with waypoint-order + end-on-max-number."""
    cols, rows, wps, walls, start, end, max_n = compile_level(level)
    total = cols * rows
    solutions: list[list[tuple[int, int]]] = []
    start_mask = 1 << (start[1] * cols + start[0])
    path = [start]
    deadline = None if timeout_s is None else time.monotonic() + timeout_s

    def degree(x: int, y: int, visited: int) -> int:
        d = 0
        for nx, ny in neighbors(x, y, cols, rows, walls):
            bit = 1 << (ny * cols + nx)
            if visited & bit == 0:
                d += 1
        return d

    def dfs(x: int, y: int, visited: int, next_n: int) -> None:
        if deadline is not None and time.monotonic() > deadline:
            raise SolverTimeout()
        if solutions and not find_all:
            return
        if len(solutions) >= limit:
            return
        if len(path) == total:
            if (x, y) == end and next_n == max_n + 1:
                solutions.append(list(path))
            return
        cand = []
        for nx, ny in neighbors(x, y, cols, rows, walls):
            bit = 1 << (ny * cols + nx)
            if visited & bit:
                continue
            num = wps.get((nx, ny), 0)
            if num != 0 and num != next_n:
                continue
            if (nx, ny) == end and len(path) + 1 != total:
                continue
            cand.append((degree(nx, ny, visited), nx, ny, num))
        cand.sort()
        for _, nx, ny, num in cand:
            bit = 1 << (ny * cols + nx)
            path.append((nx, ny))
            dfs(nx, ny, visited | bit, next_n + 1 if num == next_n else next_n)
            path.pop()
            if solutions and not find_all:
                return
            if len(solutions) >= limit:
                return

    dfs(start[0], start[1], start_mask, 2)
    return solutions


def format_path(path: list[tuple[int, int]]) -> str:
    return " -> ".join(f"({x},{y})" for x, y in path)


def report_solve_exit(total: int, unsolvable: int, timed_out: int) -> int:
    """TIMEOUT keeps the board (README contract). Only a proven no-solution fails."""
    if unsolvable:
        print(f"RESULT: {unsolvable} unsolvable level(s). Do not ship.")
        return 1
    if timed_out:
        print(f"RESULT: {total - timed_out} solved, {timed_out} timed out.")
        return 0
    print(f"RESULT: all {total} levels have ≥1 solution.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Prove every shipped level has ≥1 solution.")
    parser.add_argument(
        "--json",
        default="entry/src/main/resources/rawfile/levels.json",
        help="Path to levels.json",
    )
    parser.add_argument("--limit", type=int, default=1, help="Max solutions to search per level")
    parser.add_argument(
        "--timeout",
        type=float,
        default=8.0,
        help="Seconds per level; do not invent or alter boards on timeout",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    json_path = Path(args.json)
    if not json_path.is_absolute():
        json_path = root / json_path
    if not json_path.exists():
        print(f"FAIL: missing {json_path}", file=sys.stderr)
        return 2

    levels = load_levels(json_path)
    if len(levels) != 20:
        print(f"FAIL: need exactly 20 locked 涿郡+平原 levels, found {len(levels)}", file=sys.stderr)
        return 2

    failed = 0
    timed_out = 0
    print(f"Solving {len(levels)} levels from {json_path}")
    print("-" * 60)
    for level in levels:
        validate_schema(level)
        tag = f"#{level['id']} {level['name']} {level['cols']}x{level['rows']}"
        walls = len(level.get("walls") or [])
        wps = len(level["waypoints"])
        try:
            solutions = solve(level, find_all=False, limit=args.limit, timeout_s=args.timeout)
        except SolverTimeout:
            timed_out += 1
            print(f"TIMEOUT {tag}  waypoints={wps} walls={walls}")
            continue
        if solutions:
            print(f"OK   {tag}  waypoints={wps} walls={walls}")
            print(f"     sample: {format_path(solutions[0])}")
        else:
            failed += 1
            print(f"FAIL {tag}  waypoints={wps} walls={walls}  (no solution)")
    print("-" * 60)
    return report_solve_exit(len(levels), failed, timed_out)


if __name__ == "__main__":
    sys.exit(main())
