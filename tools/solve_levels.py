#!/usr/bin/env python3
"""Independent solver / proof runner for 「驿路巡点」 levels (100 shipped).

Base rules (LinkedIn Zip / Hamiltonian path with ordered waypoints):
  orthogonal 4-direction steps; every cell visited exactly once; numbered
  waypoints visited in increasing order 1..N; start on waypoint 1 (驿号 1);
  no stepping through walls or onto an already-visited cell.

Mechanisms handled by this solver (all in the committed rules layer
`Rules`/`expand`/`apply`/`check_path`/`validate_mechanics`):
  ferry      渡口 one-way jump 甲->乙 (exactly one jump, jump itself
             bypasses walls/one-ways; entering 甲 obeys them)
  ow         one_way directed edges (lvbu_ch4)
  slide      slide_cells 泽地 (chibi_ch7)
  seal       seal_gates + token_cells 封印/符节 (rushu_ch8)
  collapse   collapse step_on_trigger edge removal (beifa_ch10)
  burden     burden 负重 forbidden cells / load / unload (beifa_ch10)
  parity     parityEdges even/odd cell constraints (hanzhong_ch9)

Independence: this module never imports the design code — it is a fully
re-implemented, standalone checker.  Where rules were ambiguous, behaviour
follows the design code literally and the citation (file:line) is in a code
comment next to the rule.  Design sources of truth:
  /workspace/lvbu_ch4/zip_oneway.py, /workspace/jingzhou_ch6/zip_ferry.py,
  /workspace/chibi_ch7/zip_full.py + zip_slide.py, /workspace/rushu_ch8/
  zip_seal.py, /workspace/hanzhong_ch9/zip_parity.py,
  /workspace/beifa_ch10/zip_burden.py (+ sibling zip_*.py), and the repo's
  boards-locked/*.json (rule tables: cjmp-smoke/mech/PHASE0.md §1,
  cjmp-smoke/mech/analysis/rules_raw.md §10).

Data conventions: waypoints/walls/parityEdges use x/y (x=col, y=row); the
new mechanism keys keep boards-locked [r, c] shape verbatim (no coordinate
conversion in Python).  Only boards carrying a mechanism carry its key.

Usage (from repo root):
    python3 tools/solve_levels.py
    python3 tools/solve_levels.py --json entry/src/main/resources/rawfile/levels.json
    python3 tools/solve_levels.py --limit 2 --timeout 60 --table out.md
    python3 tools/solve_levels.py --ids 52,59,60        # debug subset

Exit codes:
    0  every level SOLVED
    1  at least one level proven UNSOLVABLE (do not ship)
    2  data/parameter error (not exactly 100 levels, ids != 0..99, bad schema)
    3  no UNSOLVABLE but at least one TIMEOUT (unverified -> NOT a pass)
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


def solve_rules(
    level: dict,
    limit: int = 1,
    timeout_s: float | None = None,
) -> list[list[tuple[int, int]]]:
    """Mechanism-aware DFS on top of the committed rules layer.

    Candidates are simply the four orthogonal neighbours of the current cell;
    stepping onto 渡口甲 already forces the jump to 乙 inside `Rules.expand`
    (beifa_ch10/zip_burden.py:195-202), so no extra candidate is needed.
    Returns up to `limit` solution paths as `(x, y)` tuples — for a ferry
    board 甲 and 乙 are two adjacent elements of the path.
    Raises SolverTimeout when `timeout_s` elapses (checked every 1024 nodes).
    """
    rules = Rules(level)
    state0 = rules.initial_state()
    if state0 is None:
        return []  # unwinnable start (beifa_ch10/zip_burden.py:331-332)
    solutions: list[list[tuple[int, int]]] = []
    deadline = None if timeout_s is None else time.monotonic() + timeout_s
    nodes = 0
    walls = rules.walls
    cols, rows = rules.cols, rules.rows
    ferry = rules.ferry
    all_cells = frozenset((x, y) for x in range(cols) for y in range(rows))

    def connected(state: State) -> bool:
        """(a) Optimistic connectivity of the remaining cells.

        Flood-fill from the current cell over edges that ignore every
        mechanism except walls (one-way / gate / collapse / parity / 禁区 are
        all treated as open, i.e. an over-estimate of real reachability), plus
        the extra 渡口 甲→乙 jump edge (jingzhou_ch6/zip_ferry.py:52-57) when the
        landing 乙 is still unvisited.  Prunes only when even this optimistic
        graph leaves some unvisited cell unreachable — sound because every
        real solution's future steps are a subset of these edges."""
        cur = state.path[-1]
        visited = state.visited
        seen = {cur}
        stack = [cur]
        while stack:
            x, y = stack.pop()
            if ferry is not None and (x, y) == ferry[0] and ferry[1] not in visited:
                yx, yy = ferry[1]
                if (yx, yy) not in seen:
                    seen.add((yx, yy))
                    stack.append((yx, yy))
            for dx, dy in DIRS:
                nx, ny = x + dx, y + dy
                if not (0 <= nx < cols and 0 <= ny < rows):
                    continue
                if edge_key((x, y), (nx, ny)) in walls:
                    continue
                n = (nx, ny)
                if n in seen or n in visited:
                    continue
                seen.add(n)
                stack.append(n)
        return all(c in seen for c in all_cells - visited)

    end_cell = next(xy for xy, n in rules.clue.items() if n == rules.max_n)

    def deg1_ok(state: State) -> bool:
        """(c) Boards with no ferry and no slide: after exclusions, at most
        one unvisited cell may have optimistic degree 1.

        Degree = wall-free unvisited neighbours (ignoring one-way/gate/parity/
        禁区 → over-estimate, so real degrees are never smaller).  In any real
        solution the remaining path's interior cells keep ≥2 unvisited path
        neighbours; the two ends are the last cell (largest waypoint, excluded)
        and the first remaining cell (a wall-free neighbour of the current
        cell, excluded).  Counting >1 after those exclusions therefore only
        happens in dead ends — sound prune."""
        if ferry is not None or rules.slide:
            return True
        cur = state.path[-1]
        visited = state.visited
        cur_adj = set()
        for dx, dy in DIRS:
            nx, ny = cur[0] + dx, cur[1] + dy
            if 0 <= nx < cols and 0 <= ny < rows and edge_key(cur, (nx, ny)) not in walls:
                cur_adj.add((nx, ny))
        ones = 0
        for cell in all_cells - visited:
            d = 0
            for dx, dy in DIRS:
                qx, qy = cell[0] + dx, cell[1] + dy
                if not (0 <= qx < cols and 0 <= qy < rows):
                    continue
                if edge_key(cell, (qx, qy)) in walls:
                    continue
                if (qx, qy) not in visited:
                    d += 1
            if d == 1 and cell != end_cell and cell not in cur_adj:
                ones += 1
                if ones > 1:
                    return False
        return True

    def dfs(state: State) -> None:
        nonlocal nodes
        nodes += 1
        if nodes & 1023 == 0 and deadline is not None and time.monotonic() > deadline:
            raise SolverTimeout()
        if len(solutions) >= limit:
            return
        if rules.is_win(state):
            solutions.append(list(state.path))
            return
        if state.filled >= rules.total:
            return
        if not connected(state):
            return
        if not deg1_ok(state):
            return
        cur = state.path[-1]
        cands = []
        for dx, dy in DIRS:
            nx, ny = cur[0] + dx, cur[1] + dy
            if not (0 <= nx < rules.cols and 0 <= ny < rules.rows):
                continue
            seg = rules.expand(state, (nx, ny))
            if seg is None:
                continue
            # (b) order by the landing cell's optimistic open unvisited
            # neighbour count, ascending — heuristic only, never filters.
            # (ferry: landing = 乙 = seg[-1]; slide: last slid cell)
            landing = seg[-1]
            free = 0
            for ddx, ddy in DIRS:
                qx, qy = landing[0] + ddx, landing[1] + ddy
                if not (0 <= qx < cols and 0 <= qy < rows):
                    continue
                if edge_key(landing, (qx, qy)) in walls:
                    continue
                if (qx, qy) in state.visited or (qx, qy) in seg:
                    continue
                free += 1
            cands.append((free, nx, ny, seg))
        cands.sort(key=lambda c: c[0])
        for _, nx, ny, seg in cands:
            dfs(rules.apply(state, seg))
            if len(solutions) >= limit:
                return

    dfs(state0)
    return solutions


