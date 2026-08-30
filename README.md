# 驿路巡点

鸿蒙 2D 可玩原型。规则对齐 LinkedIn Zip（正交哈密顿路径 + 按号巡驿），**不是**中国「一笔画」描边。

- 语言：仓颉 1.1.3
- UI：ArkUI Canvas + `onTouch`
- 无内购、无登录、无 Game Service
- 本仓库 **没有** 在 CI / 云主机上编出 HAP：当前环境没有 DevEco / 仓颉鸿蒙工具链。请用本机 DevEco 打开后编译。

## 玩法

1. 从标了 **1** 的格子起笔，按正交四向拖过邻格（禁止对角线）。
2. 必须经过每一个格子恰好一次。
3. 有数字的驿站必须按 1..N **升序**经过；最高号是整盘的终点。
4. 相邻格之间可以有墙，路径不能穿墙、不能自交。
5. 拖回上一格 = 撤销一步。另有 **撤销**、**重置**。
6. 原型不提供 Hint。

### 界面

| 屏 | 内容 |
| --- | --- |
| 驿册 | 关卡名 + 尺寸 |
| 巡点 | Canvas 棋盘，撤销 / 重置，返回驿册 |
| 达驿 | 文案「文书达驿」，下一站 |

视觉是占位驿路 / 信使风（纸色 `#F3EBDD`、墨色 `#2B2A27`、路色 `#4A6670`），颜色和间距集中在 `entry/src/main/cangjie/src/theme.cj`。不要当成春节皮肤。设计师可整文件替换。

## 关卡 JSON

路径：`entry/src/main/resources/rawfile/levels.json`（给求解器用）。应用内用同内容的仓颉字面量 `entry/src/main/cangjie/src/levels.cj`——**未采用** rawfile 读取 API，因为仓颉 1.1.3 的资源读取绑定未在官方文档里核对到可安全使用的写法。

```json
{
  "id": 1,
  "name": "长安",
  "cols": 3,
  "rows": 3,
  "waypoints": [{"n": 1, "x": 0, "y": 0}, {"n": 2, "x": 2, "y": 2}],
  "walls": [{"x1": 0, "y1": 0, "x2": 1, "y2": 0}]
}
```

- `x` 列、`y` 行，原点左上。
- `walls` 是正交相邻格之间的边；没有墙就省略该字段。

已收录 12 关，由 3×3 教程到 4×4、5×5，后半段带 1–3 面墙。驿名取真实驿路 / 大运河节点：长安、洛阳、汴梁、扬州、杭州、苏州、凉州、敦煌、肃州、滑州、通州、济宁。示例里的「汽梁」按历史地名写作 **汴梁**（开封）。

依据：

- 长安 / 洛阳 / 凉州 / 肃州 / 敦煌：唐代驿路与丝绸之路河西走廊节点（两京、凉州、肃州、沙州/敦煌）。
- 汴梁、扬州、杭州、苏州、滑州、通州、济宁：隋唐至明清大运河沿线州府（汴河、淮扬、江南河、会通河、通惠河）。

## 引擎 vs 占位

| 层 | 路径 | 职责 |
| --- | --- | --- |
| 可复用网格引擎 | `entry/src/main/cangjie/src/engine/` | 格子、墙、触摸落格、撤销栈、路径。无 Canvas、无本关规则。 |
| 本游戏规则 | `entry/src/main/cangjie/src/game/` | 升序驿站 + 填满网格 + 终点最高号。 |
| 关卡数据 | `levels.json` + `levels.cj` | 同一套 12 关。 |
| 占位皮肤 | `theme.cj` + Canvas 描线 | 纸墨色、驿站圆环、数字叠字。 |

引擎可以在没有 Canvas 的情况下被推理 / 用 Python 镜像单测（`tools/test_rules.py`）。仓颉侧目前没有在本机跑 `cjpm test`（无 `cjc`）。

## 独立求解器

```bash
python3 tools/solve_levels.py
python3 tools/test_rules.py
```

`solve_levels.py` 与应用代码无关，用回溯证明每关至少一条解。未通过的关不得入库。

