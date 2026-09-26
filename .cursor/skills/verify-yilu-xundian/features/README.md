# 驿路巡点 verification map

Maintained source for verifying user-facing behavior of `com.yilu.xundian`. Read this index, then the matching feature file.

## Baseline preconditions

- `hdc` target reachable (`YILU_HDC_TARGET`, default `127.0.0.1:5555`).
- Bundle `com.yilu.xundian` installed with `EntryAbility`.
- Repo root checkout with `tools/test_rules.py` green (unless documented skip).
- Run `python3 tools/verify/control_yilu.py doctor` before the first drive.
- One agent owns the target for the whole pass (shared touch session).

## Driving conventions

- Start from cold launch or Home unless a recipe says otherwise.
- Prefer `uitest dumpLayout` text matches (`开始传书`, `章节`, `撤销`, `重绘驿道`, `涿郡`, `涿郡·涿`, `未开`, `当前`) over raw coordinates.
- Do not search the needle `可入`. On the chapter list the subtitle is `选章入驿 · 开章可入 · 灰章未启` (`entry/src/main/cangjie/index.cj`), and that node is the first dumpLayout hit — before the card badge. In `_ship/verify-proof/20260916T092315Z/chapter-list.layout.json` the hit is the header `[70,339][1250,388]`, not the `可入` badge.
- Do not search the needle `驿程` on that screen. The footer `已开 1 · 未启 9 · 点开章入驿程` contains `驿程` and matches first (`[70,2681][1250,2730]` in the same dump). Home’s muted `驿程` link is a different screen (global station list).
- Station rows (涿郡·驿程) use `当前` / `已通` / `锁` and the level name (`涿郡·涿`). `可入` / `未开` are chapter-card badges only. `未开` itself is a safe read: on a fresh list the first node is 平原’s badge.
- Treat every `control_yilu.py` invocation as literal.
- After each drive, keep live evidence under `artifacts/verify/<run-id>/` (gitignored JPEG + layout).
- Review-gate copies live under `_ship/verify-proof/<run-id>/` with `PROOF.md`.

## Proof and skip reporting

- UI proof needs a fullscreen JPEG with readable chrome (title or bottom bar visible).
- Pair JPEG with layout dump when claiming a control was tapped.
- Report unreachable paths with the unmet precondition (e.g. 平原 locked while `cleared < 10`).
- Do not claim board clear unless the 通关 overlay is in evidence (full clear is slow; smoke may stop at board chrome).

## Feature entry contract

Each feature file uses H1, one summary paragraph, then exactly four H2s: `Sub-features`, `How to get to it (user POV)`, `Driving it with control_yilu`, `Gotchas`.

## Features

- [Home start](./home-start.md) covers Home and `开始传书`.
- [Chapter flow](./chapter-flow.md) covers Home → 章节 list and open/locked cards.
- [Board patrol](./board-patrol.md) covers entering a 涿郡 station board and path chrome.
- [Undo and redraw](./undo-redraw.md) covers bottom-bar 撤销 / 重绘驿道.
- [Progress lock](./progress-lock.md) covers 平原 grey-lock until 涿郡 cleared.
