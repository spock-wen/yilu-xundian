# CJMP (Keels) 移动端应用基座

`mobile/cjmp` 是基于 CJMP OpenSDK 0.2.2 与 Keels 工具链构建的 iOS / Android 跨平台应用源码（M1 基座）。

> **说明**：本项目独立于 `ios/` 与 `android/` 下的原生 UIKit / Kotlin 宿主壳，原有的原生壳保持原样未做任何修改。

## 目录结构

- `lib/`：应用源码与模块逻辑。包含页面入口、关卡数据加载及与引擎交互的逻辑。
- `fonts/`：精简后的字形子集字体文件（`YiluSerif-Regular.otf`、`YiluSerif-Bold.otf`；`YiluSans-Regular.otf`、`YiluSans-Medium.otf` 待设计交付，见 `fonts/PENDING_SANS.md`）、字表定义（`charset.txt`；`charset_serif.txt` / `charset_sans.txt` 由 `check_fonts.py` 自动生成）与开源许可（`OFL.txt`）。
- `scripts/`：工具脚本。
  - `build_from_repo.sh`：**唯一文档化的构建命令**（见下文）。
  - `sync_to_keels.sh`：将源码、共用引擎、关卡 JSON 与资源同步至 Keels 工程（仅拷贝代码引用到的 PNG，并清除 rawfile 目录中过期的未引用 PNG）。
  - `check_fonts.py`：逐字族（serif/sans）严格字形覆盖检查，无任何回退；写出生成 `charset_serif.txt` / `charset_sans.txt`。
  - `subset_fonts.py`：基于实际关卡与代码文本提取字符集并子集化 Noto Serif SC 字体。

## 环境准备

构建前需：

1. **CJMP OpenSDK 0.2.2 环境脚本**：使 `keels` CLI 进入 PATH 并设置 `CJMP_SDK_HOME`。该脚本路径因机器而异（勿在脚本中硬编码），例如 `source ~/orca/cjmp/env.sh`（示例路径，以本机实际为准）。
2. `python3` 在 PATH 上；字形检查依赖 `fontTools`（`python3 -m pip install fonttools`）。
3. **Xcode**（iOS 构建，需 iOS 15.0 部署目标）。
4. **Android SDK + NDK 26.3.11579264**（Android 构建）。

## 一条命令构建

在任意工作目录运行：

```bash
mobile/cjmp/scripts/build_from_repo.sh [--out DIR] [--android] [--ios] [--pending-sans-ok]
```

- 默认同时构建双平台；`--android` / `--ios` 只构建对应平台。
- 默认输出目录为 `<仓库>/mobile/cjmp/.host/`（已被 `.gitignore` 忽略），可用 `--out` 覆盖。
- 脚本会自动完成：创建 Keels 工程 → **打两个已知模板补丁**（见下）→ 同步源码与资源 → `check_level.py` 与 `check_fonts.py` 校验 → `keels build apk` / `keels build ios-sim` → 打印产物路径、SHA-256 与包名。
- 最终输出 `BUILD_FROM_REPO OK`；若带了 `--pending-sans-ok` 且两个 sans 字体仍缺失，则输出带 PENDING 横幅的 `BUILD_FROM_REPO OK (PENDING SANS)`，**不可用于发布**。

## 已知 Keels 模板补丁（脚本自动处理）

1. **FindClass 包名 bug**：`keels create -n xundian --org com.yilu` 生成的 `android/app/src/main/cpp/xundian.cpp` 中，`g_jniEnv->FindClass("com/example/xundian/xundian")` 硬编码了 `com.example`，与命名空间 `com.yilu.xundian` 不符，导致启动即 `ClassNotFoundException com.example.xundian.xundian` 崩溃。脚本将其修补为 `com/yilu/xundian/xundian` 并校验。
2. **iOS 部署目标**：模板生成的 `IPHONEOS_DEPLOYMENT_TARGET = 12.0`（project.pbxproj 中 4 处）在 Xcode 26/27 SDK 下无法构建，脚本统一修补为 `15.0` 并校验。

