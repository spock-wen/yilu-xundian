# CJMP (Keels) 移动端应用基座

`mobile/cjmp` 是基于 CJMP OpenSDK 0.2.2 与 Keels 工具链构建的 iOS / Android 跨平台应用源码（M1 基座）。

> **说明**：本项目独立于 `ios/` 与 `android/` 下的原生 UIKit / Kotlin 宿主壳，原有的原生壳保持原样未做任何修改。

## 目录结构

- `lib/`：应用源码与模块逻辑。包含页面入口、关卡数据加载及与引擎交互的逻辑。
- `fonts/`：精简后的字形子集字体文件（`YiluSerif-Regular.otf`、`YiluSerif-Bold.otf`；`YiluSans-Regular.ttf`、`YiluSans-Medium.ttf`、`YiluSans-Bold.ttf`）、字表定义（`charset.txt`；`charset_serif.txt` / `yilu_sans_chars.txt` 由 `check_fonts.py` 自动生成）与开源许可（`OFL.txt`）。
- `scripts/`：工具脚本。
  - `build_from_repo.sh`：**唯一文档化的构建命令**（见下文）。
  - `sync_to_keels.sh`：将源码、共用引擎、关卡 JSON 与资源同步至 Keels 工程（仅拷贝代码引用到的 PNG，并清除 rawfile 目录中过期的未引用 PNG）。
  - `check_fonts.py`：逐字族（serif/sans）严格字形覆盖检查，无任何回退；写出生成 `charset_serif.txt` / `yilu_sans_chars.txt`。
  - `subset_fonts.py`：基于实际关卡与代码文本提取字符集并子集化 Noto Serif SC 字体。

## 环境准备

构建前需：

1. **CJMP OpenSDK 0.2.2 环境脚本**：使 `keels` CLI 进入 PATH 并设置 `CJMP_SDK_HOME`。该脚本路径因机器而异（勿在脚本中硬编码），例如 `source ~/orca/cjmp/env.sh`（示例路径，以本机实际为准）。
2. `python3` 在 PATH 上；字形检查依赖 `fontTools`（`python3 -m pip install fonttools`，或使用 `--auto-venv` 标志让脚本自动在 `mobile/cjmp/.venv` 创建并安装，也可以通过设置 `YILU_PY` 环境变量指定含有该依赖的 Python 解释器路径）。
3. **Xcode**（iOS 构建，需 iOS 15.0 部署目标）。
4. **Android SDK + NDK 26.3.11579264**（Android 构建）。

## 一条命令构建

在任意工作目录运行：

```bash
mobile/cjmp/scripts/build_from_repo.sh [--out DIR] [--android] [--ios] [--auto-venv]
```

- 默认同时构建双平台；`--android` / `--ios` 只构建对应平台。
- 默认输出目录为 `<仓库>/mobile/cjmp/.host/`（已被 `.gitignore` 忽略），可用 `--out` 覆盖。
- 脚本会自动完成：创建 Keels 工程 → **打三个已知模板补丁**（见下）→ 同步源码与资源 → `check_level.py` 与 `check_fonts.py` 校验 → `keels build apk` / `keels build ios-sim` → 打印产物路径、SHA-256 与包名。
- 最终输出 `BUILD_FROM_REPO OK`。

## 已知 Keels 模板补丁（脚本自动处理）

