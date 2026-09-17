# Board patrol

On an open station board the player draws an orthogonal Hamiltonian path visiting numbered waypoints in order, filling every cell, ending on the highest number.

## Sub-features

- `board-enter` opens a 涿郡 station board with top title and path canvas.
- `board-chrome` shows bottom `撤销` and `重绘驿道` plus the 涿郡 landscape band (`band_zhuojun_v91`, always on levels 0–9; busts are in the band composite).
- `board-clear` (optional heavy) reaches 通关 overlay after a full valid path.

## How to get to it (user POV)

- Home → 章节 → 涿郡 (`涿郡·驿程`) → first station row. Or Home → `开始传书`, which opens the current board directly.
- From 驿程 pick an unlocked station row.

## Driving it with control_yilu

Preconditions:

- Chapter 涿郡 open; doctor passed.

- **Enter board.** Run `python3 tools/verify/control_yilu.py drive board-zhuo`. Fullscreen shows grid + station numbers + bottom chrome.
- **Smoke chrome only.** Do not require a full DFS clear for routine ships. Capture `evidence --label board-zhuo`.
- **Full clear (optional).** Drive cells via `uitest uiInput drag` along a known solution from `tools/solve_levels.py` for id 0. Proof requires 通关 / `文书到` visible. Record as `board-clear` only when overlay is in the JPEG.

## Gotchas

- Do not edit `levels.json` during verification.
- Band / bust sizing regressions need fullscreen board shots, not chapter thumbs alone.
- Simulator density changes Path2D digit size; judge glance readability on fullscreen.
