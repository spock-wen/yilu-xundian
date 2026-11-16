#!/usr/bin/env python3
"""Lock the shared v1 board to levels.json id 1 and keep ohos imports out of engine/shared.

Checks, in order:
  1. engine/shared/levels/levels.json is byte-identical to entry levels.json;
  2. 100 levels with ids 0..99;
  3. id 1 (涿郡·范阳) pure-Zip shape + copies (engine/ios/android) match id 1;
  4. no ohos/ArkUI imports under engine/shared;
  5. solver gate (default ON):
       - `tools/solve_levels.py --limit 2 --timeout 60` (cwd=ROOT). Exit codes:
         0 pass / 1 UNSOLVABLE (a level proven unsolvable -> fail) /
         2 data error -> fail / 3 TIMEOUT, unverified -> NOT a pass -> fail.
       - `tools/replay_locked_paths.py`; any non-zero exit -> fail.
     Skip with `--skip-solve` argv flag or SKIP_SOLVE=1 env var (prints a
     loud "SKIPPED solver gate" warning; skipping is for fast local runs only).
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# Meaning of tools/solve_levels.py strict-gate exit codes.
SOLVE_EXIT_MEANING = {
    1: "1 UNSOLVABLE (有不可解关)",
    2: "2 数据错误 (data error)",
    3: "3 TIMEOUT 未验证 (timeout, unverified — not a pass)",
}

ROOT = Path(__file__).resolve().parents[2]
LEVELS = ROOT / "entry/src/main/resources/rawfile/levels.json"
COPIES = (
    ROOT / "engine/shared/levels/zhuojun-fanyang.json",
    ROOT / "ios/app/YiluXundian/level.json",
    ROOT / "android/app/src/main/assets/level.json",
)
SHARED_LEVELS = ROOT / "engine/shared/levels/levels.json"
SHARED = ROOT / "engine/shared"


def solver_gate() -> int:
    """Run solve_levels.py then replay_locked_paths.py. 0 = pass."""
    print("gate: tools/solve_levels.py --limit 2 --timeout 60")
    proc = subprocess.run(
        [sys.executable, "tools/solve_levels.py", "--limit", "2", "--timeout", "60"],
        cwd=ROOT,
    )
    if proc.returncode != 0:
        meaning = SOLVE_EXIT_MEANING.get(proc.returncode, "unknown exit code")
        print(
            f"FAIL: solver gate exit {meaning} — TIMEOUT 未验证不算通过, "
            f"UNSOLVABLE/数据错误不许发布",
            file=sys.stderr,
        )
        return 1
    print("ok solve_levels.py (all 100 levels solved within timeout)")

    print("gate: tools/replay_locked_paths.py")
    proc = subprocess.run([sys.executable, "tools/replay_locked_paths.py"], cwd=ROOT)
    if proc.returncode != 0:
        print(f"FAIL: replay_locked_paths.py exit {proc.returncode}", file=sys.stderr)
        return 1
    print("ok replay_locked_paths.py")
    return 0


def main() -> int:
    skip_solve = "--skip-solve" in sys.argv[1:] or os.environ.get("SKIP_SOLVE", "") not in ("", "0")
    if not SHARED_LEVELS.exists():
        print(f"FAIL: {SHARED_LEVELS.relative_to(ROOT)} does not exist", file=sys.stderr)
        return 1
    if SHARED_LEVELS.read_bytes() != LEVELS.read_bytes():
        print(f"FAIL: {SHARED_LEVELS.relative_to(ROOT)} is not byte-identical to {LEVELS.relative_to(ROOT)}", file=sys.stderr)
        return 1
    print(f"ok {SHARED_LEVELS.relative_to(ROOT)} is byte-identical to {LEVELS.relative_to(ROOT)}")

    levels = json.loads(LEVELS.read_text(encoding="utf-8"))
    if len(levels) != 100:
        print(f"FAIL: levels.json contains {len(levels)} levels, expected 100", file=sys.stderr)
        return 1
    if [lv.get("id") for lv in levels] != list(range(100)):
        print("FAIL: levels.json level ids are not 0..99", file=sys.stderr)
        return 1
    print("ok levels.json contains 100 levels with ids 0..99")

    want = levels[1]
    if want.get("id") != 1 or want.get("name") != "涿郡·范阳":
        print("FAIL: levels.json[1] is not 涿郡·范阳", file=sys.stderr)
        return 1
    if want.get("parityEdges") != [] or want.get("stepLimit") != 0:
        print("FAIL: id 1 is no longer a pure Zip board", file=sys.stderr)
        return 1
    if want.get("cols") != 6 or want.get("rows") != 6 or len(want.get("walls", [])) != 2:
        print("FAIL: id 1 shape changed", file=sys.stderr)
        return 1
    for path in COPIES:
        got = json.loads(path.read_text(encoding="utf-8"))
        if got != want:
            print(f"FAIL: {path.relative_to(ROOT)} != levels.json id 1", file=sys.stderr)
            return 1
        print(f"ok {path.relative_to(ROOT)} == levels.json id 1 ({want['name']})")
    banned = ("ohos_app_cangjie_entry", "kit.ArkUI", "import ohos.")
    for path in SHARED.rglob("*.cj"):
        text = path.read_text(encoding="utf-8")
        for token in banned:
            if token in text:
                print(f"FAIL: {path.relative_to(ROOT)} contains {token}", file=sys.stderr)
                return 1
    print("ok engine/shared has no ohos/ArkUI imports")

    if skip_solve:
        print("=" * 64)
        print("!! WARNING: SKIPPED solver gate (--skip-solve / SKIP_SOLVE set)")
        print("!! WARNING: SKIPPED solver gate — run it before shipping!")
        print("=" * 64)
    elif solver_gate() != 0:
        print("FAIL: solver gate", file=sys.stderr)
        return 1
    print("PASS: check_level")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