1. **FindClass 包名 bug**：`keels create -n xundian --org com.yilu` 生成的 `android/app/src/main/cpp/xundian.cpp` 中，`g_jniEnv->FindClass("com/example/xundian/xundian")` 硬编码了 `com.example`，与命名空间 `com.yilu.xundian` 不符，导致启动即 `ClassNotFoundException com.example.xundian.xundian` 崩溃。脚本将其修补为 `com/yilu/xundian/xundian` 并校验。
2. **iOS 部署目标**：模板生成的 `IPHONEOS_DEPLOYMENT_TARGET = 12.0`（project.pbxproj 中 4 处）在 Xcode 26/27 SDK 下无法构建，脚本统一修补为 `15.0` 并校验。
3. **UIScene 生命周期（iOS 27 SDK 要求，TN3187）**：脚本（`patch_ios_scene.py`）在生成的 iOS 宿主里补 `UIApplicationSceneManifest`、新增 `SceneDelegate`、把窗口/根控制器创建从 AppDelegate 移到 scene willConnect；`StageApplication` 初始化保留在 AppDelegate。构建后（STEP G）校验 .app 的 Info.plist 及可执行文件。注意：补丁锚点按 Keels 引擎样例工程编写，尚未在 `keels create` 0.2.2 实际生成物上确认，首次 Mac 构建若报 template changed 需按实际模板调整。
4. **系统栏/白带（顶部状态栏区域）**：iOS：Keels 模板把根控制器（EntryEntryAbilityViewController）放进 UINavigationController，导航栏可见且 setNaviAppearance 把背景设成 whiteColor、窗口背景也是 whiteColor，iPhone 17 Pro（iOS 27）上状态栏+导航栏合计 116pt 纯白（iPhone 16/iOS 18 上 98pt），Keels 视图从导航栏下沿才开始。`patch_ios_scene.py patch --bars hide|paper|off`，`build_from_repo.sh` 通过环境变量 `YILU_IOS_BARS` 传入，**默认 hide**（方案 B 的 iOS 默认）：使用 `YiluNavigationController` 隐藏导航栏，UIWindow、UINavigationController 视图及根 VC 视图均设纸色 `#F3E8D6`，强制浅色模式（overrideUserInterfaceStyle = Light），状态栏样式覆写为深色内容 `UIStatusBarStyleDarkContent`。hide 模式必须配合仓颉根容器 safe-top / safe-bottom padding（已同批合入；未设置 `YILU_SAFE_TOP` 时内容会贴到状态栏下）；同时注入 safe area inset 环境变量导出钩子（通过 `setenv` 导出 `YILU_SAFE_TOP` 与 `YILU_SAFE_BOTTOM`，ASCII 十进制整数，单位 1/100 逻辑点；负数/NaN 记为 0）。注入时机已按 Mac E2/E3/E8 实测（2026-10-04，iPhone 17 402×874 pt、iOS 27.0、Xcode 27.0）固化：`makeKeyAndVisible`+`layoutIfNeeded` 之后导出第一次（早于会触发 viewDidLoad 的 `viewController.view.backgroundColor` 访问），`rootViewController` 赋值之后再导出一次（实测此时 window.safeAreaInsets=(62,0,34,0)，iPhone 17 的 safeAreaTop 为 62、iPhone 16 为 59），并在 `YiluNavigationController` 的 `viewSafeAreaInsetsDidChange`/`viewWillTransitionToSize:` completion 与 `sceneDidBecomeActive:` 里补读——实测 vc.view.safeAreaInsets 在 viewDidLoad/viewWillAppear 仍为 0，要到 viewSafeAreaInsetsDidChange 之后才非 0，故一律读 window/导航控制器 view 而非根 VC view；E8 实测仓颉 `getVariable` 能读到宿主 setenv（YILU_SAFE_TOP=6200，逐字节 ASCII 解析无误）。E3 实测：模板主 VC edgesForExtendedLayout=UIRectEdgeNone，hide 模式导航栏隐藏后 vc.view 全屏 (0,0,402,874)、无白带，无需改 edgesForExtendedLayout。另外提供两个可选模式：`paper` 为保留导航栏但整体染纸色 `#F3E8D6`、去阴影细线、强制浅色模式（Mac 实测 ΔRGB=0、内容起点与 off 相同）；`off` 保持模板原样（纯白背景）。补丁锚点已在 Mac 的 `keels create` 0.2.2 实际生成物上跑通（hide/paper/off 三次构建均 BUILD_FROM_REPO OK + check-app OK）。Android：`patch_android_bars.py`（STEP C4）在 onPostCreate 把状态栏/导航栏设成 `#F3E8D6` 并用浅色图标，但**默认不执行**（`YILU_ANDROID_BARS` 默认 off，构建日志打印 skipping (default off)，仅显式 `YILU_ANDROID_BARS=on` 时运行）——Mac 实测 API35 模拟器（A411 挖孔）上零视觉效果：dumpsys 证实补丁 flags 生效（LIGHT_STATUS/NAVIGATION_BAR），但顶部 128px 黑块是挖孔 inset（`mDisplayCutout` top=128px > 状态栏 63px），应用窗口被放在挖孔之下，`setStatusBarColor` 画不到那里；真正消除需 edge-to-edge + cutout 方案（方案 B，另议），真机/无挖孔设备可显式 `YILU_ANDROID_BARS=on` 复测。已知局限：章节页的 paper 色（`Theme.paperOf`）与 `#F3E8D6` 略有差异，系统栏只能用固定色；iOS hide/paper 均强制浅色模式，深色模式下的表现待确认。

