#!/usr/bin/env python3
"""Emit Cangjie LevelCatalog from levels.json.

Does not invent levels. Tutorial (designer 6x8 长安) is first; the next 12
are the solver-verified table shipped as-is.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "entry/src/main/resources/rawfile/levels.json"
OUT_PATH = ROOT / "entry/src/main/cangjie/levels.cj"

TUTORIAL = {
    "id": 0,
    "name": "长安",
    "cols": 6,
    "rows": 8,
    "waypoints": [
        {"n": 1, "x": 2, "y": 0},
        {"n": 2, "x": 3, "y": 2},
        {"n": 3, "x": 1, "y": 4},
        {"n": 4, "x": 5, "y": 5},
        {"n": 5, "x": 0, "y": 7},
    ],
    "walls": [],
}

EXPECTED_NAMES = (
    "长安",
    "洛阳",
    "汴梁",
    "扬州",
    "杭州",
    "苏州",
    "凉州",
    "敦煌",
    "肃州",
    "滑州",
    "通州",
    "济宁",
)


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


def load_verified() -> list[dict]:
    levels = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    if not isinstance(levels, list):
        raise SystemExit("levels.json must be a JSON array")
    if len(levels) < 13:
        raise SystemExit("need tutorial + 12 verified levels")
    tut = levels[0]
    if (
        int(tut["id"]) != TUTORIAL["id"]
        or tut["name"] != TUTORIAL["name"]
        or int(tut["cols"]) != TUTORIAL["cols"]
        or int(tut["rows"]) != TUTORIAL["rows"]
        or [_wp_key(w) for w in tut["waypoints"]] != [_wp_key(w) for w in TUTORIAL["waypoints"]]
        or (tut.get("walls") or []) != []
    ):
        raise SystemExit("refusing to emit: tutorial 长安 6x8 waypoints were changed")
    rest = levels[1:]
    names = [lv["name"] for lv in rest]
    if names != list(EXPECTED_NAMES):
        raise SystemExit(f"refusing to emit: verified names {names} != {list(EXPECTED_NAMES)}")
    if any(lv["name"] == "汽梁" for lv in levels):
        raise SystemExit("refusing to emit: 汽梁 is a typo; use 汴梁")
    return levels


def main() -> None:
    levels = load_verified()
    OUT_PATH.write_text(emit(levels), encoding="utf-8")
    print(f"wrote {OUT_PATH} ({len(levels)} levels: tutorial + 12 verified)")


if __name__ == "__main__":
    main()
