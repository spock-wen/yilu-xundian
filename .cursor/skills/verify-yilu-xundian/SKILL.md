---
name: verify-yilu-xundian
description: "Drive and prove 驿路巡点 (com.yilu.xundian) on a HarmonyOS phone/emulator via hdc. Use when verifying UI flows, shipping a HAP, or before review that requires fullscreen screenshot evidence."
---

# Verify 驿路巡点

Agent-facing control skill for the Cangjie HarmonyOS Zip-patrol game. Surface is the installed HAP UI on a device or emulator reached by `hdc`. Rules-layer Python tests are a doctor gate, not a substitute for UI proof.

**Principles used when generating this skill:** Build the Lever (rerunnable `tools/verify/control_yilu.py`), Prove It Works (fullscreen screenshot + layout dump after a real user path).

## Launch

Preconditions:

- DevEco / hdc on PATH (Mac checkout is usually `~/orca/yilu-xundian`).
- Target up: default `127.0.0.1:5555` (override with `YILU_HDC_TARGET`).
- Package `com.yilu.xundian` installed (ability `EntryAbility`).

Start (or foreground) the app:

```bash
python3 tools/verify/control_yilu.py launch
```

Ready when `doctor` reports the ability process and a fresh screenshot can be taken. There is no long-lived server: each drive uses the shared device session. Do not double-drive the same target from two agents at once (shared touch focus).

Teardown: `python3 tools/verify/control_yilu.py cleanup` (force-stops the ability only; leaves evidence).

## Doctor

```bash
python3 tools/verify/control_yilu.py doctor
```

Checks (read-only):

1. `hdc -t "$YILU_HDC_TARGET" list targets` contains the target.
2. `bm dump -n com.yilu.xundian` (or `hdc shell bm dump`) shows the bundle.
3. From repo root, `python3 tools/test_rules.py` exit 0 (rules + catalog lock). Skip only if `YILU_SKIP_RULES=1` and document why.
4. Optional: HAP mtime / git `HEAD` short SHA printed for the proof log.

If doctor fails, fix the environment before Drive.

## Drive

Harness: `tools/verify/control_yilu.py`. Prefer text/bounds from `uitest dumpLayout` over hard-coded coordinates. Coordinates in feature recipes are fallbacks for the 1080×2340-class emulator used in prior ships; re-dump if layout drifts.

```bash
# Home → 开始传书 → current board (fresh install: 涿郡·涿)
python3 tools/verify/control_yilu.py drive home-start

# Home → 章节 (chapter list)
python3 tools/verify/control_yilu.py drive chapter-list

# 章节 → 涿郡·驿程 → first station board (when 可入)
python3 tools/verify/control_yilu.py drive board-zhuo

# On board: tap 撤销 / 重绘驿道 chrome (does not claim a full clear)
python3 tools/verify/control_yilu.py drive undo-redraw
```

Read `.cursor/skills/verify-yilu-xundian/features/` before a non-smoke run. A proof that only opens Home is incomplete when the map lists board and lock paths.

## Evidence

Live directory (survives cleanup, gitignored): `artifacts/verify/<run-id>/`

hdc `snapshot_display` writes **JPEG** (`<label>.jpeg`), not PNG. Pair with `<label>.layout.json` when claiming a tap.

For a review gate, copy that run folder to `_ship/verify-proof/<run-id>/` (see the tracked `PROOF.md` there). Do not treat `artifacts/verify/` as the committed proof — it is ignored.

Required for review gate:

- Fullscreen JPEG via `snapshot_display` (not a cropped window).
- Optional: `uitest dumpLayout` JSON beside the JPEG.
- `PROOF.md` naming feature ID, commands, target, git SHA, and what the screenshot shows.

```bash
python3 tools/verify/control_yilu.py evidence --label home-start
```

Proof standards:

- Exercise the real taps a player uses (`开始传书`, chapter cards, board chrome). Do not set internal `cleared` via debug APIs (none ship).
- Capture action + resulting state (e.g. Home tap then chapter or board screen), not only the final frame if intermediate state matters.
- Rules tests prove catalog/engine; they do not replace fullscreen UI evidence for visual ships.

## Cleanup

```bash
python3 tools/verify/control_yilu.py cleanup
```

Force-stops `com.yilu.xundian`. Does not delete `artifacts/verify/`. Does not uninstall the HAP.

## Helpers

| Command | Role |
| --- | --- |
| `python3 tools/verify/control_yilu.py doctor` | Health gate |
| `python3 tools/verify/control_yilu.py launch` | Start EntryAbility |
| `python3 tools/verify/control_yilu.py drive <feature>` | Drive one mapped path |
| `python3 tools/verify/control_yilu.py evidence --label <id>` | Screenshot + layout dump |
| `python3 tools/verify/control_yilu.py proof-home` | doctor → launch → home-start → evidence → cleanup |
| `python3 tools/verify/control_yilu.py cleanup` | Stop ability |

Env:

- `YILU_HDC_TARGET` (default `127.0.0.1:5555`)
- `YILU_BUNDLE` (default `com.yilu.xundian`)
- `YILU_ABILITY` (default `EntryAbility`)
- `YILU_ARTIFACTS` (default `artifacts/verify`)
- `YILU_SKIP_RULES=1` (doctor skips `test_rules.py`)

## Maintain

When UI copy, chapter flow, or hdc recipes drift, run `/maintain-verification-skill` against this skill only (edit `.cursor/skills/verify-yilu-xundian/` and `tools/verify/`). Do not change product code or `levels.json` in a maintain pass.