## 包名

Android namespace / applicationId 与 iOS bundle identifier 均为 `com.yilu.xundian`（`keels create --org com.yilu`）。
**正式上架前的最终包名待定，发布前需确认。**

## 资源同步策略（仅拷贝被代码引用的 PNG）

`sync_to_keels.sh` 以正则 `rawImg("([A-Za-z0-9_]+)")` 扫描 `mobile/cjmp/lib/*.cj` 收集引用名；任一被引用 PNG 缺失即失败退出。media 目录中存在但未被引用的 PNG 会从 rawfile 目录中清除（仅清理这些文件）。当前 49 张 PNG 中有 44 张被引用，排除的 5 张及原因：

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
- sans ← `sansFamily()` / `sansMediumFamily()` / `sansBoldFamily()` / `Theme.sans` / `Theme.sansMedium` / `Theme.sansBold`（`sansBold` 校验由专用 sans-bold 子族对 YiluSans-Bold.ttf 执行，仅用于首页「章节」）

可选中的字符集来自解析 `Text(...)` / `Button(...)` 及其后链式 `.fontFamily(...)`：静态字符串按其字面字符计入；含 `${...}` 插值或非字面量表达式则计入「动态数据字符集」（chapter.cj 全部字符串字面量 + levels.json 所有关卡 `name` + 数字 0-9 + 全部可打印 ASCII）。任何未被 `.fontFamily(...)` 覆盖的 `Text`/`Button` 视为错误（`NO_FAMILY` —— 全部文字必须使用内置字体，绝不允许系统字体）。

## 进度存档

- **当前状态**：已实现落盘。纯逻辑 `lib/progress.cj`（编解码、校验、`ProgressStore`、`ProgressBackend` 接口），后端 `lib/progress_io.cj`（std.fs 文件后端 `FileProgressBackend` + 纯函数 `progressPickDir` + 工厂 `makeProgressBackend`），`index.cj` 接线（启动 `aboutToAppear` 读取、通关时写）。selftest J23（纯逻辑）与 J24（真实 std.fs 文件，写 /tmp）覆盖。Android 宿主补丁 `scripts/patch_android_filesdir.py`（带 `selftest` 子命令）已接入 `build_from_repo.sh` 的 STEP C3。真机/模拟器上的实际落盘尚未验证（见已知问题）。
- **存档格式**：`{"v":1,"cleared":N}`；`cleared` = 已通关数（0..总关数，总关数取 `levels.size`，当前 100）；`v` 不为 1、JSON 损坏、负数、非整数、超长数字一律按 0；超过总关数则截断到总关数；写失败只打一行 `[progress] save failed` 并降级为内存。
- **存档位置与目录选择规则**：文件名 `progress.json`（写入 `progress.json.tmp` 再 rename 覆盖，成功后不残留 tmp）。目录：先取环境变量 `YILU_FILES_DIR`（Android 宿主补丁在 Activity.onCreate 里 `android.system.Os.setenv` 设为 `getFilesDir()`，即 `/data/data/com.yilu.xundian/files`），其次 `HOME` 非空且不是 `/` 时用 `$HOME/Documents`（iOS，HOME 即 app 数据容器），都没有则用 Null 后端（不落盘）。不调用 `std.env.getHomeDirectory()`（pw_dir 为 NULL 时可能崩）。目录不存在会自动创建。
- **已知问题**：**Android 补丁锚点（Keels `keels create` 0.2.2 生成物里的 `setInstanceName(...)` 行）和 iOS 的 HOME 目录需在真机/模拟器上确认**；锚点变化时 build_from_repo.sh 会明确报错退出；Android 返回键补丁用 moveTaskToBack，进程存活，不能当「杀进程」；iOS 的 Documents 在备份/文件共享范围内属实现细节，未评估。
- **清除办法**：Android `adb shell pm clear com.yilu.xundian`（或 `adb shell run-as com.yilu.xundian rm files/progress.json`）；iOS 模拟器 `xcrun simctl uninstall booted com.yilu.xundian`（卸载会删除数据容器）。不提供 App 内清除入口（PM 已定）。
- **验证要点**：杀进程必须用 `adb shell am force-stop com.yilu.xundian` / `xcrun simctl terminate booted com.yilu.xundian`，不能用返回键。检查落盘：Android `adb shell run-as com.yilu.xundian cat files/progress.json`（debug 包）；iOS `xcrun simctl get_app_container booted com.yilu.xundian data` 下的 `Documents/progress.json`。步骤：通第 1 关 → 文件应为 `{"v":1,"cleared":1}` → 杀进程 → 重启 → 首页「已通 1」→ 点「开始」应进入第 2 关 → 清除 → 重启回到只开第一关。

