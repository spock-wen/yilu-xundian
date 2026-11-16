# 棋盘地貌带 BANDS (v9.1)

Shippable cut assets for **涿郡** + **平原**. Layout locked to `render_chapter_skins_v9.py`.

## Canvas

| token | value |
|---|---|
| vpScale / SCALE | **3** |
| canvas | **1080×1920** px |
| `BOARD_OY_VP` | **202** |
| `TOPBAR_Y0` | 66 px = 22 vp |
| `TOPBAR_H` | 168 px = 56 vp |
| `TOPBAR_BOT` | **234** px = **78** vp |
| `BOARD_CLEAR` | **30** px = **10** vp |
| `EDGE_MARGIN` | 36 px = 12 vp |
| `BUST_W` × `BUST_H` | 156×210 px = 52×70 vp |
| `FLAG_W` × `FLAG_H` | 84×108 px = 28×36 vp |
| `PORTRAIT_GAP` | 18 px = 6 vp |

## Board geometry (`board_geometry`)

```
oy = vp(BOARD_OY_VP) = 606
frame_pad = 30
board = [ox−pad, oy−pad, ox+gw+pad, oy+gh+pad]
board (px) = [102, 576, 978, 1452]
board (vp) = [34.0, 192.0, 326.0, 484.0]
board.top (px) = 576
```

## Band rect (`top_band_rect`)

```
band = [0, TOPBAR_BOT + vp(4), W, board[1] − BOARD_CLEAR]
band (px) = [0, 246, 1080, 546]   # [x0,y0,x1,y1]
band (vp) = [0.0, 82.0, 360.0, 182.0]
band size = 1080 × 300 px = 360 × 100 vp
```

**band height = 300 px = 100 vp**

## Hard rule (never overlap grid)

```
band.bottom ≤ board.top − BOARD_CLEAR
546 ≤ 576 − 30
546 ≤ 546   ✓ (equality by construction)
```

Coder: place band strip at `(0, 246)` with height `300`. Do **not** extend into `[board.top − CLEAR, …]` or the grid.

## Portrait blocks (`place_portrait_block`)

Same for both chapters (geometry only; assets differ).

### Left

| | px | vp |
|---|---|---|
| block | [36, 258, 294, 468] | [12.0, 86.0, 98.0, 156.0] |
| bust xy | (36, 258) | (12.0, 86.0) |
| flag xy | (210, 282) | (70.0, 94.0) |
| flag_side | `right` (pole toward center) | |

### Right

| | px | vp |
|---|---|---|
| block | [786, 258, 1044, 468] | [262.0, 86.0, 348.0, 156.0] |
| bust xy | (888, 258) | (296.0, 86.0) |
| flag xy | (786, 282) | (262.0, 94.0) |
| flag_side | `left` | |

Positions are **absolute on the 1080×1920 canvas**. Relative to band strip origin `(0, 246)`:

- left bust local y = 12
- left flag local y = 36

### Chapter mounts

| chapter | L bust/flag | R bust/flag | terrain | silhouette |
|---|---|---|---|---|
| 涿郡 `zhuojun` | P01 仓官 / 汉 | P02 渠帅 / 黄 | loess 黄土岗阜 | city_gate 安喜城影 |
| 平原 `pingyuan` | P03 公孙 / 公孙 | P04 袁绍 / 袁 | wheat 麦原 | tile_roof 郡治瓦脊 |

## Layer order (coder)

1. **terrain** (`band-terrain-*.png`) — bottom; 岗阜/麦原 + 城影 silhouette already baked into terrain export
2. *(optional split)* if separating silhouette later, keep it above terrain fills
3. **bust + flag** — top (`band-composite-*.png` already includes all three)

`band-terrain-*.png` = transparent RGBA, **no** bust/flag.  
`band-composite-*.png` = paper + terrain + silhouette + bust + flags (mock-faithful).

## Files

| file | content |
|---|---|
| `band-terrain-zhuojun.png` | 1080×300 RGBA transparent; loess + 城影 |
| `band-terrain-pingyuan.png` | 1080×300 RGBA transparent; wheat + 瓦脊 |
| `band-composite-zhuojun.png` | 1080×300 RGB(A) paper composite |
| `band-composite-pingyuan.png` | 1080×300 RGB(A) paper composite |
| `band-layout-annotated.png` | 涿郡 full-vp guide (band / clear / bust / flag / layers) |
| `band-layout-annotated-pingyuan.png` | 平原 full-vp guide |
| `export_bands.py` | regenerator (repo root) |

## Regenerate

```bash
cd /workspace/yilu-xundian && .venv/bin/python export_bands.py
```
