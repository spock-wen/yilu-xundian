# iOS 壳复用了什么

鸿蒙模块仍在 `entry/`，包名仍是 `ohos_app_cangjie_entry`。iOS 不改那些文件，另拷一份到 `ios/shared/`，只改包名。

## 抽进 `yilu_zip` 的

| iOS | 拷贝自 | 包名 |
| --- | --- | --- |
| `ios/shared/src/engine/cell.cj` | `entry/src/main/cangjie/engine/cell.cj` | `yilu_zip.engine` |
| `ios/shared/src/engine/wall.cj` | `entry/src/main/cangjie/engine/wall.cj` | `yilu_zip.engine` |
| `ios/shared/src/engine/grid.cj` | `entry/src/main/cangjie/engine/grid.cj` | `yilu_zip.engine` |
| `ios/shared/src/engine/undo.cj` | `entry/src/main/cangjie/engine/undo.cj` | `yilu_zip.engine` |
| `ios/shared/src/engine/path.cj` | `entry/src/main/cangjie/engine/path.cj` | `yilu_zip.engine` |
| `ios/shared/src/game/level.cj` | `entry/src/main/cangjie/game/level.cj` | `yilu_zip.game` |
| `ios/shared/src/game/patrol.cj` | `entry/src/main/cangjie/game/patrol.cj` | `yilu_zip.game` |

这 7 个文件在鸿蒙侧没有 `import ohos` / `import kit.ArkUI`。规则仍是正交、不穿墙、不走重复格、驿站按号、最高号必须在填满时进入、拖回上一格撤销。`parityEdges` 的判断留在 `patrol.cj` 里，和鸿蒙同一份逻辑；v1 加载的范阳盘是空列表，所以不会触发。

`stepLimit` 在 `LevelDef` 上。鸿蒙 `PatrolGame` 不读取它，iOS 这份也不读。

## 只在 iOS 新增的

| 文件 | 作用 |
| --- | --- |
| `ios/shared/src/game/json_level.cj` | 读一盘 JSON，建成 `LevelDef`。不用 `stdx`。`String` 按下标取的是 UTF-8 字节（[1.1.3 String](https://cj-docs.gitcode.com/zh/1.1.3/libs/std/core/core_package_api/core_package_structs.html)：`operator [](Int64): Byte`，`indexOf` 示例传入 `108u8`）。 |
| `ios/shared/src/ffi.cj` | 顶层 `@C` 函数，给 Swift 调。命名避免 `CJ_` 前缀（[仓颉-C 互操作](https://cj-docs.gitcode.com/zh/1.1.3/dev-guide/source_zh_cn/FFI/cangjie-c.html)）。 |
| `ios/app/YiluXundian/*.swift` | 读 bundle 里的 `level.json`，画格子，触摸调用 `yilu_touch_to_cell` 和 `yilu_try_step`。不实现 Zip 规则。 |

Swift 不解析驿站顺序，也不判断胜负。`yilu_is_win` / `yilu_number_at` / `yilu_wall_at` / `yilu_path_at` 都从引擎读。

## 留在鸿蒙、没有搬进来的

- `entry/src/main/cangjie/index.cj`、`main_ability.cj`、`ability_stage.cj`、`theme.cj`、`chapter.cj`、`levels.cj`、`resource_helper.cj`
- `import kit.ArkUI.*`、`ohos.arkui.state_macro_manage.*`、Canvas、`onTouch`
- 章节、关防、皮肤、奇偶步提示文案、符节
- `entry/cjpm.toml` 里的 `aarch64-linux-ohos` / `x86_64-linux-ohos` 目标

`levels.cj` 是 20 关字面量。iOS v1 不生成、也不链接它，只把 `levels.json` 的 id 1 打进 App。

## 为什么是拷贝而不是共用源文件

鸿蒙包名 `ohos_app_cangjie_entry.*` 绑在 DevEco 模块上。iOS 静态库必须能用社区 / iOS SDK 的 `cjpm` 编，不能带 ohos target。两边各留一份，避免改 `entry/` 的 import。
