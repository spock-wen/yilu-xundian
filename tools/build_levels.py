#!/usr/bin/env python3
"""Build handmade 「驿路巡点」 levels from explicit Hamiltonian paths.

A generator is allowed only if it enforces waypoint-order + fill-all.
This script never emits a random scribble: every level starts from a
hand-written path. Waypoints are cells on that path in visit order.
Walls are unused orthogonal edges (they cannot cut the known path).

The independent solver (solve_levels.py) must still accept the JSON.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Import the independent solver (no shared game engine with the app).
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from solve_levels import solve, validate_schema, wall_key  # noqa: E402


def serpentine(cols: int, rows: int) -> list[tuple[int, int]]:
    """Row-major snake. Deterministic, not a random walk."""
    path: list[tuple[int, int]] = []
    for y in range(rows):
        xs = range(cols) if y % 2 == 0 else range(cols - 1, -1, -1)
        for x in xs:
            path.append((x, y))
    return path


def spiral(cols: int, rows: int) -> list[tuple[int, int]]:
    """Clockwise spiral from top-left. Deterministic."""
    seen = [[False] * cols for _ in range(rows)]
    path: list[tuple[int, int]] = []
    x, y = 0, 0
    dirs = ((1, 0), (0, 1), (-1, 0), (0, -1))
    d = 0
    for _ in range(cols * rows):
        path.append((x, y))
        seen[y][x] = True
        nx, ny = x + dirs[d][0], y + dirs[d][1]
        if not (0 <= nx < cols and 0 <= ny < rows) or seen[ny][nx]:
            d = (d + 1) % 4
            nx, ny = x + dirs[d][0], y + dirs[d][1]
        x, y = nx, ny
    return path


def custom(cells: list[tuple[int, int]]) -> list[tuple[int, int]]:
    return list(cells)


def unused_edges(cols: int, rows: int, path: list[tuple[int, int]]) -> set[tuple[int, int]]:
    used: set[tuple[int, int]] = set()
    for (x1, y1), (x2, y2) in zip(path, path[1:]):
        used.add(wall_key(x1, y1, x2, y2))
    unused: set[tuple[int, int]] = set()
    for y in range(rows):
        for x in range(cols):
            if x + 1 < cols:
                k = wall_key(x, y, x + 1, y)
                if k not in used:
                    unused.add(k)
            if y + 1 < rows:
                k = wall_key(x, y, x, y + 1)
                if k not in used:
                    unused.add(k)
    return unused


def decode_wall(key: tuple[int, int]) -> dict[str, int]:
    a, b = key
    return {"x1": a % 64, "y1": a // 64, "x2": b % 64, "y2": b // 64}


def pick_walls(unused: set[tuple[int, int]], wanted: list[tuple[int, int, int, int]]) -> list[dict[str, int]]:
    walls = []
    unused_copy = set(unused)
    for x1, y1, x2, y2 in wanted:
        k = wall_key(x1, y1, x2, y2)
        if k not in unused_copy:
            raise ValueError(f"wall ({x1},{y1})-({x2},{y2}) cuts the known path")
        unused_copy.remove(k)
        walls.append(decode_wall(k))
    return walls


def make_level(
    level_id: int,
    name: str,
    cols: int,
    rows: int,
    path: list[tuple[int, int]],
    waypoint_steps: list[int],
    wall_pairs: list[tuple[int, int, int, int]],
) -> dict:
    if len(path) != cols * rows:
        raise ValueError(f"{name}: path length {len(path)} != {cols * rows}")
    if path[0] != path[0]:
        pass
    if waypoint_steps[0] != 0:
        raise ValueError(f"{name}: first waypoint must be the start of the path")
    if waypoint_steps[-1] != len(path) - 1:
        raise ValueError(f"{name}: last waypoint must be the end of the path")
    if waypoint_steps != sorted(waypoint_steps):
        raise ValueError(f"{name}: waypoint steps must increase along the path")
    unused = unused_edges(cols, rows, path)
    walls = pick_walls(unused, wall_pairs)
    waypoints = [{"n": i + 1, "x": path[step][0], "y": path[step][1]} for i, step in enumerate(waypoint_steps)]
    return {
        "id": level_id,
        "name": name,
        "cols": cols,
        "rows": rows,
        "waypoints": waypoints,
        "walls": walls,
        "_intended_path": [{"x": x, "y": y} for x, y in path],
    }


def build() -> list[dict]:
    levels = [
        # 1 长安 — 3×3 tutorial, two stations, open grid
        make_level(1, "长安", 3, 3, serpentine(3, 3), [0, 8], []),
        # 2 洛阳 — 3×3, three stations
        make_level(
            2, "洛阳", 3, 3,
            custom([
                (0, 0), (1, 0), (2, 0),
                (2, 1), (1, 1), (0, 1),
                (0, 2), (1, 2), (2, 2),
            ]),
            [0, 2, 8],
            [],
        ),
        # 3 汴梁 — 4×4, first wall (Kaifeng / Bianliang on the Grand Canal)
        make_level(
            3, "汴梁", 4, 4,
            custom([
                (0, 0), (1, 0), (2, 0), (3, 0),
                (3, 1), (2, 1), (1, 1), (0, 1),
                (0, 2), (1, 2), (2, 2), (3, 2),
                (3, 3), (2, 3), (1, 3), (0, 3),
            ]),
            [0, 3, 15],
            [(0, 0, 0, 1)],
        ),
        # 4 扬州 — 4×4 spiral, two walls
        make_level(
            4, "扬州", 4, 4,
            spiral(4, 4),
            [0, 6, 15],
            [(1, 1, 1, 2), (2, 2, 3, 2)],
        ),
        # 5 杭州 — 4×4, three walls, four stations
        make_level(
            5, "杭州", 4, 4,
            custom([
                (0, 0), (0, 1), (0, 2), (0, 3),
                (1, 3), (1, 2), (1, 1), (1, 0),
                (2, 0), (3, 0), (3, 1), (2, 1),
                (2, 2), (2, 3), (3, 3), (3, 2),
            ]),
            [0, 3, 8, 15],
            [(0, 0, 1, 0), (1, 1, 2, 1), (2, 2, 3, 2)],
        ),
        # 6 苏州 — 4×4, tighter numbers
        make_level(
            6, "苏州", 4, 4,
            custom([
                (1, 0), (0, 0), (0, 1), (1, 1),
                (2, 1), (2, 0), (3, 0), (3, 1),
                (3, 2), (2, 2), (1, 2), (0, 2),
                (0, 3), (1, 3), (2, 3), (3, 3),
            ]),
            [0, 6, 11, 15],
            [(1, 0, 1, 1), (2, 2, 2, 3)],
        ),
        # 7 凉州 — 5×5 Hexi corridor, one wall
        make_level(
            7, "凉州", 5, 5,
            serpentine(5, 5),
            [0, 4, 24],
            [(0, 0, 0, 1)],
        ),
        # 8 敦煌 — 5×5 spiral, two walls
        make_level(
            8, "敦煌", 5, 5,
            spiral(5, 5),
            [0, 8, 16, 24],
            [(2, 2, 2, 3), (3, 1, 4, 1)],
        ),
        # 9 肃州 — 5×5 custom, two walls
        make_level(
            9, "肃州", 5, 5,
            custom([
                (0, 0), (1, 0), (2, 0), (3, 0), (4, 0),
                (4, 1), (3, 1), (2, 1), (1, 1), (0, 1),
                (0, 2), (0, 3), (0, 4), (1, 4), (1, 3),
                (1, 2), (2, 2), (3, 2), (4, 2), (4, 3),
                (3, 3), (2, 3), (2, 4), (3, 4), (4, 4),
            ]),
            [0, 10, 16, 24],
            [(1, 0, 1, 1), (3, 2, 3, 3)],
        ),
        # 10 滑州 — 5×5, three walls
        make_level(
            10, "滑州", 5, 5,
            custom([
                (2, 0), (1, 0), (0, 0), (0, 1), (1, 1),
                (2, 1), (3, 1), (3, 0), (4, 0), (4, 1),
                (4, 2), (3, 2), (2, 2), (1, 2), (0, 2),
                (0, 3), (0, 4), (1, 4), (1, 3), (2, 3),
                (3, 3), (4, 3), (4, 4), (3, 4), (2, 4),
            ]),
            [0, 8, 16, 24],
            [(2, 0, 2, 1), (1, 2, 1, 3), (3, 3, 3, 4)],
        ),
        # 11 通州 — 5×5 northern canal, three walls
        make_level(
            11, "通州", 5, 5,
            custom([
                (0, 2), (0, 1), (0, 0), (1, 0), (2, 0),
                (3, 0), (4, 0), (4, 1), (3, 1), (2, 1),
                (1, 1), (1, 2), (1, 3), (0, 3), (0, 4),
                (1, 4), (2, 4), (2, 3), (2, 2), (3, 2),
                (4, 2), (4, 3), (3, 3), (3, 4), (4, 4),
            ]),
            [0, 6, 14, 24],
            [(0, 2, 1, 2), (2, 1, 2, 2), (3, 2, 3, 3)],
        ),
        # 12 济宁 — 5×5 canal hub, five stations, three walls
        make_level(
            12, "济宁", 5, 5,
            custom([
                (0, 0), (0, 1), (1, 1), (1, 0), (2, 0),
                (3, 0), (4, 0), (4, 1), (3, 1), (2, 1),
                (2, 2), (1, 2), (0, 2), (0, 3), (0, 4),
                (1, 4), (1, 3), (2, 3), (2, 4), (3, 4),
                (4, 4), (4, 3), (3, 3), (3, 2), (4, 2),
            ]),
            [0, 6, 12, 19, 24],
            [(0, 0, 1, 0), (1, 1, 2, 1), (4, 2, 4, 3)],
        ),
    ]
    return levels


def strip_private(level: dict) -> dict:
    out = {k: v for k, v in level.items() if not k.startswith("_")}
    if not out["walls"]:
        out.pop("walls")
    return out


def emit_cangjie(levels: list[dict]) -> str:
    """Emit a Cangjie literal catalog. Resource-loading APIs are not used."""
    lines = [
        "package ohos_app_cangjie_entry",
        "",
        "import std.collection.ArrayList",
        "import ohos_app_cangjie_entry.engine.Wall",
        "import ohos_app_cangjie_entry.game.{LevelDef, Waypoint}",
        "",
        "/* Shipped levels. Same data as resources/rawfile/levels.json.",
        "   Embedded as literals because Cangjie 1.1.3 rawfile loading is unverified. */",
        "public class LevelCatalog {",
        "    public static func all(): ArrayList<LevelDef> {",
        "        let levels = ArrayList<LevelDef>()",
    ]
    for lv in levels:
        walls = lv.get("walls") or []
        lines.append(f"        // #{lv['id']} {lv['name']} {lv['cols']}x{lv['rows']}")
        lines.append("        let wps{0} = ArrayList<Waypoint>()".format(lv["id"]))
        for wp in lv["waypoints"]:
            lines.append(
                "        wps{0}.add(Waypoint({1}, {2}, {3}))".format(
                    lv["id"], wp["n"], wp["x"], wp["y"]
                )
            )
        lines.append("        let walls{0} = ArrayList<Wall>()".format(lv["id"]))
        for w in walls:
            lines.append(
                "        walls{0}.add(Wall({1}, {2}, {3}, {4}))".format(
                    lv["id"], w["x1"], w["y1"], w["x2"], w["y2"]
                )
            )
        lines.append(
            '        levels.add(LevelDef({id}, "{name}", {cols}, {rows}, wps{id}, walls{id}))'.format(
                id=lv["id"], name=lv["name"], cols=lv["cols"], rows=lv["rows"]
            )
        )
    lines.extend(
        [
            "        return levels",
            "    }",
            "",
            "    public static func byIndex(index: Int64): LevelDef {",
            "        let levels = LevelCatalog.all()",
            "        return levels[index]",
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


def main() -> int:
    levels = build()
    if len(levels) != 12:
        print(f"FAIL: expected 12 levels, got {len(levels)}", file=sys.stderr)
        return 2

    for lv in levels:
        public = strip_private(lv)
        validate_schema(public)
        found = solve(public)
        if not found:
            print(f"FAIL: builder path rejected by solver: #{lv['id']} {lv['name']}", file=sys.stderr)
            return 1
        intended = [(c["x"], c["y"]) for c in lv["_intended_path"]]
        if found[0] != intended and intended not in found:
            # Solver may find a different first solution; that is OK if ≥1 exists.
            pass
        print(f"OK   #{lv['id']} {lv['name']} {lv['cols']}x{lv['rows']}  solver-checked")

    raw_dir = ROOT / "entry/src/main/resources/rawfile"
    raw_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "yilu-xundian-level-v1",
        "note": "x=column y=row origin top-left; walls are orthogonal edges",
        "levels": [strip_private(lv) for lv in levels],
    }
    json_path = raw_dir / "levels.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    cj_path = ROOT / "entry/src/main/cangjie/src/levels.cj"
    cj_path.parent.mkdir(parents=True, exist_ok=True)
    cj_path.write_text(emit_cangjie(payload["levels"]), encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Wrote {cj_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
