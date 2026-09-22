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

- **Tap chrome.** Run `python3 tools/verify/control_yilu.py drive undo-redraw`. The drive returns non-zero if `撤销` or `重绘驿道` is missing from the dump. Layout dump before/after still shows the board; no crash.
- **Evidence.** `evidence --label undo-redraw` with bottom bar in frame.

## Gotchas

- Empty-path undo must not crash; absence of a toast is OK.
- Icon regressions are visual; fullscreen JPEG proof is mandatory for icon ships.
