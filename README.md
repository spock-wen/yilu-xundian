# 驿路巡点

2D 路径解谜游戏。规则对齐 LinkedIn Zip（正交哈密顿路径 + 按号巡驿），**不是**中国「一笔画」描边。无内购、无登录、无 Game Service。锁定 100 关（10 章 × 10 关，ids 0..99）。项目已于 2026-10-24 结项，本仓库现在只做维护。

## 三端各在哪个目录，现在用哪套

| 平台 | 目录 | 状态 | 一句话 |
| --- | --- | --- | --- |
| 鸿蒙 | 仓库根的 `entry/`、`AppScope/`、`hvigor/`、`build-profile.json5`、`hvigorfile.ts`、`oh-package.json5` | **在用** | DevEco 工程。要求这些文件留在仓库根，所以没有挪。仓颉 1.1.3 + ArkUI Canvas。 |
| iOS + Android | [`app-ios-android/`](app-ios-android/README.md) | **在用** | CJMP 0.2.2 / Keels 跨平台应用（原 `mobile/cjmp`，它是目录，不是 git 分支）。 |
| 共用引擎 | [`engine/`](engine/ENGINE.md) | 在用 | `engine/shared` 是无 ohos 依赖的仓颉 Zip 引擎（包名 `yilu_zip`）+ 共用 `levels.json`；`app-ios-android` 构建时从这里同步。 |
| 旧 iOS / Android 原生壳 | [`legacy/ios/`](legacy/ios/README.md)、[`legacy/android/`](legacy/android/README.md) | **已废弃** | UIKit / Kotlin 壳，10-03 之后没再动，已被 `app-ios-android/` 取代。保留作历史，不删。 |

## 目录结构

```text
entry/ AppScope/ hvigor/               鸿蒙 DevEco 工程（必须留在仓库根）
build-profile.json5 hvigorfile.ts oh-package.json5
app-ios-android/                       iOS + Android（CJMP / Keels）：lib/ 源码、fonts/、scripts/（构建与检查脚本）
engine/
  shared/                              共用仓颉 Zip 引擎 + levels.json
  shared-test/                         引擎的 cjpm 测试模块
  include/yilu_zip.h                   旧原生壳用的 C ABI 头文件
  scripts/check_level.py               共用关卡一致性检查
  ENGINE.md                            引擎说明
boards-locked/                         锁定的 100 关棋盘数据（10 章 JSON），关卡的源头
tools/                                 求解器、关卡生成、规则测试、鸿蒙 verify 脚本（tools/verify）
design/                                设计资产：icons/（撤销/重绘 SVG）、mockups/（章节皮肤稿）
third_party/                           第三方字体许可说明（Noto Serif SC）
docs/                                  文档与历史记录（见下）
legacy/                                已废弃的旧 iOS / Android 原生壳
.cursor/skills/                        verify-yilu-xundian 鸿蒙 verify skill
```

文档索引（`docs/`）：

- [harmony-build.md](docs/harmony-build.md)：用 DevEco 编译运行鸿蒙版
- [harmony-architecture.md](docs/harmony-architecture.md)：引擎 / 规则 / 皮肤分层，工程形状
- [harmony-api-notes.md](docs/harmony-api-notes.md)：用到的仓颉 / ArkUI API 的文档依据
- [design-tokens.md](docs/design-tokens.md)：设计师 token
- [level-name-sources.md](docs/level-name-sources.md)：驿名的史地依据
- [history/native-shell-gates.md](docs/history/native-shell-gates.md)：旧原生壳的门禁 / 冒烟记录
- [verify-proof/](docs/verify-proof/20260916T092315Z/PROOF.md)：鸿蒙 verify 的留档证据

## 怎么编

- **鸿蒙**：本机 DevEco Studio 打开仓库根，步骤见 [docs/harmony-build.md](docs/harmony-build.md)。本仓库没有在 CI / 云主机上编出 HAP（没有 DevEco / 仓颉鸿蒙工具链）。
- **iOS / Android**：装好 CJMP OpenSDK 0.2.2 后运行 `app-ios-android/scripts/build_from_repo.sh [--android] [--ios] [--auto-venv]`，前置条件见 [app-ios-android/README.md](app-ios-android/README.md)。iOS 需要 Mac + Xcode，Android 需要 SDK + NDK。
- **引擎测试**：`cd engine/shared-test && cjpm test`（需要仓颉 SDK）。
- **不用编译器就能跑的检查**：见下文「本机检查」。


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

## 关卡 JSON（锁定 100 关，ids 0..99）

路径：`entry/src/main/resources/rawfile/levels.json`（给求解器用）。应用内用同内容的仓颉字面量 `entry/src/main/cangjie/levels.cj`——**未采用** rawfile 读取 API，因为仓颉 1.1.3 的资源读取绑定未在官方文档里核对到可安全使用的写法。

可玩目录是锁定的 **10 章 × 10 关（共 100 关，ids 0..99）**，逐字来自 `boards-locked/ch1_zhuo.json` … `ch10_beifa.json`。ch1–ch3 为 6×6（30 关），ch4–ch10 为 7×7（70 关）。盘名原文上架，禁止再发明关卡或改驿站坐标。平原在 `cleared >= 10` 后可入；每一章都在 `cleared >= levelStart`（0 / 10 / … / 90）后可入，投袁…北伐在未解锁时点开是皮肤预览（`ChapterCatalog.hasSkinPreview`）。

