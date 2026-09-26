#!/usr/bin/env python3
"""Lock the iOS v1 board to levels.json id 1 and keep ohos imports out of ios/shared."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEVELS = ROOT / "entry/src/main/resources/rawfile/levels.json"
COPIES = (
    ROOT / "ios/shared/levels/zhuojun-fanyang.json",
    ROOT / "ios/app/YiluXundian/level.json",
)
SHARED = ROOT / "ios/shared"


def main() -> int:
    levels = json.loads(LEVELS.read_text(encoding="utf-8"))
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
    print("ok ios/shared has no ohos/ArkUI imports")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
