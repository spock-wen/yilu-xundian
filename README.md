# 驿路巡点

鸿蒙 2D 可玩原型。规则对齐 LinkedIn Zip（正交哈密顿路径 + 按号巡驿），**不是**中国「一笔画」描边。

- 语言：仓颉 1.1.3
- UI：官方仓颉 ArkUI Canvas + `onTouch`
- 无内购、无登录、无 Game Service
- 本仓库 **没有** 在 CI / 云主机上编出 HAP：当前环境没有 DevEco / 仓颉鸿蒙工具链。请用本机 DevEco 打开后编译。

## 玩法

1. 从标了 **1** 的格子起笔，按正交四向拖过邻格（禁止对角线）。
2. 必须经过每一个格子恰好一次。
3. 有数字的驿站必须按 1..N **升序**经过；最高号是整盘的终点。
4. 相邻格之间可以有墙，路径不能穿墙、不能自交。墙只挡住正交边，不删格子。
5. 拖回上一格 = 撤销一步。另有 **撤销**、**重绘驿道**。
6. 原型不提供 Hint。

### 界面（设计师手稿 01–06 为视觉源）

| 屏 | 文案 |
| --- | --- |
| 首页 | 标题「驿路巡点」，副题「传书过驿」，主按钮「开始传书」，次入口「驿程」，朱印「关防」 |
| 棋盘 | 顶栏「{驿名}·第 N 驿」（N = 驿程 1-based 序号，不是盘上最高驿站号），底栏「撤销」「重绘驿道」 |
| 通关 | 「通关」+ 同标题；「驿道已通」「文书递达本驿」；朱印「文书到」；「下一驿」 |
| 驿程 | 顶栏「驿程」；行态：已通 / 当前 / 锁 |

视觉 token 只来自手稿，写在 `entry/src/main/cangjie/theme.cj`。禁止熊猫、红包、灯笼堆、龙兔贴图、宪法海报风。金只作发丝线，朱砂只作关防 / 文书到印。

## 关卡 JSON（12/12 已由求解器验证）

路径：`entry/src/main/resources/rawfile/levels.json`（给求解器用）。应用内用同内容的仓颉字面量 `entry/src/main/cangjie/levels.cj`——**未采用** rawfile 读取 API，因为仓颉 1.1.3 的资源读取绑定未在官方文档里核对到可安全使用的写法。

第一关是设计师教程 **长安 6×8**（驿站 `1=(2,0) 2=(3,2) 3=(1,4) 4=(5,5) 5=(0,7)`），其后 12 关是已验证表 **原样上架**。唯一改名：汽梁 → **汴梁**。禁止再发明关卡或改教程坐标。

```json
{"id":1,"name":"长安","cols":3,"rows":3,"waypoints":[{"n":1,"x":0,"y":0},{"n":2,"x":2,"y":2}],"walls":[]}
```

- `x` 列、`y` 行，原点左上。
- `walls` 是正交相邻格之间的边；没有墙则为 `[]`。
- 求解器：哈密顿路径、四向、驿站按号顺序、墙挡住正交边。

| id | 驿名 | 尺寸 | 驿站数 | 墙 |
| --- | --- | --- | --- | --- |
| 0 | 长安（教程） | 6×8 | 5 | 0 |
| 1 | 长安 | 3×3 | 2 | 0 |
| 2 | 洛阳 | 3×3 | 3 | 0 |
| 3 | 汴梁 | 3×3 | 4 | 0 |
| 4 | 扬州 | 4×4 | 3 | 0 |
| 5 | 杭州 | 4×4 | 4 | 0 |
| 6 | 苏州 | 4×4 | 5 | 0 |
| 7 | 凉州 | 4×4 | 4 | 1 |
| 8 | 敦煌 | 5×5 | 4 | 1 |
| 9 | 肃州 | 5×5 | 5 | 2 |
| 10 | 滑州 | 5×5 | 5 | 2 |
| 11 | 通州 | 5×5 | 6 | 3 |
| 12 | 济宁 | 5×5 | 6 | 3 |

驿名取真实驿路 / 大运河节点，不是自造地名。

依据：

- 长安 / 洛阳 / 凉州 / 肃州 / 敦煌：唐代驿路与丝绸之路河西走廊节点（两京、凉州、肃州、沙州/敦煌）。
- 汴梁、扬州、杭州、苏州、滑州、通州、济宁：隋唐至明清大运河沿线州府（汴河、淮扬、江南河、会通河、通惠河）。汴梁即开封。

## 引擎 vs 占位

| 层 | 路径 | 职责 |
| --- | --- | --- |
| 可复用网格引擎 | `entry/src/main/cangjie/engine/` | 格子、墙、触摸落格、撤销栈、路径。无 Canvas、无本关规则。 |
| 本游戏规则 | `entry/src/main/cangjie/game/` | 升序驿站 + 填满网格 + 终点最高号。 |
| 关卡数据 | `levels.json` + `levels.cj` | 同一套已验证 12 关。 |
| 设计师皮肤 | `theme.cj` + Canvas 描线 | 手稿 token：纸底、已访底、墨环、青填已过、金发丝下一驿、朱印。 |