## 已知问题与变通方案 (Workarounds)

- **资源引用**：CJMP OpenSDK 0.2.2 暂不支持 `@r` 语法，图片与媒体资源统一通过 `resource://RAWFILE/` 协议路径加载。
- **字体注册**：由于公共字体注册 API 限制，字体通过引擎底层私有 FFI 符号 `FfiFontManagerRegisterFont` 配合 `dlsym` 进行动态注册（属内部私有符号，后续 SDK 版本可能调整）。
- **页面返回（方案 A2，页内返回按钮）**：iOS 系统的侧滑返回手势在当前容器下不可用，Android 的系统返回键在此桥接容器内不会天然触发页面回退，因此所有子页面均内置页面内返回按钮 `〈`（方案 A2）；Android 系统返回键被映射为触发同一页内返回按钮的处理逻辑，保证双端返回行为一致。
- **安全区与状态栏**：iOS 默认启用方案 B edge-to-edge（`--bars hide`），状态栏下为各页底色（原生壳与根 VC 背景 #F3E8D6，状态栏深色文字），由仓颉 safe-top/safe-bottom padding 避开安全区；安全区 inset 由宿主在 `makeKeyAndVisible` 及 `sceneDidBecomeActive:` 导出环境变量 `YILU_SAFE_TOP` 与 `YILU_SAFE_BOTTOM`（ASCII 十进制整数，单位 1/100 逻辑点；具体时机与实测值待 Mac E2/E3/E8 核验）；详细机制见上文「已知 Keels 模板补丁」第 4 条。
- **棋盘实现**：M2 起棋盘由 shape 组件（Rect/Line/Circle/Path 等，非 Canvas）绘制，托盘与格宽基于 BoardGeom 几何计算（间隙 6vp，见 lib/board.cj）。
- 仓颉编译器（CJMP OpenSDK 0.2.2 cjc）偶发随机崩溃/失败，重跑即可；且构建产物不可逐字节复现，因此脚本打印的 APK / iOS 二进制 SHA-256 仅供参考（用于核对同一次构建的传递），不作为版本一致性依据。
- **特殊机制与修缮关卡**：6 种核心特殊机制及修缮关卡暂未实现，计划在 M3 里程碑实现。

## 字体许可

字体基于 Noto Serif SC 与 Noto Sans SC，遵循 SIL Open Font License 1.1 开源协议。详情请参阅 `fonts/OFL.txt`。
- **YiluSerif**（Regular / Bold，CFF OTF）：Noto Serif SC 子集。
- **YiluSans**（Regular 400 / Medium 500 / Bold 700，TrueType）：Noto Sans SC 可变字体实例化 400/500 后的子集；Bold 700（TrueType，136672 字节）来自 addendum-d04 外部来源（sha256 前缀 `7e46ee679e9d`），仅用于首页「章节」。

### 字体子集化（可复现）

