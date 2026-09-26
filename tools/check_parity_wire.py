#!/usr/bin/env python3
"""Self-check: parity edges survive boards-locked → levels.json → levels.cj.

Run after `python3 tools/build_levels.py --sync-json`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCKED_PATH = ROOT / "boards-locked/ch9_hanzhong.json"
JSON_PATH = ROOT / "entry/src/main/resources/rawfile/levels.json"
LEVELS_CJ = ROOT / "entry/src/main/cangjie/levels.cj"
LEVELDEF_CJ = ROOT / "entry/src/main/cangjie/game/level.cj"

# ch9 is the 9th locked chapter file (index 8); tip0 is its first board.
CH9_TIP0_ID = 8 * 10 + 0
CH9_TIP0_NAME = "汉中·阳平关"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    tip0 = json.loads(LOCKED_PATH.read_text(encoding="utf-8"))["boards"][0]
    if tip0["name"] != CH9_TIP0_NAME:
        fail(f"locked ch9 tip0 is {tip0['name']!r}, expected {CH9_TIP0_NAME!r}")
    locked_edges = tip0.get("parity_edges") or []
    if len(locked_edges) != 2:
        fail(f"locked ch9 tip0 has {len(locked_edges)} parity_edges, expected 2")

    levels = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    lv = levels[CH9_TIP0_ID]
    if lv["name"] != CH9_TIP0_NAME:
        fail(f"levels.json id {CH9_TIP0_ID} is {lv['name']!r}, expected {CH9_TIP0_NAME!r}")
    edges = lv.get("parityEdges") or []
    if len(edges) != 2:
        fail(f"levels.json ch9 tip0 has {len(edges)} parityEdges after regen, expected 2")
    for e in edges:
        if not (e["requireOdd"] ^ e["requireEven"]):
            fail(f"parity edge {e} must set exactly one of requireOdd/requireEven")

    cj = LEVELS_CJ.read_text(encoding="utf-8")
    for field in ("parityEdges", "stepLimit"):
        if field not in cj:
            fail(f"LevelDef field name {field!r} missing from levels.cj")
    header, sep, _ = cj.partition(f"levels.add(LevelDef({CH9_TIP0_ID},")
    if not sep:
        fail(f"levels.cj has no LevelDef({CH9_TIP0_ID}, …) call")
    block = header.rsplit("\n\n", 1)[-1]
    edge_calls = block.count(f"parityEdges{CH9_TIP0_ID}.add(ParityEdge(")
    if edge_calls != 2:
        fail(f"levels.cj ch9 tip0 block has {edge_calls} ParityEdge adds, expected 2")

    leveldef = LEVELDEF_CJ.read_text(encoding="utf-8")
    for field in ("parityEdges", "stepLimit"):
        if f"public var {field}" not in leveldef:
            fail(f"LevelDef does not declare public var {field}")

    print(f"OK: {CH9_TIP0_NAME} has 2 parity edges in boards-locked + levels.json + levels.cj")
    print("OK: LevelDef field names parityEdges/stepLimit present in levels.cj")


if __name__ == "__main__":
    main()
