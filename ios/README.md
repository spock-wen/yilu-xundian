# 驿路巡点 iOS 壳

这是鸿蒙应用之外的 **iOS 壳**：仓颉 Zip 引擎交叉编译成静态库，Swift/UIKit 只负责画格子和把手势交给引擎。不是鸿蒙 ArkUI 的移植，也不是用 Swift 重写 Zip 规则。

## SMOKE: PASSED（iOS Simulator，tip `eaf7aed`）

门禁：tester 与 reviewer 在 tip `eaf7aed` 上 PASS。iOS 模拟器进入 **涿郡·范阳（id 1）**。PM 指定的截图目录是 `qa-shots/ios-shell-eaf7aed-gate`。本仓库检出里没有 `qa-shots/`，也没有已跟踪的 `_smoke/`，截图文件不在这次提交里。

**Android** 在 tip `f25f813`：程序员 Mac 冒烟 PASSED，测试门禁 PASS（两件记录，见 [android/README.md](../android/README.md)）。tip `4986524` 曾 FAIL。

此前同一台 Mac（Xcode 27，`CANGJIE_HOME=/Users/spock/sdk/cangjie`，包 `cangjie-sdk-mac-aarch64-ios-1.1.3`）上、更早 tip 的失败记录：

- `cjpm` 编 `aarch64-apple-ios-simulator` 静态库：成功。
- 旧脚本的 `-destination 'generic/platform=iOS Simulator'`：失败。该目标还会链 **x86_64**，仓颉模拟器库只有 arm64，x86_64 切片报 `Undefined symbols: _yilu_*`。
- 只编 arm64（iPhone 16 的 UDID，加上 `EXCLUDED_ARCHS=x86_64` / `ARCHS=arm64`）可以编过并装上（bundle id `com.yilu.xundian.ios`）。`a6c9b53` 的 arm64 脚本在 Mac 上**编译和安装都成功了**。
- `a6c9b53` 启动后不再是早先的 `MRT_TryNewAndRunCJThread` / `FormatLog` abort。运行时已经进了仓颉帧。新的崩溃是 **SIGSEGV** `KERN_PROTECTION_FAILURE`，信息 `Could not determine thread index for stack guard region`，故障地址在 Stack Guard。日志：`YiluXundian-2026-09-26-223058.ips`。触发线程栈顶是 `_CNatUarray$37arrayIndexOutOfBoundsExceptionMessageHll` 与 `numberToString` / `StringBuilder.append` 互相调用，下面才是：

  `_CNat13StringBuilder6appendHi` → `_CNatXk8toStringHv` → `_CN8yilu_zip20yilu_load_level_jsonHk` → `yilu_load_level_json` → `YiluZip.loadBundledLevel`（`YiluZip.swift` 的 `withCString` / `yilu_load_level_json`）→ `BoardViewController.viewDidLoad`。

  仓颉 runtime 标签 [v1.1.3 的 `c_string_resource.cj`](https://github.com/cangjielanguage/cangjie_runtime/blob/v1.1.3/stdlib/libs/std/core/c_string_resource.cj) 里，`CString.toString` 在长度 ≥ [`STRING_C_THRESHOLD` = 32](https://github.com/cangjielanguage/cangjie_runtime/blob/v1.1.3/stdlib/libs/std/core/string_common.cj) 时用 `memcpy_s`，失败则抛 `IllegalMemoryException("... error code: ${rc}.")`，`${rc}` 是 `StringBuilder.append(Int32)`。[`array.cj` 的越界文案](https://github.com/cangjielanguage/cangjie_runtime/blob/v1.1.3/stdlib/libs/std/core/array.cj)再插值下标，同一条 `numberToString` 递归直到栈保护页。本仓库 `ios/app/YiluXundian/level.json` 是 **613** 字节（`wc -c`），会走 ≥32 的分支。本环境不能反汇编 Mac 上的 `.a`，没有把 `toString +540` 逐条指令对上；源码里这条函数唯一的 `append(Int32)` 就是那个 `${rc}`。

`6da2283` 在 Mac 上能编过、能装上。`CString.toString` 那条栈溢出没有再出现。加载解析出了 `LevelDef`，然后在 `PatrolGame.reset` 里崩。日志：`YiluXundian-2026-09-26-225202.ips`。`EXC_BAD_ACCESS` / `SIGSEGV` `KERN_INVALID_ADDRESS at 0x8`。栈：`CJ_MCC_WriteRefField` → `PatrolGame.reset` → `yilu_load_level_json` → `YiluZip.loadBundledLevel` → `viewDidLoad`。

[v1.1.3 `MCC_WriteRefField`](https://github.com/cangjielanguage/cangjie_runtime/blob/v1.1.3/runtime/src/CompilerCalls.cpp) 在对象不是堆地址时执行 `field->SetTargetObject`。故障地址 `0x8` 是空接收者加上对象头之后的第一个引用字段（`this.level`）。全局 `gGame = PatrolGame(blankLevel())` 当时仍是空引用。iOS 只跑名字里带 `_CGP` 的全局初始化（[CjFile.cpp](https://github.com/cangjielanguage/cangjie_runtime/blob/v1.1.3/runtime/src/Loader/BinaryFile/CjFile/CjFile.cpp)）。`eaf7aed` 在 `yilu_load_level_json` 里执行 `gGame = PatrolGame(level)`。这一 tip 的模拟器门禁已进入涿郡·范阳。

## 这一版接上的一关

`entry/src/main/resources/rawfile/levels.json` 的 **id 1「涿郡·范阳」**（6×6，6 个驿站，2 堵墙，`parityEdges: []`，`stepLimit: 0`）。

锁定目录里没有 5×5。id 0「涿郡·涿」是教程盘，但 `walls` 为空。id 1 是涿郡里最早一盘**既有驿站又有墙**、且没有奇偶边的纯 Zip。引擎在 `mobile/shared/`，iOS 与 Android 共用。三份 JSON 必须和 `levels.json` 的这一条相同：

- `mobile/shared/levels/zhuojun-fanyang.json`
- `ios/app/YiluXundian/level.json`（打进 App bundle，启动时整段交给 `yilu_load_level_json`）
- `android/app/src/main/assets/level.json`

不依赖 Xcode 的检查：

```bash
python3 mobile/scripts/check_level.py
```

## 目录

```text
mobile/shared/                    # 包名 yilu_zip，iOS 与 Android 共用，无 ohos / ArkUI
mobile/include/yilu_zip.h         # 同一份 C ABI
ios/
  README.md
  ENGINE.md                       # 指向 mobile/ENGINE.md
  app/                            # Xcode + UIKit
  scripts/build_simulator.sh
```

CJMP / `keels create` **没有**生成这棵树。云环境没有 CJMP SDK，也不能在这里下载私有工具链。可选的 CJMP 前置条件写在文末，本 PR 走官方静态库路径。

## Mac 安装

宿主必须是 **macOS aarch64**。交叉编译表里，编 iOS 的一行就是 macOS (aarch64) + `cangjie-sdk-mac-aarch64-ios`（[交叉编译](https://cj-docs.gitcode.com/zh/1.1.3/dev-guide/source_zh_cn/compile_and_build/cross_compilation.html)）。

1. 安装 **Xcode.app**，并在 Xcode 里装上 iOS 平台（同一页的 “Downloading and installing additional Xcode components”）。CJMP 文档另外要求 Xcode 16+；静态库这条路径按上面的交叉编译页，用本机 Xcode 的 iOS SDK 即可。
2. 打开 [仓颉 1.1.3 下载页](https://cangjie-lang.cn/download/1.1.3)，下载 **`cangjie-sdk-mac-aarch64-ios-1.1.3.tar.gz`**（该页列出的 Mac iOS 包；文档里的写法是 `cangjie-sdk-mac-aarch64-ios.x.y.z.tar.gz`）。不要用鸿蒙 SDK，也不要用只含 macOS 宿主的 `cangjie-sdk-mac-aarch64-1.1.3.tar.gz`。
3. 解压。解压后有 `cangjie/` 目录时，`CANGJIE_HOME` 指到**含 `envsetup.sh` 的那一层**（安装说明是 `source cangjie/envsetup.sh`，见 [安装仓颉工具链](https://docs.cangjie-lang.cn/cjnative/user_manual/source_zh_cn/first_understanding/install_Community.html)）。
4. 路径不要带空格。`build_simulator.sh` 会把该路径写进 xcconfig。

```bash
export CANGJIE_HOME=/absolute/path/to/cangjie
source "$CANGJIE_HOME/envsetup.sh"
cjc -v
xcodebuild -version
```

`cjc -v` 里的 `Target` 是这套 iOS SDK 的默认三元组。模拟器编译用的 `--target` 见下一节。

部署目标：仓颉运行时写的是 **iOS 11+**（交叉编译页）。Xcode 工程把 `IPHONEOS_DEPLOYMENT_TARGET` 设为 **15.0**，因为 [Xcode 16 的系统要求](https://developer.apple.com/xcode/system-requirements/)里，Xcode 16 对应的 iOS 部署/调试范围从 iOS 15 起。模拟器请选 iOS 15 或更新的运行时。

## 编模拟器

在仓库根目录：

```bash
source "$CANGJIE_HOME/envsetup.sh"
ios/scripts/build_simulator.sh
```

脚本依次做：

1. 在 `mobile/shared` 执行 `cjpm build --target aarch64-apple-ios-simulator -V`  
   三元组来自交叉编译页的模拟器条目：`--target=aarch64-apple-ios-simulator`，再加 `--output-type=staticlib`（`mobile/shared/cjpm.toml` 的 `output-type = "static"` 会走到静态库；`-V` 会打印实际 `cjc` 命令）。`cjpm --target` 见 [cjpm 手册](https://docs.cangjie-lang.cn/cjnative/user_manual/tools/source_zh_cn/tools/cjpm_manual_cjnative_community.html)。
2. 用 `/usr/bin/libtool -static` 把 `libyilu_zip*.a` 合成 `ios/app/YiluXundian/Cangjie/libyilu_zip.a`。
3. 写下 `ios/app/Config/Cangjie.local.xcconfig`。链接顺序按交叉编译页：
   - `$CANGJIE_HOME/lib/ios_simulator_aarch64_cjnative/section.o`
   - `$CANGJIE_HOME/lib/ios_simulator_aarch64_cjnative/cjstart.o`
   - `-lc++`
   - `-Wl,-u,_CJ_MRT_CjRuntimeInit`（把运行时初始化从静态库里拉进来）
   - 然后是本仓库的 `libyilu_zip.a`（`-force_load`）和该目录下全部 `.a`
   - 另加 `-Wl,-no_compact_unwind`（同一页：Xcode 15 在 compact unwind 断言失败时需要 `-Wl,-ld_classic` 或 `-Wl,-no_compact_unwind`）
   - `DEAD_CODE_STRIPPING = NO`
4. `xcodebuild` 的模拟器目标是一台 **arm64 iPhone**（已 Booted 的优先，否则 `simctl list devices available` 里第一台 iPhone）。可用 `YILU_SIM_UDID` 指定。同时传入 `ARCHS=arm64 EXCLUDED_ARCHS=x86_64 ONLY_ACTIVE_ARCH=YES`。**不要**再用 `generic/platform=iOS Simulator`：那个目标会去链 x86_64。工程里的 `Cangjie.defaults.xcconfig` 也排除了模拟器的 x86_64。
5. 链接行在交叉编译页的 `section.o`、`cjstart.o`、`-lc++` 之后加了 `-Wl,-u,_CJ_MRT_CjRuntimeInit`，把运行时初始化对象拉进来。`cjstart.o` 只调用 `MRT_LibraryOnLoad`（[aarch64 iOS Cjstart.S](https://github.com/cangjielanguage/cangjie_runtime/blob/main/runtime/src/arch/aarch64_ios/Cjstart.S)），元数据可以先排队、运行时单例仍是空的（[LoaderManager.cpp](https://github.com/cangjielanguage/cangjie_runtime/blob/main/runtime/src/LoaderManager.cpp)）。第一次进 `@C` 时 `Runtime::Current()` 发现单例为空就会 fatal 然后 `abort`（[Runtime.h](https://github.com/cangjielanguage/cangjie_runtime/blob/main/runtime/src/Common/Runtime.h)）。壳在 `yilu_load_level_json` 之前调用 Apple 导出符号 `CJ_MRT_CjRuntimeInit`（[CjScheduler.cpp](https://github.com/cangjielanguage/cangjie_runtime/blob/main/runtime/src/CjScheduler.cpp) 里对 `MRT_CjRuntimeInit` 的别名）。1.1.3 SDK 的崩溃符号名是 `MRT_TryNewAndRunCJThread`，当前开源树里对应函数叫 `MRT_NewForeignCJThread`；本环境不能对 Mac 上的 `.a` 做 `nm`。若链接报 `_CJ_MRT_CjRuntimeInit` 未定义，在 Mac 上查：

```bash
nm -gU "$CANGJIE_HOME/lib/ios_simulator_aarch64_cjnative/"*.a | grep -E 'CjRuntimeInit|TryNewAndRun'
```

脚本编完**不安装、不启动**。Mac 上复验（把 UDID 和 `.app` 路径换成脚本打印的那两行）：

```bash
xcrun simctl boot "$YILU_SIM_UDID"
xcrun simctl install "$YILU_SIM_UDID" ios/app/build/Build/Products/Debug-iphonesimulator/YiluXundian.app
xcrun simctl launch --console "$YILU_SIM_UDID" com.yilu.xundian.ios
```

预期第一屏是 **涿郡·范阳 · id 1**。从标了 1 的格子拖，正交一步交给 `yilu_try_step`；拖回上一格、点「撤销」「重绘驿道」都进仓颉引擎。门禁 tip `eaf7aed` 已经进入这一屏。脚本本身仍然不安装、不启动。

若 `cjc` 不接受默认的 `aarch64-apple-ios-simulator`，把 `YILU_IOS_TARGET` 设成 `cjc -v` 打印的 `Target` 再跑。交叉编译页的模拟器条目没有写 SDK 版本后缀；版本后缀出现在设备示例 `--target=aarch64-apple-ios17.5`（17.5 要换成 `xcrun --sdk iphoneos --show-sdk-version`）。

设备静态库（仍然不签名、不安装到真机）用交叉编译页的设备示例形式，版本号换成 `xcrun --sdk iphoneos --show-sdk-version`：

```bash
export YILU_IOS_TARGET=aarch64-apple-ios17.5
ios/scripts/build_simulator.sh
```

这时脚本改用 `ios_aarch64_cjnative` 和 `xcodebuild -sdk iphoneos`。真机签名不在这一版里。

产物 `libyilu_zip.a`、`Cangjie.local.xcconfig`、`mobile/shared/target/`、`ios/app/build/` 都不提交。

## 可选：CJMP / keels

没有在本仓库跑过 `keels create`。若以后改走 CJMP，而不是这条静态库路径，[CJMP start-overview](https://gitcode.com/CJMP/Docs/blob/main/zh-cn/app-dev/quick-start/start-overview.md) 和 [start-tools](https://gitcode.com/CJMP/Docs/blob/opensource/zh-cn/app-dev/quick-start/start-tools.md) 写的是：

- `CJMP_SDK_HOME` 指到 SDK 根目录，并把 `$CJMP_SDK_HOME/cjmp-tools/bin` 放进 `PATH`
- Xcode 16.0+（不要装多个版本）
- `IOS_SDK_DIR=/Applications/Xcode.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS.sdk`
- 模拟器 SDK 目录（overview 页上的变量名以该页为准）：`/Applications/Xcode.app/Contents/Developer/Platforms/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator.sdk`
- Homebrew、Ruby、`xcodeproj`
- `keels doctor` 检查 Xcode、Ruby、xcodeproj
- 创建与运行：

```bash
"$CJMP_SDK_HOME/cjmp-tools/bin/keels" create demo
cd demo
"$CJMP_SDK_HOME/cjmp-tools/bin/keels" run
```

文档里跑通后的界面是 `Hello Keels`，不是本仓库的棋盘。

## 已知限制

- **iOS SMOKE: PASSED**（tip `eaf7aed`，模拟器进入涿郡·范阳 id 1）。截图目录名是 `qa-shots/ios-shell-eaf7aed-gate`；本检出不含该目录。**Android** tip `f25f813`：程序员 Mac 冒烟 PASSED（AVD `grokdump`，涿郡·范阳 id 1，6×6），测试门禁 PASS（另一条全屏记录）。见 [android/README.md](../android/README.md)。tip `4986524` 曾 FAIL。
- v1 只加载一关。`parityEdges` 非空会拒绝加载。`stepLimit` 会写进 `LevelDef`，`PatrolGame` 不读它（和鸿蒙 `patrol.cj` 一样）。
- JSON 加载器接受这一盘用到的对象/数组/字符串/整数，以及 `\"` `\\` `\/` `\b` `\f` `\n` `\r` `\t`。不接受 `\u` 转义；范阳这盘的站名是 UTF-8 原文。
- `@C` 符号名按[仓颉-C 互操作](https://cj-docs.gitcode.com/zh/1.1.3/dev-guide/source_zh_cn/FFI/cangjie-c.html)应为未改名的 `yilu_*`。本环境没有 `nm` 可对 iOS 静态库做验证。链接失败时在 Mac 上执行 `nm -g ios/app/YiluXundian/Cangjie/libyilu_zip.a | grep yilu_`。