## 包名

Android namespace / applicationId 与 iOS bundle identifier 均为 `com.yilu.xundian`（`keels create --org com.yilu`）。
**正式上架前的最终包名待定，发布前需确认。**

## 资源同步策略（仅拷贝被代码引用的 PNG）

`sync_to_keels.sh` 以正则 `rawImg("([A-Za-z0-9_]+)")` 扫描 `mobile/cjmp/lib/*.cj` 收集引用名；任一被引用 PNG 缺失即失败退出。media 目录中存在但未被引用的 PNG 会从 rawfile 目录中清除（仅清理这些文件）。当前 41 张 PNG 中有 36 张被引用，排除的 5 张及原因：

| PNG | 排除原因 |
|-----|----------|
| `app_icon` | HarmonyOS 启动器图标，仅由 `entry/src/main/module.json5` 使用 |
| `band_terrain_pingyuan_v91` | v91 band 素材的地形专用图层，仓库内无任何代码引用；CJMP 使用合成后的 `band_*_v91` |
| `band_terrain_zhuojun_v91` | 同上 |
| `skin_01_zhuojun_v91` | 开放章节 1 的章节皮肤，仅登记在 HarmonyOS 资产清单 `tools/test_rules.py`；CJMP 无展示开放章节皮肤的页面 |
| `skin_02_pingyuan_v91` | 同上 |

SVG 图标（`icon-undo`、`icon-reset`）与字体的同步行为不变。

## 逐字族字体检查（无回退）

- serif ← `serifFamily()` / `serifBoldFamily()` / `Theme.serif` / `Theme.serifBold`
- sans ← `sansFamily()` / `sansMediumFamily()` / `Theme.sansRegular` / `Theme.sansMedium`

可选中的字符集来自解析 `Text(...)` / `Button(...)` 及其后链式 `.fontFamily(...)`：静态字符串按其字面字符计入；含 `${...}` 插值或非字面量表达式则计入「动态数据字符集」（chapter.cj 全部字符串字面量 + levels.json 所有关卡 `name` + 数字 0-9 + 全部可打印 ASCII）。任何未被 `.fontFamily(...)` 覆盖的 `Text`/`Button` 视为错误（`NO_FAMILY` —— 全部文字必须使用内置字体，绝不允许系统字体）。

sans 两个字体文件全部缺失时，构建可用 `--pending-sans-ok` 宽松通过（exit 3，结果不可发布）；只缺其中一个仍然失败。详见 `fonts/PENDING_SANS.md`。

## 已知问题与变通方案 (Workarounds)

- **资源引用**：CJMP OpenSDK 0.2.2 暂不支持 `@r` 语法，图片与媒体资源统一通过 `resource://RAWFILE/` 协议路径加载。
- **字体注册**：由于公共字体注册 API 限制，字体通过引擎底层私有 FFI 符号 `FfiFontManagerRegisterFont` 配合 `dlsym` 进行动态注册（属内部私有符号，后续 SDK 版本可能调整）。
- **页面返回（方案 A2，页内返回按钮）**：iOS 系统的侧滑返回手势在当前容器下不可用，Android 的系统返回键在此桥接容器内不会天然触发页面回退，因此所有子页面均内置页面内返回按钮 `〈`（方案 A2）；Android 系统返回键被映射为触发同一页内返回按钮的处理逻辑，保证双端返回行为一致。
- **安全区与状态栏**：安全区及状态栏间距当前为占位实现（PLACEHOLDER），等待产品经理（PM）的设计决策最终确定。
- **棋盘实现**：当前棋盘为占位展示，完整巡点交互逻辑将在 M2 里程碑接入。
- **特殊机制与修缮关卡**：6 种核心特殊机制及修缮关卡暂未实现，计划在 M3 里程碑实现。

## 字体许可

字体基于 Noto Serif SC，遵循 SIL Open Font License 1.1 开源协议。详情请参阅 `fonts/OFL.txt`。
