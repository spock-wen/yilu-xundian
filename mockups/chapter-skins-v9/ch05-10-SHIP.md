# 章皮 v9.1 · Paint B · 后六章 05–10 SHIP

> Lock: `ch05-10-lock-2026-09-06b` · status `locked_for_design` · BOARD_OY_VP=**202** · canvas **1080×1920** (vpScale=3)

## 全屏章皮

| 章 | 文件 | 左/右 | 旗 | 地貌 |
|---|---|---|---|---|
| 05 投袁·邺 | `05-touyuan-v91.png` | P04/P06 | 袁×曹 | 邺下漳水/平原仓邑；乌巢焦褐 |
| 06 荆州·襄阳 | `06-jingzhou-v91.png` | P05/P06 | 刘×曹 | 汉水岸柳；南郡江雾 |
| 07 赤壁·柴桑 | `07-chibi-v91.png` | P08/P06 | 孙×曹 | 长江江岸·江夜墨云·岸火一点 |
| 08 入蜀·白水关 | `08-rushu-v91.png` | P05/S01 | 刘×纹样(无姓字) | 峡江+栈道山；关城嵌山 |
| 09 汉中南中·阳平关 | `09-hanzhong-v91.png` | P09/P06 | 诸葛×曹 | 秦岭冷石 / 滇池苔绿双调 |
| 10 北伐·五丈原 | `10-beifa-v91.png` | P09/P10 | 诸葛×司马 | 渭北黄土·五丈原空仓 |

## 新资产

| 文件 | 说明 |
|---|---|
| `assets/flag-gate-pattern.png` | 08 右旗：关城门洞 + 栈道木纹；**零汉字**；禁 `flag-s01-guan.png` |

## 色票（tokens / 十章色表）

| 章 | paper | shade | qing | qing-deep | ink |
|---|---|---|---|---|---|
| 05 | `#E8E4DC` | `#D4CFC4` | `#6B6A62` | `#3E3D38` | `#2A2824` |
| 06 | `#E8EDE8` | `#D2DDD4` | `#6A8A72` | `#3A5544` | `#2A2E2A` |
| 07 | `#E2E4EA` | `#C8CCD8` | `#4A5A6E` | `#2A3548` | `#1E2228` |
| 08 | `#E6E8E2` | `#D0D6C8` | `#4A6B58` | `#2F4A3A` | `#2A2C28` |
| 09 | `#E4E8E6` | `#CED8D4` | `#5A6E78` | `#2F4540` | `#252A28` |
| 10 | `#EDE6D8` | `#DDD0BC` | `#7A8480` | `#4A5250` | `#2C2A26` |

## 布局硬门禁（同 v9.1）

- BOARD_OY_VP = 202；BUST 52×70 vp；FLAG 28×36 vp；BOARD_CLEAR = 10 vp
- band.bottom ≤ board.top − BOARD_CLEAR；半身/旗/地貌不侵网格
- 半身不压旗面字；08 右旗无「关」字（不读成关羽）
- 复姓写全：诸葛 / 司马

## 对照 / 卡

- 对照：`00-ch5-10-v91-compare.png`
- 章卡（灰锁）：`card-05-touyuan-v91.png`, `card-06-jingzhou-v91.png`, `card-07-chibi-v91.png`, `card-08-rushu-v91.png`, `card-09-hanzhong-v91.png`, `card-10-beifa-v91.png`

## 脚本

- `/workspace/yilu-xundian/render_chapter_skins_v91_ch05_10.py`

## 禁止

- 使用 `flag-s01-guan.png` / 旗面写「关」
- 发明关卡盘 / 改前四盘
- 复姓缩字；入蜀右挂曹脸

## 复审补交（2026-09-07）

- 对照 P0 已修：`00-ch5-10-v91-compare.png` 现为拟合 2×3，**05–10 六章完整入画**（07/08 不再裁底，09/10 不再飞出）。
- 脚本：`render_chapter_skins_v91_ch05_10.py` → `render_compare` 按剩余高度算 `cell_h`，断言六格底边在画布内。
- 全屏/灰锁卡未改；仍禁 `flag-s01-guan.png`。