引擎可以在没有 Canvas 的情况下被推理 / 用 Python 镜像单测（`tools/test_rules.py`）。仓颉侧目前没有在本机跑 `cjpm test`（无 `cjc`）。

## 独立求解器

```bash
python3 tools/solve_levels.py
python3 tools/test_rules.py
```

`solve_levels.py` 与应用代码无关，用回溯证明每关至少一条解。未通过的关不得入库。本机已跑通 **13/13**（含设计师 6×8 教程）。若以后 DFS 超时：关卡仍保留、驿站坐标不改，求解器打印 `TIMEOUT`。

`tools/build_levels.py` **只**把已验证的 `levels.json` 抄成仓颉字面量，不生成路径、不发明关卡。改关后必须先改 JSON，再：

```bash
python3 tools/build_levels.py
python3 tools/solve_levels.py
python3 tools/test_rules.py
```

禁止随机乱画格子当关卡。

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

## 用 DevEco 编译运行

仓颉 HAP **必须**用与 DevEco 锁步的仓颉插件。插件 5.x 不能装在 DevEco 6.0.1 上。仓颉 SDK 1.1.3 见 [cangjie-lang.cn/download/1.1.3](https://cangjie-lang.cn/download/1.1.3)。入门流程见仓颉官网《HarmonyOS 应用开发入门指导》：报名 → 安装匹配的 DevEco + 仓颉插件 → **[Cangjie] Empty Ability**。

### 推荐：先建官方空工程再铺源码

这是官方创建路径，也最不容易和本机 SDK / hvigor 插件版本打架。

1. 安装 **DevEco Studio**，用 **Plugins → Install Plugin from Disk** 安装 **与该 DevEco 同号** 的仓颉插件，重启 IDE。
2. `File → New → Create Project` → Application → **[Cangjie] Empty Ability**。仓颉目前只提供 Phone。
3. 工程名 / 显示名填 **驿路巡点**，bundle name 建议 `com.yilu.xundian`。
4. 等工程同步结束（仓颉 SDK 默认在 macOS `$HOME/.cangjie-sdk`、Windows `%USERPROFILE%\.cangjie-sdk`）。
5. 用本仓库覆盖生成工程里的：
   - `entry/src/main/cangjie/`
   - `entry/cjpm.toml`
   - `entry/src/main/resources/`
   - `entry/src/main/module.json5`（或只改 `label` / `icon`）
   - `AppScope/app.json5` 的 `bundleName` / `label`
   - `AppScope/resources/base/element/string.json`（`app_name` = 驿路巡点）
6. 若走 x86 模拟器，确认 `entry/build-profile.json5` 含：

```json5
"cangjieOptions": {
  "path": "./cjpm.toml",
  "abiFilters": ["arm64-v8a", "x86_64"]
}
```

（出处：上述官方第一应用目录把 `cjpm.toml` 放在 `entry/`；x86 过滤器见仓颉 Empty Ability 构建说明。默认只编 `arm64-v8a`。）

7. 配置签名，选 Phone 模拟器或真机，Run。
8. **不要**添加 IAP / 登录 / Game Service。

### 直接打开本仓库

也可以 `File → Open` 本仓库。首次同步时 DevEco 可能改写：

- `build-profile.json5` 的 `compatibleSdkVersion`（请改成你本机 HarmonyOS SDK）
- `hvigor/hvigor-config.json5` 里的仓颉 hvigor 支持包版本
- `local.properties`（SDK 路径，已 gitignore）

这些文件因本机插件而异，不要从网上抄一个对不上的 `cangjie-build-support-*.tgz` 版本。仓颉插件会在本机提供 `@ohos/cangjie-build-support`，该本机路径不要提交进 `hvigor/hvigor-config.json5`（仓库里保持 `dependencies: {}`）。

## API 依据（未编造 `@ohos.*` / ArkTS-only）

全部对照 [openharmony/docs_cangjie](https://gitcode.com/openharmony/docs_cangjie) 的仓颉文档，**不是** ArkTS 文档。

| 用法 | 依据 |
| --- | --- |
| Empty Ability 树：`entry/src/main/cangjie/{ability_stage,index,main_ability}.cj` + `entry/cjpm.toml` + `module.json5` | [cj-quick-start-first-cangjie-app.md](https://gitcode.com/openharmony/docs_cangjie/blob/master/zh-cn/application-dev/cj-start/start/quick-start/cj-quick-start-first-cangjie-app.md) |
| `import kit.ArkUI.*` + `import ohos.arkui.state_macro_manage.*`；`@Entry` `@Component` `@State` | 同上 `index.cj` 初始代码；Canvas 指南同套 import |
| `kit.AbilityKit.*`、`UIAbility`、`windowStage.loadContent("EntryView")` | [cj-application-window-stage.md](https://gitcode.com/openharmony/docs_cangjie/blob/master/zh-cn/application-dev/windowmanager/cj-application-window-stage.md) |
| `RenderingContextSettings(antialias: true)` 再 `CanvasRenderingContext2D(settings)`（无 `new`） | [cj-drawing-customization-on-canvas.md](https://gitcode.com/openharmony/docs_cangjie/blob/master/zh-cn/application-dev/arkui-cj/cj-drawing-customization-on-canvas.md) |
| 颜色 `0XF3E8D6` 等 token 整数，坐标 `Float64` vp（`50.0`） | 同上示例 `0XF5DC62`、`fillRect(50.0, 50.0, …)`；色值来自设计师手稿 |
| `Text.fontFamily("serif")` / `"sans-serif"` | [cj-text-input-text.md](https://gitcode.com/openharmony/docs_cangjie/blob/master/zh-cn/application-dev/reference/arkui-cj/cj-text-input-text.md) `func fontFamily`。手稿指定 Noto Serif/Sans SC，但仓颉文档**没有**可核对的 Noto 资源绑定，因此用系统 `serif` / `sans-serif`，**未**自造 font kit import |
| `Divider` / `Blank` / `Stack` / `.rotate(angle:)` / `.border` / `.layoutWeight` | docs_cangjie 对应通用属性与容器页 |
| `lineWidth` / `strokeStyle` / `fillStyle` / `font` 是 **属性**：`this.context.lineWidth = 2.0` | [cj-canvas-drawing-canvasrenderingcontext2d.md](https://gitcode.com/openharmony/docs_cangjie/blob/master/zh-cn/application-dev/reference/arkui-cj/cj-canvas-drawing-canvasrenderingcontext2d.md)（`prop lineWidth`） |
| 首次绘制在 `onReady`；`clearRect` / `fillRect` / `beginPath` / `moveTo` / `lineTo` / `stroke` / `fill` / `fillText` / `arc` | 上述两篇 Canvas 文档 |
| 底栏「撤销」「重绘驿道」：可点击 `Row` + 24vp Canvas；弧用 `Path2D()` + `stroke(path)`，三角箭头用当前路径 `fill()`；`lineWidth` 是属性。不用 `Button("撤销")` | [cj-canvas-drawing-canvasrenderingcontext2d.md](https://gitcode.com/openharmony/docs_cangjie/blob/master/zh-cn/application-dev/reference/arkui-cj/cj-canvas-drawing-canvasrenderingcontext2d.md) 的 `func stroke(Path2D)`、`func fill()`。HarmonyOS 6.1.1 默认 Button 仍带 start icon，缺字形会变成方块。几何见 `tools/bar_icons.py`（手稿甲） |
| `onTouch({ event => match (event.eventType) { case TouchType.Down => … } })`；点 `event.touches[0].x` / `.y` | [cj-common-events-touch-screen-event.md](https://gitcode.com/openharmony/docs_cangjie/blob/master/zh-cn/application-dev/arkui-cj/cj-common-events-touch-screen-event.md) 的**代码示例**。字段是 `event.eventType`（类型定义见 `cj-common-types.md` 的 `TouchEvent.eventType`），**不是** ArkTS 的 `event.type`（该页散文里的 `event.type` 与示例不一致，以代码与类型定义为准） |
| `ArrayList.add` / `remove(at:)` / `size` | [仓颉 1.1.3 ArrayList](https://cj-docs.gitcode.com/zh/1.1.3/dev-guide/source_zh_cn/collections/collection_arraylist.html) |

明确 **没有** 使用：

- 过时 `import ohos.component.*` / `ohos.state_manage.*`
- 未在官方 Canvas 页出现的 `import ohos.arkui.component.Canvas`
- ArkTS `event.type`、`new CanvasRenderingContext2D`
- OffscreenCanvas / XComponent / Component3D
- 未核对的 `@ohos.*` 包

用户提到的 Beat Roguelike 仓库 https://gitcode.com/yunitia/qwe 当前页面无可用 Canvas 源码，**没有抄游戏代码**。

## 显示名

- 应用名 / Ability label：`驿路巡点`
- bundleName：`com.yilu.xundian`

## 本机已跑过的检查

```bash
python3 tools/solve_levels.py
python3 tools/test_rules.py
```

当前环境：`cjc` / DevEco **不存在**，因此没有声称编过 HAP，也无法在真机上对照六张手稿逐像素验收。

## 设计师 token（勿漂移）

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

间距（vp）：屏边 20，顶栏 56，底栏 72，教程格 48，驿站直径 40，路宽 8，主按钮高 52，撤销/重绘 56。
