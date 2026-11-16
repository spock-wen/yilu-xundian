# 共用 Zip 引擎

鸿蒙模块仍在 `entry/`，包名仍是 `ohos_app_cangjie_entry`。iOS / Android 不改那些文件。无鸿蒙依赖的一份在 `engine/shared/`，包名 `yilu_zip`。两边壳都调 `engine/include/yilu_zip.h` 里的 `yilu_*`。

## 抽进 `yilu_zip` 的

| 共用源文件 | 拷贝自 | 包名 |
| --- | --- | --- |
| `engine/shared/src/engine/cell.cj` | `entry/src/main/cangjie/engine/cell.cj` | `yilu_zip.engine` |
| `engine/shared/src/engine/wall.cj` | `entry/src/main/cangjie/engine/wall.cj` | `yilu_zip.engine` |
| `engine/shared/src/engine/grid.cj` | `entry/src/main/cangjie/engine/grid.cj` | `yilu_zip.engine` |
| `engine/shared/src/engine/undo.cj` | `entry/src/main/cangjie/engine/undo.cj` | `yilu_zip.engine` |
| `engine/shared/src/engine/path.cj` | `entry/src/main/cangjie/engine/path.cj` | `yilu_zip.engine` |
| `engine/shared/src/game/level.cj` | `entry/src/main/cangjie/game/level.cj` | `yilu_zip.game` |
| `engine/shared/src/game/patrol.cj` | `entry/src/main/cangjie/game/patrol.cj` | `yilu_zip.game` |

这 7 个文件在鸿蒙侧没有 `import ohos` / `import kit.ArkUI`。规则仍是正交、不穿墙、不走重复格、驿站按号、最高号必须在填满时进入、拖回上一格撤销。`parityEdges` 的判断留在 `patrol.cj` 里；加载器支持解析 `parityEdges`（v1 的范阳盘本身是空列表）。

`stepLimit` 在 `LevelDef` 上。鸿蒙 `PatrolGame` 不读取它，这份也不读。

## 只在共用模块里新增的

