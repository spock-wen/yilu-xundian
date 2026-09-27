# 驿路巡点

鸿蒙 2D 可玩原型。规则对齐 LinkedIn Zip（正交哈密顿路径 + 按号巡驿），**不是**中国「一笔画」描边。

- 语言：仓颉 1.1.3
- UI：官方仓颉 ArkUI Canvas + `onTouch`
- 无内购、无登录、无 Game Service
- 本仓库 **没有** 在 CI / 云主机上编出 HAP：当前环境没有 DevEco / 仓颉鸿蒙工具链。请用本机 DevEco 打开后编译。
- iOS 壳见 [ios/README.md](ios/README.md)。Android 壳见 [android/README.md](android/README.md)。两边共用 [mobile/shared](mobile/shared) 里的仓颉 Zip 引擎，不是把规则重写成 Swift 或 Kotlin。**iOS 模拟器冒烟 PASSED**（tip `eaf7aed`，进入涿郡·范阳 id 1；截图目录 `qa-shots/ios-shell-eaf7aed-gate`，本检出不含该目录）。**Android** 把程序员 Mac 冒烟和测试门禁分开记，都在 tip `f25f813`（`f25f813d81388b550fd336f3b819b93117f214c5`）。**程序员 Mac 冒烟 PASSED**（AVD `grokdump`，进入涿郡·范阳 id 1，6×6 可见；目录 `_smoke/android-fanyang-f25f813-resmoke-*`、`qa-shots/android-shell-f25f813-gate/`，本检出可不含）。**测试门禁 PASS**（全屏目录 `qa-shots/android-shell-f25f813-tester`，本检出可不含）。更早 tip `4986524` 因缺少 `CJ_MRT_CjRuntimeInit` 为 FAIL。见 [android/README.md](android/README.md)。

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
| 棋盘 | 顶栏盘名原文（如「涿郡·涿」「平原·祝阿·第 2 驿」；部分盘名已含「·第 2 驿」），底栏「撤销」「重绘驿道」 |
| 通关 | 「通关」+ 同标题；「驿道已通」「文书递达本驿」；朱印「文书到」；「下一驿」 |
| 驿程 | 顶栏「驿程」；行态：已通 / 当前 / 锁 |

视觉 token 只来自手稿，写在 `entry/src/main/cangjie/theme.cj`。禁止熊猫、红包、灯笼堆、龙兔贴图、宪法海报风。金只作发丝线，朱砂只作关防 / 文书到印。

## 关卡 JSON（20/20 已由求解器验证）

路径：`entry/src/main/resources/rawfile/levels.json`（给求解器用）。应用内用同内容的仓颉字面量 `entry/src/main/cangjie/levels.cj`——**未采用** rawfile 读取 API，因为仓颉 1.1.3 的资源读取绑定未在官方文档里核对到可安全使用的写法。

可玩目录是锁定的 **涿郡 10 + 平原 10**（ids 0..19，全 6×6）。盘名原文上架，禁止再发明关卡或改驿站坐标。平原在 `cleared >= 10` 后可入；徐州 / 吕布 / 投袁…北伐只有章节卡或皮肤预览，**没有**棋盘。

```json
{"id":0,"name":"涿郡·涿","cols":6,"rows":6,"waypoints":[{"n":1,"x":3,"y":2},{"n":2,"x":3,"y":5},{"n":3,"x":0,"y":1},{"n":4,"x":4,"y":4},{"n":5,"x":4,"y":1},{"n":6,"x":0,"y":0}],"walls":[]}
```

（上例坐标抄自 `levels.json` id 0，不是示意盘。）

- `x` 列、`y` 行，原点左上。
- `walls` 是正交相邻格之间的边；没有墙则为 `[]`。
- 求解器：哈密顿路径、四向、驿站按号顺序、墙挡住正交边。

| id | 驿名 | 尺寸 | 驿站数 | 墙 |
| --- | --- | --- | --- | --- |
| 0 | 涿郡·涿 | 6×6 | 6 | 0 |
| 1 | 涿郡·范阳 | 6×6 | 6 | 2 |
| 2 | 涿郡·故安 | 6×6 | 5 | 3 |
| 3 | 涿郡·遒 | 6×6 | 5 | 3 |
| 4 | 涿郡·中山 | 6×6 | 6 | 3 |
| 5 | 涿郡·中山·第 2 驿 | 6×6 | 5 | 3 |
| 6 | 涿郡·卢奴 | 6×6 | 4 | 3 |
| 7 | 涿郡·卢奴·第 2 驿 | 6×6 | 4 | 4 |
| 8 | 涿郡·安喜 | 6×6 | 4 | 4 |
| 9 | 涿郡·安喜·第 2 驿 | 6×6 | 4 | 4 |
| 10 | 平原·高唐 | 6×6 | 5 | 3 |
| 11 | 平原·高唐·第 2 驿 | 6×6 | 5 | 3 |
| 12 | 平原·郡治 | 6×6 | 5 | 5 |
| 13 | 平原·郡治·第 2 驿 | 6×6 | 5 | 5 |
| 14 | 平原·安德 | 6×6 | 5 | 4 |
| 15 | 平原·安德·第 2 驿 | 6×6 | 4 | 5 |
| 16 | 平原·鬲 | 6×6 | 4 | 7 |
| 17 | 平原·鬲·第 2 驿 | 6×6 | 4 | 7 |
| 18 | 平原·祝阿 | 6×6 | 4 | 7 |
| 19 | 平原·祝阿·第 2 驿 | 6×6 | 4 | 8 |

