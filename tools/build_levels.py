#!/usr/bin/env python3
"""Emit Cangjie LevelCatalog from the verified levels.json. Does not invent levels."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "entry/src/main/resources/rawfile/levels.json"
OUT_PATH = ROOT / "entry/src/main/cangjie/levels.cj"


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
        lines.append(f"        let wps{lv['id']} = ArrayList<Waypoint>()")
        for wp in lv["waypoints"]:
            lines.append(f"        wps{lv['id']}.add(Waypoint({wp['n']}, {wp['x']}, {wp['y']}))")
        lines.append(f"        let walls{lv['id']} = ArrayList<Wall>()")
        for w in lv["walls"]:
            lines.append(
                f"        walls{lv['id']}.add(Wall({w['x1']}, {w['y1']}, {w['x2']}, {w['y2']}))"
            )
        lines.append(
            f"        levels.add(LevelDef({lv['id']}, \"{lv['name']}\", {lv['cols']}, {lv['rows']}, wps{lv['id']}, walls{lv['id']}))"
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


def load_verified() -> list[dict]:
    levels = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    if not isinstance(levels, list):
        raise SystemExit("levels.json must be a JSON array of verified levels")
    names = [lv["name"] for lv in levels]
    if names != list(EXPECTED_NAMES):
        raise SystemExit(f"refusing to emit: names {names} != verified {list(EXPECTED_NAMES)}")
    if any(lv["name"] == "汽梁" for lv in levels):
        raise SystemExit("refusing to emit: 汽梁 is a typo; use 汴梁")
    return levels


def main() -> None:
    levels = load_verified()
    OUT_PATH.write_text(emit(levels), encoding="utf-8")
    print(f"wrote {OUT_PATH} ({len(levels)} levels, copied from verified JSON)")


if __name__ == "__main__":
    main()