def _solve_plain(
    level: dict,
    find_all: bool = False,
    limit: int = 1,
    timeout_s: float | None = None,
) -> list[list[tuple[int, int]]]:
    """DFS Hamiltonian path with waypoint-order + end-on-max-number.

    The original mechanism-free `solve()` body, renamed verbatim in B3b; its
    behaviour is intentionally untouched (walls + waypoints + end-on-max only)."""
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


# Optional mechanism keys in levels.json (emitted per commit 69e810d); parity
# is published separately as camelCase `parityEdges`, unchanged since B1.
MECH_KEYS = (
    "ferry",
    "one_ways",
    "slide_cells",
    "seal_gates",
    "token_cells",
    "collapse",
    "burden",
)


def _has_mechanisms(level: dict) -> bool:
    """True when the board carries any mechanism key or parityEdges."""
    return bool(level.get("parityEdges")) or any(level.get(k) for k in MECH_KEYS)


def solve(
    level: dict,
    find_all: bool = False,
    limit: int = 1,
    timeout_s: float | None = None,
) -> list[list[tuple[int, int]]]:
    """Find up to `limit` solution paths as `(x, y)` tuples.

    Mechanism-free and parity-free boards keep the original fast bit-DFS
    (`_solve_plain`, behaviour unchanged).  Anything else is delegated to the
    rules layer `solve_rules` so ferry/one_ways/slide/seal/token/collapse/
    burden/parityEdges all follow the committed rules (design code is the
    sole authority; see Rules/expand docstrings for file:line citations).
    """
    if not _has_mechanisms(level):
        return _solve_plain(level, find_all=find_all, limit=limit, timeout_s=timeout_s)
    return solve_rules(
        level,
        limit=limit if not find_all else max(limit, 1000),
        timeout_s=timeout_s,
    )