表内尺寸 / 驿站数 / 墙数与 `levels.json`（及 `tools/build_levels.py` 的 `EXPECTED_NAMES`）一致。

驿名取东汉郡县城，不是自造地名。

依据：

- 目录本身：`entry/src/main/resources/rawfile/levels.json` ids 0..19；测试锁在 `tools/test_rules.py` 的 `VerifiedCatalogTests` / `ChapterFlowV13Tests`。
- 涿、范阳、故安、遒：西汉涿郡属县。班固《汉书·地理志下》涿郡「县二十九：涿，迺，…故安，…范阳，…」（维基文库 [漢書/卷028](https://zh.wikisource.org/wiki/%E6%BC%A2%E6%9B%B8/%E5%8D%B7028%E4%B8%8B)）。志文作「迺」，后世常写「遒」，本关用「遒」。
- 中山、卢奴、安喜：中山国有卢奴（《汉书·地理志》中山国）；刘备「涿郡涿县人」「除安喜尉」，裴注《典略》作「中山安喜尉」（《三国志·蜀书·先主传》，维基文库 [三國志/卷32](https://zh.wikisource.org/wiki/%E4%B8%89%E5%9C%8B%E5%BF%97/%E5%8D%B732)）。
- 高唐、安德、鬲、祝阿：西汉平原郡属县。《汉书·地理志上》平原郡「县十九：…鬲，高唐，…祝阿，…安德，…」（同上卷028）。刘备后为高唐尉、试守平原令、领平原相（同上先主传）。

## 引擎 vs 占位

| 层 | 路径 | 职责 |
| --- | --- | --- |
| 可复用网格引擎 | `entry/src/main/cangjie/engine/` | 格子、墙、触摸落格、撤销栈、路径。无 Canvas、无本关规则。 |
| 本游戏规则 | `entry/src/main/cangjie/game/` | 升序驿站 + 填满网格 + 终点最高号。 |
| 关卡数据 | `levels.json` + `levels.cj` | 同一套已验证 20 关（涿郡+平原）。 |
| 设计师皮肤 | `theme.cj` + Canvas 描线 | 手稿 token：纸底、已访底、墨环、青填已过、金发丝下一驿、朱印。 |

引擎可以在没有 Canvas 的情况下被推理 / 用 Python 镜像单测（`tools/test_rules.py`）。仓颉侧目前没有在本机跑 `cjpm test`（无 `cjc`）。

## 独立求解器

```bash
python3 tools/solve_levels.py
python3 tools/test_rules.py
```

`solve_levels.py` 与应用代码无关，用回溯证明每关至少一条解。未通过的关不得入库。本机已跑通 **20/20**（涿郡+平原，无 6×8 教程）。若以后 DFS 超时：关卡仍保留、驿站坐标不改，求解器打印 `TIMEOUT` 且退出码为 0。

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

### Mac 模拟器一条命令冒烟

云主机没有 DevEco / `hdc`，编不出 HAP，也截不了模拟器。Mac 上用一条命令完成：单独 worktree、编译、按指定设备安装启动、全屏截图。脚本不 `sudo`、不问交互问题。不要在主检出里切分支或编译。

```bash
bash tools/mac_smoke.sh <git-ref> <hdc-serial>
```

例（序列号来自 `hdc list targets`，多开模拟器时必须带上，避免装到别人的会话）：

```bash
bash tools/mac_smoke.sh 06adc4e 127.0.0.1:5555
```

| 项 | 位置 |
| --- | --- |
| worktree | `~/orca/yilu-xundian-smoke-<ref>`（ref 里的 `/` 换成 `-`）。已存在则 `checkout --detach` 到该提交再编 |
| 截图 | `~/orca/yilu-xundian-smoke-out/<ref>/<UTC时间>/`。`hdc shell snapshot_display -f …jpeg` 再 `hdc file recv` |
| 编译 | 在 worktree 里执行 `hvigorw assembleHap --mode module -p product=default -p buildMode=debug --no-daemon`。`product=default` 与 `buildMode=debug` 对应仓库 `build-profile.json5`。`hvigorw` / `hdc` 优先用 PATH，否则用 `/Applications/DevEco-Studio.app` |
| 设备 | 每条 `hdc` 都是 `hdc -t <serial>` |

固定截图点（冷启动，`cleared` 在内存里从 0 开始；没有调试入口能改进度）：

1. `01-home` 首页，可见「开始传书」
2. `02-board` 点「开始传书」后的棋盘，可见「撤销」（新装是涿郡·涿）
3. `03-chapters` 点「章节」，可见「选章入驿」
4. `04-yicheng` 点「驿程」，可见「涿郡·涿」
5. `05-maintenance` 在驿程里滚到可见的「修缮中」（并看到「樊城」）。这 6 关即使还没解锁也标「修缮中」，不必先打到第 51 关。第 7 章要 `cleared >= 60` 才开，这条命令不代替那条通关路径。

任一步失败：打印 `RESULT: FAIL`，退出码非 0。成功打印 `RESULT: PASS`。主检出的 HEAD 和工作区不应被改动。SDK 路径若只写在主检出的 `local.properties`（gitignore），脚本会把它**复制**进 worktree，不回写主检出。

## API 依据（未编造 `@ohos.*` / ArkTS-only）

全部对照 [openharmony/docs_cangjie](https://gitcode.com/openharmony/docs_cangjie) 的仓颉文档，**不是** ArkTS 文档。

| 用法 | 依据 |
| --- | --- |
| Empty Ability 树：`entry/src/main/cangjie/{ability_stage,index,main_ability}.cj` + `entry/cjpm.toml` + `module.json5` | [cj-quick-start-first-cangjie-app.md](https://gitcode.com/openharmony/docs_cangjie/blob/master/zh-cn/application-dev/cj-start/start/quick-start/cj-quick-start-first-cangjie-app.md) |
| `import kit.ArkUI.*` + `import ohos.arkui.state_macro_manage.*`；`@Entry` `@Component` `@State` | 同上 `index.cj` 初始代码；Canvas 指南同套 import |
| `kit.AbilityKit.*`、`UIAbility`、`windowStage.loadContent("EntryView")` | [cj-application-window-stage.md](https://gitcode.com/openharmony/docs_cangjie/blob/master/zh-cn/application-dev/windowmanager/cj-application-window-stage.md) |
| `RenderingContextSettings(antialias: true)` 再 `CanvasRenderingContext2D(settings)`（无 `new`） | [cj-drawing-customization-on-canvas.md](https://gitcode.com/openharmony/docs_cangjie/blob/master/zh-cn/application-dev/arkui-cj/cj-drawing-customization-on-canvas.md) |
| 颜色 `0XF3E8D6` 等 token 整数，坐标 `Float64` vp（`50.0`） | 同上示例 `0XF5DC62`、`fillRect(50.0, 50.0, …)`；色值来自设计师手稿 |
| `Text.fontFamily("serif")` / `"sans-serif"` | [cj-text-input-text.md](https://gitcode.com/openharmony/docs_cangjie/blob/master/zh-cn/application-dev/reference/arkui-cj/cj-text-input-text.md) `func fontFamily`。非棋盘文案仍用系统 generic family |
| `Divider` / `Blank` / `Stack` / `.rotate(angle:)` / `.border` / `.layoutWeight` | docs_cangjie 对应通用属性与容器页 |
| `lineWidth` / `strokeStyle` / `fillStyle` / `font` 是 **属性**：`this.context.lineWidth = 2.0` | [cj-canvas-drawing-canvasrenderingcontext2d.md](https://gitcode.com/openharmony/docs_cangjie/blob/master/zh-cn/application-dev/reference/arkui-cj/cj-canvas-drawing-canvasrenderingcontext2d.md)（`prop lineWidth` / `prop font`） |
| 棋盘驿站数字：`Path2D` + `moveTo` / `lineTo` / `arc` + `stroke(path)`，单位 **vp**（与驿站圆同一套） | [cj-canvas-drawing-path2d.md](https://gitcode.com/openharmony/docs_cangjie/blob/master/zh-cn/application-dev/reference/arkui-cj/cj-canvas-drawing-path2d.md) `moveTo`/`lineTo`/`arc`「默认单位：vp」；[cj-canvas-drawing-canvasrenderingcontext2d.md](https://gitcode.com/openharmony/docs_cangjie/blob/master/zh-cn/application-dev/reference/arkui-cj/cj-canvas-drawing-canvasrenderingcontext2d.md) `func stroke(Path2D)`。字形高 = 直径 × 0.60（教程 40vp → 24vp）。`fillText` / `font` 的 `px` 与 `vp`、以及 `vp2px` 在真机上未能放大墨像素（教程站 1 的 180×180 裁切相对 e90cacf 为 0 px diff），因此数字不用 font |
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

间距（vp）：屏边 20，顶栏 56，底栏 72，教程格 48，驿站直径 40（随格子 `cs/48` 缩放），驿站数字 Path2D 高 24vp（直径 × 0.60，下限 22，同样随 `cs/48` 缩放），路宽 8，主按钮高 52，撤销/重绘 56，底栏图标 24。