| 文件 | 作用 |
| --- | --- |
| `engine/shared/src/game/json_level.cj` | 读单盘或全量关卡 JSON，建成 `LevelDef`（支持解析 `parityEdges`）。不用 `stdx`。字节用 `String.get`（越界返回 `None`），不用会抛 `IndexOutOfBoundsException` 的 `[]`（[1.1.3 String](https://cj-docs.gitcode.com/zh/1.1.3/libs/std/core/core_package_api/core_package_structs.html)）。错误文案用手写十进制拼接，不走 `${整数}`。 |
| `engine/shared/src/ffi.cj` | 顶层 `@C` 函数。命名避免 `CJ_` 前缀（[仓颉-C 互操作](https://cj-docs.gitcode.com/zh/1.1.3/dev-guide/source_zh_cn/FFI/cangjie-c.html)）。`yilu_load_level_json` 不用 `CString.toString()`。加载成功时执行 `gGame = PatrolGame(level)`，不调用可能仍是空引用的 `gGame.reset`。 |
| `engine/include/yilu_zip.h` | 同一份 C 声明。iOS bridging header 引用它；Android `yilu_jni.c` 也引用它。 |

## 壳里没有 Zip 规则

| 壳 | 做什么 |
| --- | --- |
| `legacy/ios/app/YiluXundian/*.swift` | 读 bundle 里的 `level.json`，画格子，触摸调用 `yilu_touch_to_cell` / `yilu_try_step`。链接 iOS **静态库**。进第一笔 `yilu_*` 之前由 `CangjieRuntimeBootstrap.c` 调用 `CJ_MRT_CjRuntimeInit`。模拟器冒烟在 tip `eaf7aed` 通过（涿郡·范阳 id 1）；截图目录 `qa-shots/ios-shell-eaf7aed-gate`（本检出不含该目录）。 |
| `legacy/android/app/src/main/java/com/yilu/xundian/*.kt` | 读 assets 里的同一盘 JSON，经 JNI 调同一批符号。加载 Android **动态库** `libyilu_zip.so`。进第一笔 `yilu_*` 之前由 `legacy/android/app/src/main/cpp/CangjieRuntimeBootstrap.c` 调用 `CJ_MRT_CjRuntimeInit`（ELF `.init_array` 只排队元数据）。tip `f25f813`：程序员 Mac 冒烟 PASSED（涿郡·范阳 id 1，6×6），测试门禁 PASS。tip `4986524` 曾因缺少这次初始化而 FAIL。 |

iOS 用已提交的 `cjpm.toml`（`output-type = "static"`）。Android 脚本另写一份 gitignore 的 manifest（`output-type = "dynamic"`），因为同一个 toml 不能同时是静态库和动态库。源码仍是这一份 `src/`。cjpm 1.1.3 拒绝 `src-dir = "../src"`，脚本把 `src/` 拷进 `engine/shared/.android-build/src` 再写 `src-dir = "./src"`。

## 留在鸿蒙、没有搬进来的

- `entry/src/main/cangjie/index.cj`、`main_ability.cj`、`ability_stage.cj`、`theme.cj`、`chapter.cj`、`levels.cj`、`resource_helper.cj`
- `import kit.ArkUI.*`、Canvas、`onTouch`
- 章节、关防、皮肤、奇偶步提示文案、符节
- `entry/cjpm.toml` 里的 ohos target

## 为什么是拷贝而不是和 `entry/` 共用文件

鸿蒙包名绑在 DevEco 模块上。这份必须能用 iOS SDK / Android SDK 的 `cjpm` 编，不能带 ohos target。

## 机制扩展 API（给 CJMP UI 用，Phase 2a–2c）

### 与上文的差异

- 上文各表是抽取时的快照，只描述基础 Zip 规则；机制扩展直接写进 `level.cj` / `patrol.cj` 内部，不新增共用源文件行，上文「共用 7 个文件」清单仍为真。
- 上文「拖回上一格撤销」在机制关扩展为「拖回整个输入单元」（见 §4）；鸿蒙 `entry/` 拷贝没有这些机制代码。
- 新增独立测试模块 `engine/shared-test`，不在上文任何表格里。

### 1. 范围与不变量

| 项 | 说明 |
| --- | --- |
| 无机制关逐位一致 | `levels.json` 共 100 关，其中 67 关无机制键，行为与旧版逐位一致（回放测试覆盖） |
| JSON 形状 | 机制键 snake_case：`ferry` / `one_ways` / `slide_cells` / `seal_gates` / `token_cells` / `collapse` / `burden`；坐标 `[r,c]`，解析器 `readRcPair` 转为 `x=c, y=r` |
| 缺省 | 键缺失或 `null` = 无机制，`LevelDef` 字段默认值即空列表 / `None` |
| 不在范围 | 鸿蒙 `entry/`、iOS / Android 壳文件不改 |
| 测试 | 独立模块 `engine/shared-test`（`cd engine/shared-test && cjpm test`）；不在 `engine/shared/src` 下，故不被 `sync_to_keels.sh` 复制，也不进 iOS / Android 构建 |

### 2. `LevelDef` 新增

机制成员（`init` 签名不变，加载后按成员赋值）：

| 成员 | 类型 | 字段 |
| --- | --- | --- |
| `ferry` | `Option<FerryDef>` | `jiaX, jiaY, yiX, yiY`（甲 / 乙，引擎坐标） |
| `oneWays` | `ArrayList<OneWay>` | `fromX, fromY, toX, toY`（只放行 from → to） |
| `slideCells` | `ArrayList<Cell>` | 泽地格集合 |
| `sealGates` | `ArrayList<SealGate>` | `x1, y1, x2, y2`（无向；`locked_until_token` 恒真，故不存该字段） |
| `tokenCells` | `ArrayList<Cell>` | 符节格集合 |
| `collapse` | `Option<CollapseDef>` | `triggerX, triggerY, x1, y1, x2, y2`（触发格 + 塌边） |
| `burden` | `Option<BurdenDef>` | `forbidden: ArrayList<Cell>`、`loadX, loadY, unloadX, unloadY`、`startLaden: Bool` |

便捷方法：

| 签名 | 语义 |
| --- | --- |
| `hasMechanics(): Bool` | 任一机制键存在 |
| `isTokenCell(x: Int64, y: Int64): Bool` | 是否符节格 |
| `isForbiddenCell(x: Int64, y: Int64): Bool` | burden 禁区格（无 burden 恒假） |
| `oneWayConstrains(a: Cell, b: Cell): Bool` | 该邻边受某条单向约束（无向匹配） |
| `oneWayAllows(from: Cell, to: Cell): Bool` | 正向 from → to 放行 |
| `gateAt(a: Cell, b: Cell): Bool` | 该邻边为符节闸（无向匹配） |

### 3. `PatrolGame` 新增公共成员

运行状态（每次成功 `tryStep` 前快照进 `UnitSnap`，undo 时恢复）：

| 成员 | 类型 | 含义 |
| --- | --- | --- |
| `hasToken` | `Bool` | 已得符；整段落完才置真，同段内过闸仍用入口值 |
| `laden` | `Bool` | 负重载态；初始 = `burden.start_laden`（无 burden 为 false） |
| `collapseDown` | `Bool` | 踏触发格后置真，只置真不回退，由 undo 快照 / clear / reset 复位 |
| `lastReject` | `Int64` | 最近一次拒绝码（0 = 无） |
| `lastRejectFromX` / `FromY` / `ToX` / `ToY` | `Int64` | 拒绝边两端格坐标，未知为 -1 |

拒绝码常量表（`patrol.cj` 顶层 `REJECT_*`）：

| 值 | 常量 | 含义 |
| --- | --- | --- |
| 0 | `REJECT_NONE` | 无拒绝 |
| 1 | `REJECT_PARITY` | 奇偶边不符（配合 `lastRejectParity`：1 = 需奇步、2 = 需偶步） |
| 2 | `REJECT_ONE_WAY` | 单向边逆向通过 |
| 3 | `REJECT_SEALED_GATE` | 无符过闸 |
| 4 | `REJECT_BURDEN_FORBIDDEN` | 载态进禁区（含渡口乙在禁区） |
| 5 | `REJECT_WALL` | 墙 / 非邻；**同时用于塌桥封边的占位**（无独立塌桥码） |
| 6 | `REJECT_VISITED` | 目标格已铺 |
| 7 | `REJECT_WAYPOINT` | 段内路标次序不符，或最大号不在整盘最后一格 |
| 8 | `REJECT_BOUNDS` | 越界 |
| 9 | `REJECT_FERRY` | 进甲被拒：乙已在 path 里（或乙 == 甲） |
| 10 | `REJECT_START` | 首格必须是 1 号 |

其他公共成员：

| 成员 | 说明 |
| --- | --- |
| `isEdgeCollapsed(x1, y1, x2, y2): Bool` | 无向查询塌边当前是否已断；UI 可据此画断边（占位用墙样式） |
| `class UnitSnap` | 字段 `startLen: Int64`、`hasToken: Bool`、`laden: Bool`、`down: Bool`，一次输入前的快照 |
| `tryStep(cell: Cell): Bool` / `undo(): Bool` / `clear(): Unit` / `reset(level: LevelDef): Unit` | 签名保持不变 |

### 4. 一次输入 = 一个撤销单元

| 项 | 规则 |
| --- | --- |
| 单元大小 | 普通格 +1；渡口一次 +2（甲、乙同单元）；滑行一次 +N（整段同单元） |
| 拖回撤销 | 落在该单元入口前的头格（输入前的头），或落在单元内非头格 → 撤销整个单元 |
| 落头格 | 落在单元头（末格）不撤销，走 `REJECT_VISITED` 拒绝 |
| `undo()` | 纯回退，不受单向 / 闸门等通行约束 |
| `clear()` / `reset()` | 路径与单元清空，`hasToken=false`、`collapseDown=false`、`laden=start_laden` |

给 UI 的提示：

- `path.size()` 一次 `tryStep` 可能增加多格（渡口 +2、滑行 +N）。UI 应在每次 `tryStep` 后用 `game.path` 整体重绘，不要自己按 +1 推算。
- 滑行落地后，连续 Move 手势里越过滑行末格的下一格是正常新输入，直接再调 `tryStep` 即可。

### 5. 各机制一句话规则

| 机制 | 规则 |
| --- | --- |
| 渡口 | 踏甲的那一次输入强制同时铺 `[甲, 乙]`、落点为乙（跳接豁免墙 / 闸 / 奇偶 / 单向 / 塌桥）；乙已在 path（或乙 == 甲）→ `REJECT_FERRY` |
| 单向门 | 只放行 `from → to`，逆向 → `REJECT_ONE_WAY` |
| 滑行 | 目标 ∈ `slideCells` 则沿该方向滑到底；越界 / 墙 / 闸 / 奇偶 / 单向 / 禁区 / 已访 / 已入段 / 数字格 / 渡口甲乙 / 非泽地 → 停在前一格（不整段拒绝） |
| 符节闸 | 无符不过闸；符节在整段落完后才记入 `hasToken`，同段先过闸后得符不算数 |
| 塌桥 | 踏 `trigger` 触发格后置 `collapseDown`，从下一格起塌边断开 |
| 负重 | `laden` 时不可进 `forbidden` 禁区格；落 `load` 装粮、落 `unload` 卸粮（同格时后写的卸生效） |

参考实现：`tools/solve_levels.py` 的 `Rules` 类（引擎注释均标了对应行号）。权威来源是设计码 `zip_*.py`，仅作核对参考。

### 6. 已知限制

| 项 | 说明 |
| --- | --- |
| `JsonParser` 不解析小数 | `parseNumber` 遇 `.` / `e` / `E` 报 `only integers are accepted`；`levels.json` 全整数，无影响 |
| `stepLimit` | 存在 `LevelDef` 上，引擎不读、不强制（同上文鸿蒙侧行为） |
| `isWin` | 不检查「必须用过渡口」——那是设计解的有效性条件；满盘铺满即隐含已用渡口 |
