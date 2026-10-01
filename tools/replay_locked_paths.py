#!/usr/bin/env python3
"""Replay every boards-locked solution path against the shipped levels.json.

Reads boards-locked/ch1..ch10 in the same order as `build_levels.LOCKED_FILES`
(global_id = chapter_index * 10 + board_index, i.e. ids 0..99), takes each
board's archived `path` (`[r, c]` sequence) and replays it with
`solve_levels.check_path(level, path)` on the corresponding released level.

Extra assertion (no solving, locked fields only): every board that carries a
渡口 `ferry` must show the 甲→乙 jump as consecutive path entries exactly once
(PM ruling: 路线恰好一次甲→乙跳接; design jingzhou_ch6/zip_ferry.py).

Usage (from repo root):
    PYTHONDONTWRITEBYTECODE=1 python3 tools/replay_locked_paths.py
    ... --json entry/src/main/resources/rawfile/levels.json \
        --locked-dir boards-locked --table /tmp/replay_table.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from solve_levels import check_path, load_levels, validate_schema  # noqa: E402

# Same tuple/order as tools/build_levels.py:20-33 (single source of truth).
from build_levels import LOCKED_FILES  # noqa: E402

JSON_PATH = ROOT / "entry/src/main/resources/rawfile/levels.json"
LOCKED_DIR = ROOT / "boards-locked"

# Optional mechanism keys on released levels (PM: only boards that have the
# mechanism carry the key). `parity` is inferred from a non-empty parityEdges
# (pre-existing key, x/y camelCase — unchanged).
MECH_KEYS = (
    "ferry",
    "one_ways",
    "slide_cells",
    "seal_gates",
    "token_cells",
    "collapse",
    "burden",
)
MECH_SHORT = {
    "ferry": "ferry",
    "one_ways": "ow",
    "slide_cells": "slide",
    "seal_gates": "seal",
    "token_cells": "token",
    "collapse": "collapse",
    "burden": "burden",
}


def mech_list(level: dict) -> list[str]:
    names = [MECH_SHORT[k] for k in MECH_KEYS if level.get(k)]
    if level.get("parityEdges"):
        names.append("parity")
    return names


def count_ferry_jumps(path: list, jia, yi) -> int:
    """Count consecutive 甲→乙 entries in the archived path (locked [r, c])."""
    n = 0
    for a, b in zip(path, path[1:]):
        if a == jia and b == yi:
            n += 1
    return n


def md_cell(text: str) -> str:
    return str(text).replace("|", "\\|")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay boards-locked paths against shipped levels.json."
    )
    parser.add_argument("--json", default=str(JSON_PATH), help="levels.json path")
    parser.add_argument("--locked-dir", default=str(LOCKED_DIR), help="boards-locked dir")
    parser.add_argument("--table", default=None, help="write the markdown table here too")
    args = parser.parse_args()

    levels_path = Path(args.json)
    locked_dir = Path(args.locked_dir)
    if not levels_path.is_file():
        print(f"error: levels.json not found: {levels_path}", file=sys.stderr)
        return 1

    levels = load_levels(levels_path)
    by_id: dict[int, dict] = {}
    schema_errors: dict[int, str] = {}
    for lv in levels:
        try:
            validate_schema(lv)
        except ValueError as exc:
            schema_errors[int(lv.get("id", -1))] = str(exc)
        by_id[int(lv["id"])] = lv

    rows: list[str] = []
    missing_path: list[str] = []
    missing_level: list[str] = []
    failures = 0
    ferry_checked = 0
    ferry_ok = 0
    mech_count = 0  # boards carrying one of the 7 new mech keys ("33 机制关")
    parity_count = 0
    total = 0

    for ch_idx, fname in enumerate(LOCKED_FILES):
        fpath = locked_dir / fname
        if not fpath.is_file():
            print(f"error: missing locked board file: {fpath}", file=sys.stderr)
            return 1
        data = json.loads(fpath.read_text(encoding="utf-8"))
        for tip_idx, board in enumerate(data["boards"]):
            gid = ch_idx * 10 + tip_idx
            total += 1
            name = board.get("name", "")
            path = board.get("path")
            level = by_id.get(gid)
            if level is None:
                missing_level.append(f"id {gid} ({fname} board {tip_idx})")
                rows.append(
                    f"| {gid} | {gid + 1} | {md_cell(name)} | - | FAIL | "
                    "no such id in levels.json | - |"
                )
                failures += 1
                continue
            if level.get("name"):
                name = level["name"]
            mechs = mech_list(level)
            if any(level.get(k) for k in MECH_KEYS):
                mech_count += 1
            if level.get("parityEdges"):
                parity_count += 1
            mech_col = "/".join(mechs) if mechs else "-"

            if path is None:
                missing_path.append(f"id {gid} ({fname} board {tip_idx})")
                rows.append(
                    f"| {gid} | {gid + 1} | {md_cell(name)} | {mech_col} | FAIL | "
                    "locked board has no 'path' | - |"
                )
                failures += 1
                continue

            if gid in schema_errors:
                rows.append(
                    f"| {gid} | {gid + 1} | {md_cell(name)} | {mech_col} | FAIL | "
                    f"schema: {md_cell(schema_errors[gid])} | - |"
                )
                failures += 1
                continue

            ok, reason, first_bad = check_path(level, path)

            # Ferry assertion on locked fields only: exactly one 甲→乙 jump.
            ferry = board.get("ferry")
            if ferry:
                ferry_checked += 1
                jumps = count_ferry_jumps(path, ferry["jia"], ferry["yi"])
                if jumps != 1:
                    ok = False
                    f_reason = f"ferry jump count={jumps} (want exactly 1 甲→乙)"
                    reason = f"{reason}; {f_reason}" if reason else f_reason
                else:
                    ferry_ok += 1

            status = "ok" if ok else "FAIL"
            if not ok:
                failures += 1
            rows.append(
                f"| {gid} | {gid + 1} | {md_cell(name)} | {mech_col} | {status} | "
                f"{md_cell(reason)} | {first_bad} |"
            )

    header = (
        "| id | 玩家号 | 关名 | 机制 | 状态 | reason | first_bad_index |\n"
        "| ---: | ---: | --- | --- | --- | --- | ---: |"
    )
    table = "\n".join([header, *rows])
    print(table)

    # ---- summary ----
    print()
    print(f"RESULT: total={total} pass={total - failures} fail={failures} "
          f"mech_levels={mech_count} parity_levels={parity_count} "
          f"ferry_checked={ferry_checked} ferry_ok={ferry_ok}")
    if mech_count != 33:
        print(f"FAIL: expected 33 mech levels, got {mech_count}")
    if total != 100:
        print(f"FAIL: expected 100 levels, got {total}")
    if missing_path:
        print("FAIL: locked boards without 'path': " + "; ".join(missing_path))
    if missing_level:
        print("FAIL: locked ids missing from levels.json: " + "; ".join(missing_level))

    if args.table:
        Path(args.table).write_text(table + "\n", encoding="utf-8")
        print(f"table written to {args.table}")

    if failures or total != 100 or missing_path or missing_level or mech_count != 33:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
