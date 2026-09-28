# Board patrol

On an open station board the player draws an orthogonal Hamiltonian path visiting numbered waypoints in order, filling every cell, ending on the highest number.

## Sub-features

- `board-enter` opens a 涿郡 station board with top title and path canvas.
- `board-chrome` shows bottom `撤销` and `重绘驿道` plus the 涿郡 landscape band (`band_zhuojun_v91`, always on levels 0–9; busts are in the band composite). Parity boards also show top-bar `第 N 步` (`stepChipLabel`); boards with `stepLimit > 0` show `余步 · N`. Neither chip is a tap target for smoke drives.
- `board-clear` (optional heavy) reaches 通关 overlay after a full valid path.

## How to get to it (user POV)

- Home → 章节 → 涿郡 (`涿郡·驿程`) → first station row. Or Home → `开始传书`, which opens the current board directly.
- From 驿程 pick an unlocked station row.

## Driving it with control_yilu

Preconditions:

- Chapter 涿郡 open; doctor passed.

- **Enter board.** Run `python3 tools/verify/control_yilu.py drive board-zhuo` (chapter card `涿郡`, then station row `涿郡·涿`). Fullscreen shows grid + station numbers + bottom chrome. The drive fails if either text is missing; it does not tap `可入` or `驿程`.
- **Smoke chrome only.** Do not require a full DFS clear for routine ships. Capture `evidence --label board-zhuo`.
- **Full clear (optional).** Drive cells via `uitest uiInput drag` along a known solution from `tools/solve_levels.py` for id 0. Proof requires overlay chrome visible: `通关` and `驿道已通` (also `文书递达本驿`). The vermillion seal is three separate Text nodes (`文` / `书` / `到`), not one `文书到` string — do not dumpLayout-needle `文书到`. Record as `board-clear` only when that overlay is in the JPEG.

## Gotchas

- Do not edit `levels.json` during verification.
- Band / bust sizing regressions need fullscreen board shots, not chapter thumbs alone.
- Simulator density changes Path2D digit size; judge glance readability on fullscreen.
- Top-bar `第 N 步` / `余步 · N` (parity-step-v1) are read-only chrome. Do not dumpLayout-needle them for taps; prefer station title + `撤销` / `重绘驿道`.
