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


def neighbors(x: int, y: int, cols: int, rows: int, walls: set[tuple[int, int]]) -> Iterable[tuple[int, int]]:
    for dx, dy in DIRS:
        nx, ny = x + dx, y + dy
        if 0 <= nx < cols and 0 <= ny < rows:
            if wall_key(x, y, nx, ny) not in walls:
                yield nx, ny


def solve(level: dict, find_all: bool = False, limit: int = 1) -> list[list[tuple[int, int]]]:
    """DFS Hamiltonian path with waypoint-order + end-on-max-number."""
    cols, rows, wps, walls, start, end, max_n = compile_level(level)
    total = cols * rows
    solutions: list[list[tuple[int, int]]] = []
    start_mask = 1 << (start[1] * cols + start[0])
    path = [start]

    def degree(x: int, y: int, visited: int) -> int:
        d = 0
        for nx, ny in neighbors(x, y, cols, rows, walls):
            bit = 1 << (ny * cols + nx)
            if visited & bit == 0:
                d += 1
        return d

    def dfs(x: int, y: int, visited: int, next_n: int) -> None:
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Prove every shipped level has ≥1 solution.")
    parser.add_argument(
        "--json",
        default="entry/src/main/resources/rawfile/levels.json",
        help="Path to levels.json",
    )
    parser.add_argument("--limit", type=int, default=1, help="Max solutions to search per level")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    json_path = Path(args.json)
    if not json_path.is_absolute():
        json_path = root / json_path
    if not json_path.exists():
        print(f"FAIL: missing {json_path}", file=sys.stderr)
        return 2

    levels = load_levels(json_path)
    if len(levels) < 12:
        print(f"FAIL: need ≥12 levels, found {len(levels)}", file=sys.stderr)
        return 2

    failed = 0
    print(f"Solving {len(levels)} levels from {json_path}")
    print("-" * 60)
    for level in levels:
        validate_schema(level)
        solutions = solve(level, find_all=False, limit=args.limit)
        tag = f"#{level['id']} {level['name']} {level['cols']}x{level['rows']}"
        walls = len(level.get("walls") or [])
        wps = len(level["waypoints"])
        if solutions:
            print(f"OK   {tag}  waypoints={wps} walls={walls}")
            print(f"     sample: {format_path(solutions[0])}")
        else:
            failed += 1
            print(f"FAIL {tag}  waypoints={wps} walls={walls}  (no solution)")
    print("-" * 60)
    if failed:
        print(f"RESULT: {failed} unsolvable level(s). Do not ship.")
        return 1
    print(f"RESULT: all {len(levels)} levels have ≥1 solution.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
