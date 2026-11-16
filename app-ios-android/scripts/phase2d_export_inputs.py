#!/usr/bin/env python3
"""Export per-level *input sequences* (one click may lay 1..k cells) for the
CJMP UI replay harness. Read-only w.r.t. the repo: imports tools/solve_levels.

Outputs:
  /workspace/cjmp-smoke/mech/p2d/solutions_mech.json
      {id: {cols, rows, path:[[x,y] inputs], violate:null,
             cells:[[x,y] full design path], n_inputs}}
  /workspace/cjmp-smoke/mech/p2d/inputs.txt
      one line per level: "<id> <x>,<y> <x>,<y> ..."
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "/workspace/tmp/yilu-mech/tools")
import solve_levels as S  # noqa: E402

LOCKED_DIR = Path("/workspace/tmp/yilu-mech/boards-locked")
# mirror of tools/build_levels.py LOCKED_FILES (chapter order => id = ch*10+tip)
LOCKED_FILES = (
    "ch1_zhuo.json", "ch2_pingyuan.json", "ch3_xuzhou.json", "ch4_lvbu.json",
    "ch5_touyuan.json", "ch6_jingzhou.json", "ch7_chibi.json", "ch8_rushu.json",
    "ch9_hanzhong.json", "ch10_beifa.json",
)
LEVELS_JSON = Path("/workspace/tmp/yilu-mech/engine/shared/levels/levels.json")
OUT_JSON = Path("/workspace/cjmp-smoke/mech/p2d/solutions_mech.json")
OUT_TXT = Path("/workspace/cjmp-smoke/mech/p2d/inputs.txt")


def replay(gid: int, rules: S.Rules, cells: list) -> list:
    """Collapse the design path into input cells (expand/apply per input)."""
    state = rules.initial_state()
    assert state is not None, f"id {gid}: None initial state"
    assert state.path == (cells[0],), f"id {gid}: start {state.path} != {cells[0]}"
    inputs = [cells[0]]
    i = 0
    while i < len(cells) - 1:
        nxt = cells[i + 1]
        seg = rules.expand(state, nxt)
        assert seg is not None, f"id {gid}: expand rejected input {nxt} at i={i}"
        assert seg == cells[i + 1:i + 1 + len(seg)], (
            f"id {gid}: seg {seg} != design {cells[i + 1:i + 1 + len(seg)]} at i={i}")
        inputs.append(nxt)
        state = rules.apply(state, seg)
        i += len(seg)
    assert i == len(cells) - 1, f"id {gid}: last consumed index {i}/{len(cells) - 1}"
    assert rules.is_win(state), f"id {gid}: replay not a win"
    return inputs


def main() -> None:
    levels = S.load_levels(LEVELS_JSON)
    assert len(levels) == 100, f"expected 100 levels, got {len(levels)}"
    out: dict = {}
    lines: list[str] = []
    multi: list[int] = []
    for ch_idx, fname in enumerate(LOCKED_FILES):
        data = json.loads((LOCKED_DIR / fname).read_text(encoding="utf-8"))
        for tip, board in enumerate(data["boards"]):
            gid = ch_idx * 10 + tip
            assert int(levels[gid]["id"]) == gid, f"levels[{gid}].id mismatch"
            cells = [S.rc_to_xy(rc) for rc in board["path"]]
            rules = S.Rules(levels[gid])
            assert (rules.cols, rules.rows) == (
                int(levels[gid]["cols"]), int(levels[gid]["rows"])), f"id {gid}: cols/rows"
            inputs = replay(gid, rules, cells)
            if len(inputs) != len(cells):
                multi.append(gid)
            out[str(gid)] = {
                "cols": rules.cols, "rows": rules.rows,
                "path": [list(c) for c in inputs], "violate": None,
                "cells": [list(c) for c in cells], "n_inputs": len(inputs),
            }
            lines.append(f"{gid} " + " ".join(f"{x},{y}" for x, y in inputs))
    assert len(out) == 100 and len(lines) == 100, "did not produce 100 levels"
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    OUT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"total levels: {len(out)}")
    print(f"inputs != cells ({len(multi)}): {multi}")
    print("EXPORT OK 100")


if __name__ == "__main__":
    main()
