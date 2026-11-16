# 设计师 token（勿漂移）

> 从根 README 迁出（2026-11-16 整理）。代码侧真源是 `entry/src/main/cangjie/theme.cj`。


| token | hex | 仓颉 |
| --- | --- | --- |
| paper | `#F3E8D6` | `0XF3E8D6` |
| paper-shade | `#E6D5B8` | `0XE6D5B8` |
| paper-line | `#D4C4A8` | `0XD4C4A8` |
| ink | `#2C2A26` | `0X2C2A26` |
| ink-muted | `#5C574E` | `0X5C574E` |
| qing | `#6B7A78` | `0X6B7A78` |
| qing-deep | `#3D4A47` | `0X3D4A47` |
| path | `#3F4F4C` | `0X3F4F4C` |
| gold | `#C4A35A` | `0XC4A35A`（只作发丝线） |
| vermillion-seal | `#9B3A2F` | `0X9B3A2F`（只作印） |
| locked | `#C9BBA6` | `0XC9BBA6` |
| success-celadon | `#5E7A6A` | `0X5E7A6A` |
| white-paper | `#FBF6EC` | `0XFBF6EC` |

间距（vp）：屏边 20，顶栏 56，底栏 72，教程格 48，驿站直径 40（随格子 `cs/48` 缩放），驿站数字 Path2D 高 24vp（直径 × 0.60，下限 22，同样随 `cs/48` 缩放），路宽 8，主按钮高 52，撤销/重绘 56，底栏图标 24。
