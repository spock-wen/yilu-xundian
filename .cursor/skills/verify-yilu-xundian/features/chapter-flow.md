# Chapter flow

Chapter list (v1.3) lets the player pick 涿郡 / 平原 when open, see locked later chapters (`未开`), and open fullscreen skin preview for chapters 05–10 (投袁…北伐) without inventing boards. 徐州 / 吕布 stay card-only (tap is a no-op).

## Sub-features

- `chapter-open-list` opens the 章节 scroll from Home.
- `chapter-zhuo-enter` enters 涿郡 when marked `可入`.
- `chapter-locked-card` shows `未开` (or grey card) for locked chapters without entering a fake board.

## How to get to it (user POV)

- From Home tap the bordered `章节` row (not the muted `驿程` link — that opens the global station list).
- Run `drive chapter-list` which taps `章节` then dumps list chrome.

## Driving it with control_yilu

Preconditions:

- Doctor passed; prefer cold launch.
- For 涿郡 enter: chapter 涿郡 must be open (default for fresh install).

- **Open list.** Run `python3 tools/verify/control_yilu.py drive chapter-list`. Screenshot/list dump shows `章节`, `涿郡` `可入`, and later `未开` cards.
- **Enter 涿郡.** Run `python3 tools/verify/control_yilu.py drive board-zhuo`. It taps `章节`, then the chapter card whose label contains `涿郡` (badge `可入`, screen 4), which lands on `涿郡·驿程` (screen 5). It then taps the station name `涿郡·涿` (row badge `当前`). Station rows do not say `可入`. A needle of `涿` matches the screen title `涿郡·驿程` before the station row.
- **Evidence.** `evidence --label chapter-list` (JPEG + layout) with at least two chapter rows visible.

## Gotchas

- 徐州 / 吕布 have `levelCount` 0 and no fullscreen skin preview (tap stays on the list). Chapters 05–10 show skin cards / preview only. Do not claim a playable board there.
- 平原 may be `未开` until progress lock is satisfied. That is expected; see progress-lock.md.
- Needle `可入` is not the badge. Subtitle `选章入驿 · 开章可入 · 灰章未启` matches first (proof: `chapter-list.layout.json` header, not `[1044,552][1212,650]`). Needle `驿程` matches footer `点开章入驿程` before any `·驿程` title. Enter 涿郡 with `涿郡`, then station `涿郡·涿`.
