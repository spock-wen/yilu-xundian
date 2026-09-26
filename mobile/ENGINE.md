# 共用 Zip 引擎

鸿蒙模块仍在 `entry/`，包名仍是 `ohos_app_cangjie_entry`。iOS / Android 不改那些文件。无鸿蒙依赖的一份在 `mobile/shared/`，包名 `yilu_zip`。两边壳都调 `mobile/include/yilu_zip.h` 里的 `yilu_*`。

## 抽进 `yilu_zip` 的

| 共用源文件 | 拷贝自 | 包名 |
| --- | --- | --- |
| `mobile/shared/src/engine/cell.cj` | `entry/src/main/cangjie/engine/cell.cj` | `yilu_zip.engine` |
| `mobile/shared/src/engine/wall.cj` | `entry/src/main/cangjie/engine/wall.cj` | `yilu_zip.engine` |
| `mobile/shared/src/engine/grid.cj` | `entry/src/main/cangjie/engine/grid.cj` | `yilu_zip.engine` |
| `mobile/shared/src/engine/undo.cj` | `entry/src/main/cangjie/engine/undo.cj` | `yilu_zip.engine` |
| `mobile/shared/src/engine/path.cj` | `entry/src/main/cangjie/engine/path.cj` | `yilu_zip.engine` |
| `mobile/shared/src/game/level.cj` | `entry/src/main/cangjie/game/level.cj` | `yilu_zip.game` |
| `mobile/shared/src/game/patrol.cj` | `entry/src/main/cangjie/game/patrol.cj` | `yilu_zip.game` |

这 7 个文件在鸿蒙侧没有 `import ohos` / `import kit.ArkUI`。规则仍是正交、不穿墙、不走重复格、驿站按号、最高号必须在填满时进入、拖回上一格撤销。`parityEdges` 的判断留在 `patrol.cj` 里；v1 的范阳盘是空列表。

`stepLimit` 在 `LevelDef` 上。鸿蒙 `PatrolGame` 不读取它，这份也不读。

## 只在共用模块里新增的

| 文件 | 作用 |
| --- | --- |
| `mobile/shared/src/game/json_level.cj` | 读一盘 JSON，建成 `LevelDef`。不用 `stdx`。`String` 按下标取的是 UTF-8 字节（[1.1.3 String](https://cj-docs.gitcode.com/zh/1.1.3/libs/std/core/core_package_api/core_package_structs.html)）。 |
| `mobile/shared/src/ffi.cj` | 顶层 `@C` 函数。命名避免 `CJ_` 前缀（[仓颉-C 互操作](https://cj-docs.gitcode.com/zh/1.1.3/dev-guide/source_zh_cn/FFI/cangjie-c.html)）。 |
| `mobile/include/yilu_zip.h` | 同一份 C 声明。iOS bridging header 引用它；Android `yilu_jni.c` 也引用它。 |

## 壳里没有 Zip 规则

| 壳 | 做什么 |
| --- | --- |
| `ios/app/YiluXundian/*.swift` | 读 bundle 里的 `level.json`，画格子，触摸调用 `yilu_touch_to_cell` / `yilu_try_step`。链接 iOS **静态库**。进第一笔 `yilu_*` 之前由 `CangjieRuntimeBootstrap.c` 调用 `CJ_MRT_CjRuntimeInit`。 |
| `android/app/src/main/java/com/yilu/xundian/*.kt` | 读 assets 里的同一盘 JSON，经 JNI 调同一批符号。加载 Android **动态库** `libyilu_zip.so`。 |

iOS 用已提交的 `cjpm.toml`（`output-type = "static"`）。Android 脚本另写一份 gitignore 的 manifest（`output-type = "dynamic"`），因为同一个 toml 不能同时是静态库和动态库。源码目录仍是这一份 `src/`。

## 留在鸿蒙、没有搬进来的

- `entry/src/main/cangjie/index.cj`、`main_ability.cj`、`ability_stage.cj`、`theme.cj`、`chapter.cj`、`levels.cj`、`resource_helper.cj`
- `import kit.ArkUI.*`、Canvas、`onTouch`
- 章节、关防、皮肤、奇偶步提示文案、符节
- `entry/cjpm.toml` 里的 ohos target

## 为什么是拷贝而不是和 `entry/` 共用文件

鸿蒙包名绑在 DevEco 模块上。这份必须能用 iOS SDK / Android SDK 的 `cjpm` 编，不能带 ohos target。