```json
{"id":0,"name":"涿郡·涿","cols":6,"rows":6,"waypoints":[{"n":1,"x":3,"y":2},{"n":2,"x":3,"y":5},{"n":3,"x":0,"y":1},{"n":4,"x":4,"y":4},{"n":5,"x":4,"y":1},{"n":6,"x":0,"y":0}],"walls":[],"parityEdges":[],"stepLimit":0}
```

（上例抄自 `levels.json` id 0，不是示意盘。有机制的关另带可选键：`ferry` / `one_ways` / `slide_cells` / `seal_gates` / `token_cells` / `collapse` / `burden`；奇偶关带 `parityEdges`。）

- `x` 列、`y` 行，原点左上。
- `walls` 是正交相邻格之间的边；没有墙则为 `[]`。
- 求解器：哈密顿路径、四向、驿站按号顺序、墙挡住正交边。

| 章 | 卡片 | ids | 关数 | 首关 | 末关 | 尺寸 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 第1章 涿郡 | 0–9 | 10 | 涿郡·涿 | 涿郡·安喜·第 2 驿 | 6×6 |
| 2 | 第2章 平原 | 10–19 | 10 | 平原·高唐 | 平原·祝阿·第 2 驿 | 6×6 |
| 3 | 第3章 徐州 | 20–29 | 10 | 徐州·郯 | 徐州·海西·第 2 驿 | 6×6 |
| 4 | 第4章 吕布 | 30–39 | 10 | 吕布·下邳·第 1 驿 | 吕布·下邳·第 4 驿 | 7×7 |
| 5 | 第5章 投袁 | 40–49 | 10 | 投袁·青州 | 投袁·㶏强·第 2 驿 | 7×7 |
| 6 | 第6章 荆州 | 50–59 | 10 | 荆州·新野 | 荆州·公安·第 2 驿 | 7×7 |
| 7 | 第7章 赤壁 | 60–69 | 10 | 赤壁·樊口 | 赤壁·鄂·第 2 驿 | 7×7 |
| 8 | 第8章 入蜀 | 70–79 | 10 | 入蜀·江州 | 入蜀·成都·第 2 驿 | 7×7 |
| 9 | 第9章 汉中南中 | 80–89 | 10 | 汉中·阳平关 | 南中·滇池·第 2 驿 | 7×7 |
| 10 | 第10章 北伐 | 90–99 | 10 | 北伐·箕谷 | 北伐·五丈原 | 7×7 |

章名 / 关数 / 首末关 / 尺寸与 `levels.json`（及 `tools/build_levels.py` 的 `EXPECTED_NAMES`）一致，共 100 行；逐关的驿名 / 尺寸 / 驿站数 / 墙数以 `levels.json` 本身为准。


## 独立求解器

```bash
python3 tools/solve_levels.py
python3 tools/test_rules.py
```

`solve_levels.py` 与应用代码无关，用回溯证明每关至少一条解。未通过的关不得入库。全量求解：`python3 tools/solve_levels.py`（对 100 关逐关求解）。若 DFS 超时：关卡仍保留、驿站坐标不改，结果表中该关标 `TIMEOUT`（超时**不算**通过），退出码为 3。

退出码（`exit_code_strict` / `main`）：`0` = 全部有解；`1` = 存在已证明无解的关；`2` = 数据或参数错误（缺文件、非 100 关、坏 `--ids`、schema 不合法）；`3` = 不存在无解关但有超时关。

生成的 `entry/src/main/cangjie/levels.cj` **携带 `ferry`**（渡口：`levelsN.ferry = Some(FerryDef(...))`，共 8 关 52/57/59/60/63/67/87/89；`entry/src/main/cangjie/game/{level,patrol}.cj` 实现了进甲一次输入推 `[甲,乙]`）。其余机制键仍**不携带**（`one_ways` / `slide_cells` / `seal_gates` / `token_cells` / `collapse` / `burden`；HarmonyOS 路径不在这些机制的范围内）。CJMP / iOS / Android 路径经 `mobile/shared/src/game/json_level.cj` 读取 `levels.json`。

`tools/build_levels.py` **只**把已验证的 `levels.json` 抄成仓颉字面量，不生成路径、不发明关卡。改关后必须先改 JSON，再：

```bash
python3 tools/build_levels.py
python3 tools/solve_levels.py
python3 tools/test_rules.py
```

禁止随机乱画格子当关卡。


## 显示名

- 应用名 / Ability label：`驿路巡点`
- bundleName：`com.yilu.xundian`

## 本机检查

```bash
python3 tools/solve_levels.py                  # 100 关逐关求解
python3 tools/test_rules.py                    # 规则 / 目录 / UI 契约测试
python3 tools/replay_locked_paths.py           # boards-locked 归档路径重放
python3 tools/check_parity_wire.py
python3 engine/scripts/check_level.py          # 共用关卡一致性
python3 -m unittest discover -s tools/verify -p test_skill_doctor_contract.py
python3 app-ios-android/scripts/check_ui_diffs.py --selftest   # app-ios-android/scripts/check_*.py 同类
```

当前环境：`cjc` / DevEco / CJMP SDK **不存在**，因此没有声称编过 HAP / APK / iOS 包，也无法在真机上对照六张手稿逐像素验收。
