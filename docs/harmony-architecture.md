# 架构与工程形状（鸿蒙侧）

> 从根 README 迁出（2026-11-16 整理）。内容未改，仅路径随目录整理更新。

## 引擎 vs 占位

| 层 | 路径 | 职责 |
| --- | --- | --- |
| 可复用网格引擎 | `entry/src/main/cangjie/engine/` | 格子、墙、触摸落格、撤销栈、路径。无 Canvas、无本关规则。 |
| 本游戏规则 | `entry/src/main/cangjie/game/` | 升序驿站 + 填满网格 + 终点最高号。 |
| 关卡数据 | `levels.json` + `levels.cj` | 同一套锁定 100 关（10 章：涿郡…北伐，ids 0..99）。 |
| 设计师皮肤 | `theme.cj` + Canvas 描线 | 手稿 token：纸底、已访底、墨环、青填已过、金发丝下一驿、朱印。 |

引擎可以在没有 Canvas 的情况下被推理 / 用 Python 镜像单测（`tools/test_rules.py`）。仓颉侧目前没有在本机跑 `cjpm test`（无 `cjc`）。


## 工程形状（官方 Empty Ability）

对照 [docs_cangjie 第一个仓颉应用](https://gitcode.com/openharmony/docs_cangjie/blob/master/zh-cn/application-dev/cj-start/start/quick-start/cj-quick-start-first-cangjie-app.md) 的目录（无 `ets/`）：

```text
entry/
├── cjpm.toml                          # name = ohos_app_cangjie_entry
├── build-profile.json5                # cangjieOptions.path = "./cjpm.toml"
└── src/main/
    ├── module.json5
    └── cangjie/
        ├── ability_stage.cj
        ├── index.cj
        ├── main_ability.cj
        ├── theme.cj                   # 本仓库附加：皮肤
        ├── levels.cj                  # 本仓库附加：关卡字面量
        ├── engine/                    # 本仓库附加：无 UI 网格引擎
        └── game/                      # 本仓库附加：Zip 规则薄层
```

`cjpm.toml` 的 `src-dir = "./src/main/cangjie"`，`cjc-version = "1.1.3"`。

