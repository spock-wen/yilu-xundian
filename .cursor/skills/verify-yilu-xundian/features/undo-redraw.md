# Undo and redraw

Bottom bar offers `撤销` (undo last segment) and `重绘驿道` (clear path / redraw). Icons are stroke Path/SVG, not tofu blocks.

## Sub-features

- `undo-tap` activates 撤销 while a path exists or is empty-safe.
- `redraw-tap` activates 重绘驿道 and clears the path state.
- `icon-legible` proves controls are recognizable at 24vp on fullscreen.

## How to get to it (user POV)

- Enter any open board, then use the bottom bar.

## Driving it with control_yilu

Preconditions:

- On a board screen (`drive board-zhuo` first).

- **Tap chrome.** Run `python3 tools/verify/control_yilu.py drive undo-redraw`. Text match is preferred. If `撤销` or `重绘驿道` is missing from the dump, the drive still taps the measured centers from `docs/verify-proof/20260916T092315Z/home-start.layout.json` and returns 0: `撤销` `[355,2599][467,2665]` → (411, 2632), `重绘驿道` `[910,2599][1134,2665]` → (1022, 2632), root `[0,0][1320,2856]`. A missing text node on this drive is not a non-zero exit. Layout dump before/after still shows the board; no crash. If the root bounds change, ignore those pixels and re-dump.
- **Evidence.** `evidence --label undo-redraw` with bottom bar in frame.

## Gotchas

- Empty-path undo must not crash; absence of a toast is OK.
- Icon regressions are visual; fullscreen JPEG proof is mandatory for icon ships.
