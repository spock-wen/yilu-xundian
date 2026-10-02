#!/usr/bin/env python3
"""Rerunnable hdc harness for 驿路巡点 (com.yilu.xundian).

Build the lever: agents re-run this instead of ad-hoc hdc one-liners.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = os.environ.get("YILU_BUNDLE", "com.yilu.xundian")
ABILITY = os.environ.get("YILU_ABILITY", "EntryAbility")
TARGET = os.environ.get("YILU_HDC_TARGET", "127.0.0.1:5555")
ART_ROOT = Path(os.environ.get("YILU_ARTIFACTS", str(ROOT / "artifacts" / "verify")))


def hdc(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    cmd = ["hdc", "-t", TARGET, *args]
    try:
        return subprocess.run(cmd, text=True, capture_output=True, check=check)
    except FileNotFoundError as exc:
        # Cloud VMs often have no DevEco hdc. Exit 1; do not look like a pass.
        sys.stdout.flush()
        print(f"FAIL: hdc not on PATH ({exc.filename})", file=sys.stderr)
        raise SystemExit(1)


def hdc_shell(script: str, check: bool = True) -> subprocess.CompletedProcess:
    return hdc("shell", script, check=check)


def run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def art_dir(label: str | None = None) -> Path:
    rid = os.environ.get("YILU_RUN_ID") or run_id()
    os.environ["YILU_RUN_ID"] = rid
    d = ART_ROOT / rid
    d.mkdir(parents=True, exist_ok=True)
    if label:
        (d / "labels").mkdir(exist_ok=True)
    return d


def git_sha() -> str:
    try:
        p = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        return p.stdout.strip()
    except Exception:
        return "unknown"


def cmd_doctor(_: argparse.Namespace) -> int:
    print(f"target={TARGET} bundle={BUNDLE} sha={git_sha()}")
    listed = hdc("list", "targets", check=False)
    blob = (listed.stdout or "") + (listed.stderr or "")
    print(listed.stdout or listed.stderr)
    # hdc may print bare IP or IP:port. Absent target is a fail
    # (do not pass just because the output lacks the word "Empty").
    host = TARGET.split(":")[0]
    if TARGET not in blob and host not in blob:
        print("doctor FAIL: target not in hdc list targets", file=sys.stderr)
        return 1
    dump = hdc_shell(f"bm dump -n {BUNDLE}", check=False)
    if dump.returncode != 0 or BUNDLE not in (dump.stdout or ""):
        # older images use different bm flags; try aa dump
        dump2 = hdc_shell(f"bm dump -a | grep {BUNDLE}", check=False)
        if BUNDLE not in (dump.stdout or "") + (dump2.stdout or ""):
            print("doctor FAIL: bundle not installed", file=sys.stderr)
            print(dump.stdout, dump.stderr)
            return 1
    print("bundle: ok")
    if os.environ.get("YILU_SKIP_RULES") == "1":
        print("rules: skipped (YILU_SKIP_RULES=1)")
    else:
        rules = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "test_rules.py")],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        if rules.returncode != 0:
            print(rules.stdout[-2000:] if rules.stdout else "")
            print(rules.stderr[-2000:] if rules.stderr else "", file=sys.stderr)
            print("doctor FAIL: tools/test_rules.py", file=sys.stderr)
            return 1
        print("rules: ok")
    print("doctor PASS")
    return 0


def cmd_launch(_: argparse.Namespace) -> int:
    hdc_shell(f"aa force-stop {BUNDLE}", check=False)
    time.sleep(0.4)
    r = hdc_shell(f"aa start -a {ABILITY} -b {BUNDLE}", check=False)
    print(r.stdout or r.stderr)
    # Cold start on emulator often lands dumpLayout on the launcher icon grid
    # if we probe too early (seen 2026-09-28: texts were demo labels + 驿路巡点 icon).
    time.sleep(2.5)
    return 0 if r.returncode == 0 else r.returncode


def cmd_cleanup(_: argparse.Namespace) -> int:
    r = hdc_shell(f"aa force-stop {BUNDLE}", check=False)
    print(r.stdout or r.stderr or "stopped")
    print(f"evidence kept under {ART_ROOT}")
    return 0


def dump_layout(path: Path) -> Path:
    remote = "/data/local/tmp/yilu_verify_layout.json"
    hdc_shell(f"uitest dumpLayout -p {remote}", check=False)
    local = path
    hdc("file", "recv", remote, str(local), check=False)
    return local


def find_text_center(layout_path: Path, needle: str) -> tuple[int, int] | None:
    if not layout_path.exists():
        return None
    try:
        raw = layout_path.read_text(encoding="utf-8", errors="replace")
        data = json.loads(raw)
    except Exception:
        return None

    def walk(node):
        if isinstance(node, dict):
            text = str(node.get("text") or node.get("description") or "")
            if needle in text:
                b = node.get("bounds") or node.get("bound") or ""
                # bounds like [x1,y1][x2,y2] or dict
                if isinstance(b, dict):
                    x1, y1, x2, y2 = b.get("left"), b.get("top"), b.get("right"), b.get("bottom")
                    if None not in (x1, y1, x2, y2):
                        return (int((x1 + x2) / 2), int((y1 + y2) / 2))
                if isinstance(b, str) and "][" in b:
                    a, c = b.split("][")
                    x1, y1 = a.strip("[]").split(",")
                    x2, y2 = c.strip("[]").split(",")
                    return (int((int(x1) + int(x2)) / 2), int((int(y1) + int(y2)) / 2))
            for v in node.values():
                hit = walk(v)
                if hit:
                    return hit
        elif isinstance(node, list):
            for it in node:
                hit = walk(it)
                if hit:
                    return hit
        return None

    return walk(data)


def tap(x: int, y: int) -> None:
    hdc_shell(f"uitest uiInput click {x} {y}", check=False)
    time.sleep(0.6)


def tap_text(needle: str, fallback: tuple[int, int] | None = None) -> bool:
    d = art_dir()
    layout = dump_layout(d / f"layout-before-{needle}.json")
    pt = find_text_center(layout, needle)
    if pt is None and fallback:
        pt = fallback
        print(f"tap fallback for {needle!r} -> {pt}")
    if pt is None:
        print(f"FAIL: no bounds for {needle!r}", file=sys.stderr)
        return False
    print(f"tap {needle!r} at {pt}")
    tap(*pt)
    return True


# Last-resort pixels only. Measured text-node centers in
# _ship/verify-proof/20260916T092315Z/home-start.layout.json
# (root bounds [0,0][1320,2856]): 撤销 [355,2599][467,2665],
# 重绘驿道 [910,2599][1134,2665]. Not a 1080-wide assumption.
# Home / chapter taps have no measured fallback in that dump — fail closed.
FB_UNDO = (411, 2632)
FB_REDRAW = (1022, 2632)


def cmd_drive(ns: argparse.Namespace) -> int:
    feat = ns.feature
    if feat == "home-start":
        ok = tap_text("开始传书", None)
        return 0 if ok else 2
    if feat == "chapter-list":
        # 章节 opens screen 4. 驿程 is the global station list (screen 3), not a fallback.
        if not tap_text("章节", None):
            return 2
        time.sleep(0.5)
        d = art_dir()
        dump_layout(d / "layout-chapter-list.json")
        return 0
    if feat == "board-zhuo":
        # Home 章节 → chapter card label 涿郡 (badge text is 可入, but do not
        # search 可入: subtitle 开章可入 is the first hit in
        # _ship/verify-proof/20260916T092315Z/chapter-list.layout.json).
        # Screen 5 title is 涿郡·驿程; needle 涿 matches that title first.
        # Station row name is 涿郡·涿 (badge 当前). Do not search 驿程:
        # chapter-list footer 点开章入驿程 matches first.
        if not tap_text("章节", None):
            return 2
        time.sleep(0.4)
        if not tap_text("涿郡", None):
            return 2
        time.sleep(0.4)
        if not tap_text("涿郡·涿", None):
            return 2
        return 0
    if feat == "undo-redraw":
        if not tap_text("撤销", FB_UNDO):
            return 2
        if not (tap_text("重绘驿道", FB_REDRAW) or tap_text("重绘", FB_REDRAW)):
            return 2
        return 0
    print(f"unknown feature {feat}", file=sys.stderr)
    return 2


def cmd_evidence(ns: argparse.Namespace) -> int:
    d = art_dir(ns.label)
    label = ns.label or "shot"
    remote = f"/data/local/tmp/yilu_verify_{label}.jpeg"
    hdc_shell(f"snapshot_display -f {remote}", check=False)
    local = d / f"{label}.jpeg"
    hdc("file", "recv", remote, str(local), check=False)
    layout = dump_layout(d / f"{label}.layout.json")
    proof = d / "PROOF.md"
    line = (
        f"- feature: `{label}`\n"
        f"- time_utc: {datetime.now(timezone.utc).isoformat()}\n"
        f"- target: `{TARGET}`\n"
        f"- git: `{git_sha()}`\n"
        f"- screenshot: `{local.name}` exists={local.exists()} size={local.stat().st_size if local.exists() else 0}\n"
        f"- layout: `{layout.name}` exists={layout.exists()}\n"
    )
    prev = proof.read_text(encoding="utf-8") if proof.exists() else "# Proof log\n\n"
    proof.write_text(prev + line + "\n", encoding="utf-8")
    print(f"evidence: {local} ({'ok' if local.exists() and local.stat().st_size > 0 else 'MISSING'})")
    return 0 if local.exists() and local.stat().st_size > 0 else 1


def cmd_proof_home(_: argparse.Namespace) -> int:
    os.environ["YILU_RUN_ID"] = run_id()
    steps = [
        ("doctor", cmd_doctor),
        ("launch", cmd_launch),
        ("drive", lambda n: cmd_drive(argparse.Namespace(feature="home-start"))),
        ("evidence", lambda n: cmd_evidence(argparse.Namespace(label="home-start"))),
        ("cleanup", cmd_cleanup),
    ]
    ns = argparse.Namespace()
    for name, fn in steps:
        print(f"== {name} ==")
        rc = fn(ns)
        if rc != 0:
            print(f"proof-home FAIL at {name} rc={rc}", file=sys.stderr)
            cmd_cleanup(ns)
            return rc
    d = ART_ROOT / os.environ["YILU_RUN_ID"]
    shot = d / "home-start.jpeg"
    if not shot.exists() or shot.stat().st_size == 0:
        print("proof-home FAIL: evidence missing after cleanup", file=sys.stderr)
        return 1
    print(f"proof-home PASS evidence={shot}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="control_yilu")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor").set_defaults(func=cmd_doctor)
    sub.add_parser("launch").set_defaults(func=cmd_launch)
    sub.add_parser("cleanup").set_defaults(func=cmd_cleanup)
    d = sub.add_parser("drive")
    d.add_argument("feature", choices=["home-start", "chapter-list", "board-zhuo", "undo-redraw"])
    d.set_defaults(func=cmd_drive)
    e = sub.add_parser("evidence")
    e.add_argument("--label", default="shot")
    e.set_defaults(func=cmd_evidence)
    sub.add_parser("proof-home").set_defaults(func=cmd_proof_home)
    ns = p.parse_args()
    return int(ns.func(ns))


if __name__ == "__main__":
    sys.exit(main())