若改关卡，先改 `tools/build_levels.py` 里的**手写路径**（生成器强制：路径必须走遍全图，驿站必须按访问顺序，墙只能打在未走边上），再：

```bash
python3 tools/build_levels.py
python3 tools/solve_levels.py
python3 tools/test_rules.py
```

禁止随机乱画格子当关卡。

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
   - `entry/src/main/resources/`
   - `entry/src/main/module.json5`（或只改 `label` / `icon`）
   - `AppScope/app.json5` 的 `bundleName` / `label`
   - `AppScope/resources/base/element/string.json`（`app_name` = 驿路巡点）
6. 若走 x86 模拟器，确认 `entry/build-profile.json5` 含：

```json5
"cangjieOptions": {
  "path": "./src/main/cangjie/cjpm.toml",
  "abiFilters": ["arm64-v8a", "x86_64"]
}
```

（出处：仓颉官方入门与 2025 年 Empty Ability 构建说明。默认只编 `arm64-v8a`。）

7. 配置签名，选 Phone 模拟器或真机，Run。
8. **不要**添加 IAP / 登录 / Game Service。

### 直接打开本仓库

也可以 `File → Open` 本仓库。首次同步时 DevEco 可能改写：

- `build-profile.json5` 的 `compatibleSdkVersion`（请改成你本机 HarmonyOS SDK）
- `hvigor/hvigor-config.json5` 里的仓颉 hvigor 支持包版本
- `local.properties`（SDK 路径，已 gitignore）

这些文件因本机插件而异，不要从网上抄一个对不上的 `cangjie-build-support-*.tgz` 版本。

## API 依据（未编造 `@ohos.*`）

| 用法 | 依据 |
| --- | --- |
| `[Cangjie] Empty Ability` 目录、`loadContent("EntryView")` | 仓颉官网入门；[docs_cangjie 第一应用](https://gitcode.com/hcwww/docs_cangjie) |
| `kit.AbilityKit.UIAbility` / `AbilityStage` | OpenHarmony 官方仓颉封装示例 [filemanagement_filemanagement_cangjie_wrapper](https://gitcode.com/openharmony/filemanagement_filemanagement_cangjie_wrapper)（Huawei Device Co. 2025） |
| `import ohos.component.*` / `@Entry` `@Component` `@State` | 已发表仓颉 UI 教程（幽蓝计划 / Changwei 组件篇） |
| `RenderingContextSettings(antialias: true)`、`CanvasRenderingContext2D`、`Path2D`、`onTouch`、`e.eventType.toString()`、`e.touches[0].x/y`、`lineWidth` / `strokeStyle(0xRRGGBB)` / `clearRect` / `stroke` | HarmonyOS NEXT 仓颉画板案例（[腾讯云](https://cloud.tencent.com/developer/article/2535093) / [DEV](https://dev.to/youlanjihua/a-case-of-implementing-a-drawing-board-with-the-cangjie-development-language-in-harmonyos-next-4498)） |
| 网格线 / 路径只用 `Path2D.moveTo` + `bezierCurveTo` + `stroke` | 同上；不用未在仓颉示例里出现的 `TouchType` |
| 驿站数字用 `Text` 叠在 Canvas 上 | 仓颉 `Text` / `ForEach` / `.position` 已有发表示例；避免未核对的仓颉 `fillText` 绑定 |
| `ArrayList.add` / `remove(at:)` / `size` | [仓颉 1.1.3 ArrayList](https://cj-docs.gitcode.com/zh/1.1.3/dev-guide/source_zh_cn/collections/collection_arraylist.html) |

用户提到的 Beat Roguelike 仓库 https://gitcode.com/yunitia/qwe 当前页面无可用 Canvas 源码，**没有抄游戏代码**，只对照「Harmony 仓颉 + Canvas 2D」这一结构约束。

未使用任何未核对的 `@ohos.*` 包。

## 显示名

- 应用名 / Ability label：`驿路巡点`
- bundleName：`com.yilu.xundian`

## 本机已跑过的检查

```bash
python3 tools/solve_levels.py
python3 tools/test_rules.py
```

当前环境：`cjc` / DevEco **不存在**，因此没有声称编过 HAP。
