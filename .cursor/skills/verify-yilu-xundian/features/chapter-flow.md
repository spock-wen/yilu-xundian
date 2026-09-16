# Chapter flow

Chapter list (v1.3) lets the player pick 涿郡 / 平原 when open, see grey-locked later chapters, and open skin preview for locked skinned chapters without inventing boards.

## Sub-features

- `chapter-open-list` opens the 章节 scroll from Home.
- `chapter-zhuo-enter` enters 涿郡 when marked `可入`.
- `chapter-locked-card` shows `未开` (or grey card) for locked chapters without entering a fake board.

## How to get to it (user POV)

- From Home choose the 章节 / 驿程 entry the build exposes (shipped UI uses chapter navigation from Home chrome).
- Run `drive chapter-list` which taps the documented Home secondary control then asserts list chrome.

## Driving it with control_yilu

Preconditions:

- Doctor passed; prefer cold launch.
- For 涿郡 enter: chapter 涿郡 must be open (default for fresh install).

- **Open list.** Run `python3 tools/verify/control_yilu.py drive chapter-list`. Screenshot/list dump shows chapter titles such as `涿郡` and locked later chapters.
- **Enter 涿郡.** Run `python3 tools/verify/control_yilu.py drive board-zhuo` only after list is open (or use the combined path the script documents). 驿程 or board for 涿郡 appears.
- **Evidence.** `evidence --label chapter-list` with at least two chapter rows visible.

## Gotchas

- 徐州 / 吕布 / 05–10 may show skin cards but `levelCount` 0. Do not claim a playable board there.
- 平原 may be `未开` until progress lock is satisfied. That is expected; see progress-lock.md.