脚本：`scripts/subset_yilu_fonts.py`（仅依赖 Python 3 + fontTools，已用 fontTools 4.66 验证）。字表即事实来源：`fonts/yilu_serif_chars.txt`（369 字）与 `fonts/yilu_sans_chars.txt`（359 字）；`fonts/charset.txt` 与 serif 字表相同。`check_fonts.py` 另行生成 `charset_serif.txt` / `charset_sans.txt`（运行所需字符，仅供参考）。

官方源文件（sha256 已在脚本中固定，下载后校验，不符即中止）：

| 源 | URL | sha256 |
|---|---|---|
| NotoSansSC[wght].ttf（google/fonts `ofl/notosanssc` @ a85815a，v2.004-H2） | https://github.com/google/fonts/raw/a85815a42757630ce188fdad368c2dfc444d4773/ofl/notosanssc/NotoSansSC%5Bwght%5D.ttf | a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da |
| Sans OFL.txt | https://raw.githubusercontent.com/google/fonts/a85815a42757630ce188fdad368c2dfc444d4773/ofl/notosanssc/OFL.txt | 1c05c68c34f9708415aada51f17e1b0092d2cea709bf4a94cd38114f9e73d7d9 |
| NotoSerifSC-Regular.otf（notofonts/noto-cjk `Serif/SubsetOTF/SC` @ f8d1575，v2.003） | https://github.com/notofonts/noto-cjk/raw/f8d157532fbfaeda587e826d4cd5b21a49186f7c/Serif/SubsetOTF/SC/NotoSerifSC-Regular.otf | e8f396decc1f0963a016a989c3d8852e863d1350996f573860a80767c83a1cd3 |
| NotoSerifSC-Bold.otf（同上） | https://github.com/notofonts/noto-cjk/raw/f8d157532fbfaeda587e826d4cd5b21a49186f7c/Serif/SubsetOTF/SC/NotoSerifSC-Bold.otf | 24693d48bdb9152f0a06b02af625638a1097abd6de4010ebba027f6e82710527 |
| Serif LICENSE（SIL OFL 1.1） | https://raw.githubusercontent.com/notofonts/noto-cjk/f8d157532fbfaeda587e826d4cd5b21a49186f7c/Serif/LICENSE | 6a73f9541c2de74158c0e7cf6b0a58ef774f5a780bf191f2d7ec9cc53efe2bf2 |

命令（在仓库根目录）：

```
python3 mobile/cjmp/scripts/subset_yilu_fonts.py fetch  --src-dir /tmp/yilu-font-src
python3 mobile/cjmp/scripts/subset_yilu_fonts.py build  --src-dir /tmp/yilu-font-src   # 实例化 + 子集化，改写 fonts/ 下四个字体与字表
python3 mobile/cjmp/scripts/subset_yilu_fonts.py verify --old-dir <旧字体目录> [--json report.json]   # 逐字形对比旧/新子集
```

等价的 pyftsubset 参数——Sans（先用 `fontTools.varLib.instancer` 取 wght=400/500，得到的静态字体与设计交付时的中间件逐字节一致）：`--text-file=fonts/yilu_sans_chars.txt --no-hinting --desubroutinize --layout-features='*' --name-IDs='*' --notdef-outline --glyph-names=false`；Serif：`--text-file=fonts/yilu_serif_chars.txt --no-hinting --glyph-names=false`。

字表在保留原有全部字符的基础上新增 13 个字：`甲乙符滑渡负塌泽停闸门禁此`（YiluSerif 与 YiluSans 均已收录；`此` 原本已在 YiluSerif 中，故 YiluSerif 实际新增 12 字、YiluSans 新增 13 字）。`verify` 结果：原有字符（serif 357、sans 346）的字形轮廓与横/纵向 advance 与旧子集逐字一致（0 差异），OpenType 特性标签不变。以后增字只需在字表文件中追加字符后重跑 `build`。

字体大小（字节）：YiluSerif-Regular 89780→93508，YiluSerif-Bold 89336→93132，YiluSans-Regular 134796→138048，YiluSans-Medium 134732→137984，YiluSans-Bold 136672（外部来源 addendum-d04）。