def count_solutions(
    level: dict,
    limit: int = 2,
    timeout_s: float | None = None,
) -> tuple[int, bool, float]:
    """Count solutions up to `limit` -> `(count<=limit, truncated_by_limit, seconds)`.

    Uniformly uses the rules layer (`solve_rules`) so plain boards are counted
    by the same code as mechanism boards.  `solve_rules` may be much slower
    than `_solve_plain` on mechanism-free grids, so a plain board gets a 60s
    rules budget first and then falls back to the bit-DFS count
    (`find_all=True`, so the run actually reaches `limit` instead of stopping
    at 1).  A timeout raised under the caller's own `timeout_s` propagates.
    """
    t0 = time.monotonic()
    if not _has_mechanisms(level):
        budget = 60.0 if timeout_s is None else min(timeout_s, 60.0)
        try:
            sols = solve_rules(level, limit=limit, timeout_s=budget)
        except SolverTimeout:
            if timeout_s is not None and time.monotonic() - t0 >= timeout_s:
                raise  # the caller's own budget elapsed, not the 60s grace
            sols = _solve_plain(level, find_all=True, limit=limit, timeout_s=timeout_s)
    else:
        sols = solve_rules(level, limit=limit, timeout_s=timeout_s)
    n = len(sols)
    return n, n >= limit, time.monotonic() - t0


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


def exit_code_strict(unsolvable: int, timed_out: int) -> int:
    """Strict CI gate: 1 if any level is proven unsolvable, else 3 if any
    timed out, else 0.  (`report_solve_exit` above keeps its README contract:
    timeout never fails the run.)"""
    if unsolvable:
        return 1
    if timed_out:
        return 3
    return 0


MECH_COLUMN_KEYS = (
    ("ferry", "ferry"),
    ("one_ways", "ow"),
    ("slide_cells", "slide"),
    ("seal_gates", "seal"),
    ("token_cells", "token"),
    ("collapse", "collapse"),
    ("burden", "burden"),
    ("parityEdges", "parity"),
)

TABLE_HEADER = (
    "| id | 玩家号(id+1) | 关名 | 机制 | 状态 | 解数 | 唯一 | 用时s |\n"
    "|---|---|---|---|---|---|---|---|"
)


def mech_labels(level: dict) -> str:
    """Mechanism column: present keys only; `parity` iff parityEdges non-empty."""
    tags = [label for key, label in MECH_COLUMN_KEYS if level.get(key)]
    return "+".join(tags) if tags else "-"


