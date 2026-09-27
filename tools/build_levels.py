#!/usr/bin/env python3
"""Emit Cangjie LevelCatalog from levels.json.

Does not invent levels. The locked SoT catalog is ch1..10 (涿郡..北伐):
100 boards with ids 0..99. Names stay as written (chapter·station, sometimes
already including ·第 N 驿).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "entry/src/main/resources/rawfile/levels.json"
OUT_PATH = ROOT / "entry/src/main/cangjie/levels.cj"
LOCKED_DIR = ROOT / "boards-locked"
LOCKED_FILES = (
    "ch1_zhuo.json",
    "ch2_pingyuan.json",
    "ch3_xuzhou.json",
    "ch4_lvbu.json",
    "ch5_touyuan.json",
    "ch6_jingzhou.json",
    "ch7_chibi.json",
    "ch8_rushu.json",
    "ch9_hanzhong.json",
    "ch10_beifa.json",
)

ST02_WALLS = [
    {"x1": 2, "y1": 4, "x2": 3, "y2": 4},
    {"x1": 2, "y1": 3, "x2": 2, "y2": 4},
]

# Mechanic fields the lossy levels.json projection does not emit.
# parity_edges and step_limit are kept (parityEdges / stepLimit).
DROPPED_MECHANIC_FIELDS = (
    "one_ways",
    "ferry",
    "slide_cells",
    "seal_gates",
    "token_cells",
    "burden",
    "collapse",
)


class DroppedMechanicsError(Exception):
    """convert_board refused to silently omit mechanic fields."""

    def __init__(self, rows: list[tuple[int, str, list[str]]]) -> None:
        self.rows = rows
        super().__init__(format_dropped_mechanics(rows))


def mechanic_value_present(value: object) -> bool:
    """True when a locked-board field carries a mechanic, not an empty placeholder."""
    if value is None:
        return False
    if isinstance(value, (list, tuple, dict)) and len(value) == 0:
        return False
    return True


def dropped_mechanic_fields(board: dict) -> list[str]:
    return [
        name
        for name in DROPPED_MECHANIC_FIELDS
        if mechanic_value_present(board.get(name))
    ]


def format_dropped_mechanics(rows: list[tuple[int, str, list[str]]]) -> str:
    lines = ["convert_board would drop mechanic fields:"]
    for gid, name, fields in rows:
        lines.append(f"  id={gid} {name} dropped={','.join(fields)}")
    return "\n".join(lines)


def iter_locked_boards() -> list[tuple[int, dict]]:
    missing = [fname for fname in LOCKED_FILES if not (LOCKED_DIR / fname).is_file()]
    if missing:
        print(
            f"error: missing locked board file(s) under {LOCKED_DIR}: {', '.join(missing)}",
            file=sys.stderr,
        )
        sys.exit(1)
    boards: list[tuple[int, dict]] = []
    for ch_idx, fname in enumerate(LOCKED_FILES):
        data = json.loads((LOCKED_DIR / fname).read_text(encoding="utf-8"))
        for tip_idx, board in enumerate(data["boards"]):
            boards.append((ch_idx * 10 + tip_idx, board))
    return boards


def convert_board(b: dict, global_id: int, *, allow_dropped_mechanics: bool = False) -> dict:
    """Project one locked board into the levels.json object.

    Fails by default when mechanic fields would be omitted. The returned object
    stays the historical lossy shape (no one_ways/ferry/slide/seal/burden/collapse)
    so an allowed projection remains byte-identical to the shipped catalog.
    """
    dropped = dropped_mechanic_fields(b)
    if dropped and not allow_dropped_mechanics:
        raise DroppedMechanicsError([(global_id, str(b.get("name", "")), dropped)])
    wps = [{"n": int(n), "x": int(c), "y": int(r)} for r, c, n in b["numbers_rc"]]
    wps.sort(key=lambda item: item["n"])
    walls = []
    for r, c in b.get("walls", {}).get("h_between", []):
        walls.append({"x1": int(c), "y1": int(r), "x2": int(c) + 1, "y2": int(r)})
    for r, c in b.get("walls", {}).get("v_between", []):
        walls.append({"x1": int(c), "y1": int(r), "x2": int(c), "y2": int(r) + 1})
    # parity_edges.between is [[r, c], [r, c]] → cells are (x = c, y = r), like numbers_rc.
    parity_edges = []
    for e in b.get("parity_edges") or []:
        (r1, c1), (r2, c2) = e["between"]
        parity_edges.append(
            {
                "x1": int(c1),
                "y1": int(r1),
                "x2": int(c2),
                "y2": int(r2),
                "requireOdd": bool(e["require_odd"]),
                "requireEven": bool(e["require_even"]),
            }
        )
    return {
        "id": global_id,
        "name": b["name"],
        "cols": int(b["size"]),
        "rows": int(b["size"]),
        "waypoints": wps,
        "walls": walls,
        "parityEdges": parity_edges,
        "stepLimit": int(b.get("step_limit") or 0),
    }


def load_source_levels(*, allow_dropped_mechanics: bool = False) -> list[dict]:
    """Project boards-locked into the levels.json shape.

    Default refuses when a mechanic field would be omitted. Pass
    allow_dropped_mechanics=True only to reproduce the current lossy snapshot.
    """
    dropped_rows: list[tuple[int, str, list[str]]] = []
    levels: list[dict] = []
    for global_id, board in iter_locked_boards():
        dropped = dropped_mechanic_fields(board)
        if dropped:
            dropped_rows.append((global_id, str(board.get("name", "")), dropped))
        if dropped and not allow_dropped_mechanics:
            continue
        levels.append(convert_board(board, global_id, allow_dropped_mechanics=True))
    if dropped_rows and not allow_dropped_mechanics:
        raise DroppedMechanicsError(dropped_rows)
    return levels


EXPECTED_NAMES = tuple(board["name"] for _, board in iter_locked_boards())


def _cj_bool(value: bool) -> str:
    return "true" if value else "false"


def emit(levels: list[dict]) -> str:
    lines = [
        "package ohos_app_cangjie_entry",
        "",
        "/* Generated from resources/rawfile/levels.json. Do not invent levels here. */",
        "import std.collection.ArrayList",
        "import ohos_app_cangjie_entry.engine.Wall",
        "import ohos_app_cangjie_entry.game.{LevelDef, ParityEdge, Waypoint}",
        "",
        "public class LevelCatalog {",
        "    public static func all(): ArrayList<LevelDef> {",
        "        let levels = ArrayList<LevelDef>()",
    ]
    for lv in levels:
        key = lv["id"]
        lines.append(f"        let wps{key} = ArrayList<Waypoint>()")
        for wp in lv["waypoints"]:
            lines.append(f"        wps{key}.add(Waypoint({wp['n']}, {wp['x']}, {wp['y']}))")
        lines.append(f"        let walls{key} = ArrayList<Wall>()")
        for w in lv["walls"]:
            lines.append(
                f"        walls{key}.add(Wall({w['x1']}, {w['y1']}, {w['x2']}, {w['y2']}))"
            )
        lines.append(f"        let parityEdges{key} = ArrayList<ParityEdge>()")
        for pe in lv.get("parityEdges") or []:
            lines.append(
                f"        parityEdges{key}.add(ParityEdge({pe['x1']}, {pe['y1']}, {pe['x2']}, {pe['y2']}, {_cj_bool(pe['requireOdd'])}, {_cj_bool(pe['requireEven'])}))"
            )
        lines.append(f"        let stepLimit{key} = {int(lv.get('stepLimit') or 0)}")
        lines.append(
            f"        levels.add(LevelDef({lv['id']}, \"{lv['name']}\", {lv['cols']}, {lv['rows']}, wps{key}, walls{key}, parityEdges{key}, stepLimit{key}))"
        )
        lines.append("")
    lines.extend(
        [
            "        return levels",
            "    }",
            "",
            "    public static func byIndex(index: Int64): LevelDef {",
            "        return LevelCatalog.all()[index]",
            "    }",
            "",
            "    public static func count(): Int64 {",
            "        return LevelCatalog.all().size",
            "    }",
            "}",
            "",
        ]
    )
    return "\n".join(lines)


def _wp_key(w: dict) -> tuple[int, int, int]:
    return (int(w["n"]), int(w["x"]), int(w["y"]))


def _wall_key(w: dict) -> tuple[int, int, int, int]:
    return (int(w["x1"]), int(w["y1"]), int(w["x2"]), int(w["y2"]))


def _parity_key(p: dict) -> tuple[int, int, int, int, bool, bool]:
    return (
        int(p["x1"]),
        int(p["y1"]),
        int(p["x2"]),
        int(p["y2"]),
        bool(p["requireOdd"]),
        bool(p["requireEven"]),
    )


def load_verified() -> list[dict]:
    levels = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    if not isinstance(levels, list):
        raise SystemExit("levels.json must be a JSON array")
    if len(levels) != 100:
        raise SystemExit(f"need exactly 100 locked ch1..10 levels, found {len(levels)}")
    ids = [int(lv["id"]) for lv in levels]
    if ids != list(range(100)):
        raise SystemExit(f"refusing to emit: ids {ids} are not 0..99 consecutive")
    names = [lv["name"] for lv in levels]
    if names != list(EXPECTED_NAMES):
        raise SystemExit(f"refusing to emit: locked names {names} != expected names")
    if any("_src" in lv for lv in levels):
        raise SystemExit("refusing to emit: levels.json must not contain _src fields")
    if any(lv["name"] == "汽梁" for lv in levels):
        raise SystemExit("refusing to emit: 汽梁 is a typo; use 汴梁")
    # Byte-compare against the lossy projection. Regeneration itself is refused
    # in main() unless --allow-dropped-mechanics is set.
    source_levels = load_source_levels(allow_dropped_mechanics=True)
    for idx, (lv, src_lv) in enumerate(zip(levels, source_levels)):
        if lv["name"] != src_lv["name"]:
            raise SystemExit(
                f"level {idx} name mismatch: {lv['name']} != {src_lv['name']}"
            )
        if int(lv["cols"]) != src_lv["cols"] or int(lv["rows"]) != src_lv["rows"]:
            raise SystemExit(
                f"level {idx} size mismatch: ({lv['cols']},{lv['rows']}) != ({src_lv['cols']},{src_lv['rows']})"
            )
        if [_wp_key(w) for w in lv["waypoints"]] != [_wp_key(w) for w in src_lv["waypoints"]]:
            raise SystemExit(f"level {idx} waypoints mismatch with locked source")
        if [_wall_key(w) for w in (lv.get("walls") or [])] != [
            _wall_key(w) for w in src_lv["walls"]
        ]:
            raise SystemExit(f"level {idx} walls mismatch with locked source")
        if [_parity_key(p) for p in (lv.get("parityEdges") or [])] != [
            _parity_key(p) for p in (src_lv.get("parityEdges") or [])
        ]:
            raise SystemExit(f"level {idx} parityEdges mismatch with locked source")
        if int(lv.get("stepLimit") or 0) != int(src_lv.get("stepLimit") or 0):
            raise SystemExit(f"level {idx} stepLimit mismatch with locked source")
    st01 = levels[0]
    if (
        st01["name"] != "涿郡·涿"
        or int(st01["cols"]) != 6
        or int(st01["rows"]) != 6
        or len(st01["waypoints"]) != 6
        or [_wall_key(w) for w in (st01.get("walls") or [])] != []
    ):
        raise SystemExit("refusing to emit: ST01 涿郡·涿 must be 6x6 with 6 waypoints and no walls")
    st02 = levels[1]
    if st02["name"] != "涿郡·范阳" or [_wall_key(w) for w in (st02.get("walls") or [])] != [
        _wall_key(w) for w in ST02_WALLS
    ]:
        raise SystemExit("refusing to emit: ST02 涿郡·范阳 walls were changed")
    return levels


def _print_dropped(rows: list[tuple[int, str, list[str]]], *, allowed: bool) -> None:
    header = (
        "WARNING: dropping mechanic fields because --allow-dropped-mechanics was set:"
        if allowed
        else "FAIL: convert_board would drop mechanic fields (refusing to emit):"
    )
    stream = sys.stdout if allowed else sys.stderr
    print(header, file=stream)
    for gid, name, fields in rows:
        print(f"  id={gid} {name} dropped={','.join(fields)}", file=stream)
    if not allowed:
        print(
            "Pass --allow-dropped-mechanics to project the current lossy catalog anyway.",
            file=stream,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit Cangjie LevelCatalog from levels.json.")
    parser.add_argument(
        "--sync-json",
        action="store_true",
        help="Rebuild entry/src/main/resources/rawfile/levels.json from boards-locked/",
    )
    parser.add_argument(
        "--allow-dropped-mechanics",
        action="store_true",
        help="Permit converting boards while omitting mechanic fields that levels.json does not store. Prints every omitted field. Without this flag the command exits non-zero and writes nothing.",
    )
    args = parser.parse_args()
    dropped_rows: list[tuple[int, str, list[str]]] = []
    for global_id, board in iter_locked_boards():
        dropped = dropped_mechanic_fields(board)
        if dropped:
            dropped_rows.append((global_id, str(board.get("name", "")), dropped))
    if dropped_rows and not args.allow_dropped_mechanics:
        _print_dropped(dropped_rows, allowed=False)
        sys.exit(1)
    if dropped_rows and args.allow_dropped_mechanics:
        _print_dropped(dropped_rows, allowed=True)
    if args.sync_json:
        source_levels = load_source_levels(allow_dropped_mechanics=True)
        JSON_PATH.write_text(
            json.dumps(source_levels, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {JSON_PATH} ({len(source_levels)} levels)")
    levels = load_verified()
    OUT_PATH.write_text(emit(levels), encoding="utf-8")
    print(f"wrote {OUT_PATH} ({len(levels)} locked levels ch1..ch10)")


if __name__ == "__main__":
    main()
