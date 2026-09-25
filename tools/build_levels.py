#!/usr/bin/env python3
"""Emit Cangjie LevelCatalog from levels.json.

Does not invent levels. The locked SoT catalog is ch1..10 (涿郡..北伐):
100 boards with ids 0..99. Names stay as written (chapter·station, sometimes
already including ·第 N 驿).
"""
from __future__ import annotations

import argparse
import json
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


def convert_board(b: dict, global_id: int) -> dict:
    wps = [{"n": int(n), "x": int(c), "y": int(r)} for r, c, n in b["numbers_rc"]]
    wps.sort(key=lambda item: item["n"])
    walls = []
    for r, c in b.get("walls", {}).get("h_between", []):
        walls.append({"x1": int(c), "y1": int(r), "x2": int(c) + 1, "y2": int(r)})
    for r, c in b.get("walls", {}).get("v_between", []):
        walls.append({"x1": int(c), "y1": int(r), "x2": int(c), "y2": int(r) + 1})
    return {
        "id": global_id,
        "name": b["name"],
        "cols": int(b["size"]),
        "rows": int(b["size"]),
        "waypoints": wps,
        "walls": walls,
    }


def load_source_levels() -> list[dict]:
    source_dir = (
        LOCKED_DIR
        if (LOCKED_DIR / LOCKED_FILES[0]).exists()
        else Path("/workspace/tmp/locked-boards-inject")
    )
    levels = []
    for ch_idx, fname in enumerate(LOCKED_FILES):
        fpath = source_dir / fname
        data = json.loads(fpath.read_text(encoding="utf-8"))
        for tip_idx, b in enumerate(data["boards"]):
            global_id = ch_idx * 10 + tip_idx
            levels.append(convert_board(b, global_id))
    return levels


EXPECTED_NAMES = tuple(lv["name"] for lv in load_source_levels())


def emit(levels: list[dict]) -> str:
    lines = [
        "package ohos_app_cangjie_entry",
        "",
        "/* Generated from resources/rawfile/levels.json. Do not invent levels here. */",
        "import std.collection.ArrayList",
        "import ohos_app_cangjie_entry.engine.Wall",
        "import ohos_app_cangjie_entry.game.{LevelDef, Waypoint}",
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
        lines.append(
            f"        levels.add(LevelDef({lv['id']}, \"{lv['name']}\", {lv['cols']}, {lv['rows']}, wps{key}, walls{key}))"
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
    source_levels = load_source_levels()
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit Cangjie LevelCatalog from levels.json.")
    parser.add_argument(
        "--sync-json",
        action="store_true",
        help="Rebuild entry/src/main/resources/rawfile/levels.json from boards-locked/",
    )
    args = parser.parse_args()
    if args.sync_json:
        source_levels = load_source_levels()
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