def emit_table(rows: list[str], table_path: str | None) -> None:
    """Print the markdown table and optionally write it to `--table PATH`."""
    text = TABLE_HEADER + "".join(f"\n{r}" for r in rows) + "\n"
    print(text, end="")
    if table_path:
        Path(table_path).write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Count solutions for every shipped level (strict ship gate)."
    )
    parser.add_argument(
        "--json",
        default="entry/src/main/resources/rawfile/levels.json",
        help="Path to levels.json (default: entry/src/main/resources/rawfile/levels.json)",
    )
    parser.add_argument(
        "--limit", type=int, default=2, help="Max solutions to count per level (default 2)"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Seconds per level; a TIMEOUT is NOT a pass (default 60)",
    )
    parser.add_argument("--table", default=None, help="Write the markdown result table to PATH")
    parser.add_argument(
        "--ids", default=None, help="Comma-separated ids to run (debug; skips the 100-level check)"
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    json_path = Path(args.json)
    if not json_path.is_absolute():
        json_path = root / json_path
    if not json_path.exists():
        print(f"FAIL: missing {json_path}", file=sys.stderr)
        return 2
    try:
        levels = load_levels(json_path)
    except (ValueError, OSError) as exc:
        print(f"FAIL: cannot load {json_path}: {exc}", file=sys.stderr)
        return 2

    by_id = {}
    for lv in levels:
        if "id" not in lv:
            print(f"FAIL: level without id: {lv.get('name')!r}", file=sys.stderr)
            return 2
        by_id[int(lv["id"])] = lv
    if args.ids is not None:
        # debug subset: ids must be 0..99, but the 100-level requirement is lifted
        try:
            wanted = [int(p) for p in args.ids.split(",") if p.strip()]
        except ValueError:
            print(f"FAIL: bad --ids value {args.ids!r}", file=sys.stderr)
            return 2
        bad = [i for i in wanted if not 0 <= i <= 99]
        if bad:
            print(f"FAIL: ids must be 0..99, got {bad}", file=sys.stderr)
            return 2
        missing = [i for i in wanted if i not in by_id]
        if missing:
            print(f"FAIL: ids not present in {json_path}: {missing}", file=sys.stderr)
            return 2
        selected = [by_id[i] for i in wanted]
    else:
        if len(levels) != 100:
            print(f"FAIL: need exactly 100 levels, found {len(levels)}", file=sys.stderr)
            return 2
        if sorted(by_id) != list(range(100)):
            print(f"FAIL: ids must be exactly 0..99, got {sorted(by_id)}", file=sys.stderr)
            return 2
        selected = [by_id[i] for i in range(100)]

    total = len(selected)
    rows: list[str] = []
    solved = unsolvable = timeout = 0
    for k, level in enumerate(selected, 1):
        try:
            validate_schema(level)
        except ValueError as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            return 2
        mech = mech_labels(level)
        pid = int(level["id"]) + 1
        name = level["name"]
        t0 = time.monotonic()
        try:
            n, truncated, _dt = count_solutions(
                level, limit=args.limit, timeout_s=args.timeout
            )
        except SolverTimeout:
            timeout += 1
            secs = time.monotonic() - t0
            status, count_str, uniq, tag = "TIMEOUT", "-", "-", "TIMEOUT"
        else:
            secs = time.monotonic() - t0
            if n == 0:
                unsolvable += 1
                status, count_str, uniq, tag = "UNSOLVABLE", "0", "-", "UNSOLVABLE"
            else:
                solved += 1
                status = "SOLVED"
                count_str = f">={args.limit}" if truncated else str(n)
                uniq = "yes" if (args.limit >= 2 and n == 1) else "-"
                tag = f"SOLVED({n})"
        print(
            f"[{k}/{total}] id={level['id']} 玩家号={pid} {name} {mech} -> {tag}"
            f"  t={secs:.1f}s",
            flush=True,
        )
        rows.append(
            f"| {level['id']} | {pid} | {name} | {mech} | {status} |"
            f" {count_str} | {uniq} | {secs:.1f} |"
        )
    emit_table(rows, args.table)
    print(
        f"RESULT: solved={solved} unsolvable={unsolvable} timeout={timeout}"
        f" (total={total})"
    )
    return exit_code_strict(unsolvable, timeout)


if __name__ == "__main__":
    sys.exit(main())
