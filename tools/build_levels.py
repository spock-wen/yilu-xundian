#!/usr/bin/env python3
"""Emit Cangjie LevelCatalog from levels.json.

Does not invent levels. The locked SoT catalog is 涿郡 + 平原: exactly 20
boards with ids 0..19. Names stay as written (chapter·station, sometimes
already including ·第 2 驿).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "entry/src/main/resources/rawfile/levels.json"
OUT_PATH = ROOT / "entry/src/main/cangjie/levels.cj"

EXPECTED_NAMES = (
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
    "平原·高唐",
    "平原·高唐·第 2 驿",
    "平原·郡治",
    "平原·郡治·第 2 驿",
    "平原·安德",
    "平原·安德·第 2 驿",
    "平原·鬲",
    "平原·鬲·第 2 驿",
    "平原·祝阿",
    "平原·祝阿·第 2 驿",
)

ST02_WALLS = [
    {"x1": 2, "y1": 4, "x2": 3, "y2": 4},
    {"x1": 2, "y1": 3, "x2": 2, "y2": 4},
]


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
    if len(levels) != 20:
        raise SystemExit(f"need exactly 20 locked 涿郡+平原 levels, found {len(levels)}")
    ids = [int(lv["id"]) for lv in levels]
    if ids != list(range(20)):
        raise SystemExit(f"refusing to emit: ids {ids} are not 0..19 consecutive")
    names = [lv["name"] for lv in levels]
    if names != list(EXPECTED_NAMES):
        raise SystemExit(f"refusing to emit: locked names {names} != {list(EXPECTED_NAMES)}")
    if any("_src" in lv for lv in levels):
        raise SystemExit("refusing to emit: levels.json must not contain _src fields")
    if any(lv["name"] == "汽梁" for lv in levels):
        raise SystemExit("refusing to emit: 汽梁 is a typo; use 汴梁")
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
    levels = load_verified()
    OUT_PATH.write_text(emit(levels), encoding="utf-8")
    print(f"wrote {OUT_PATH} ({len(levels)} locked 涿郡+平原 levels)")


if __name__ == "__main__":
    main()
